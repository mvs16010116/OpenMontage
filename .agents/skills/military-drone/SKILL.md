---
name: military-drone
description: Generate a deterministic vector drone animation (quadcopter line-art, rotor spin, flight path trace, formation, telemetry HUD) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs a drone/UAV segment — 无人机, 侦察无人机, 察打一体, swarm formation, 航线, 电子侦察 without real footage. Triggers: 无人机, UAV, drone, swarm, 察打一体, 侦察机, flight path.
---

# Military Drone (无人机矢量动画)

Generate a **line-art drone** segment — quadcopter silhouette with spinning rotors, animated flight-path trace, optional formation (swarm), and telemetry HUD readouts — as a standalone deterministic HyperFrames composition. Vector-only, no stock footage.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_drone.mjs \
  --project <project> --name "察打一体无人机" --mode flight \
  --path "0.25,0.7 0.45,0.42 0.65,0.55 0.82,0.30" \
  --alt "5500m" --speed "180km/h" --formation 3 \
  --duration 8 --accent #22d3ee
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--name`, `--mode flight|hover|swarm`, `--path "t,xx t,xx ..."` (normalized 0-1 waypoints), `--alt`/`--speed`/`--formation N` (HUD + extra drones), `--duration`, `--accent`.
- Formation N>1 spawns `N-1` wingmen offset deterministically along the path.

## Composition anatomy

- **Drone**: SVG quadcopter (central body, 4 arms, 4 rotor circles). Rotor blur = rotating dashed ring with `rotation` tween (finite, many repeats but not `repeat:-1` — use a finite count).
- **Path trace**: the mission path draws on as `stroke-dashoffset` (trim-path style) while the drone glides along it; waypoint markers pulse in sequence.
- **HUD**: corners show alt/speed/heading readouts (static text + a subtle blink on a dot, not on text).
- **Swarm mode**: wingmen copy the lead motion with per-drone position offsets + stagger.

## Determinism rules (non-negotiable)

- Single paused timeline on `window.__timelines["main"]`; key == `data-composition-id`.
- Drone position along the path is computed from tween progress (`onUpdate` writing `transform` via GSAP, or a proxy), **never** `tl.call` for stateful updates.
- Rotor repeat uses a **finite** count: `repeat: Math.max(0, Math.floor(dur / cycle) - 1)`.
- No `Math.random()` — use `_military-shared/composition.mjs` `mulberry32(seed)` for wingman offsets.
- Animate only the allowlist (`opacity,x,y,scale,rotation,...`).

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` in the project dir → 0 errors.
2. `npx hyperframes snapshot --frames 5` — drone follows path, rotors spin, HUD legible.
3. Render: `npx hyperframes render . --skill=military-drone -q standard -o <project>/renders/drone.mp4`.

## Completion criterion

- `hyperframes/index.html` with drone silhouette, spinning rotors, path draw-on + flight, HUD, optional formation.
- `lint`/`validate` pass; snapshots show no blank frame, no clipped labels.
- MP4 available for narration-montage compose.
