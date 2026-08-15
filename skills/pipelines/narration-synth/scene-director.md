# Scene Director - Narration Synth Pipeline

## When To Use

The script exists with timed sections. You now turn each section into a SCENE: a
window of time plus a **`generation_spec`** — the one `military-*` skill and its
exact CLI arguments that will generate that scene's animation. The asset director
executes the spec; the edit director places one generated scene per section.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, timings, visual_anchor |
| Prior artifact | `state.artifacts["idea"]["brief"]` | visual_register, bookend_plan, tone |
| Layer 3 | `.agents/skills/military-*/SKILL.md` + each `scripts/build_*.mjs` | Exact CLI contracts |
| Reference | `skills/pipelines/narration-synth/executive-producer.md` | Cross-stage rules |

## Mental Model

The scene director is a **storyboard artist with a generator catalog**. Each scene
declares exactly how it will be drawn — which skill, which arguments, which
duration, which accent — so the asset stage never has to guess. Good specs are
deterministic: same spec → same animation, every run.

## Generation Spec Contract

Every scene MUST carry `generation_spec`:

```json
"generation_spec": {
  "skill": "military-warship",
  "build_script": ".agents/skills/military-warship/scripts/build_warship.mjs",
  "cli_args": {
    "--name": "新型驱逐舰",
    "--hull": "173 号",
    "--stats": ["满载排水量:12000吨", "垂直发射单元:48", "航速:32节"],
    "--accent": "#fbbf24",
    "--palette": "dark"
  },
  "cluster_args": { "duration": 8 },
  "output_note": "scene_02 — warship plus count-up stats under the tonnage line"
}
```

The `--duration` (or per-skill equivalent) tells the composition runtime; the
ASSET stage sets its own render length from `scene.end_seconds - scene.start_seconds`
and, where the skill supports it, splits the window across the composition. The
scene plan's `end_seconds - start_seconds` IS the target scene duration.

## Process

### 1. One Scene Per Section

Walk `script.sections[]` in order. One scene each, `start/end` COPIED from the
section. Scene windows equal section windows. No offsets yet — the edit stage
aligns to real audio.

### 2. Bookend Injection (from brief.bookend_plan)

- **Scene 0 (offset `-1.0` or before script start):** an opener
  `military-title-card --mode center` with the video title (~2-4s).
- **Chapter breaks:** insert a lower-mode `military-title-card` (2-3s) every 2-3
  sections where the 口播 transitions to a new chapter, per
  `brief.metadata.bookend_plan.chapter_breaks`.
- Bookends are scenes their own: give them section ids `section_opener` /
  `section_chapter_N` (no narration text) so the edit/compose lay them correctly.
  Their `end-start` is the short bookend hold, NOT a narration gap.

### 3. Choose The Skill Per Scene

Read `section.visual_anchor` + the section text, then pick ONE allowed skill from
`brief.metadata.visual_register.allowed_skills`:

| Anchor / line intent | Skill |
|----------------------|-------|
| 军舰/舰艇/航母/舰艇数据 | `military-warship` |
| 导弹/弹道/火箭/射程 | `military-missile` |
| 战略态势/战区/推演/战线 | `military-map-deduction` |
| 军费/装备对比/比例/预算/时间轴 | `military-data-viz` |
| 章节/标题/关键词/数字强调 | `military-title-card` |
| 文件/文书/指令/签署/公告 | `military-seal` |
| 无人机/编队/蜂群 | `military-drone` |
| 雷达/电子战/干扰/巡航空域 | `military-radar-ew` |
| 卫星/侦察/轨道/覆盖 | `military-satellite` |
| 军徽/勋章/旗帜/军衔/授衔 | `military-insignia` |
| 印章/红头/盖章/批复 | `military-seal` |

Constraints:

- **Adjacent scenes must not share the same skill family.** Two warship scenes in
  a row read as one long animation. Break the pattern or insert a title-card.
- **Match the generator to the meaning**, not to the first noun you see.
- Only skills listed in `allowed_skills` are permitted — if the clouding scene
  wants a skill outside the whitelist, escalate to re-lock the register first,
  do not silently widen it.

### 4. Fill The CLI Args — Deterministically

Read the specific skill's `SKILL.md` for its exact flags and defaults. Fill every
arg the composition needs from the section's concrete nouns: ship names, hull
numbers, stat `label:value` pairs, range numbers, theatre names, chart series,
title strings. Rules:

- **No randomness.** Fixed palette from `visual_register`; fixed accent. If a
  skill supports a seed, set it deterministically (e.g. derived from the scene id).
