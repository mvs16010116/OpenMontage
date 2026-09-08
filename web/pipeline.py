# -*- coding: utf-8 -*-
"""narration-synth pipeline core: narration_text -> project dir -> final.mp4.

Decoupled from FastAPI. `run_pipeline(task_id, narration_text, progress)`
drives the 6 steps and returns the absolute path to the rendered `final.mp4`.

The generated project mirrors the CLI narration-synth layout under
``projects/<slug>/``:
    artifacts/script.json           timed section windows
    artifacts/pexels_manifest.json  per-section keyword<->photo audit trail
    assets/audio/narration_section_0X.mp3
    assets/images/section_0X/*.jpg
    assets/video/section_0X.mp4     (hyperframes-rendered scene)
    assets/subtitles.ass
    renders/final.mp4

Everything downstream of TTS/Pexels is local (Node + ffmpeg). This module is
pure Python — no FastAPI dependency — so it can be unit-tested on its own.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"

ACCENT = "#fbbf24"
FONT_SIZE = 80
OUTLINE_WIDTH = 5
MARGIN_V = 90
FPS = 30
SCENE_IMAGES = 3
CHAR_PER_SEC = 4.0  # Chinese narration pace chars/second used to pre-slice windows

# ---------------------------------------------------------------------------
# tiny English keyword dictionary for Pexels search extraction.
# Keys are Chinese substrings matched inside a section; value = Pexels query.
# ---------------------------------------------------------------------------
KEYWORD_MAP = [
    ("霍尔木兹海峡", "Hormuz strait tanker sea"),
    ("油轮", "oil tanker cargo ship sea"),
    ("海峡", "strait ocean shipping lane"),
    ("石油", "crude oil barrels refinery"),
    ("美国海军", "US Navy warship fleet"),
    ("海军", "navy warship destroyer"),
    ("导弹", "missile launch military"),
    ("伊朗", "Iran middle east flag"),
    ("中东", "middle east desert"),
    ("航母", "aircraft carrier navy sea"),
    ("战舰", "warship ocean fleet"),
    ("军队", "soldiers military formation"),
    ("战争", "battlefield war"),
    ("雷达", "military radar antenna"),
    ("基地", "military base hangar"),
    ("港口", "port container ship dock"),
    ("制裁", "sanctions documents"),
    ("军队部署", "military deployment convoy"),
    ("防空阵地", "air defense system military"),
]


def _slugify(text: str) -> str:
    """ASCII-safe project slug derived from the narration head.

    CJK chars are stripped (not transliterated) to keep filesystem paths and
    the `npx hyperframes render` CLI guaranteed ASCII. The ``task_id`` suffix
    (appended by the caller) provides uniqueness.
    """
    keep = [c for c in text if c.isascii() and (c.isalnum() or c in "-_")]
    slug = "".join(keep).strip("-") or "narration"
    return slug[:20]


def _run(cmd: list[str], cwd: Path, *, timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, errors="replace",
        timeout=timeout,
    )


def _windows_cmd(cmd: list[str], cwd: Path, *, timeout: int | None = None) -> subprocess.CompletedProcess:
    """Resolve .cmd/.bat wrappers (npx) on Windows without shell=True."""
    import shutil
    resolved = list(cmd)
    if os.name == "nt" and resolved:
        exe = shutil.which(resolved[0])
        if exe:
            resolved[0] = exe
    return subprocess.run(
        resolved, cwd=str(cwd), capture_output=True, text=True, errors="replace",
        timeout=timeout,
    )


def _load_env() -> None:
    """Load .env key names into os.environ if not already set (no overwrite)."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def parse_script(text: str, title: str) -> dict:
    """Split narration into sections and assign estimated time windows.

    Sections split at sentence-final punctuation (。！？；). Each section's
    duration is estimated from char count / CHAR_PER_SEC. Windows are stacked
    back-to-back from t=0 (opener card is folded into section_01).
    """
    parts = re.split(r"(?<=[。！？；])", text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [text.strip()]
    sections = []
    cursor = 0.0
    for i, p in enumerate(parts, start=1):
        dur = max(4.0, len(p) / CHAR_PER_SEC)
        sections.append({
            "id": f"section_{i:02d}",
            "text": p,
            "start_seconds": round(cursor, 2),
            "end_seconds": round(cursor + dur, 2),
        })
        cursor += dur
    return {
        "version": "1.0",
        "title": title,
        "sections": sections,
        "total_duration_seconds": round(cursor, 2),
    }


def derive_keyword(section_text: str) -> tuple[str, bool]:
    """Return (english_query, usable). Fallback to empty/False for dark card."""
    for cn, en in KEYWORD_MAP:
        if cn in section_text:
            return en, True
    return "", False


def _ensure_project(project_dir: Path) -> None:
    for sub in ("artifacts", "assets/audio", "assets/images", "assets/video",
                "renders", "hyperframes"):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)


TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+0%"
TTS_PAUSE_GAP = 0.6  # seconds of silence tail added per segment for breathing room


def _probe_audio_duration(path: Path) -> float:
    """Duration in seconds of an audio file via ffprobe."""
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=noprint_wrappers=1:nokey=1", str(path)], REPO_ROOT)
    if r.returncode != 0:
        return 0.0
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _synthesize_edge(path: Path, text: str, voice: str = TTS_VOICE) -> float:
    """Synthesize `text` to `path` as MP3 via free local edge-tts.

    Returns the resulting audio duration in seconds. Network is only hit by
    edge-tts for the stream; no API key required.
    """
    import asyncio
    import edge_tts

    def _run() -> None:
        async def _inner() -> None:
            communicate = edge_tts.Communicate(text, voice=voice, rate=TTS_RATE)
            await communicate.save(str(path))
        asyncio.run(_inner())

    try:
        # smallest available loop; retry once for transient network failures
        try:
            _run()
        except Exception:
            _run()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Edge TTS synthesis failed for '{text[:20]}...': {exc}")
    return _probe_audio_duration(path)


def step_tts(script: dict, project_dir: Path, voice: str | None = None) -> dict:
    """Generate one MP3 per section via local Edge TTS.

    Returns narration assets incl. the real (probed) duration of each segment,
    which the caller uses to rebuild scene/subtitle windows from actual speech
    timing instead of the initial estimate.
    """
    voice = voice or TTS_VOICE
    narration_assets = []
    for sec in script["sections"]:
        idx = sec["id"].replace("section_", "")
        out = project_dir / "assets" / "audio" / f"narration_section_{idx}.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = _synthesize_edge(out, sec["text"], voice=voice)
        if duration <= 0:
            raise RuntimeError(f"Edge TTS produced empty audio for {sec['id']}")
        narration_assets.append({
            "scene_id": f"scene_{idx}", "type": "narration",
            "duration_seconds": round(duration, 2), "output": str(out),
        })
    return {"assets": narration_assets}


def rewindow_script(script: dict, narration_assets: dict) -> dict:
    """Rebuild section start/end windows from REAL narration durations.

    Sections are back-to-back from t=0 with a fixed breathing gap between them.
    This keeps the concatenated scene timeline in sync with the narration.
    """
    dur_by_idx = {
        str(a["scene_id"]).replace("scene_", ""): a["duration_seconds"]
        for a in narration_assets["assets"]
    }
    cursor = 0.0
    for sec in script["sections"]:
        idx = sec["id"].replace("section_", "")
        dur = dur_by_idx.get(idx)
        if dur is None or dur <= 0:
            dur = max(3.0, sec["end_seconds"] - sec["start_seconds"])
        sec["start_seconds"] = round(cursor, 2)
        sec["end_seconds"] = round(cursor + dur + TTS_PAUSE_GAP, 2)
        cursor += dur + TTS_PAUSE_GAP
    # drop a trailing pause after the last section
    last = script["sections"][-1]
    last["end_seconds"] = round(last["start_seconds"] + (last["end_seconds"] - last["start_seconds"]) - TTS_PAUSE_GAP, 2)
    script["total_duration_seconds"] = round(cursor - TTS_PAUSE_GAP, 2)
    return script


