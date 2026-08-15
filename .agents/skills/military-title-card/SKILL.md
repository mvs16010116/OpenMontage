---
name: military-title-card
description: Generate a deterministic title / term-emphasis card (big title, keyword highlight, count-up number, lower-third style) as a HyperFrames composition for military-political commentary. Use when a narration-led pipeline needs 标题卡, 术语强调, 重点数字 count-up, 开场片头, 章节标题 without stock footage. Triggers: 标题卡, 术语强调, 重点词, count-up, 片头, 章节标题, title card, keyword, lower third, 数字.
---

# Military Title Card (标题/术语强调/数字 count-up)

Generate a **title/emphasis card** segment — big headline typography, a keyword highlight box, an optional count-up number, and a lower-third caption — as a standalone deterministic HyperFrames composition. Works as a section opener, chapter title, or stat emphasis in 军政 commentary.

## Run the generator

```bash
node <SKILL_DIR>/scripts/build_title_card.mjs \
  --project <project> --title "新时代军事战略方针" \
  --keyword "总体国家安全观" --number "2035:实现目标" \
  --lower "第一章 · 战略概述" --duration 6 --accent #fbbf24
```

- Writes `projects/<project>/hyperframes/index.html`. Flags: `--title`, `--keyword` (highlight box under title), `--number "value:label"` (big count-up + label), `--lower` (lower-third caption), `--duration`, `--accent`.
- Without `--number`, it renders a pure title/keyword card.

## Composition anatomy

- **Headline**: large centered title; letters/words reveal with a clip/`y`+opacity stagger.
- **Keyword box**: a pill/underline highlight appearing under a key term (accent bar draws in).
- **Count-up**: a very large number counts up via proxy tween `onUpdate` with unit/label beside it.
- **Lower-third**: bottom-left small caption (chapter/section name).

## Determinism rules

- Single paused timeline `window.__timelines["main"]`; key == `data-composition-id`.
- count-up via **proxy tween + `onUpdate`** (never `tl.call`).
- Title reveal animates `y`+`opacity` per-word (block-level spans); accent bar animates `scaleX` on a sized element.
- No `Math.random`/`Date.now`/`repeat:-1`; animate allowlist only.

## Verify

1. `npx hyperframes lint` + `npx hyperframes validate` → 0 errors.
2. `npx hyperframes snapshot --frames 5` — headline, keyword, number, lower-third all legible.
3. Render: `npx hyperframes render . --skill=military-title-card -o <project>/renders/title_card.mp4`.

## Completion criterion

- `hyperframes/index.html` with headline, keyword highlight, optional count-up, lower-third.
- `lint`/`validate` pass; MP4 available to narration-montage compose.