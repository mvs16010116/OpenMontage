# -*- coding: utf-8 -*-
import asyncio, re, sys, pathlib, time
import edge_tts

VOICE = "zh-CN-YunxiNeural"
SRC = pathlib.Path(r"projects/guofang-shikong-20260808/assets/narration_copy.txt")
OUT = pathlib.Path(r"projects/guofang-shikong-20260808/assets/audio")
OUT.mkdir(parents=True, exist_ok=True)

text = SRC.read_text(encoding="utf-8")
blocks = [b.strip() for b in re.split(r"###SEG\d+###", text) if b.strip()]

async def gen(i, t):
    out = OUT / f"seg{i+1}.mp3"
    if out.exists() and out.stat().st_size > 1000:
        print(f"seg{i+1} exists, skipping", flush=True)
        return
    for attempt in range(4):
        try:
            print(f"Generating seg{i+1} ({len(t)} chars) attempt {attempt+1}...", flush=True)
            c = edge_tts.Communicate(t, VOICE)
            await c.save(str(out))
            print(f"  -> {out} {out.stat().st_size} bytes", flush=True)
            return
        except Exception as e:
            print(f"  attempt {attempt+1} failed: {type(e).__name__}", flush=True)
            if out.exists():
                out.unlink()
            await asyncio.sleep(8 + attempt * 8)
    raise RuntimeError(f"seg{i+1} failed after retries")

async def main():
    for i, b in enumerate(blocks):
        await gen(i, b)

if __name__ == "__main__":
    asyncio.run(main())
    print("DONE")