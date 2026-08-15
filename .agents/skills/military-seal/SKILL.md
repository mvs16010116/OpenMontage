---
name: military-seal
description: Generate a deterministic official-seal / red-header stamp animation (五角星红印, 环绕文字印章 slam, 文件抬头) as a HyperFrames composition. Use when a narration-led pipeline needs 印章, 公章, 红头文件, 盖章仪式, official approval moments without real footage. Triggers: 印章, 公章, 红印, 盖章, 红头文件, seal, stamp, chop, 批准.
---

# Military Seal (印章/红头盖章动效)

Generate an **official seal stamp** segment — red circular 五角星 seal with surrounding characters that slams onto the document, plus a red-header 文件 layout beneath — as a standalone deterministic HyperFrames composition. Companion to `military-agreement`.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_seal.mjs \
  --project <project> --title "批复文件" --org "某部装备处" --seal-text "中国人民解放军·装备部" \
  --duration 6 --accent #d33
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--org`, `--seal-text` (wraps around the seal circle; short text ≈ 6-10 chars), `--duration`, `--accent`.
- Uses the same 红头 document look as `military-agreement`; this skill focuses on the seal slam beat.

## Composition anatomy

- **Document**: red-header paper behind (silent static layout), centered.
- **Seal**: circular red seal — outer ring, 五角星, 环绕文字 (hand-placed along the ring via build-time math). Slams down: `scale: 2.4 → 1` with `back.out` + slight rotation settle.
- **Beat**: tiny screen shake (finite, subtle) as the seal lands; a stamp "ink" pulse.
- **Caption**: "已批准 / 盖章生效" text fades in after the slam.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Seal characters positioned at build time (no runtime layout sampling).
- Slam uses fixed keyframes; shake is finite; no `Math.random`/`Date.now`/`repeat:-1`.
- Ink pulse uses finite repeat.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — seal, ring text, caption legible.
3. Render: `npx hyperframes render . --skill=military-seal -o <project>/renders/seal.mp4`.

## Completion criterion

- `hyperframes/index.html` with red-header doc, seal slam + ring text, caption.
- `lint`/`validate` pass; MP4 available to narration-montage compose.