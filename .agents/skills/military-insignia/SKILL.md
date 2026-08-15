---
name: military-insignia
description: Generate a deterministic military insignia animation (军徽, 勋章, 旗帜, 军衔 emblem — vector star/wreath/laurel reveal with shine sweep) as a HyperFrames composition. Use when a narration-led pipeline needs 军徽, 勋章, 旗帜, 军衔, 国徽, 臂章, badge/medal/flag emblems without real footage. Triggers: 军徽, 勋章, 旗帜, 军衔, 国徽, 臂章, 徽章, emblem, badge, medal, star, wreath.
---

# Military Insignia (军徽/勋章/旗帜/军衔)

Generate an **emblem reveal** — vector star + laurel/wreath + ribbon, with a shine sweep and a name plate — as a standalone deterministic HyperFrames composition. Reusable as a section opener/closer for 军政 commentary.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_insignia.mjs \
  --project <project> --title "陆军徽标" --sub "忠诚 · 无畏" \
  --kind star --duration 7 --accent #facc15
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--sub` (motto), `--kind star|shield|flag|wreath` (changes the emblem geometry), `--duration`, `--accent`.
- `--kind flag` renders a waving flag (path distortion by time via proxy `onUpdate`); `shield`/`wreath`/`star` render vector badge geometry.

## Composition anatomy

- **Emblem**: centered vector group (star points, wreath arcs, ribbon ribbon).
- **Reveal**: emblem scales/fades in, then a **shine sweep** (a diagonal highlight bar crossing, finite).
- **Name plate**: title + motto fade in under the emblem.
- **Pulse**: subtle accent glow on the emblem (finite, not decorative overload).

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Flag waving: path `d` updated by proxy `onUpdate` (deterministic sine of time fraction), never a clock.
- Shine sweep is one finite pass; pulse uses finite repeat.
- No `Math.random`/`Date.now`/`repeat:-1`; animate allowlist only.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — emblem, shine, name plate legible.
3. Render: `npx hyperframes render . --skill=military-insignia -o <project>/renders/insignia.mp4`.

## Completion criterion

- `hyperframes/index.html` with the emblem geometry, reveal + shine, name plate.
- `lint`/`validate` pass; MP4 available to narration-montage compose.