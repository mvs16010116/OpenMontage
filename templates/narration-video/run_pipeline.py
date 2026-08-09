# -*- coding: utf-8 -*-
"""Narration → Video pipeline template for OpenMontage.

Usage:
  python templates/narration-video/run_pipeline.py \
      --text templates/narration-video/input/script.txt \
      --queries templates/narration-video/input/queries.json \
      --title "我的新视频"

Produces: projects/<title>/renders/final.mp4
Pipeline: split -> TTS(edge-tts) -> SRT -> karaoke ASS -> Pexels fetch
          -> assemble (no-loop) -> subtitle burn + audio mux.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Config (tweak here)
# --------------------------------------------------------------------------
VOICE = "zh-CN-YunxiNeural"  # male Mandarin voice (edge-tts)
FONT_SIZE = 84               # karaoke subtitle font size (big, senior-friendly)
MAXLEN = 10                  # max chars per karaoke subtitle line
FPS = 30
W, H = 1920, 1080
CRF = 21

ROOT = Path(__file__).resolve().parent.parent.parent

# Default per-scene Pexels keyword sets when queries.json is missing.
DEFAULT_SCENES = [
    ["news studio broadcast", "television news studio camera"],
    ["military tank convoy", "armored vehicle military"],
    ["military night exercise shooting", "army night operation"],
    ["world map pins strategy", "satellite earth globe"],
    ["flag waving sky", "national flag wind"],
]

_PUNCT = re.compile(
    r"[，。、；：？！…—\-—·‘’“”「」『』（）《》〈〉【】\[\]()!?.,:;\"'`~]"
)
_SPLIT = re.compile(r"[，。；：、！？…—]")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(
            f"cmd failed: {' '.join(str(c) for c in cmd)}\n{r.stderr[-1200:]}"
        )
    return r.stdout.strip()


def ffprobe_dur(path) -> float:
    out = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)]
    )
    return float(out.splitlines()[0])


def ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, rem = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{rem:03d}"


# --------------------------------------------------------------------------
# 1. script -> segments
# --------------------------------------------------------------------------
def parse_segments(text: str) -> list[str]:
    if "###SEG" in text:
        blocks = re.split(r"###SEG\d+###", text)
    else:
        blocks = re.split(r"\n\s*\n", text)
    segs = [b.strip() for b in blocks if b.strip()]
    return segs or [text.strip()]


# --------------------------------------------------------------------------
# 2. TTS
# --------------------------------------------------------------------------
async def _tts_one(idx, text, out_dir, voice):
    out = out_dir / f"seg{idx}.mp3"
    if out.exists() and out.stat().st_size > 1000:
        return
    last_err = ""
    for attempt in range(4):
        try:
            import edge_tts
            c = edge_tts.Communicate(text, voice)
            await c.save(str(out))
            return
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            print(f"  seg{idx} attempt {attempt + 1} failed: {last_err}", flush=True)
            if out.exists():
                out.unlink()
            await asyncio.sleep(8 + attempt * 8)
    raise RuntimeError(f"TTS seg{idx} failed after retries: {last_err}")


def generate_tts(segs, out_dir, voice=VOICE):
    async def go():
        for i, s in enumerate(segs, 1):
            await _tts_one(i, s, out_dir, voice)
    asyncio.run(go())
    # concat into narration_full.mp3
    full = out_dir / "narration_full.mp3"
    lst = out_dir / "concat.txt"
    lst.write_text(
        "".join(f"file '{ (out_dir / f'seg{i}.mp3').as_posix() }'\n"
                for i in range(1, len(segs) + 1)),
        encoding="utf-8",
    )
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(full)])
    return full


# --------------------------------------------------------------------------
# 3. SRT (auto sub-cues per segment by sentence)
# --------------------------------------------------------------------------
def split_sentences(text_chunk, max_chars=18):
    text = text_chunk.strip()
    if not text:
        return []
    out = []
    while len(text) > max_chars:
        cut = text.rfind("，", 0, max_chars)
        cut = cut if cut > 0 else max_chars
        out.append(text[:cut].strip() or text[:max_chars])
        text = text[cut:].strip()
    if text:
        out.append(text)
    return out


def build_srt(segs, durs, out_path):
    offsets = []
    t = 0.0
    for d in durs:
        offsets.append(t)
        t += d
    lines = []
    idx = 1
    for i, (b, start, dur) in enumerate(zip(segs, offsets, durs)):
        clean_text = _PUNCT.sub(" ", b)
        clean_text = re.sub(r"\s+", "", clean_text)
        cues = split_sentences(clean_text)
        each = (dur if dur > 0 else 0.1) / max(len(cues), 1)
        for j, cue in enumerate(cues):
            s = start + j * each
            e = start + (j + 1) * each
            lines.append(f"{idx}\n{ts(s)} --> {ts(e)}\n{cue}\n")
            idx += 1
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return idx - 1


# --------------------------------------------------------------------------
# 4. karaoke ASS
# --------------------------------------------------------------------------
def build_karaoke_ass(srt_path, ass_path, font_size=FONT_SIZE, maxlen=MAXLEN):
    import re as _re
    cues = []
    for block in _re.split(r"\n\s*\n", srt_path.read_text(encoding="utf-8").strip()):
        lns = [x.rstrip() for x in block.splitlines() if x.strip()]
        if len(lns) < 2:
            continue
        m = _re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lns[1],
        )
        if not m:
            continue
        text = " ".join(lns[2:])
        if not text:
            continue
        start = (
            int(m.group(1)) * 3600 + int(m.group(2)) * 60
            + int(m.group(3)) + int(m.group(4)) / 1000
        )
        end = (
            int(m.group(5)) * 3600 + int(m.group(6)) * 60
            + int(m.group(7)) + int(m.group(8)) / 1000
        )
        cues.append((start, end, text))

    segs = [(s, e, _PUNCT.sub("", t)) for (s, e, t) in cues]
    flat = []
    for s, e, text in segs:
        parts = []
        for chunk in [c.strip() for c in _SPLIT.split(text) if c.strip()]:
            while len(chunk) > maxlen:
                parts.append(chunk[:maxlen])
                chunk = chunk[maxlen:]
            if chunk:
                parts.append(chunk)
        total = e - s
        chars = sum(len(p) for p in parts)
        t = s
        for p in parts:
            d = total * len(p) / max(chars, 1)
            flat.append((t, t + d, p))
            t += d

    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,MS YaHei,{font_size},&H00FFFFFF,&H0000FFFF,"
        "&H80000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,40,40,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    def _tsass(sec):
        cs = int(round(sec * 100))
        h, rem = divmod(cs, 360_000)
        m, rem = divmod(rem, 6_000)
        s, rem = divmod(rem, 100)
        return f"{h}:{m:02d}:{s:02d}.{rem:02d}"

    events = []
    for s, e, text in flat:
        if not text:
            continue
        dur = max(e - s, 0.1)
        per = max(int(round(dur * 100 / len(text))), 1)
        body = "".join(r"{\k%d}%s" % (per, ch) for ch in text)
        events.append(f"Dialogue: 0,{_tsass(s)},{_tsass(e)},Default,,0,0,0,,{body}")
    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return len(events)


# --------------------------------------------------------------------------
# 5. Pexels fetch (distinct clips per scene, no loop)
# --------------------------------------------------------------------------
def fetch_scenes(queries, out_dir, n_scenes):
    sys.path.insert(0, str(ROOT))
    from tools.tool_registry import registry

    registry.discover()
    tool = registry.get("pexels_video")
    if tool is None:
        raise RuntimeError("pexels_video not available (PEXELS_API_KEY?)")

    seen: set[str] = set()
    per_scene: dict[int, list[str]] = {}
    for si in range(n_scenes):
        per_scene[si + 1] = []
        qs = queries[si] if si < len(queries) else []
        if not qs:
            qs = ["military", "army", "national flag", "world map"]
        cdir = out_dir / f"scene{si+1}"
        cdir.mkdir(parents=True, exist_ok=True)
        for qi, q in enumerate(qs, 1):
            dst = cdir / f"clip{qi}.mp4"
            if dst.exists():
                per_scene[si + 1].append(str(dst))
                continue
            resp = tool.execute({
                "query": q, "page": 1, "per_page": 5, "orientation": "landscape",
                "preferred_quality": "hd", "output_path": str(dst),
            })
            if not resp.success:
                print(f"  scene{si+1} fail '{q}': {resp.error}")
                continue
            vid = resp.data.get("video_id")
            if vid in seen:
                dst.unlink(missing_ok=True)
                continue
            seen.add(vid)
            per_scene[si + 1].append(str(dst))
    return per_scene


# --------------------------------------------------------------------------
# 6. assemble per scene (no loop) into silent master
# --------------------------------------------------------------------------
VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
      "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")


def assemble_scenes(per_scene, seg_durs, work, master):
    pieces_total = []
    for si, dur in enumerate(seg_durs, 1):
        clips = per_scene.get(si, [])
        if not clips:
            raise RuntimeError(f"scene{si} has no clips")
        # take a unique time-window per clip; never reuse a clip
        acc = 0.0
        pieces = []
        for i, cl in enumerate(clips):
            if acc >= dur:
                break
            clip_dur = ffprobe_dur(cl)
            take = min(clip_dur, dur - acc)
            p = work / f"s{si}_c{i}.mp4"
            run(["ffmpeg", "-y", "-ss", "0", "-i", cl, "-t", f"{take:.3f}",
                 "-vf", VF, "-an", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "22", "-pix_fmt", "yuv420p", str(p)])
            pieces.append(p)
            acc += take
        if acc < dur - 0.05:
            raise RuntimeError(
                f"scene{si} clips sum {acc:.1f}s < needed {dur:.1f}s "
                f"({len(clips)} clips) — add more query keywords")
        le = work / f"scene{si}.txt"
        le.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8"
        )
        flat = work / f"scene{si}_flat.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(le),
             "-c", "copy", str(flat)])
        master_total.append(flat)
    lst = work / "all.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in master_total), encoding="utf-8"
    )
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(master)])


master_total: list = []


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="path to 文案 txt")
    ap.add_argument("--queries", default="", help="path to queries.json")
    ap.add_argument("--title", default="narrated-video")
    ap.add_argument("--max-chars", type=int, default=MAXLEN)
    ap.add_argument("--font-size", type=int, default=FONT_SIZE)
    args = ap.parse_args()

    title = re.sub(r"[\\/:*?\"<>|]", "-", args.title.strip()) or "narrated-video"
    proj = ROOT / "projects" / title
    assets = proj / "assets"
    (assets / "audio").mkdir(parents=True, exist_ok=True)
    (assets / "video").mkdir(parents=True, exist_ok=True)
    (proj / "renders").mkdir(parents=True, exist_ok=True)
    work = assets / "work"
    work.mkdir(parents=True, exist_ok=True)

    print("=== 1. 读取文案 ===")
    segs = parse_segments(Path(args.text).read_text(encoding="utf-8"))
    print(f"segments: {len(segs)}")

    print("=== 2. 配音 edge-tts ===")
    narration = generate_tts(segs, assets / "audio")
    durs = [ffprobe_dur(assets / "audio" / f"seg{i}.mp3") for i in range(1, len(segs) + 1)]
    print(f"durations: {[round(d,2) for d in durs]} total={sum(durs):.2f}s")

    print("=== 3. SRT + 卡拉OK 字幕 ===")
    srt = assets / "subtitles.srt"
    ncues = build_srt(segs, durs, srt)
    print(f"srt: {ncues} cues")
    ass = assets / "karaoke.ass"
    nevents = build_karaoke_ass(srt, ass, font_size=args.font_size, maxlen=args.max_chars)
    print(f"karaoke: {nevents} events (font={args.font_size})")

    print("=== 4. Pexels 素材采集（互异、无循环） ===")
    queries = None
    if args.queries and Path(args.queries).exists():
        queries = json.loads(Path(args.queries).read_text(encoding="utf-8")).get("scenes")
    scenes = fetch_scenes(queries or DEFAULT_SCENES, assets / "video", len(segs))
    for si, paths in scenes.items():
        print(f"  scene{si}: {len(paths)} clips")

    print("=== 5. 场景拼接（无重复） ===")
    assemble_scenes(scenes, durs, work, assets / "video" / "planA_visuals.mp4")
    master = assets / "video" / "planA_visuals.mp4"
    print(f"master: {ffprobe_dur(master):.2f}s")

    print("=== 6. 合成 final ===")
    final = proj / "renders" / "final.mp4"
    run(["ffmpeg", "-y", "-i", str(master), "-i", str(narration),
         "-vf", f"ass={ass.name}", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF),
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
        cwd=str(assets))
    print(f"DONE -> {final} ({ffprobe_dur(final):.2f}s)")


if __name__ == "__main__":
    main()