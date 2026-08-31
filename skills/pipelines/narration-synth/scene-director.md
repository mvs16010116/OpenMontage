# Scene Director - Narration Synth Pipeline

## When To Use

The script exists with timed sections. You now turn each section into ONE SHOT
PER SEMANTIC SENTENCE: each shot is a window of time plus a **`materials[]`**
stack — the layer materials (each a `military-*` skill + its exact CLI args) that
are overlaid in the SAME window to fill that shot's frame. A story is many small
stories: a section is many sentences, and each sentence is its own shot layered
from materials. The asset director executes each material's spec; the edit
director overlays the materials per shot and concatenates shots in section order.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, timings, visual_anchor |
| Prior artifact | `state.artifacts["idea"]["brief"]` | visual_register, bookend_plan, tone |
| Layer 3 | `.agents/skills/military-*/SKILL.md` + each `scripts/build_*.mjs` | Exact CLI contracts |
| Reference | `skills/pipelines/narration-synth/executive-producer.md` | Cross-stage rules |

## Mental Model

The scene director is a **storyboard artist with a generator catalog**. Each shot
declares its material stack — which skills, which arguments, which duration,
which accent, in which layer order — so the asset stage never has to guess. Good
specs are deterministic: same spec → same animation, every run. Sections
decompose into sentence-shots so the edit has shot variety, not one long hold.

## Generation Spec Contract — Materials

Every scene MUST carry `materials[]` — the layer stack that fills its window.
**A shot is one frame assembled from many materials overlaid in the SAME time**:
a background scene (map / warship / stratosphere) + foreground data / seal / text
cards. Each material is independently generated and rendered to a transparent
MP4; the edit director overlays them per shot window.

```json
"materials": [
  {
    "id": "scene_02_mat_bg",
    "layer": "background",
    "skill": "military-map-deduction",
    "build_script": ".agents/skills/military-map-deduction/scripts/build_map.mjs",
    "cli_args": {
      "--theatre": "西太平洋",
      "--arrows": ["第一岛链", "宫古海峡"],
      "--accent": "#fbbf24",
      "--palette": "dark"
    },
    "output_note": "scene_02 background — theatre map with push arrows"
  },
  {
    "id": "scene_02_mat_fg",
    "layer": "foreground",
    "skill": "military-data-viz",
    "build_script": ".agents/skills/military-data-viz/scripts/build_viz.mjs",
    "cli_args": {
      "--series": ["驱逐舰数量:8", "护卫舰数量:12"],
      "--font-size": "72",
      "--accent": "#fbbf24",
      "--palette": "dark"
    },
    "output_note": "scene_02 foreground — animated bar data over the map"
  }
]
```

Rules:

- **≥1 material per scene**; typically 2-3. A single-material shot = background
  only (fine for bookends / a strong hero).
- **Layer semantics:** `background` (fills the frame), `midground`,
  `foreground` (text/data overlays). Edit overlay order = layer order: background
  first, then midground, then foreground on top.
- **Every material has its own spec** — a different skill where the meaning
  changes; two materials in one shot MAY reuse a skill ONLY if they occupy
  different layers and different content (e.g. two data cards on one map) — but
  adjacent SCENES still must not share the same skill.
- Materials are OVERLAID in the same window, NOT concatenated — do not split the
  shot window across materials.
- `--duration` (or per-skill equivalent) = the scene window length; the asset
  stage renders each material to its own transparent MP4 of that length, and the
  edit director overlays them for exactly `scene.end_seconds - scene.start_seconds`.

## Process

### 1. One Semantic Sentence Per Scene

Walk `script.sections[]` in order. **A section is a beat of the story; each
semantic sentence inside it is a SCENE (shot).** A story is many small stories: a
section is many small paragraphs (sentences), and each small paragraph is one
shot.

Split each section's narration into its semantic sentences:

- Split at meaning boundaries — sentence-level breaks (。！？; and logical
  clause pauses), never mid-sentence. A semantic sentence is a self-contained
  unit ("驱逐舰以 32 节航速巡航", "垂发单元同时锁定 48 个目标").
- Each semantic sentence becomes one scene, window = sentence fraction of the
  section window, proportional to that sentence's character share (sum of scene
  windows = section window).
- A section with 3 semantic sentences = 3 scenes. This is the DEFAULT — do not
  wait for a "too long" threshold to split; every sentence earns its own shot.
- Keep each scene/sentence window ≥ ~2s of narration (a sentence under ~9 chars
  is usually part of a neighbor, not a standalone shot).

Every scene carries `materials[]` — **a shot is made of the layer stack that
fills its window**, overlaid in the SAME time window (not sequential):

### 2. Bookend Injection (from brief.bookend_plan)

- **Scene 0 (offset `-1.0` or before script start):** an opener
  `military-title-card --mode center` with the video title (~2-4s).
- **Chapter breaks:** insert a lower-mode `military-title-card` (2-3s) every 2-3
  sections where the 口播 transitions to a new chapter, per
  `brief.metadata.bookend_plan.chapter_breaks`.
- Bookends are scenes their own: give them section ids `section_opener` /
  `section_chapter_N` (no narration text) so the edit/compose lay them correctly.
  Their `end-start` is the short bookend hold, NOT a narration gap.

### 3. Choose The Skill Per Scene (per material)

Read `section.visual_anchor` + the semantic sentence text, then pick ONE allowed
skill from `brief.metadata.visual_register.allowed_skills` per MATERIAL, guided
by its layer + meaning:

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

Layer guidance: a FULL-FRAME skill (map / warship / missile / satellite / radar)
fills `background`; text/data skills (title-card / data-viz / seal / insignia)
are the natural `foreground` overlay. A sentence like "驱逐舰已进入宫古海峡"
= map background + a warship/radar midground + optional seal foreground.