def step_images(script: dict, project_dir: Path) -> list:
    """Fetch Pexels images per section where a keyword maps; else empty list."""
    _load_env()
    from tools.graphics.pexels_image import PexelsImage
    tool = PexelsImage()
    manifest = []
    for sec in script["sections"]:
        idx = sec["id"].replace("section_", "")
        query, usable = derive_keyword(sec["text"])
        entry = {
            "section_id": sec["id"],
            "query": query,
            "usable": usable,
            "photos": [],
        }
        if usable:
            out_dir = project_dir / "assets" / "images" / sec["id"]
            res = tool.execute({
                "query": query,
                "output_dir": str(out_dir),
                "count": SCENE_IMAGES,
            })
            if res.success and res.data.get("candidates"):
                entry["photos"] = res.data["candidates"]
        manifest.append(entry)
    meta = project_dir / "artifacts" / "pexels_manifest.json"
    meta.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def step_render_scenes(script: dict, manifest: list, project_dir: Path) -> list[str]:
    """Render one HyperFrames scene MP4 per section via photo-carousel builder."""
    node = os.environ.get("NODE", "node")
    video_paths = []
    for sec, m in script_sections_zip(script, manifest):
        idx = sec["id"].replace("section_", "")
        out = project_dir / "assets" / "video" / f"{sec['id']}.mp4"
        duration = max(3.0, sec["end_seconds"] - sec["start_seconds"])
        image_names = []
        for p in (m["photos"] or []):
            out = p.get("output") if isinstance(p, dict) else p
            if out:
                image_names.append(Path(out).name)
        args = [
            node, str(REPO_ROOT / ".agents/skills/military-photo-carousel/scripts/build_photo_carousel.mjs"),
            "--project", project_dir.name,
            "--slug", sec["id"],
            "--title", (sec["text"][:14] or "口播视频"),
            "--keyword", (sec["text"][:8] if m["usable"] else ""),
            "--duration", f"{duration:.1f}",
            "--accent", ACCENT,
        ]
        if image_names:
            # builder resolves projects/<proj>/<path>; images live under
            # assets/images/<section_id>/<photo>.jpg
            args += ["--images", ";".join(
                f"assets/images/{sec['id']}/{n}" for n in image_names)]
        else:
            args.append("--no-carousel")
        r = _run(args, REPO_ROOT)
        if r.returncode != 0:
            raise RuntimeError(f"carousel build failed: {r.stderr[-500:]}")
        # render via hyperframes CLI (headless local)
        render_cmd = [
            "npx", "hyperframes", "render",
            f"projects/{project_dir.name}/hyperframes",
            "-o", f"projects/{project_dir.name}/assets/video/{sec['id']}.mp4",
            "--fps", str(FPS), "-q", "standard", "--workers", "1", "--quiet",
        ]
        rr = _windows_cmd(render_cmd, REPO_ROOT, timeout=600)
        if rr.returncode != 0:
            raise RuntimeError(f"hyperframes render failed: {rr.stderr[-500:]}")
        video_paths.append(str(out))
    return video_paths


def script_sections_zip(script: dict, manifest: list):
    by_id = {m["section_id"]: m for m in manifest}
    for sec in script["sections"]:
        yield sec, by_id.get(sec["id"], {"usable": False, "photos": []})


def step_subtitles(script: dict, narration_assets: dict, project_dir: Path) -> str:
    """Generate subtitles.ass via the ass-subtitle-generator build_ass.py."""
    manifest_path = project_dir / "artifacts" / "_narration_manifest.json"
    manifest_path.write_text(
        json.dumps(narration_assets, ensure_ascii=False, indent=2), encoding="utf-8")
    script_path = project_dir / "artifacts" / "script.json"
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    out = project_dir / "assets" / "subtitles.ass"
    py = sys.executable or "python"
    r = _run([
        py, str(REPO_ROOT / ".agents/skills/ass-subtitle-generator/scripts/build_ass.py"),
        f"--script={script_path}", f"--manifest={manifest_path}", f"--output={out}",
        f"--font-size={FONT_SIZE}", f"--outline-width={OUTLINE_WIDTH}",
        f"--margin-v={MARGIN_V}", "--max-chars=16",
    ], REPO_ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"build_ass failed: {r.stderr[-500:]}")
    return str(out)


