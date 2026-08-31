# Asset Director - Narration Synth Pipeline

## When To Use

The scene plan exists. You produce the raw material the edit needs: **one
self-generated animation MP4 PER MATERIAL** (executing each `materials[].spec`
through its `military-*` skill), the narration audio (TTS) per section, and the
music bed. Each material renders to its OWN transparent-background MP4 at the
scene window length — the edit overlays the materials per shot, then concatenates
shots. The output is an `asset_manifest` with full provenance on every asset.

Three workstreams, run in parallel where possible: (A) self-generated material
animations, (B) narration TTS, (C) music.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation (supports `type: "animation"`) |
| Prior artifact | `state.artifacts["scene_plan"]["scene_plan"]` | Scenes + materials[] + windows |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, voice_performance, delivery cues |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, visual_register |
| Layer 3 | `.agents/skills/military-*/SKILL.md` | Per-skill build + verify commands (MANDATORY) |
| Layer 3 | `hyperframes-core` / `hyperframes-cli` | Deterministic composition + render contract |
| Tool | `tts_selector` | Narration (route through selector) |

## Workstream A — Self-Generated Material Animations

### A1. Per-Material Execution

For each scene, read its `materials[]`. For EACH material, execute ITS spec:

1. **Build the composition:** run `node <build_script> --project <name> <cli_args>`
   from the project root. This writes
   `projects/<name>/hyperframes/index.html` (each material overwrites the workspace —
   render immediately after building, per material, so no composition is lost).
   Use a scratch copy if a skill can't parameterize every material; the *output MP4*
   is the artifact, not the intermediate HTML.
2. **Lint + validate:** `npx hyperframes lint` then `npx hyperframes validate`
   (or `hyperframes_compose` `operation="lint"` / `"validate"`). **0 errors
   required** before render. Record the result in `metadata.validation_results`.
