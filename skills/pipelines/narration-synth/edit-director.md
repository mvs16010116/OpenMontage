# Edit Director - Narration Synth Pipeline

## When To Use

Every scene has its generated animation MP4, every section has narration audio,
the music bed is locked. You build the timeline: **one generated scene per
section**, subtitle style, audio layout, and the render grammar. The output is the
`edit_decisions` artifact.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["assets"]["asset_manifest"]` | Scene animations + narration + music paths |
| Prior artifact | `state.artifacts["scene_plan"]["scene_plan"]` | Scene windows, hero flags, bookend roles |
| Prior artifact | `state.artifacts["idea"]["brief"]` | tone, subtitle_style, bookend_plan |

## Mental Model

There is no multi-clip cadence here. Each scene's animation is **a single
generated shot** that fills its window. The edit's job is placement, not re-cutting:
put scene N's MP4 into timeline slot N, bookends at their slots, narration at the
section starts, subtitles force-aligned. Restraint still rules — the piece must
breathe, but the variety comes from skill choice (scene plan) not from re-cutting.

## Process

### 0. Guardrails — No Silent Major Changes

Re-read the brief. STOP and surface if: a different TTS voice was generated than
approved; narration was opted out but the edit wants to add a voice-over; the
approved duration changed materially.

### 1. Place One Cut Per Generated Scene

Walk the scene plan in order. Each scene (including bookends) becomes exactly ONE
cut:

- `cut.source` = the scene's animation asset_id.
- `in_seconds` = 0.0 (the animation is authored to its full window).
- `out_seconds` = scene window length (`scene.end_seconds - scene.start_seconds`).
- Handle any delta: if the render duration ≠ window (skill-capped), trim
  `in/out` to the render length and annotate in `metadata.duration_deltas`.
- `transition_in`/`transition_out`: default `cut`; bookends and the first/last
  scene use `fade_in`/`fade_out`. No wipes/pushes — this pipeline's register is
  documentary-clean.
- `reason` on every cut — one line tying the scene to its section's line.

Never split a scene animation into sub-shots. It reads as a render bug and breaks
one-scene-per-section.

### 2. Enforce Adjacent Variety

Walk cuts pairwise. Same `generation_spec.skill` in two adjacent cuts? The scene
plan should already prevent it — if you see it, go back and re-plan, don't paper
over it at edit time. Log the check in `metadata.adjacency_notes`.

### 3. Set The Subtitle Contract

Static whole-line burn, force-aligned source (identical to narration-montage):

```json
{
  "subtitles": {
    "enabled": true,
    "style": "static_whole_line",
    "source": "force_aligned",
    "font_size": 56,
    "color": "#FFFFFF",
    "outline_color": "#000000",
    "background": "#00000080",
    "position": "bottom-center",
    "max_words_per_line": 12
  }
}
```

Chinese narration → ~16-18 chars/line at 56px. Bookend scenes (title cards)
usually don't need burned subtitles — they carry their own typography; note
`subtitles.exclude_scene_ids: ["scene_opener", ...]`.

### 4. Set The Audio Layout

Narration (spine) + music (support):

```json
{
  "audio": {
    "narration": {
      "segments": [
        { "asset_id": "asset_narration_section_02", "start_seconds": 5.5, "end_seconds": 14.1 }
      ]
    },
    "music": {
      "asset_id": "asset_music_bed",
      "volume": 0.35,
      "fade_in_seconds": 1.0,
      "fade_out_seconds": 3.0,
      "ducking": { "enabled": true, "threshold_db": -20, "reduction_db": 8 }
    }
  }
}
```

Bookend scenes carry no narration — place narration segments only at real section
starts. Music low (0.25-0.4), ducking ON.

### 5. Lock The Render Grammar (BINDING)

```json
{
  "renderer_family": "narration-synth",
  "render_runtime": "ffmpeg"
}
```

`render_runtime` MUST stay `"ffmpeg"`. Scene animation MP4s are already rendered at
the assets stage (via `npx hyperframes render`); compose concatenates them + burns
subtitles + muxes audio through `video_compose`'s ffmpeg path. A silent swap to
Remotion or a full HyperFrames timeline is a CRITICAL governance violation.

### 6. Emit The Edit Decisions

```json
{
  "version": "1.0",
  "renderer_family": "narration-synth",
  "render_runtime": "ffmpeg",
  "cuts": [
    {
      "id": "cut_opener",
      "source": "asset_scene_opener_animation",
      "in_seconds": 0.0,
      "out_seconds": 3.0,
      "layer": "primary",
      "transition_in": "fade_in",
      "transition_out": "cut",
      "transition_duration": 0.5,
      "reason": "opener — center title card under the hook"
    },
    {
      "id": "cut_02",
      "source": "asset_scene_02_animation",
      "in_seconds": 0.0,
      "out_seconds": 8.5,
      "layer": "primary",
      "transition_in": "cut",
      "transition_out": "cut",
      "reason": "scene_02 — warship specs animation under the tonnage + VLS line"
    }
  ],
  "audio": { "...": "as above" },
  "subtitles": { "...": "as above", "exclude_scene_ids": ["scene_opener"] },
  "metadata": {
    "pipeline": "narration-synth",
    "scene_count": 6,
    "hero_scenes": ["scene_opener", "scene_02"],
    "total_duration_seconds": 93.0,
    "adjacency_notes": [],
    "duration_deltas": []
  }
}
```

### 7. Quality Gate

- `renderer_family = "narration-synth"` and `render_runtime = "ffmpeg"` carried
  unchanged from proposal.
- One cut per scene; no scene split into repeated sub-shots.
- Bookends present at opener + chapter breaks with no narration attached.
- `subtitles.enabled = true`, style static whole-line, `source = "force_aligned"`,
  bookend scenes excluded.
- Audio layout matches brief (music low, ducking on, narration at section starts).
- Every cut has a `reason`.
- Timeline duration within ±10% of `script.total_duration_seconds` (+ bookends).

## Common Pitfalls

- Splitting a generated scene into sub-shots to "add rhythm". The animation is the
  shot; the scene plan already varied the skill.
- Forgetting bookends have no narration, then placing a narration segment in an
  empty slot.
- `render_runtime` set to anything but `"ffmpeg"`. Scene generation already
  happened at assets; compose is ffmpeg concat + burn + mux.
- Word-by-word/karaoke subtitles — hard fail.
- Music at narration level, or without ducking.
- Bookends without `scene_opener`/`section_chapter_*` ids leaking into subtitle
  timing.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.