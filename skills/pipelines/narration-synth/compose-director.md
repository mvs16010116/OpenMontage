# Compose Director - Narration Synth Pipeline

## When To Use

The edit decisions exist with a cut list (one per generated scene), subtitle
style, and audio layout. You render the final master: force-align subtitles to the
real narration audio, **concatenate the generated scene MP4s**, burn the
subtitles, mux narration + music, and prove the output correct. You produce TWO
artifacts: `render_report` (render evidence) and `final_review` (structured
self-review).

## Runtime Routing (HARD CONSTRAINT)

`render_runtime="ffmpeg"`. Scene animations were rendered to MP4 **at the assets
stage** via `npx hyperframes render`. Compose is ffmpeg-native: concat →
`video_compose` ASS subtitle burn → narration/music mux.

- If `edit_decisions.render_runtime` is anything but `ffmpeg`, STOP. Critical
  governance violation — surface, re-lock, log a `render_runtime_selection`
  correction, resume.
- Close a loop: the SCENES are HyperFrames-rendered, but this FINISHING pass is
  ffmpeg. Do not re-render scenes here; do not route the final master through a
  live HyperFrames timeline.
- Pass `proposal_packet` to `video_compose.execute()` so the in-tool
  `runtime_swap_detected` check confirms `ffmpeg` end-to-end.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Render evidence |
| Schema | `schemas/artifacts/final_review.schema.json` | Post-render self-review |
| Prior artifact | `state.artifacts["edit"]["edit_decisions"]` | Cuts, subtitles, audio, render grammar |
| Prior artifact | `state.artifacts["assets"]["asset_manifest"]` | Scene MP4s, narration ticks, real durations |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, tone |
| Tool | `video_compose` (ffmpeg) | Concat + subtitle burn + audio mux |
| Tool | `transcriber` | Force-align subtitles to real narration audio |
| Tool (optional) | `subtitle_gen` | Build subtitle file from aligned timings |

## Mental Model

Compose seals the CONTRACT between words and image. The narration audio is real;
section timings were estimates. Make on-screen text match what is actually said,
at the moment it is said, over the concatenated generated scenes. Then prove it.

Never trust estimated timings for the final burn. Always force-align.

## Process

### 0. Hard Requirement Check

STOP and surface if:

- `brief.metadata.narration_plan.enabled` is true but no narration assets exist —
  render would be silent on a narration spine.
- `edit_decisions.renderer_family` is not `"narration-synth"`.
- `edit_decisions.render_runtime` is not `"ffmpeg"`.

### 1. Concat Order (from edit)

The master timeline is the cut list in `edit_decisions.cuts` order. Build a concat
source from each cut's animation MP4 (`asset_manifest` path) with the cut window.
Bookends listed first/last; scene cuts in scene order. Verify every referenced MP4
exists before composing.

### 2. Force-Align Subtitles To Real Audio (CRITICAL)

1. Collect every narration asset (`type: "narration"`) with REAL probed duration.
2. Align each narration text to its actual audio via `transcriber`/`subtitle_gen`,
   producing per-line timestamps that match the audio's real boundaries.
3. Build the subtitle file — static whole-line, NO `\k` karaoke markers; follow
   `edit_decisions.subtitles` style (font size, color, position).
4. Write to `projects/<name>/assets/subtitles.srt`. Skip `exclude_scene_ids`
   (bookends) — they carry their own typography.
5. If a narration's probed duration differs from the scene window estimate by
   >15%, re-check the scene window and flag it in `warnings`.

### 3. Resolve The Canvas

`brief.target_platform`: youtube/generic → 1920x1080; instagram/tiktok → 1080x1920.
Scene MP4s are authored 1920x1080; center-crop/scale to the canvas. Commit in
`render_report.metadata.canvas`.

### 4. Render Via video_compose (ffmpeg)

```python
video_compose.execute({
    "operation": "render",
    "output_path": "projects/<name>/renders/final.mp4",
    "edit_decisions": edit_decisions,      # renderer_family=narration-synth, render_runtime=ffmpeg
    "asset_manifest": asset_manifest,
    "proposal_packet": proposal_packet,     # so runtime_swap_detected runs
    "subtitles_path": "projects/<name>/assets/subtitles.srt",
})
```

Read the live `video_compose` schema at render time (`agent_skills`: `ffmpeg`,
`hyperframes-core`) — concat of clips may pass through `edit_decisions.cuts` or a
dedicated concat param. Do not invent parameters.