Constraints:

- **Adjacent SCENES must not share the same full-frame/background skill family.**
  Two warship-background shots in a row read as one long animation. Break the
  pattern or insert a title-card.
- Foreground overlays (title-card / data-viz / seal) are exempt from the
  adjacency rule — a data card over a map, then a data card over a radar is the
  intended cadence; the BACKGROUND decides visual variety.
- **Match the generator to the meaning**, not to the first noun you see.
- Only skills listed in `allowed_skills` are permitted — if a material wants a
  skill outside the whitelist, escalate to re-lock the register first, do not
  silently widen it.

### 4. Fill The CLI Args — Deterministically (per material)

Read the specific skill's `SKILL.md` for its exact flags and defaults. Fill every
arg each material needs from the semantic sentence's concrete nouns: ship names,
hull numbers, stat `label:value` pairs, range numbers, theatre names, chart
series, title strings. Rules:

- **No randomness.** Fixed palette from `visual_register`; fixed accent across
  materials in one shot (so the overlay looks unified). If a skill supports a
  seed, set it deterministically (e.g. derived from the scene id + layer).
- **Concrete text only** — titles/stats come from the script, never placeholder
  junk.
- **Keep durations in range** — `--duration` per material = the scene window
  length; the asset stage will reconcile.

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
      "materials": [
        {
          "id": "scene_opener_mat",
          "layer": "background",
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
        }
      ],
      "framing": "wide",
      "movement": "static",
      "transition_in": "fade_in",
      "transition_out": "cut",
      "shot_language": "title_card_open",
      "shot_intent": "establish the video's thesis with authoritative typography",
      "narrative_role": "opener",
      "hero_moment": true,
      "required_assets": [
        { "type": "animation", "material_id": "scene_opener_mat", "description": "military-title-card center composition", "source": "self_generated" }
      ]
    },
    {
      "id": "scene_02",
      "type": "generated",
      "description": "西太平洋 theatre map with push arrows, fleet-buildup bars overlaid on top",
      "semantic_sentence": "驱逐舰编队已进入宫古海峡，区域反舰体系同步成型。",
      "start_seconds": 5.5,
      "end_seconds": 14.0,
      "script_section_id": "section_02",
      "materials": [
        {
          "id": "scene_02_mat_bg",
          "layer": "background",
          "skill": "military-map-deduction",
          "build_script": ".agents/skills/military-map-deduction/scripts/build_map.mjs",
          "cli_args": {
            "--theatre": "西太平洋",
            "--arrows": ["第一岛链", "宫古海峡"],
            "--accent": "#fbbf24",
            "--palette": "dark",
            "--duration": "8"
          },
          "output_note": "background — theatre map with push arrows"
        },
        {
          "id": "scene_02_mat_fg",
          "layer": "foreground",
          "skill": "military-data-viz",
          "build_script": ".agents/skills/military-data-viz/scripts/build_viz.mjs",
          "cli_args": {
            "--series": ["驱逐舰数量:8", "护卫舰数量:12"],
            "--accent": "#fbbf24",
            "--palette": "dark",
            "--duration": "8"
          },
          "output_note": "foreground — animated bar data over the map"
        }
      ],
      "framing": "aerial",
      "movement": "static",
      "transition_in": "cut",
      "transition_out": "cut",
      "shot_language": "map_with_data_overlay",
      "shot_intent": "show the strategic push as a moving map + fleet numbers",
      "narrative_role": "body",
      "hero_moment": true,
      "texture_keywords": ["驱逐舰", "宫古海峡", "反舰体系"],
      "required_assets": [
        { "type": "animation", "material_id": "scene_02_mat_bg", "description": "theatre map background", "source": "self_generated" },
        { "type": "animation", "material_id": "scene_02_mat_fg", "description": "data-viz foreground overlay", "source": "self_generated" }
      ]
    }
  ],
  "metadata": {
    "pipeline": "narration-synth",
    "tone": "authoritative",
    "allowed_skills_used": { "military-title-card": 1, "military-map-deduction": 1, "military-data-viz": 1 },
    "adjacency_checked": true,
    "total_scene_seconds": 93.0
  }
}
```

### 8. Quality Gate

- Every section splits into one SCENE per semantic sentence; sentence windows sum
  to the section window (no unaccounted time).
- Every scene has `materials[]` with ≥1 material; each material carries a REAL
  skill, build_script path, and concrete `cli_args`; each has a `layer`.
- `cli_args` uses only the skill's documented flags (read its SKILL.md); no random
  seeds; accents consistent across materials in one shot.
- No two adjacent scenes share the same background/full-frame skill family.
- `sum(end-start)` within ±10% of `script.total_duration_seconds` (+ bookends).
- At most 2 hero scenes.
- Bookends injected per `brief.metadata.bookend_plan`.

## Common Pitfalls

- **Underspecified material specs.** `{"skill": "military-warship"}` with no args
  forces the asset stage to guess — a scene-plan defect.
- **Wrong flag names.** Each `build_*.mjs` has its own flags (`--hull`,
  `--seal-text`, `--theatre`). Read the skill before writing args.
- **Missing layer order.** Materials must declare `background` → `foreground`;
  the edit overlay follows it. Without layers, the overlay order is undefined.
- **Splitting the window across materials.** Materials OVERLAY the same window —
  do not divide `end-start` among them.
- **Sequential-style duration split** (material A 0-4s, material B 4-8s) — that is
  multi-camera, not a layered shot; encode it as two scenes instead.
- **Adjacent scenes sharing a background skill.** The cut reads as one long
  animation; vary the BACKGROUND.
- **Ignoring sentence boundaries.** Splitting mid-sentence breaks both narration
  and subtitle sync — split at meaning boundaries only.
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