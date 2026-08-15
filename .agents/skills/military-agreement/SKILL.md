---
name: military-agreement
description: Generate a deterministic "agreement document signing" animation (red-header 协议书/文件 appearance, typed/populated clauses, red seal slam, signature line) as a HyperFrames composition. Use when a military-political/legal commentary video needs a document prop — 协议书, 协约, 公报, 声明, 联合声明, 签字仪式, 协议盖章 without real paperwork footage. Triggers: 协议书, agreement, 协定, 公报, 签字, 盖章, seal, document, 联合声明.
---

# Military Agreement (协议书盖章动画)

Generate a **document** segment: an official red-header 协议书 sheet that appears, its clauses populate, then a **red seal slams down** and signature line draws — as a standalone deterministic HyperFrames composition. Vector text-layout only, real document content comes from your narration script.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_agreement.mjs \
  --project <project> --title "联合声明" --org "军工科技集团" \
  --clauses "双方同意开展联合研制" "共享防御技术成果" "条款自签署之日起生效" \
  --duration 8 --accent #ef4444
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title` (headline), `--org` (issuing body), `--clauses "line" ...` (2-5 bullet clauses), `--duration`, `--accent` (seal red).
- **NOTE**: this is a video prop only. A legally valid agreement document is out of scope — generate with your document tools, not here.

## Composition anatomy

- **Sheet**: paper rectangle with red top band (红头), title, blank-ish body. Appear via scale-in from a drop shadow.
- **Clauses**: typewriter reveal (per-clause opacity + `x` slide stagger) — the content is your narration's.
- **Seal**: red circular seal stamp (五角星 + 环绕文字) slams down with `scale` overshoot (e.g. `scale:1.3` → `1`) + slight rotation; leave it visible.
- **Signature line**: underline + holder name draws in near the bottom right.

## Determinism rules (non-negotiable)

- Single paused timeline `window.__timelines["main"]`, key == `data-composition-id`.
- No `Math.random`/`Date.now`; seal rotation/scale is a fixed tween (finite overshoot), no `repeat:-1`.
- Text reveal animates opacity/`x` only (allowlist); never animate `display`.
- Seal pulse (a soft final blink) uses finite repeat count.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — sheet, clauses, seal slam all legible.
3. Render: `npx hyperframes render . --skill=military-agreement -o <project>/renders/agreement.mp4`.

## Completion criterion

- `hyperframes/index.html` with red-header sheet, staggered clause reveal, seal slam, signature draw-on.
- `lint`/`validate` pass; snapshots clean; MP4 available to narration-montage compose.