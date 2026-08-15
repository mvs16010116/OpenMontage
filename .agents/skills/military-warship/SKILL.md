---
name: military-warship
description: Generate a deterministic vector warship animation (line-art silhouette, sea, radar sweep, stat callouts) as a HyperFrames composition for military-political commentary videos. Use when a narration-montage or similar pipeline needs a ship segment — fleet overview, 军舰/驱逐舰/航母/护卫舰 introduction, 舰艇参数 cards, 演习画面 without real footage. Triggers: 军舰, warship, destroyer, aircraft carrier, frigate, 航母, 驱逐舰, 舷号, 排水量.
---

# Military Warship (军舰矢量动画)

Generate a **line-art warship** segment — ship silhouette, animated sea, rotating radar sweep, and stat callout cards — as a standalone HyperFrames composition. Deterministic (seekable frame-by-frame), vector-only, no stock footage.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_warship.mjs \
  --project <project> --name "驱逐舰" --hull "173 号" \
  --stats "满载排水量:7500吨" "航速:32节" "舰员:280人" \
  --duration 8 --palette dark
```

- Writes `projects/<project>/hyperframes/index.html` (relative to cwd, like `bake-basemap.mjs`). Adjust the raw HTML for custom silhouettes/paths if the built-in destroyer doesn't fit.
- Flags: `--name` (ship display name), `--hull` (hull number), `--stats "label:value" ...`, `--duration`, `--palette dark|bright`, `--accent #hex`.
- No network, no clocks, no unseeded randomness — pure GSAP paused timeline (hyperframes-core determinism contract).

## Composition anatomy

- **Ship**: SVG silhouette (hull, deck, superstructure, radar mast) at ~center-bottom. Built-in destroyer profile; swap the `<path>` for other classes (carrier/patrol) by editing the generated HTML.
- **Sea**: layered sine-wave bands (2-3 opacity layers) whose path y-offset is a deterministic function of `t` (driven via a proxy tween `onUpdate`), so waves roll without `Math.sin(Date.now())`.
- **Radar sweep**: rotating wedge + echo blips (finite, staggered reveals), not decorative.
- **Stat cards**: bottom callouts (排水量/航速/舰员) revealed with count-up via proxy tween `onUpdate` writing `textContent` (never `tl.call`).

## Determinism rules (non-negotiable)

- Single paused timeline on `window.__timelines["main"]`, key == root `data-composition-id`.
- Numbers/text updates go through **proxy tween + `onUpdate`**, never `tl.call`.
- Animate only the allowlist (`opacity,x,y,scale,rotation,color,backgroundColor,borderRadius`). No `display`/`visibility`.
- No `Math.random()` unseeded — use the shared `mulberry32(seed)` from `_military-shared/composition.mjs`.
- Wave `y` is computed from a seeded base, not from a clock.

## Verify

1. `npx hyperframes lint` then `npx hyperframes validate` in the project dir → 0 errors.
2. `npx hyperframes snapshot --frames 5` — eyeball ship shape, wave motion, sweep, cards.
3. Render: `npx hyperframes render . --skill=military-warship -q standard -o <project>/renders/warship.mp4`; confirm each phase readable ≥0.3s.

## Completion criterion

- `hyperframes/index.html` written with a real ship path, sea, radar sweep, stat cards, single paused timeline.
- `lint`/`validate` pass; snapshot shows no black frame, no clipped labels, readable callouts.
- Render MP4 available for the narration-montage compose stage as a segment source.
