# Asset Director - Narration Synth Pipeline

## When To Use

The scene plan exists. You produce the raw material the edit needs: **one
self-generated animation MP4 per scene** (executing each `generation_spec` through
its `military-*` skill), the narration audio (TTS) per section, and the music bed.
The output is an `asset_manifest` with full provenance on every asset.

Three workstreams, run in parallel where possible: (A) self-generated scene
animations, (B) narration TTS, (C) music.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation (supports `type: "animation"`) |
| Prior artifact | `state.artifacts["scene_plan"]["scene_plan"]` | Scenes + generation_specs |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, voice_performance, delivery cues |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, visual_register |
| Layer 3 | `.agents/skills/military-*/SKILL.md` | Per-skill build + verify commands (MANDATORY) |
| Layer 3 | `hyperframes-core` / `hyperframes-cli` | Deterministic composition + render contract |
| Tool | `tts_selector` | Narration (route through selector) |

## Workstream A — Self-Generated Scene Animations

### A1. Per-Scene Execution

For each scene, read its `generation_spec`:

1. **Build the composition:** run `node <build_script> --project <name> <cli_args>`
   from the project root. This writes
   `projects/<name>/hyperframes/index.html` (each scene overwrites the workspace —
   render immediately after building, per scene, so no scene's HTML is lost).
   Use a scratch copy if a skill can't parameterize every scene; the *output MP4*
   is the artifact, not the intermediate HTML.
2. **Lint + validate:** `npx hyperframes lint` then `npx hyperframes validate`
   (or `hyperframes_compose` `operation="lint"` / `"validate"`). **0 errors
   required** before render. Record the result in `metadata.validation_results`.
3. **Render to MP4:**
   `npx hyperframes render . --skill=<skill> -o projects/<name>/assets/video/<scene_id>.mp4`
   Set the render length to the scene window (`scene.end_seconds - start_seconds`),
   matching the skill's duration flag; render at 1920x1080, 30fps.
4. **Probe the output:** confirm resolution 1920x1080, real `duration_seconds`,
   has video. Record these.

### A2. Provenance

Every animation asset records:
`provider: "self_generated"`, `subtype: "hyperframes_military"`,
`skill: <skill name>`, `build_script`, `cli_args` (full), `seed` (if any),
`generation_summary` (one line), `license: "procedurally generated — no external
rights required"`.

### A3. Global Dedup

Every scene generates its OWN composition from its OWN spec — there is no shared
clip pool to dedup. But enforce: **one output MP4 per scene, and no scene's spec
is a duplicate of a neighbor's** (adjacent identical specs would produce identical
animation → reads as a render bug). Log near-duplicate specs in
`metadata.rejected_specs`.

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

`type: "narration"`, `provider` from the plan, `scene_id` = the section's scene,
`voice_performance` filled, real duration.

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
      "id": "asset_scene_02_animation",
      "type": "animation",
      "path": "projects/<name>/assets/video/scene_02.mp4",
      "source_tool": "military-warship",
      "scene_id": "scene_02",
      "duration_seconds": 8.5,
      "resolution": "1920x1080",
      "format": "mp4",
      "provider": "self_generated",
      "subtype": "hyperframes_military",
      "skill": "military-warship",
      "build_script": ".agents/skills/military-warship/scripts/build_warship.mjs",
      "cli_args": { "--name": "新型驱逐舰", "--hull": "173 号", "--stats": ["满载排水量:12000吨", "垂直发射单元:48", "航速:32节"], "--accent": "#fbbf24", "--palette": "dark" },
      "license": "procedurally generated — no external rights required",
      "generation_summary": "warship silhouette + count-up stats, lint/validate 0 errors, rendered to MP4"
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
    "scene_spec_counts": { "scene_opener": "military-title-card", "scene_02": "military-warship" },
    "validation_results": { "scene_02": "lint 0 errors / validate 0 errors" },
    "rejected_specs": [],
    "narration_voice": "onyx"
  }
}
```

## Quality Gate

- One `animation` asset per scene, from the scene's exact `generation_spec`.
- Every animation asset passed `hyperframes lint` + `validate` with 0 errors
  before render (evidence in `metadata.validation_results`).
- Every animation MP4 is 1920x1080 and `duration_seconds` ≥ scene window.
- No two animation assets share the same `generation_spec` args (adjacency dedup).
- Every narration section has a TTS asset with REAL probed duration (or narration
  explicitly opted out).
- Music asset exists OR `music_plan.source = "none"` with opt-out reason.
- All file paths resolve.
- If a scene fails render or validation, STOP and surface — never silently swap a
  scene to a different skill or leave it missing.

## Common Pitfalls

- **Rendering all scenes into one workspace without saving each MP4.** Render per
  scene, save the MP4 immediately, then rebuild for the next scene.
- **Skipping lint/validate.** "It looks fine in preview" is not the gate; 0 errors
  is the gate.
- **Filing the intermediate HTML instead of the MP4 as the asset.** The edit/compose
  pipeline consumes MP4s.
- **Substituting a different skill when one scene fails.** Surface the blocker.
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