3. **Render to a TRANSPARENT MP4:**
   `npx hyperframes render . --skill=<skill> -o projects/<name>/assets/video/<scene_id>__<material_id>.mp4`
   Render with an alpha channel (WebM-vp9a or qtrle/ProRes-4444 with alpha, per
   the skill's transparency contract) so layers can be overlaid later.
   Set the render length to the SCENE window (`scene.end_seconds - start_seconds`) —
   ALL materials in a shot share that window; render at 1920x1080, 30fps.
4. **Probe the output:** confirm resolution 1920x1080, real `duration_seconds`,
   has video + alpha, duration ≈ scene window. Record these. A material whose
   render is shorter than the window is trimmed at edit time with a
   `metadata.duration_deltas` annotation.

### A2. Provenance

Every animation asset records:
`provider: "self_generated"`, `subtype: "hyperframes_military"`,
`skill: <skill name>`, `material_id`, `scene_id`, `layer`, `build_script`,
`cli_args` (full), `seed` (if any), `generation_summary` (one line),
`license: "procedurally generated — no external rights required"`.

### A3. Global Dedup

Every material generates its OWN composition from its OWN spec — there is no shared
clip pool to dedup. But enforce: **one output MP4 per material, and no two
materials in the SAME shot carry an identical spec** (identical layers would
produce identical animation → reads as a render bug). Adjacent-scene background
variety is the scene plan's job; the asset stage only rejects exact duplicates
within a shot. Log near-duplicate specs in `metadata.rejected_specs`.

## Workstream B — Narration Audio (tts_selector)

### B1. Read The Narration Plan

`brief.metadata.narration_plan`. If `enabled: false` + opt-out, skip entirely. If
enabled, execute EXACTLY the recorded provider/model/voice — never substitute here.

### B2. Generate One File Per Section

Walk `script.sections[]` (skip `section_opener`/`section_chapter_*` bookends — they
have no narration). Honor `delivery_cues` and `script.voice_performance`. Save as:

```
projects/<name>/assets/audio/narration_<section_id>.mp3
```

Read Layer 3 (`text-to-speech` + the provider skill) first. Use `tts_selector`.

### B3. Verify And Record Real Durations

Probe each file; store the REAL `duration_seconds` in the asset. This replaces
script estimates at compose time.

### B4. Record Narration Assets

`type: "narration"`, `provider` from the plan, `scene_id` = the section's FIRST
scene (narration is per section/paragraph; the section it voices spans its
sentence-shots), `voice_performance` filled, real duration.

## Workstream C — Music Bed

Read `brief.metadata.music_plan`; execute EXACTLY the recorded source
(`library` / `generated` / `none` + opt-out). Never switch music source at this
stage — log a `music_selection` decision first if the user changed it.

## Record The Asset Manifest

```json
{
  "version": "1.0",
  "assets": [
    {
      "id": "asset_scene_02_mat_bg",
      "type": "animation",
      "path": "projects/<name>/assets/video/scene_02__scene_02_mat_bg.webm",
      "source_tool": "military-map-deduction",
      "scene_id": "scene_02",
      "material_id": "scene_02_mat_bg",
      "layer": "background",
      "duration_seconds": 8.5,
      "resolution": "1920x1080",
      "format": "webm",
      "has_alpha": true,
      "provider": "self_generated",
      "subtype": "hyperframes_military",
      "skill": "military-map-deduction",
      "build_script": ".agents/skills/military-map-deduction/scripts/build_map.mjs",
      "cli_args": { "--theatre": "西太平洋", "--arrows": ["第一岛链", "宫古海峡"], "--accent": "#fbbf24", "--palette": "dark" },
      "license": "procedurally generated — no external rights required",
      "generation_summary": "theatre map background, lint/validate 0 errors, rendered transparent WebM"
    },
    {
      "id": "asset_scene_02_mat_fg",
      "type": "animation",
      "path": "projects/<name>/assets/video/scene_02__scene_02_mat_fg.webm",
      "source_tool": "military-data-viz",
      "scene_id": "scene_02",
      "material_id": "scene_02_mat_fg",
      "layer": "foreground",
      "duration_seconds": 8.5,
      "resolution": "1920x1080",
      "format": "webm",
      "has_alpha": true,
      "provider": "self_generated",
      "subtype": "hyperframes_military",
      "skill": "military-data-viz",
      "build_script": ".agents/skills/military-data-viz/scripts/build_viz.mjs",
      "cli_args": { "--series": ["驱逐舰数量:8", "护卫舰数量:12"], "--accent": "#fbbf24", "--palette": "dark" },
      "license": "procedurally generated — no external rights required",
      "generation_summary": "animated bar data overlay, lint/validate 0 errors, rendered transparent WebM"
    },
    {
      "id": "asset_narration_section_02",
      "type": "narration",
      "path": "projects/<name>/assets/audio/narration_section_02.mp3",
      "source_tool": "tts_selector",
      "scene_id": "scene_02",
      "duration_seconds": 8.6,
      "format": "mp3",
      "provider": "openai_tts",
      "model": "gpt-4o-mini-tts",
      "voice": "onyx",
      "language": "zh-CN",
      "voice_performance": { "source_section_id": "section_02", "delivery_cues_applied": true },
      "subtype": "narration_tts"
    }
  ],
  "metadata": {
    "pipeline": "narration-synth",
    "material_counts": { "scene_02": { "background": "military-map-deduction", "foreground": "military-data-viz" } },
    "validation_results": { "scene_02__scene_02_mat_bg": "lint 0 errors / validate 0 errors", "scene_02__scene_02_mat_fg": "lint 0 errors / validate 0 errors" },
    "rejected_specs": [],
    "narration_voice": "onyx"
  }
}
```

## Quality Gate

- One `animation` asset PER MATERIAL, from that material's exact spec; all
  materials of a shot present so the edit can overlay a complete frame.
- Every animation asset passed `hyperframes lint` + `validate` with 0 errors
  before render (evidence in `metadata.validation_results`).
- Every animation MP4 is 1920x1080, has alpha, and `duration_seconds` ≈ scene
  window (all layers of one shot match).
- No two animation assets in the SAME shot share identical `cli_args`.
- Every narration section has a TTS asset with REAL probed duration (or narration
  explicitly opted out).
- Music asset exists OR `music_plan.source = "none"` with opt-out reason.
- All file paths resolve.
- If a material fails render or validation, STOP and surface — never silently swap
  a material to a different skill or leave a shot's layer missing.

## Common Pitfalls

- **Rendering all materials into one workspace without saving each MP4.** Render
  per material, save the MP4 immediately, then rebuild for the next material.
- **Skipping lint/validate.** "It looks fine in preview" is not the gate; 0 errors
  is the gate.
- **Filing the intermediate HTML instead of the MP4 as the asset.** The edit/compose
  pipeline consumes MP4s/WebMs.
- **Rendering without alpha.** Layers must composite over the shot background —
  an opaque foreground MP4 would hide the background instead of overlaying it.
- **Substituting a different skill when one material fails.** Surface the blocker.
- **Trusting script estimates as final narration times.** Probe real durations.
- **Substituting the approved TTS voice at this stage.** Governance violation; log
  a `voice_selection` decision first if it must change.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact — the filmstrip shows each scene's generated animation), and **END YOUR TURN**.
Do not start the next stage in the same response. Approval is per-gate — an earlier
"go ahead" does not cover this gate.