- **Concrete text only** — titles/stats come from the script, never placeholder
  junk.
- **Keep durations in range** — `--duration` per skill should land near the scene
  window length; the asset stage will reconcile.

### 5. Set Shot Language For Film-Read Variety

`framing`/`movement` still apply as visual-register fields (the generated scenes
have a fixed camera by skill, but you enforce variety by SKILL choice and accent).
Record `shot_language` and `shot_intent` per scene for the edit stage and the
Backlot board.

### 6. Flag Hero Moments

Mark 1-2 scenes `hero_moment: true` (the hook scene + payoff scene). Heroes may
stretch their hold at edit time; the asset stage may raise their render
quality/animations.

### 7. Emit The Scene Plan

Canonical shape:

```json
{
  "version": "1.0",
  "scenes": [
    {
      "id": "scene_opener",
      "type": "generated",
      "description": "center title card — video title over dark naval background",
      "start_seconds": -1.0,
      "end_seconds": 2.0,
      "script_section_id": "section_opener",
      "generation_spec": {
        "skill": "military-title-card",
        "build_script": ".agents/skills/military-title-card/scripts/build_title_card.mjs",
        "cli_args": {
          "--title": "新型驱逐舰：改写西太平洋",
          "--sub": "装备深度分析",
          "--mode": "center",
          "--accent": "#fbbf24",
          "--duration": "3"
        },
        "output_note": "opener — title + sub over the bookend window"
      },
      "framing": "wide",
      "movement": "static",
      "transition_in": "fade_in",
      "transition_out": "cut",
      "shot_language": "title_card_open",
      "shot_intent": "establish the video's thesis with authoritative typography",
      "narrative_role": "opener",
      "hero_moment": true,
      "required_assets": [
        { "type": "animation", "description": "military-title-card center composition", "source": "self_generated" }
      ]
    },
    {
      "id": "scene_02",
      "type": "generated",
      "description": "warship silhouette with count-up stats — tonnage, VLS cells, speed",
      "start_seconds": 5.5,
      "end_seconds": 14.0,
      "script_section_id": "section_02",
      "generation_spec": {
        "skill": "military-warship",
        "build_script": ".agents/skills/military-warship/scripts/build_warship.mjs",
        "cli_args": {
          "--name": "新型驱逐舰",
          "--hull": "173 号",
          "--stats": ["满载排水量:12000吨", "垂直发射单元:48", "航速:32节"],
          "--accent": "#fbbf24",
          "--palette": "dark",
          "--duration": "8"
        },
        "output_note": "hero — warship + count-up numbers under the specs line"
      },
      "framing": "wide",
      "movement": "static",
      "transition_in": "cut",
      "transition_out": "cut",
      "shot_language": "warship_specs",
      "shot_intent": "visualize the ship's core specs as animated numbers",
      "narrative_role": "body",
      "hero_moment": true,
      "texture_keywords": ["驱逐舰", "垂发", "排水量"],
      "required_assets": [
        { "type": "animation", "description": "military-warship silhouette + stats", "source": "self_generated" }
      ]
    }
  ],
  "metadata": {
    "pipeline": "narration-synth",
    "tone": "authoritative",
    "allowed_skills_used": { "military-title-card": 1, "military-warship": 1, "military-map-deduction": 1, "military-data-viz": 1 },
    "adjacency_checked": true,
    "total_scene_seconds": 93.0
  }
}
```

### 8. Quality Gate

- One scene per section (+ injected bookends); counts correct.
- Every scene has a `generation_spec` with a REAL skill, build_script path, and
  concrete `cli_args`.
- `generation_spec.cli_args` uses only the skill's documented flags (read its
  SKILL.md); no random seeds.
- No two adjacent scenes share the same skill family.
- `sum(end-start)` within ±10% of `script.total_duration_seconds` (+ bookends).
- At most 2 hero scenes.
- Bookends injected per `brief.metadata.bookend_plan`.

## Common Pitfalls

- **Underspecified specs.** `{"skill": "military-warship"}` with no args forces the
  asset stage to guess — a scene-plan defect.
- **Wrong flag names.** Each `build_*.mjs` has its own flags (`--hull`,
  `--seal-text`). Read the skill before writing args.
- **Adjacent same-skill scenes.** The cut looks like one long animation.
- **Abstract anchors.** "战略威慑" with no concrete nouns → the scene director
  can't pick a generator. Section text must carry specifics.
- **Bookend scenes without ids.** Give them `section_opener`/`section_chapter_N`
  so edit/compose know they are narration-free holds.
- **Out-of-whitelist skills.** Escalate, don't silently widen.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.