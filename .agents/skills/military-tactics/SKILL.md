---
name: military-tactics
description: Generate a deterministic tactical field animation (grid battlefield, friendly/enemy formations, advancing arrows, phase cards) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 战术队形, 攻防推演, 合围, 突破, 战线推进, unit movement without real footage. Triggers: 战术, 队形, 攻防, 合围, 突破, 战线, 推演, tactics, formation, advance.
---

# Military Tactics (战术队形/攻防推演)

Generate a **tactical field** segment — grid battlefield, friendly (own) vs enemy blocks, advancing/retreating force arrows, and a phase caption card — as a standalone deterministic HyperFrames composition.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_tactics.mjs \
  --project <project> --title "合围演练" --phase "左右钳击" \
  --own "北线:3单元" "东线:2单元" --enemy "中心:1个单位" \
  --arrows "own-0:enemy-0:合围" --duration 8 --accent #38bdf8
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--phase`, `--own "name:units"`, `--enemy "name:units"`, `--arrows "ownId:enemyId:label"`, `--duration`, `--accent`.
- Formations drawn as small filled shape clusters (own = accent, enemy = red), arrow = bezier draw-on + moving marker.

## Composition anatomy

- **Grid**: light grid background (static, subtle).
- **Formations**: own units (accent squares) vs enemy (red diamonds) as SVG clusters, revealed stagger.
- **Movement arrows**: bezier between formation anchors, `stroke-dashoffset` draw-on + traveling marker (proxy tween).
- **Phase card**: bottom caption (e.g. "第一波 · 左翼突进"), plus a small legend (own/enemy).
- Restraint per maps module: no decorative glow/particles.

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- Arrow markers via proxy tween `onUpdate` writing `cx/cy`; never `tl.call`.
- Formation/reveal animates `opacity`+`scale`; moving units animate `x/y` transform (block-level+sized).
- No `Math.random`/`Date.now`/`repeat:-1`.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — formations, arrows, phase card all legible, no overlaps.
3. Render: `npx hyperframes render . --skill=military-tactics -o <project>/renders/tactics.mp4`.

## Completion criterion

- `hyperframes/index.html` with grid, own/enemy formations, movement arrows, phase card.
- `lint`/`validate` pass; MP4 available to narration-montage compose.