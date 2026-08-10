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
import math
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
SHOT_DUR = 3.0               # max seconds one camera shot stays on screen

ROOT = Path(__file__).resolve().parent.parent.parent

# FIX: 字幕 100% 对齐语音 —— 用 faster-whisper 对配音做词级时间戳对齐，
# SRT/卡拉OK 全部使用真实语音时间戳，而非按字数均分估算。
WHISPER_MODEL_DIR = ROOT / ".models" / "whisper" / "faster-whisper-base"
WHISPER_MODEL_SIZE = "base"   # 备选：未找到本地模型时的自动下载档位
ASR_LANG = "zh"               # 配音语言（edge-tts 中文）

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


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def run(cmd, cwd=None):
    # FIX: 显式 UTF-8 解码，避免中文系统 locale (GBK) 解码子进程输出的中文/Unicode 字节报错
    r = subprocess.run(
        [str(c) for c in cmd], capture_output=True, text=True, cwd=cwd,
        encoding="utf-8", errors="replace",
    )
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
# 3. ASR word-level timestamps (ground truth for SRT + karaoke)
# --------------------------------------------------------------------------
def transcribe_words(audio_path: Path) -> list[dict]:
    """Run faster-whisper to get real word-level timestamps for the narration.

    Returns a list of {word, start, end}. These timestamps come from the
    actual audio, so subtitles derived from them match the voice 100%.
    """
    model_dir = WHISPER_MODEL_DIR
    if not model_dir.exists():
        raise RuntimeError(
            f"whisper model not found at {model_dir}. "
            f"Download 'Systran/faster-whisper-base' via ModelScope into "
            f"{model_dir} (config.json, model.bin, tokenizer.json, vocabulary.txt)."
        )
    from faster_whisper import WhisperModel

    model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=ASR_LANG,
        word_timestamps=True,
        vad_filter=True,
    )
    words: list[dict] = []
    for seg in segments_iter:
        if not seg.words:
            continue
        for w in seg.words:
            words.append(
                {
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                }
            )
    if not words:
        raise RuntimeError("ASR produced no word timestamps for narration audio")
    print(f"  asr words: {len(words)} (lang={info.language})")
    return words


# --------------------------------------------------------------------------
# 4. Force-align original script text to ASR word timestamps
# --------------------------------------------------------------------------
def _is_punct(ch: str) -> bool:
    return _PUNCT.fullmatch(ch) is not None


def force_align_chars(segs: list[str], words: list[dict]) -> list[dict]:
    """Align the ORIGINAL script text to the ASR word timeline.

    Returns one entry per original non-punct char:
      {"ch": char, "start": float, "end": float}

    Matching chars take the ASR anchor's real time; the few chars whisper
    mis-heard (homophones) are linearly interpolated between their nearest
    timed anchors, so the printed text is 100% correct AND timing tracks the
    real voice.
    """
    orig = "".join(_PUNCT.sub("", s) for s in segs)
    if not orig:
        raise RuntimeError("empty script after punctuation strip")

    # ASR char timeline with per-char timing
    asr_chars: list[tuple[str, float, float]] = []
    for w in words:
        clean = _PUNCT.sub("", w["word"])
        if not clean:
            continue
        d = (w["end"] - w["start"]) / max(len(clean), 1)
        t = w["start"]
        for ch in clean:
            asr_chars.append((ch, t, t + d))
            t += d
    if not asr_chars:
        raise RuntimeError("ASR produced no usable chars for alignment")

    A, B = orig, "".join(c for c, _, _ in asr_chars)
    m, n = len(A), len(B)

    # LCS DP (char-level). m,n ~ a few hundred -> fine.
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        ai = A[i]
        for j in range(n - 1, -1, -1):
            if ai == B[j]:
                row[j] = nxt[j + 1] + 1
            else:
                row[j] = nxt[j] if nxt[j] >= row[j + 1] else row[j + 1]

    # backtrace
    pairs: list[tuple[int | None, int | None]] = []
    i = j = 0
    while i < m and j < n:
        if A[i] == B[j]:
            pairs.append((i, j)); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            pairs.append((i, None)); i += 1
        else:
            pairs.append((None, j)); j += 1
    while i < m:
        pairs.append((i, None)); i += 1
    while j < n:
        pairs.append((None, j)); j += 1

    # per-orig-char anchor real (start,end) from ASR char timeline (None if unmatched)
    anchor_s = [None] * m
    anchor_e = [None] * m
    for oi, bj in pairs:
        if oi is not None and bj is not None:
            _, s, e = asr_chars[bj]
            anchor_s[oi] = s
            anchor_e[oi] = e

    # Build a monotonic per-char timeline:
    #  - matched chars keep the ASR word's real window (split evenly across the
    #    word's chars by the asr_chars entries already produced above);
    #  - unmatched chars (whisper homophone errors) are placed right after the
    #    previous char, never spanning across a word gap, and clamped so they
    #    never run past the next matched anchor's start.
    start = [0.0] * m
    end = [0.0] * m
    # first anchor if any
    first = next((i for i in range(m) if anchor_s[i] is not None), None)
    for i in range(m):
        if anchor_s[i] is not None:
            start[i] = anchor_s[i]
            end[i] = anchor_e[i]
        else:
            # clamp lower bound: after previous char
            prev_end = end[i - 1] if i > 0 else 0.0
            # clamp upper bound: before next matched anchor
            nx = i + 1
            while nx < m and anchor_s[nx] is None:
                nx += 1
            next_start = anchor_s[nx] if nx < m else prev_end + 0.5
            lo = max(prev_end, 0.0)
            hi = min(next_start, lo + 0.5)
            # stagger small increments within the allowed window
            span = max(hi - lo, 0.05)
            start[i] = lo
            end[i] = lo + span

    # Strictly monotonic sweep (backward-safe): ensure no char collapses to <=0 span
    timed: list[dict] = []
    for i in range(m):
        s = start[i]
        e = max(end[i], s + 0.05)
        if i + 1 < m and e > start[i + 1]:
            e = start[i + 1] if start[i + 1] > s else s + 0.05
        timed.append({"ch": A[i], "start": s, "end": e})
    return timed


