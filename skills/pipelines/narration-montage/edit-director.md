# Edit Director - Narration Montage Pipeline

## When To Use

Every scene has its clips, every section has its narration audio, the
music bed is locked. You now build the timeline: a fixed shot cadence,
one full shot per distinct clip, subtitle style, and the audio layout.
The output is an `edit_decisions` artifact with a concrete cut list.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["assets"]["asset_manifest"]` | Clips + narration + music paths |
| Prior artifact | `state.artifacts["scene_plan"]["scene_plan"]` | Scene windows, framing/movement, hero flags |
| Prior artifact | `state.artifacts["idea"]["brief"]` | tone, shot_cadence_seconds, subtitle_style |

## Mental Model

Narration montage is **restraint editing**. The voice owns the rhythm;
the visuals simply need to keep up without calling attention to
themselves. Two rules dominate:

1. **Fixed cadence, mostly.** A steady shot length (default 3.0s) keeps
   the piece predictable and breathable. Hero scenes MAY stretch to
   4-5s; nothing else does.
2. **One full shot per clip.** Every `cut.source` is a distinct asset.
   Never re-cut a clip to reuse it in a second cut — that reads as a
   render bug and breaks the dedup contract the asset stage built.

This stage also LOCKS the render grammar: `renderer_family =
"narration-montage"` and `render_runtime = "ffmpeg"`. Both are carried
forward unchanged to compose.

## Process

### 0. Guardrails — No Silent Major Changes

Re-read the brief before touching the timeline. STOP and surface per
the Decision Communication Contract if any of these are true:

- The brief approved a specific voice but a different voice was
  generated. Voice is a MAJOR production choice.
- The brief approved `narration: "none"` (opt-out) but the edit wants
  to add a voice-over. Major change.
- The brief approved a 78s piece but the natural cut wants 120s.
  Duration stretch is a MAJOR change.

### 1. Set The Shot Cadence

Read `brief.metadata.shot_cadence_seconds` (default 3.0). This is the
base shot length. Hero scenes (`hero_moment: true`) may hold 4-5s.
Never let any single clip exceed ~6s on this pipeline — the piece is
narration-led; a 10-second B-roll hold under continuing speech becomes
a slideshow.

### 2. Build One Cut Per Shot

For each scene, in timeline order, walk its asset clips and create one
cut per clip. Rules:

- `cut.source` = the asset_id (provenance survives via the manifest).
- `in_seconds` / `out_seconds` = the clip's usable window. Prefer a
  3-4s sub-window if the clip is long; never play the whole thing to
  the end (leave a handle).
- `transition_in`/`transition_out`: default `cut` (hard). Bookends:
  first cut `fade_in`, last cut `fade_out`. Do NOT use wipes/push/zoom
  transitions — this pipeline's register is documentary-clean.
- `reason` on EVERY cut — one line saying what it shows and why it's
  here. If you can't write one, the cut is arbitrary.

Scene clip count must match the asset stage's quota
(`ceil(section_duration / cadence) + 3`). The +3 buffer means some
clips go unused — that's expected. Pick the best-fitting `+3` clips and
leave the rest.

### 3. Enforce Adjacent Variety

Walk the cut list in pairs. For each consecutive (cut_n, cut_n+1):

- Same `framing` AND same `movement` (from the scene's `shot_language`)?
  Swap one out for a different-scale clip. A wide-static followed by a
  wide-static reads as one long clip.
- Same visual register (two night-dark clips back to back)? Break the
  pattern at least every 4 cuts.
- Same Pexels video_id? **IMPOSSIBLE** if the asset stage dedup ran —
  if you see it, it's a bug: stop and re-check the asset manifest.

Log swaps in `metadata.diversity_notes`.

### 4. Set The Subtitle Contract

Narration-montage subtitles are **static whole-line burn**: one complete
line per timed window, force-aligned to real speech. Never word-by-word,
never karaoke (\k markers). Set `edit_decisions.subtitles`:

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

The `source` field documents the timing origin: `force_aligned` (real
audio via `transcriber` at compose time) is the ONLY acceptable value —
estimated timings are never burned. The compose stage does the actual
alignment; here you lock the STYLE.

For Chinese narration, `max_words_per_line` applies to characters
(~16-18 chars/line is comfortable at 56px). Keep the style values from
the brief's `metadata.subtitle_style` unless there's a reason to refine.

### 5. Set The Audio Layout

The audio stack is: narration (spine) + music (support). In
`edit_decisions.audio`:

```json
{
  "audio": {
    "narration": {
      "segments": [
        {
          "asset_id": "asset_narration_section_01",
          "start_seconds": 0.0,
          "end_seconds": 4.6
        }
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

- Music volume is LOW (0.25-0.4) — it supports speech, never competes.
- `ducking` is ON: narration dips the music. This pipeline has speech
  throughout, so ducking is the default, not an exception.
- `narration.segments` place each narration asset at the scene window
  start (`scene.start_seconds`). The compose stage refines against real
  aligned audio.

### 6. Lock The Render Grammar (BINDING)

Set BOTH fields explicitly — the schema requires `render_runtime`, and
`video_compose._pre_compose_validation` hard-blocks render without
`renderer_family`:

```json
{
  "renderer_family": "narration-montage",
  "render_runtime": "ffmpeg"
}
```

**Neither may change at compose time.** `render_runtime` must stay
`"ffmpeg"` — narration-montage renders via video_compose's ffmpeg path
(ASS subtitle burn + narration/music mux). Remotion and HyperFrames are
NOT valid runtimes on this pipeline. A silent swap is a CRITICAL
governance violation. If the ffmpeg path becomes unavailable at compose,
surface a structured blocker — never route to Remotion as a "fallback".

### 7. Emit The Edit Decisions

```json
{
  "version": "1.0",
  "renderer_family": "narration-montage",
  "render_runtime": "ffmpeg",
  "cuts": [
    {
      "id": "cut_01",
      "source": "asset_scene_01_v1",
      "in_seconds": 0.0,
      "out_seconds": 3.0,
      "layer": "primary",
      "transform": { "scale": 1.0, "position": "center" },
      "transition_in": "fade_in",
      "transition_out": "cut",
      "transition_duration": 0.5,
      "reason": "scene_01 hook — server room wide shot under the opening line"
    },
    {
      "id": "cut_02",
      "source": "asset_scene_01_v2",
      "in_seconds": 0.5,
      "out_seconds": 3.5,
      "layer": "primary",
      "transition_in": "cut",
      "transition_out": "cut",
      "reason": "scene_01 — rack close-up, varies scale from cut_01"
    }
  ],
  "audio": {
    "narration": {
      "segments": [
        { "asset_id": "asset_narration_section_01", "start_seconds": 0.0, "end_seconds": 4.6 }
      ]
    },
    "music": {
      "asset_id": "asset_music_bed",
      "volume": 0.35,
      "fade_in_seconds": 1.0,
      "fade_out_seconds": 3.0,
      "ducking": { "enabled": true, "threshold_db": -20, "reduction_db": 8 }
    }
  },
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
  },
  "metadata": {
    "pipeline": "narration-montage",
    "shot_cadence_seconds": 3.0,
    "hero_scenes": ["scene_01", "scene_07"],
    "total_duration_seconds": 78.0,
    "diversity_notes": [
      { "at": "cut_04-cut_05", "reason": "two wide-static server shots adjacent, swapped 05 for the close-up" }
    ]
  }
}
```

### 8. Quality Gate

- `renderer_family = "narration-montage"` and `render_runtime =
  "ffmpeg"` present and unchanged from proposal.
- Shot cadence is fixed (`metadata.shot_cadence_seconds`); no clip holds
  longer than ~6s except hero scenes.
- One full shot per distinct clip — no cut reuses another cut's source.
- `subtitles.enabled = true`, `subtitles.style` is a static whole-line
  mode, `subtitles.source = "force_aligned"`.
- Audio layout matches the brief's narration_plan + music_plan (music
  low, ducking on).
- Every cut has a `reason`.
- Timeline duration (sum of cut durations) within ±10% of
  `script.total_duration_seconds`.

## Common Pitfalls

- **Long holds under continuing speech.** A 3s cadence exists so the
  piece breathes. Breaking it on every scene re-creates a slideshow.
- **Reusing a clip.** The +3 buffer means you should never need to.
  If a scene is short, cut to the buffer, don't recycle.
- **Forgetting `renderer_family`.** `video_compose` hard-blocks on it.
  Lock it here.
- **Setting `render_runtime` to remotion** because the footage is nice.
  This pipeline renders via ffmpeg — that's the contract.
- **Word-by-word or karaoke subtitles.** Static whole-line only. \k
  markers are a hard fail in final review.
- **Music at narration level.** Music sits at 0.25-0.4 with ducking on.
  If you can't hear the words, the mix is wrong.
- **Transitions that call attention.** Hard cuts, one fade-in, one
  fade-out. No wipes, no pushes, no zoom-blurs.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
