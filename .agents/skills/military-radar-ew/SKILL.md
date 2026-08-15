---
name: military-radar-ew
description: Generate a deterministic radar / electronic-warfare visualization (radar screen, rotating sweep, blips, EW noise/jamming bands) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 雷达, 电子战, 探测, 干扰, 防空圈, 预警, EW/ECM segments without real footage. Triggers: 雷达, 电子战, 干扰, 探测, 防空, 预警机, radar, EW, ECM, jamming, sweep.
---

# Military Radar / EW (雷达/电子战可视化)

Generate a **radar screen / EW** segment — concentric range rings, rotating sweep line, blip echoes appearing, and an electronic-warfare variant with noise bands + jamming pulses — as a standalone deterministic HyperFrames composition.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_radar_ew.mjs \
  --project <project> --title "防空预警网" --mode radar \
  --blips "035:25:2" "120:60:1" "210:78:3" --range "400km" --duration 8 --accent #4ade80
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--mode radar|ew`, `--blips "bearing:rangePct:severity" ...` (bearing 0-360°, range % of radius, severity 1-3), `--range` (range label), `--duration`, `--accent`.
- `--mode ew` switches to noise-band + jamming-pulse variant (same screen, red/orange accents).

## Composition anatomy

- **Screen**: dark circle, 3-4 range rings (static), crosshair, small readout label top-left (range/scan type).
- **Sweep**: a wedge/line rotating continuously via a finite-repeat `rotation` tween.
- **Blips**: echoes pop in at their bearing/range (precomputed xy), with a severity-scaled pulse (finite repeat).
- **EW mode**: replaces sweep with a sweeping noise band (a few random-but-seeded bars) + jamming pulses at blip positions.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Blip xy computed from fixed bearing/range at build time (no `Math.random` at runtime; use seeded rng).
- Sweep uses a **finite** repeat count (never `repeat:-1`).
- Animate allowlist only; no `display`/`visibility`.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — rings, sweep, blips legible.
3. Render: `npx hyperframes render . --skill=military-radar-ew -o <project>/renders/radar_ew.mp4`.

## Completion criterion

- `hyperframes/index.html` with radar screen, sweep, blips (+ EW variant).
- `lint`/`validate` pass; MP4 available to narration-montage compose.