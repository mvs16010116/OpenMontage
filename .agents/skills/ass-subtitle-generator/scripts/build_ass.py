# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Generate a short-line ASS subtitle file from a narration script + per-scene narration durations.

Deterministic, standalone. Reads a script artifact and an asset_manifest (or a simple
{section_id: duration_seconds} map), splits each section's text into sentence-level
short lines (max_chars per line), distributes each line's display across the section's
real narration window proportionally to character count, and writes an ASS file ready for
ffmpeg subtitle burn.

Usage:
    python build_ass.py --script <script.json> --manifest <asset_manifest.json> \
        --output <subtitles.ass> [--font-size 68] [--max-chars 16] \
        [--primary "&H00FFFFFF"] [--outline "&H00000000"] \
        [--outline-width 3] [--margin-v 55] [--alignment 2] [--font "MS YaHei"]
"""

import argparse
import json
import re
import sys


def ts(v):
    """Seconds -> ASS timestamp HH:MM:SS.CC, clamped to >= 0."""
    v = max(0.0, float(v))
    h = int(v // 3600)
    v -= h * 3600
    m = int(v // 60)
    v -= m * 60
    s = int(v)
    ms = int(round((v - s) * 100))
    if ms == 100:
        ms = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{ms:02d}"


def clean_segment(txt):
    """Strip punctuation/speech markers that would break a readable subtitle line."""
    return re.sub(
        r"[，。！？、；：,\.!\?;:\u2018\u2019\u201c\u201d\u300e\u300f\u300c\u300d\uff08\uff09()\s]+", "", txt
    ).strip()


def split_lines(text, max_chars=16):
    """Split narration text into sentence-level short lines of <= max_chars chars.

    Splits at Chinese punctuation boundaries first, then hard-splits any
    oversized chunk, and merges tiny chunks up to max_chars. Produces one line
    per subtitle event (normal subtitle display, not whole-paragraph blocks).
    """
    parts = re.split(r"(?<=[，。！？、；：])", text)
    parts = [clean_segment(p) for p in parts]
    parts = [p for p in parts if p]
    lines = []
    buf = ""
    for p in parts:
        if buf and len(buf) + len(p) <= max_chars and len(p) <= max_chars:
            buf += p
        else:
            if buf:
                lines.append(buf)
            while len(p) > max_chars:
                lines.append(p[:max_chars])
                p = p[max_chars:]
            buf = p
    if buf:
        lines.append(buf)
    return lines


def collect_durations(script, manifest):
    """Map section_id (section_01, ...) -> narration duration_seconds.

    Prefers the asset_manifest narration assets; falls back to section windows
    (end - start) on the script when no narration assets exist.
    """
    nar = {}
    for x in (manifest or {}).get("assets", []):
        if x.get("type") == "narration" and x.get("duration_seconds"):
            sid = str(x.get("scene_id", "")).replace("scene_", "")
            nar[sid.zfill(2)] = float(x["duration_seconds"])
    if nar:
        return nar
    return {
        sec["id"].replace("section_", ""): sec["end_seconds"] - sec["start_seconds"]
        for sec in (script or {}).get("sections", [])
    }


def build(script, manifest, font_size=68, max_chars=16, primary="&H00FFFFFF",
          outline="&H00000000", outline_width=3, margin_v=55, alignment=2,
          font="MS YaHei"):
    """Build the ASS content string.

    Returns (ass_text, events) — events is a list of (start, end, text) tuples
    used for verification. ASS colors MUST be in &HAABBGGRR form (libass/ffmpeg
    force_style rejects HTML hex like #FFFFFF and falls back to black text).
    """
    sections = sorted((script or {}).get("sections", []), key=lambda s: s["id"])
    nar = collect_durations(script, manifest)
    events = []
    for sec in sections:
        idx = sec["id"].replace("section_", "")
        dur = nar.get(idx)
        if dur is None:
            continue
        # FIX: 章节起点优先使用 script.start_seconds（尊重成片时间线里的
        # opener/章节卡等非旁白间隙），仅当缺失时才退回到旁白时长累加。
        start = sec.get("start_seconds")
        if start is None:
            start = sum(
                nar[s["id"].replace("section_", "")]
                for s in sections if s["id"] < sec["id"]
            )
        lines = split_lines(sec["text"], max_chars)
        total_chars = sum(len(l) for l in lines)
        t = start
        for line in lines:
            frac = len(line) / total_chars
            end = t + dur * frac
            events.append((t, end, line))
            t = end

    for i in range(1, len(events)):
        # tiny gap between consecutive events prevents frame flash
        if events[i][0] - events[i - 1][1] < 0.02:
            events[i] = (events[i - 1][1], events[i][1], events[i][2])

    dialogs = [
        f"Dialogue: 0,{ts(st)},{ts(en)},Default,,0,0,0,,{text}"
        for st, en, text in events
    ]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary},{primary},{outline},&H00000080,-1,0,0,0,100,100,0,0,1,{outline_width},1,{alignment},60,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header + "\n".join(dialogs), events


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script", required=True, help="script artifact JSON")
    ap.add_argument("--manifest", default="", help="asset_manifest JSON (for narration durations)")
    ap.add_argument("--output", required=True, help="output .ass path")
    ap.add_argument("--font-size", type=int, default=68)
    ap.add_argument("--max-chars", type=int, default=16)
    ap.add_argument("--primary", default="&H00FFFFFF")
    ap.add_argument("--outline", default="&H00000000")
    ap.add_argument("--outline-width", type=int, default=3)
    ap.add_argument("--margin-v", type=int, default=55)
    ap.add_argument("--alignment", type=int, default=2)
    ap.add_argument("--font", default="MS YaHei")
    args = ap.parse_args()

    script = json.load(open(args.script, encoding="utf-8"))
    manifest = json.load(open(args.manifest, encoding="utf-8")) if args.manifest else None

    ass_text, events = build(
        script, manifest,
        font_size=args.font_size, max_chars=args.max_chars,
        primary=args.primary, outline=args.outline,
        outline_width=args.outline_width, margin_v=args.margin_v,
        alignment=args.alignment, font=args.font,
    )

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(ass_text)

    total = events[-1][1] if events else 0.0
    print(f"{len(events)} subtitle events, font {args.font_size}, "
          f"max_chars {args.max_chars}, total {round(total, 3)}s -> {args.output}")
    for st, en, text in events[:5]:
        print(f"  {ts(st)} -> {ts(en)} | {text}")


if __name__ == "__main__":
    main()