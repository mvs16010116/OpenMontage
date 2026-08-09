"""Generate karaoke-style ASS subtitles: short cues, per-char highlight.

Reads the existing SRT, strips punctuation, splits long cues into short
segments (<= MAXLEN chars), and emits an .ass with \\k\\ karaoke tags so the
currently-spoken word lights up while the rest of the line stays white.

Burn with ffmpeg:  -vf ass=assets/karaoke.ass
"""

from __future__ import annotations

import re
from pathlib import Path

SRT_IN = Path(
    r"C:\Users\mvs20\Documents\trae\videos\OpenMontage"
    r"\projects\guofang-shikong-20260808\assets\subtitles.srt"
)
ASS_OUT = Path(
    r"C:\Users\mvs20\Documents\trae\videos\OpenMontage"
    r"\projects\guofang-shikong-20260808\assets\karaoke.ass"
)

MAXLEN = 10  # max chars per subtitle line (after all punctuation splitting)

_PUNCT = re.compile(
    r"[，。、；：？！…—\-—·‘’“”「」『』（）《》〈〉【】\[\]()!?.,:;\"'`~]"
)
_SPLIT = re.compile(r"[，。；：、！？…—…—]")

# ---- ASS constants -------------------------------------------------------
PLAY_RES_X = "1920"
PLAY_RES_Y = "1080"
STYLE = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding"
)
# Bold white text; Secondary = karaoke highlight (yellow). BGR hex.
STYLE_LINE = (
    "Style: Default,Microsoft YaHei,84,&H00FFFFFF,&H0000FFFF,"
    "&H80000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,40,60,1"
)


def _h(h, m, s, ms):
    return h * 3600 + m * 60 + s + ms / 1000.0


def _ts_ass(sec: float) -> str:
    cs = int(round(sec * 100))
    h, rem = divmod(cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, rem = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{rem:02d}"


def parse_cues(srt: str):
    for block in re.split(r"\n\s*\n", srt.strip()):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*"
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lines[1],
        )
        if not m:
            continue
        text = " ".join(lines[2:])
        if not text:
            continue
        start = _h(int(m[1]), int(m[2]), int(m[3]), int(m[4]))
        end = _h(int(m[5]), int(m[6]), int(m[7]), int(m[8]))
        yield start, end, _PUNCT.sub("", text)


def split_to_short(text: str, maxlen: int = MAXLEN) -> list[str]:
    """Split by punctuation first, then hard-wrap long leftovers."""
    chunks: list[str] = []
    rough = [c.strip() for c in _SPLIT.split(text) if c.strip()]
    for part in rough:
        while len(part) > maxlen:
            cut, part = part[:maxlen], part[maxlen:]
            chunks.append(cut)
        if part:
            chunks.append(part)
    return chunks


def main() -> None:
    cues = list(parse_cues(SRT_IN.read_text(encoding="utf-8")))

    # Flatten into short segments with proportionally-allocated time.
    segs: list[tuple[float, float, str]] = []
    for start, end, text in cues:
        parts = split_to_short(text)
        total = end - start
        total_chars = sum(len(p) for p in parts) or 1
        t = start
        for p in parts:
            d = total * len(p) / total_chars
            segs.append((t, t + d, p))
            t += d

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_RES_X}",
        f"PlayResY: {PLAY_RES_Y}",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        STYLE,
        STYLE_LINE,
        "",
        "[Events]",
        (
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text"
        ),
    ]

    for start, end, text in segs:
        if not text:
            continue
        dur = max(end - start, 0.1)
        chars = list(text)
        per_cs = max(int(round(dur * 100 / len(chars))), 1)
        body = "".join(f"{{\\k{per_cs}}}{ch}" for ch in chars)
        lines.append(
            f"Dialogue: 0,{_ts_ass(start)},{_ts_ass(end)},Default,,0,0,0,,{body}"
        )

    ASS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {ASS_OUT} with {len(segs)} karaoke segments")


if __name__ == "__main__":
    main()