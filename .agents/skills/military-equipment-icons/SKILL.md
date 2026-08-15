---
name: military-equipment-icons
description: Generate a deterministic unified vector icon set for military equipment (坦克, 战机, 导弹, 舰艇, 无人机 silhouettes) as a HyperFrames composition for brand-consistent 军政 commentary. Use when a narration-led pipeline needs a reusable equipment icon system, 装备对比图, 武器图标, 白皮书配图 without stock footage. Triggers: 装备图标, 武器图标, 坦克, 战机, 导弹图标, 舰艇图标, icon set, silhouette, equipment.
---

# Military Equipment Icons (装备矢量图标集)

Generate a **reusable vector icon system** — consistent line-art silhouettes for 坦克/战机/导弹/舰艇/无人机/雷达, laid out on a grid with a name plate and a highlight accent, as a standalone deterministic HyperFrames composition. Use the same silhouette geometry across your series for brand consistency.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_equipment_icons.mjs \
  --project <project> --title "装备体系概览" \
  --icons "tank:主战坦克" "fighter:歼击机" "missile:导弹" "ship:舰艇" "drone:无人机" "radar:雷达" \
  --duration 8 --accent #38bdf8
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--icons "id:name" ...` (id ∈ tank|fighter|missile|ship|drone|radar|carrier), `--duration`, `--accent`.
- Grid auto-lays 3×2 (or 4×1 for 4 icons); each cell shows the silhouette + name, reveal stagger; the `--accent` one (last listed) gets a ring highlight.

## Composition anatomy

- **Icons**: each is an inline SVG path (dark-on-light or accent silhouette) drawn with a consistent 2-stroke weight.
- **Grid**: fixed positions (no sampling); cells reveal with `opacity`+`scale` stagger.
- **Highlight**: focus cell gets an accent ring + brighter fill.
- **Name plate**: bottom row lists legend chips.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Grid positions computed at build time (fixed HTML), no runtime layout reads.
- Reveal animates `opacity`+`scale` (transformOrigin set); no `Math.random`/`Date.now`/`repeat:-1`.
- Focus pulse uses finite repeat.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — icons legible, names readable, no clipping.
3. Render: `npx hyperframes render . --skill=military-equipment-icons -o <project>/renders/equipment_icons.mp4`.

## Completion criterion

- `hyperframes/index.html` with consistent silhouettes, grid reveal, focus ring, legend.
- `lint`/`validate` pass; MP4 available to narration-montage compose.