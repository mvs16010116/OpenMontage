---
name: military-org-chart
description: Generate a deterministic military organizational-chart animation (部队编制/指挥体系 tree, node reveal, command links draw-on) as a HyperFrames composition. Use when a narration-led pipeline needs 编制结构, 组织架构, 指挥体系, 参谋部/战区配置, hierarchy decomposition without real footage. Triggers: 编制, 组织架构, 指挥体系, org chart, 树状图, 建制, 战区, hierarchy.
---

# Military Org Chart (编制/组织架构图)

Generate a **command-tree diagram** — root node + branches, nodes reveal in depth order with command links drawing on, a highlight accent on the focus branch — as a standalone deterministic HyperFrames composition. Structure comes from your script.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_org_chart.mjs \
  --project <project> --title "战区指挥体系" --root "联合参谋部" \
  --nodes "陆军:2人" "海军:3人" "空军:2人" "火箭军:4人" \
  --duration 8 --accent #38bdf8 --focus 3
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--root` (top node), `--nodes "name:level" ...` (level = depth 1-3; or `"name"` for depth 1), `--focus N` (1-based node index to accent), `--duration`, `--accent`.
- Layout is auto-computed: root top-center; children fan out by level; positions stay fixed (no sampling).

## Composition anatomy

- **Root**: top-center node card.
- **Links**: vertical/horizontal connectors draw on (`scaleY`/`scaleX` on sized blocks) per branch.
- **Nodes**: cards reveal in depth order (`opacity` + `y`); focus branch gets the accent ring + brighter fill.
- **Legend/说明 row** at the bottom when `--nodes` values include roles.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Connectors animate `scaleX`/`scaleY` on elements with explicit width/height (transformed elements must be sized).
- Node positions fixed in HTML; reveal animates `opacity`+`y` only.
- No `Math.random`/`Date.now`; no `repeat:-1`. No decorative particles.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — tree reads top-down, no overlapping cards.
3. Render: `npx hyperframes render . --skill=military-org-chart -o <project>/renders/org_chart.mp4`.

## Completion criterion

- `hyperframes/index.html` with root+leaves, draw-on links, focused branch accent.
- `lint`/`validate` pass; MP4 available to narration-montage compose.