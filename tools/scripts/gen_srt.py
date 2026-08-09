# -*- coding: utf-8 -*-
import re, pathlib, subprocess, json

BASE = pathlib.Path(r"projects/guofang-shikong-20260808")
AUDIO = BASE / "assets" / "audio"
SRC = BASE / "assets" / "narration_copy.txt"

def dur_of(i):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(AUDIO / f"seg{i}.mp3")],
        capture_output=True, text=True)
    return float(r.stdout.strip())

text = SRC.read_text(encoding="utf-8")
blocks = [b.strip().replace("\n", "") for b in re.split(r"###SEG\d+###", text) if b.strip()]

durs = [dur_of(i+1) for i in range(len(blocks))]
offsets = []
t = 0.0
for d in durs:
    offsets.append(t)
    t += d
total = t
print("durations:", durs)
print("total:", total)

def ts(sec):
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# Split each block into sub-cues by sentence (~ every 12-18 chars for readability)
def split_sentences(text_chunk, max_chars=28):
    parts = re.split(r'([。！？，；])', text_chunk)
    sentences = [""]
    for p in parts:
        if sentences[-1] and len(sentences[-1]) > 0 and p in "。！？；" and not p.isspace():
            sentences[-1] += p
            sentences.append("")
        else:
            sentences[-1] += p
    sentences = [s for s in sentences if s.strip()]
    # further split long sentences
    out = []
    for s in sentences:
        while len(s) > max_chars:
            cut = s.rfind("，", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            out.append(s[:cut].strip() or s)
            s = s[cut:].strip()
        if s:
            out.append(s)
    return out

lines = []
count = 1
for i, b in enumerate(blocks):
    start = offsets[i]
    end = offsets[i] + durs[i]
    sub_cues = split_sentences(b)
    n = len(sub_cues)
    each = (end - start) / n
    for j, cue in enumerate(sub_cues):
        s = start + j * each
        e = start + (j + 1) * each
        lines.append((s, e, cue))

with open(BASE / "assets" / "subtitles.srt", "w", encoding="utf-8") as f:
    for idx, (s, e, cue) in enumerate(lines, 1):
        f.write(f"{idx}\n{ts(s)} --> {ts(e)}\n{cue}\n\n")

print(f"SRT written with {len(lines)} cues")
print("Sample:")
for s, e, cue in lines[:6]:
    print(ts(s), "->", ts(e), cue)