def _merge_span(start, end):
    return max(end - start, 0.05)


def build_srt_from_chars(chars, out_path, max_chars=18):
    """Group force-aligned original chars into SRT cues.

    Cue times = real start of its first char .. real end of its last char.
    Text = exact original script wording (no ASR homophone errors).
    """
    lines = []
    idx = 1
    buf: list[dict] = []
    count = 0
    for ch in chars:
        if buf and count >= max_chars:
            s = buf[0]["start"]
            e = buf[-1]["end"]
            cue = "".join(x["ch"] for x in buf)
            lines.append(f"{idx}\n{ts(s)} --> {ts(e)}\n{cue}\n")
            idx += 1
            buf, count = [], 0
        buf.append(ch)
        count += 1
    if buf:
        s = buf[0]["start"]
        e = buf[-1]["end"]
        cue = "".join(x["ch"] for x in buf)
        lines.append(f"{idx}\n{ts(s)} --> {ts(e)}\n{cue}\n")
        idx += 1
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return idx - 1


# --------------------------------------------------------------------------
# 5. static ASS subtitle (plain whole-line, no karaoke highlight)
# --------------------------------------------------------------------------
def build_static_ass_from_chars(chars, ass_path, font_size=FONT_SIZE, max_chars=18):
    """Plain subtitle ASS: whole lines shown at once, no karaoke highlight.

    Each line's time window comes from force alignment (first char's real
    start .. last char's real end), so text and timing both match the voice.
    """
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,MS YaHei,{font_size},&H00FFFFFF,&H00FFFFFF,"
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
    line: list[dict] = []
    for ch in chars:
        if line and len(line) >= max_chars:
            s = line[0]["start"]
            e = line[-1]["end"]
            body = "".join(c["ch"] for c in line)
            events.append(f"Dialogue: 0,{_tsass(s)},{_tsass(e)},Default,,0,0,0,,{body}")
            line = []
        line.append(ch)
    if line:
        s = line[0]["start"]
        e = line[-1]["end"]
        body = "".join(c["ch"] for c in line)
        events.append(f"Dialogue: 0,{_tsass(s)},{_tsass(e)},Default,,0,0,0,,{body}")
    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return len(events)


# --------------------------------------------------------------------------
# 5. Pexels fetch (distinct clips per scene, no loop)
# --------------------------------------------------------------------------
# Query variants used to widen the pool when a scene needs many shots, so we
# pull different videos instead of re-cutting the same one.
_QUERY_VARIANTS = [
    "", " aerial", " cinematic", " close up", " motion", " slow motion",
    " night", " background", " wide shot", " detail",
]


