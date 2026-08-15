---
name: military-missile
description: Generate a deterministic missile/rocket trajectory animation (launch, boost-to-coast flight arc, impact flash, range card) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 导弹, 弹道轨迹, 发射, 拦截试验, 试射, 火箭 segments without real footage. Triggers: 导弹, 弹道, 试射, 火箭, 拦截, missile, trajectory, launch, ballistic, ICBM.
---

# Military Missile (导弹/火箭弹道轨迹)

Generate a **missile trajectory** segment — launcher, boost straight-up phase, then an arcing ballistic path with a moving missile marker, and an impact flash + range readout card — as a standalone deterministic HyperFrames composition.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_missile.mjs \
  --project <project> --title "弹道导弹试射" --range "2400km" --apogee "800km" \
  --type icbm --duration 8 --accent #fbbf24
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--range` (range card), `--apogee` (trajectory readout), `--type icbm|sam|rocket` (adjusts launch profile: icbm = steep boost+arc, sam = short low arc, rocket = vertical launch), `--duration`, `--accent`.

## Composition anatomy

- **Launcher / launch pad**: bottom-left or bottom-center; rocket silhouette thin body.
- **Trajectory**: static dashed guide arc revealing via `stroke-dashoffset`; a missile marker (small rocket icon) travels along the precomputed quadratic bezier via proxy tween `onUpdate`.
- **Phases**: text labels ("点火 / 助推 / 中段 / 末段") fade at time windows.
- **Impact**: a flash ring (scale pulse, finite) + range card with count-up.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Missile position along bezier via proxy tween (never `tl.call`).
- Arc geometry fixed at build time; no `Math.random`/`Date.now`; no `repeat:-1`.
- Flash uses finite repeat; phase labels animate opacity only.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — arc, missile, phase labels, impact legible.
3. Render: `npx hyperframes render . --skill=military-missile -o <project>/renders/missile.mp4`.

## Completion criterion

- `hyperframes/index.html` with launch profile, trajectory arc + marker, phase labels, impact + range card.
- `lint`/`validate` pass; MP4 available to narration-montage compose.