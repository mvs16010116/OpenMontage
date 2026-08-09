"""Generate a typewriter-style SRT: punctuation stripped, per-char reveal.

For each original cue the text is cleaned of punctuation and re-emitted as a
progressive prefix sequence (char by char), producing a typewriter feel when
burned with FFmpeg's subtitles filter. Bold styling is applied at burn time
via force_style / ASS, not here.
"""

from __future__ import annotations

import re
from pathlib import Path

SRT_IN = Path(
    r"C:\Users\mvs20\Documents\trae\videos\OpenMontage"
    r"\projects\guofang-shikong-20260808\assets\subtitles.srt"
)
SRT_OUT = Path(
    r"C:\Users\mvs20\Documents\trae\videos\OpenMontage"
    r"\projects\guofang-shikong-20260808\assets\subtitles_typewriter.srt"
)

# Full-width + half-width punctuation to strip (not displayed).
_PUNCT = re.compile(
    r"[，。、；：？！…—\-—·‘’“”「」『』（）《》〈〉【】\[\]()!?.,:;\"'`~]"
)

# Characters that are *skipped* when counting the typewriter steps yet still
# shown silently if they survive after punctuation stripping (spaces).
_SKIP_STEP = set(" \t")


def strip_punct(text: str) -> str:
    return _PUNCT.sub("", text).rstrip()


def parse_cues(srt: str):
    blocks = re.split(r"\n\s*\n", srt.strip())
    for block in blocks:
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
        start = _h(
            int(m[1]), int(m[2]), int(m[3]), int(m[4])
        )
        end = _h(int(m[5]), int(m[6]), int(m[7]), int(m[8]))
        yield start, end, text


def _h(h, m, s, ms):
    return h * 3600 + m * 60 + s + ms / 1000.0


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, rem = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{rem:03d}"


def main() -> None:
    cues = list(parse_cues(SRT_IN.read_text(encoding="utf-8")))
    out = []
    idx = 1
    for start, end, text in cues:
        clean = strip_punct(text)
        if not clean:
            continue
        # counts a "visible" step for each non-skipped char
        visible = [c for c in clean if c not in _SKIP_STEP]
        step = max((end - start) / len(visible), 0.03)
        acc = ""
        cursor = start
        for ch in clean:
            if ch in _SKIP_STEP:
                acc += ch
                continue
            acc += ch
            t0 = cursor
            t1 = min(cursor + step, end)
            out.append(f"{idx}\n{_ts(t0)} --> {_ts(t1)}\n{acc}\n")
            idx += 1
            cursor = t1
    SRT_OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {SRT_OUT} with {idx - 1} cues")


if __name__ == "__main__":
    main()