---
name: military-data-viz
description: Generate deterministic data charts — bar/radar/line comparisons, timeline, count-up KPI cards — as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 军费对比, 装备数量统计, 预算占比, 时间线沿革, KPI 数字 without real footage. Triggers: 军费, 预算, 装备对比, 数据图表, 统计, 时间线, bar chart, timeline, KPI, 增长.
---

# Military Data Viz (军费/装备对比 + 时间线)

Generate a **data chart** segment — horizontal bar comparison, bracket/radar comparison, or timeline — with count-up value labels and a conclusion KPI card, as a standalone deterministic HyperFrames composition. Data comes from your script.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_data_viz.mjs \
  --project <project> --title "军费对比" --type bars \
  --bars "甲国:1680亿美元" "乙国:1420亿美元" "丙国:896亿美元" \
  --kpi "增长 8.3% · 连续三年" --duration 8 --accent #22c55e
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--type bars|radar|timeline`, `--bars "label:value" ...`, `--kpi "conclusion"`, `--duration`, `--accent`, `--timeline "2020:事件" ...` (for timeline type).
- Values parsed to numbers for bar lengths + count-up; units kept as suffix.

## Composition anatomy

- **Bars**: horizontal bars grow (`scaleX` on a sized block — remember the allowlist requires a real `width`) with staggered reveal; value label counts up via proxy tween `onUpdate`.
- **Timeline**: vertical dashed rail, milestone nodes pop in at t positions, event text slides in; a cursor line sweeps.
- **KPI card**: bottom pinned card with the conclusion and a bright accent — shown after the chart settles.

## Determinism rules (non-negotiable)

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- count-up numbers through **proxy tween + `onUpdate`** (never `tl.call`).
- Bars animate `scaleX` on elements with explicit `width` (transformed elements must be block-level + sized).
- No `Math.random`/`Date.now`; timeline positions are fixed, not sampled.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — bars/timeline legible, values readable, no clipped labels.
3. Render: `npx hyperframes render . --skill=military-data-viz -o <project>/renders/data_viz.mp4`.

## Completion criterion

- `hyperframes/index.html` with the chart, count-up values, KPI card.
- `lint`/`validate` pass; MP4 available to narration-montage compose.