Encoder: libx264 / yuv420p / CRF 18 / aac / 192k.

### 5. Verify The Render (Do Not Skip)

ffprobe the output + sample frames:

- **Duration** — within ±1s of planned total.
- **Resolution** — matches canvas.
- **Audio** — narration + music present (or planned silence).
- **Subtitles** — 3+ frames from the subtitle region; readable, not clipped, no
  `\k`.
- **Frame variety** — sample opening/middle/closing frames; confirm the generated
  scenes appear (not black, not a repeated single scene); no blank gaps.
- **Scene cuts** — the cut boundaries land at section transitions.
- **Sync spot-check** — at a known narration line, on-screen text matches the
  spoken words within ~1s.

### 6. Emit The Render Report

```json
{
  "version": "1.0",
  "outputs": [{
    "path": "projects/<name>/renders/final.mp4",
    "format": "mp4", "codec": "h264", "audio_codec": "aac",
    "resolution": "1920x1080", "fps": 30,
    "duration_seconds": 93.0, "file_size_bytes": 18253056,
    "platform_target": "youtube"
  }],
  "render_time_seconds": 40.2,
  "warnings": [
    "section_04 narration probed 18.2s vs 15.5s estimate — timing re-aligned against scene window"
  ],
  "verification_notes": [
    "Scene MP4s concatenated in edit order (6 scenes, 0 missing)",
    "Subtitle burn verified: 4 frames sampled, text readable, no karaoke markers",
    "Narration present and sync spot-checked within 1s at section_02 line"
  ],
  "render_grammar": "narration-synth",
  "final_review_ref": "projects/<name>/artifacts/final_review.json",
  "metadata": {
    "pipeline": "narration-synth",
    "canvas": { "width": 1920, "height": 1080 },
    "subtitles_force_aligned": true,
    "generated_scene_count": 6,
    "narration_present": true,
    "music_present": true
  }
}
```

### 7. Emit The Final Review

Self-review against the RENDERED FILE. Key checks:

- `technical_probe` — ffprobe facts.
- `visual_spotcheck` — ≥4 sampled frames; no black frames, no broken overlays, no
  missing scenes, self-generated animations visibly present.
- `audio_spotcheck` — narration_present, music_present, no unexpected silence.
- `promise_preservation` — `render_runtime_used = "ffmpeg"`,
  `runtime_swap_detected = false`, `renderer_family_used = "narration-synth"`,
  `generated_visuals_confirmed = true` (self-generated scenes, not stock blanks).
- `subtitle_check` — subtitles_expected=true, subtitles_present=true,
  coverage_ratio ≥ 0.9, timing_drift_detected=false.

If `status` is `revise`/`fail`, do NOT present as complete — re-render/revise per
`recommended_action`.

### 8. Quality Gate

- `render_report` and `final_review` validate against schemas.
- Output file exists + passes ffprobe.
- `render_report.metadata.subtitles_force_aligned = true`.
- `final_review.checks.subtitle_check.subtitles_present = true`.
- `final_review.checks.audio_spotcheck.narration_present = true` (or explicit
  opt-out honored).
- `final_review.checks.promise_preservation.runtime_swap_detected = false`.
- `final_review.checks.visual_spotcheck.missing_scenes = false`.
- Every substitution listed in `warnings`.

## Common Pitfalls

- **Burning estimated timings.** Always force-align.
- **Skipping the runtime check.** Pass `proposal_packet`, report honestly.
- **Re-rendering scenes at compose.** Scene MP4s are already done; compose concats.
- **Concat order drift** — the master must follow `edit_decisions.cuts` order; an
  un-ordered concat breaks the section arc.
- **No-`proposal_packet` runtime swap.** `skipped` check = governance finding.
- **Word-by-word/karaoke subtitles.** `\k` is an automatic fail.
- **Presenting a failed render.** Fix and re-render.
- **Editing cuts at compose time.** Adjustments belong in edit_decisions.

## When The Render Fails

1. Categorize (auth / provider / tool bug / plan quality).
2. Missing scene MP4 → validate every asset path; re-run that scene's generation
   spec at the assets stage (do not substitute a different skill silently).
3. Codec issues → normalize through `video_stitch`/`video_trimmer` first.
4. Surface before downgrading. There is no stock-footage fallback on this pipeline.