def fetch_scenes(queries, seg_durs, out_dir, shot_dur=SHOT_DUR):
    sys.path.insert(0, str(ROOT))
    from tools.tool_registry import registry

    registry.discover()
    tool = registry.get("pexels_video")
    if tool is None:
        raise RuntimeError("pexels_video not available (PEXELS_API_KEY?)")

    seen: set[str] = set()
    per_scene: dict[int, list[str]] = {}
    for si, dur in enumerate(seg_durs, 1):
        per_scene[si] = []
        base = queries[si - 1] if si - 1 < len(queries) else []
        if not base:
            base = ["military", "army", "national flag", "world map"]
        cdir = out_dir / f"scene{si}"
        cdir.mkdir(parents=True, exist_ok=True)

        # manifest keeps video_id per downloaded clip so cache reuse dedups too
        manifest_path = cdir / "manifest.json"
        manifest: dict[str, str] = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        seen.update(manifest.values())

        need = math.ceil(dur / shot_dur) + 3  # distinct clips, incl. short ones
        # Build a candidate list by expanding every keyword with variants and
        # a couple of result pages — enough room to find `need` unique videos.
        cands = []
        for b in base:
            for v in _QUERY_VARIANTS:
                for pg in (1, 2, 3):
                    cands.append((f"{b}{v}".strip(), pg))

        collected = 0
        for qi, (q, pg) in enumerate(cands, 1):
            if collected >= need:
                break
            dst = cdir / f"clip{qi}.mp4"
            if dst.exists():
                # cached clip: skip if its video_id duplicates an already-used one
                vid = manifest.get(dst.name)
                if vid is not None and vid in seen:
                    continue
                per_scene[si].append(str(dst))
                collected += 1
                continue
            resp = tool.execute({
                "query": q, "page": pg, "per_page": 5, "orientation": "landscape",
                "preferred_quality": "hd", "output_path": str(dst),
            })
            if not resp.success:
                print(f"  scene{si} fail '{q}' p{pg}: {resp.error}")
                continue
            vid = resp.data.get("video_id")
            if vid in seen:
                dst.unlink(missing_ok=True)
                continue
            seen.add(vid)
            manifest[dst.name] = vid
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            per_scene[si].append(str(dst))
            collected += 1
        if collected < need:
            print(f"  WARN scene{si}: only {collected} unique clips, need {need}")
    return per_scene


# --------------------------------------------------------------------------
# 6. assemble per scene (no loop) into silent master
# --------------------------------------------------------------------------
VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
      "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")


def assemble_scenes(per_scene, seg_durs, work, master, shot_dur=SHOT_DUR):
    master_total = []
    for si, dur in enumerate(seg_durs, 1):
        clips = per_scene.get(si, [])
        if not clips:
            raise RuntimeError(f"scene{si} has no clips")
        need = math.ceil(dur / shot_dur)
        if len(clips) < need:
            raise RuntimeError(
                f"scene{si} needs {need} distinct clips for {dur:.1f}s @ {shot_dur}s "
                f"but only {len(clips)} fetched — add more query keywords")
        # One full shot per clip; clips shorter than a shot are skipped so we
        # never flash-cut a too-short piece.
        acc = 0.0
        pieces = []
        k = 0
        for cl in clips:
            if acc >= dur - 0.05:
                break
            clip_dur = ffprobe_dur(cl)
            if clip_dur < shot_dur - 0.1:
                continue
            off = (k * shot_dur) % max(clip_dur - shot_dur, 0.01)
            take = min(shot_dur, dur - acc)
            p = work / f"s{si}_shot{k}.mp4"
            run(["ffmpeg", "-y", "-ss", f"{off:.3f}", "-i", cl, "-t", f"{take:.3f}",
                 "-vf", VF, "-an", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "22", "-pix_fmt", "yuv420p", str(p)])
            pieces.append(p)
            acc += take
            k += 1
            if k > 1000:
                break
        if acc < dur - 0.05:
            raise RuntimeError(
                f"scene{si} assembled {acc:.1f}s < needed {dur:.1f}s "
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
    ap.add_argument("--shot-dur", type=float, default=SHOT_DUR,
                    help="max seconds per camera shot before switching")
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

    print("=== 3. ASR 词级时间戳 -> 强制对齐 -> SRT + 静态字幕 ===")
    # FIX: 先对配音做 whisper 词级对齐，再把原文脚本强制对齐到真实语音时间戳，
    # 保证字幕文字与原文 100% 一致、字幕时间与语音 100% 同步。
    words = transcribe_words(narration)
    chars = force_align_chars(segs, words)
    print(f"  aligned chars: {len(chars)}")
    srt = assets / "subtitles.srt"
    ncues = build_srt_from_chars(chars, srt)
    print(f"srt: {ncues} cues (force-aligned to speech)")
    ass = assets / "subtitles.ass"
    nevents = build_static_ass_from_chars(chars, ass, font_size=args.font_size)
    print(f"ass: {nevents} lines (font={args.font_size}, static, force-aligned)")

    print("=== 4. Pexels 素材采集（互异、无循环） ===")
    queries = None
    if args.queries and Path(args.queries).exists():
        queries = json.loads(Path(args.queries).read_text(encoding="utf-8")).get("scenes")
    scenes = fetch_scenes(queries or DEFAULT_SCENES, durs, assets / "video",
                          shot_dur=args.shot_dur)
    for si, paths in scenes.items():
        print(f"  scene{si}: {len(paths)} clips")

    print("=== 5. 场景拼接（无重复） ===")
    assemble_scenes(scenes, durs, work, assets / "video" / "planA_visuals.mp4",
                    shot_dur=args.shot_dur)
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