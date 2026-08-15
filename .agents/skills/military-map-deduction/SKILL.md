---
name: military-map-deduction
description: Generate a deterministic strategic-map deduction animation (region silhouette fills, animated force arrows, phase labels, pinned callouts) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 战略态势, 地图推演, 部署箭头, 攻防方向, 兵力调动 without real basemap footage. Core of 军政解说. Triggers: 战略态势图, 地图推演, 兵力箭头, 部署, 攻防, theatre map, force flow.
---

# Military Map Deduction (战略态势地图推演)

Generate a **theatre map with animated force arrows** — region silhouette highlights, directional force-flow arrows (draw-on + traveling markers), phase labels, and pinned callout cards — as a standalone deterministic HyperFrames composition. Schematized vector map (no real basemap by default; see basemap note below).

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_map_deduction.mjs \
  --project <project> --theatre "亚太" \
  --regions "北部:高亮" "南海:重点" "海峡:高亮" \
  --arrows "北→南:推进" "东→西:增援" \
  --phase "第一阶段 · 集结部署" --duration 9 --accent #fbbf24
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--theatre` (title), `--regions "name:style"` (`高亮`/`重点`), `--arrows "from→to:label"` (drawn as bezier arcs), `--phase` (overlay phase label), `--duration`, `--accent`.
- Defaults to a **schematic** coastline built from 2-3 deterministic blobs. For a real-geometry result, use the `bake-basemap.mjs` lane (motion-graphics maps module) and wire its `*-coords.json` `d` paths here.

## Composition anatomy

- **Land**: 2-4 region silhouettes (SVG blobs) that fill in stagger (opacity/color reveal) — palette carries meaning (highlight vs focus), not decoration.
- **Arrows**: each a cubic bezier; `stroke-dashoffset` draw-on + a bright marker (circle) gliding along the curve at traveling point.
- **Phase label**: top-center discreet caption (readable ≥0.3s).
- **Callout card**: one pinned stat card per highlighted region (flag chip + value), not overlapping labels.

## Determinism rules (non-negotiable)

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Arrow markers move via proxy tween `onUpdate` writing `cx/cy` along the precomputed bezier (never `tl.call`).
- Region fills animate `fill`/`opacity`, not `display`. Label reveal uses `opacity` + `x` only.
- No `Math.random`/`Date.now` — use `mulberry32` for marker scatter.
- **Restraint (maps module hard rule)**: no decorative glows/particles/lens flares. Every element serves the message.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — arrows read clearly, labels legible, no overlap.
3. Render: `npx hyperframes render . --skill=military-map-deduction -o <project>/renders/map_deduction.mp4`.

## Completion criterion

- `hyperframes/index.html` with silhouette fill-in, force arrows + traveling markers, phase label, callouts.
- `lint`/`validate` pass; snapshots clean; MP4 for narration-montage compose.