def _concat_and_assemble(script: dict, project_dir: Path) -> str:
    """concat scenes -> silent base -> burn subtitles -> mux narration mix."""
    import shutil
    video_dir = project_dir / "assets" / "video"
    sections = sorted(script["sections"], key=lambda s: s["id"])
    concat_txt = project_dir / "renders" / ".compose_tmp" / "concat.txt"
    concat_txt.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for sec in sections:
        vp = video_dir / f"{sec['id']}.mp4"
        if not vp.is_file():
            raise RuntimeError(f"missing scene {vp}")
        lines.append(f"file '{vp.as_posix()}'")
    concat_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    base = project_dir / "renders" / ".compose_tmp" / "_base_silent.mp4"
    master = project_dir / "renders" / ".compose_tmp" / "_video_master.mp4"
    sub = project_dir / "assets" / "subtitles.ass"
    subwin = sub.as_posix().replace(":", "\\:")
    force = (
        "subtitles='%s':force_style='FontName=MS YaHei,FontSize=%d,Bold=0,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
        "Outline=%d,Shadow=0,MarginV=%d,Alignment=2'"
        % (subwin, FONT_SIZE, OUTLINE_WIDTH, MARGIN_V)
    )

    def ff(args):
        return _run(["ffmpeg", "-y", "-loglevel", "error", *args], project_dir)

    r = ff(["-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(base)])
    if r.returncode != 0:
        raise RuntimeError(f"concat failed: {r.stderr[-400:]}")
    r = ff(["-i", str(base), "-vf", force, "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(master)])
    if r.returncode != 0:
        raise RuntimeError(f"burn failed: {r.stderr[-400:]}")

    # narration: adelay each segment to its section start, then amix (apad after)
    audio_inputs = [project_dir / "assets" / "audio" / f"narration_{sec['id']}.mp3"
                    for sec in sections]
    mix = project_dir / "renders" / ".compose_tmp" / "narration_mix.m4a"
    adelay_labels = []
    for i, sec in enumerate(sections):
        ms = int(sec["start_seconds"] * 1000)
        adelay_labels.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    amix_ins = "".join(f"[a{i}]" for i in range(len(sections)))
    filter_complex = (";".join(adelay_labels) + f";{amix_ins}"
                      f"amix=inputs={len(sections)}:normalize=0,apad=pad_dur=10")
    rmix = _run([
        "ffmpeg", "-y", "-loglevel", "error",
        *[arg for i, x in enumerate(audio_inputs) for arg in ("-i", str(x))],
        "-filter_complex", filter_complex,
        "-ac", "2", "-c:a", "aac", str(mix),
    ], project_dir)
    if rmix.returncode != 0:
        raise RuntimeError(f"narration mix failed: {rmix.stderr[-400:]}")

    final = project_dir / "renders" / "final.mp4"
    r = ff(["-i", str(master), "-i", str(mix), "-c:v", "copy", "-c:a", "aac",
            "-shortest", str(final)])
    if r.returncode != 0:
        raise RuntimeError(f"final mux failed: {r.stderr[-400:]}")
    return str(final)


def run_pipeline(task_id: str, narration_text: str, progress=None) -> str:
    """Full pipeline. Returns absolute path to final.mp4."""
    def emit(stage, message=""):
        if progress:
            progress(stage, message)

    title = narration_text.strip().replace("\n", " ")[:40] or "口播视频"
    slug = f"{_slugify(title)}-{task_id}"
    project_dir = PROJECTS_DIR / slug
    _ensure_project(project_dir)

    emit("parse_script", "正在分节…")
    script = parse_script(narration_text, title)

    emit("generating_tts", "正在生成配音…")
    narration_assets = step_tts(script, project_dir)  # local Edge TTS, no key
    # rebuild section windows from REAL narration durations so scenes &
    # subtitles stay in sync with the actual speech timing
    script = rewindow_script(script, narration_assets)
    (project_dir / "artifacts" / "script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    emit("fetching_images", "正在检索配图…")
    manifest = step_images(script, project_dir)

    emit("rendering_scenes", "正在渲染画面…")
    step_render_scenes(script, manifest, project_dir)

    emit("subtitles", "正在生成字幕…")
    step_subtitles(script, narration_assets, project_dir)

    emit("assembling", "正在合成成片…")
    final = _concat_and_assemble(script, project_dir)

    emit("done", "生成完成")
    return final


if __name__ == "__main__":
    # python -m web.pipeline --text "..." --task-id demo
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--task-id", default="local")
    a = ap.parse_args()
    def p(stage, msg): print(f"[{stage}] {msg}", flush=True)
    out = run_pipeline(a.task_id, a.text, progress=p)
    print("RESULT", out)
