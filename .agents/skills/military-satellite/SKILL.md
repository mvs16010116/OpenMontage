---
name: military-satellite
description: Generate a deterministic satellite / reconnaissance orbit animation (Earth disc, orbit ellipse, orbiting satellite, ground track, sensor cone) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 卫星, 侦察卫星, 轨道, 对地观测, 天基侦察 segments without real footage. Triggers: 卫星, 轨道, 侦察卫星, 天基, 对地观测, satellite, orbit, recon, 北斗, GPS.
---

# Military Satellite (卫星/侦察轨道动画)

Generate a **satellite orbit** segment — Earth disc, inclined orbit ellipse, a satellite orbiting with a sensor footprint/cone to the ground, and a telemetry readout — as a standalone deterministic HyperFrames composition.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_satellite.mjs \
  --project <project> --title "侦察卫星组网" --sat "高分光学" --orbit "太阳同步" \
  --tilt 24 --alt "600km" --duration 8 --accent #38bdf8
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--sat` (satellite name), `--orbit` (orbit type label), `--tilt` (orbit ellipse tilt deg), `--alt` (altitude readout), `--duration`, `--accent`.

## Composition anatomy

- **Earth**: blue disc with faint grid/atmosphere ring, centered right-of-field.
- **Orbit**: an ellipse (via `<ellipse>` rotated by tilt) + dashed; the satellite is a small body + solar panels that traverses the ellipse (proxy tween driving `cx/cy` on a precomputed ellipse path).
- **Sensor**: a cone/beam from satellite toward Earth + a footprint ellipse that follows.
- **Readout**: top-left telemetry (altitude, inclination, satellite name).

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Satellite position on the ellipse from a proxy tween `onUpdate` (never `tl.call`).
- Ellipse geometry fixed; no `Math.random`/`Date.now`; no `repeat:-1`.
- Orbit motion uses a finite number of full revolutions: `repeat: floor(dur / period) - 1`.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — Earth, orbit, satellite, footprint legible.
3. Render: `npx hyperframes render . --skill=military-satellite -o <project>/renders/satellite.mp4`.

## Completion criterion

- `hyperframes/index.html` with Earth disc, tilted orbit ellipse, orbiting satellite + sensor, telemetry readout.
- `lint`/`validate` pass; MP4 available to narration-montage compose.