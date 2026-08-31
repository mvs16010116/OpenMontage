# Compose Director - Narration Synth Pipeline

## When To Use

The edit decisions exist with a timeline of SLOTS (one per generated shot, each
with its layered materials), subtitle style, and audio layout. You render the
final master: regenerate subtitles from real narration offsets, **overlay each
slot's materials into one shot image, then concatenate the shots**, burn the
subtitles, rebuild the narration mix back-to-back, mux narration + music, and
prove the output correct. You produce TWO
artifacts: `render_report` (render evidence) and `final_review` (structured
self-review).

## Runtime Routing (HARD CONSTRAINT)

`render_runtime="ffmpeg"`. Scene animations (material layers) were rendered **at
the assets stage** via `npx hyperframes render`. Compose is ffmpeg-native:
per-slot overlay (filter_complex) → concat → `video_compose` ASS subtitle burn →
narration/music mux.

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
| Prior artifact | `state.artifacts["edit"]["edit_decisions"]` | Slots, materials, subtitles, audio, render grammar |
| Prior artifact | `state.artifacts["assets"]["asset_manifest"]` | Material MP4s, narration ticks, real durations |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, tone |
| Tool | `video_compose` (ffmpeg) | Per-slot overlay + concat + subtitle burn + audio mux |
| Tool | `ass-subtitle-generator` | Regenerates short-line `.ass` from real narration offsets |
| Tool | `audio_mixer` | Rebuilds narration-mix back-to-back (or ffmpeg adelay+amix) |

## Mental Model

Compose seals the CONTRACT between words and image. The narration audio is real;
section timings were estimates. Make on-screen text match what is actually said,
at the moment it is said, over the layered + concatenated generated shots. Then
prove it.

Never trust estimated timings for the final burn. Always regenerate subtitles from
real narration offsets (`ass-subtitle-generator`).

## Process

### 0. Hard Requirement Check

STOP and surface if:

- `brief.metadata.narration_plan.enabled` is true but no narration assets exist —
  render would be silent on a narration spine.
- `edit_decisions.renderer_family` is not `"narration-synth"`.
- `edit_decisions.render_runtime` is not `"ffmpeg"`.

### 1. Overlay Materials Per Slot, Then Concat (from edit)

The master timeline is the SLOT list in `edit_decisions.slots` order. Two passes:

**Pass A — assemble each shot:** for every slot, overlay its materials in `layer`
order via ffmpeg `filter_complex` (background on the bottom, then midground, then
foreground on top; each material's transparent WebM/MP4 composites over the one
below). Trim each material to its `in/out` from the slot. Output one composed shot
file per slot: `projects/<name>/assets/video/shot_<scene_id>.mp4`.

**Pass B — concatenate shots:** concatenate the composed shots in slot/scene
order. Bookends listed first/last; sentence-shot slots in scene order. Verify every
referenced material MP4 exists and every composed shot exists before continuing.

A slot with ONE material still goes through Pass A (identity copy) so the concat
is uniform.

### 2. Force-Align Subtitles To Real Audio (CRITICAL)

1. Collect every narration asset (`type: "narration"`) with REAL probed duration.
2. Add the section windows to the script artifact and regenerate `subtitles.ass`
   via the **`ass-subtitle-generator`** skill — it reads
   `script.sections[].start_seconds` (real narration offsets, not cumulative
   durations) and writes a short-line 1920x1080 ASS that stays inside each
   narration window even with opener/chapter-card silence.
3. Build the subtitle file — static whole-line, NO `\k` karaoke markers,
   ≤16 chars/line, ASS-format colors (see the ass-subtitle-generator SKILL.md
   "black-text trap" — HTML hex renders black).
4. Write to `projects/<name>/assets/subtitles.ass`. Skip `exclude_scene_ids`
   (bookends) — they carry their own typography.
5. If a narration's probed duration differs from the scene window estimate by
   >15%, re-check the scene window and flag it in `warnings`.

**Narration mix — back-to-back, not gapped.** The narration master is rebuilt at
compose so sections tile seamlessly: section N's end = section N+1's start. The
ONLY silence is at the opener + chapter-card holds. Use `audio_mixer` (or ffmpeg
`adelay`+`amix` over an `anullsrc` base) to place each narration at its real
start; the base track length = last narration end (~131.98s above). A rendered
master with dead seconds between chapters means the mix was built with gaps —
re-mix, don't ship it.

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
    "audio_path": "projects/<name>/assets/audio/narration_mix.mp3",
    "subtitle_path": "projects/<name>/assets/subtitles.ass",
    "options": {"subtitle_burn": True},
})
```

Read the live `video_compose` schema at render time (`agent_skills`: `ffmpeg`,
`hyperframes-core`). Pass the two key paths explicitly:
- `audio_path` → the reconstructed narration mix (back-to-back narration +
  silence at opener/cards). Concat of clips may pass through
  `edit_decisions.cuts` — do not invent parameters.
- `subtitle_path` → the generated `subtitles.ass`; keep `subtitle_burn` on.
  The in-tool post-render `subtitle_check` looks for a subtitle STREAM and will
  report burn-ins as "not found" — that is a false positive; verify burned pixels,
  not streams (step 5).

Encoder: libx264 / yuv420p / CRF 18 / aac / 192k.

### 5. Verify The Render (Do Not Skip)

ffprobe the output + sample frames:

- **Duration** — within ±1s of planned total.
- **Resolution** — matches canvas.
- **Audio** — narration + music present (or planned silence).
- **Subtitles** — 3+ frames from the subtitle region; readable, not clipped, no
  `\k`. Since burn-in is invisible to ffprobe streams, do a **pixel check**: crop
  the lower band (~bottom 200px) and confirm a bright white-pixel share on
  subtitle frames vs a near-zero share on a bookend (no-subtitle) frame; a black
  subtitle regression shows ~0.
- **Frame variety** — sample opening/middle/closing frames; confirm the generated
  scenes appear (not black, not a repeated single scene); no blank gaps.
- **Audio layout** — volumedetect at each narration window (present) and at the
  opener/chapter cards (≈ -91 dB pure silence); dead seconds between chapters =
  mix was gapped.
- **Scene cuts** — shot boundaries land at sentence-shot transitions (and bookend
  breaks); each shot shows its intended layering (background visible under
  foreground overlays, not one material hiding another).
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
    "Shots assembled by overlaying materials in layer order, then concatenated in edit order (6 shots, 0 missing)",
    "Subtitle burn verified: 4 frames sampled, text readable, no karaoke markers",
    "Overlay sampled: foreground data visible over background at scene_02 frames",
    "Narration present and sync spot-checked within 1s at section_02 line"
  ],
  "render_grammar": "narration-synth",
  "final_review_ref": "projects/<name>/artifacts/final_review.json",
  "metadata": {
    "pipeline": "narration-synth",
    "canvas": { "width": 1920, "height": 1080 },
    "subtitles_generated_ass": true,
    "subtitles_short_lines": true,
    "generated_scene_count": 6,
    "materials_overlaid": true,
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
- `render_report.metadata.subtitles_generated_ass = true` (regenerated from real
  narration offsets, not estimated timings).
- `final_review.checks.subtitle_check.subtitles_present = true`.
- `final_review.checks.audio_spotcheck.narration_present = true` (or explicit
  opt-out honored).
- `final_review.checks.promise_preservation.runtime_swap_detected = false`.
- `final_review.checks.visual_spotcheck.missing_scenes = false`.
- Every substitution listed in `warnings`.

## Common Pitfalls

- **Burning estimated timings.** Always regenerate subtitles from real narration
  offsets via ass-subtitle-generator.
- **Skipping the runtime check.** Pass `proposal_packet`, report honestly.
- **Re-rendering scenes at compose.** Material MP4s are already done; compose
  overlays + concats.
- **Overlaying in the wrong order** (foreground under background) → the shot is
  broken; always compose background → midground → foreground.
- **Opaque foreground materials.** A foreground rendered WITHOUT alpha hides the
  background and reads as a single flat frame — the overlay check catches it.
- **Concat order drift** — the master must follow `edit_decisions.slots` order; an
  un-ordered concat breaks the section arc.
- **No-`proposal_packet` runtime swap.** `skipped` check = governance finding.
- **Word-by-word/karaoke subtitles.** `\k` is an automatic fail.
- **Counting a burn-in as missing.** `subtitle_check` looks for a subtitle STREAM;
  a burned-in ASS reports "not found" — that's expected. Verify pixels, not
  streams.
- **Gapped narration mix.** Dead seconds between chapters means the mix wasn't
  rebuilt back-to-back. Re-mix with silence only at opener/cards.
- **Presenting a failed render.** Fix and re-render.
- **Editing slots at compose time.** Adjustments belong in edit_decisions.

## When The Render Fails

1. Categorize (auth / provider / tool bug / plan quality).
2. Missing scene MP4 → validate every asset path; re-run that scene's generation
   spec at the assets stage (do not substitute a different skill silently).
3. Codec issues → normalize through `video_stitch`/`video_trimmer` first.
4. Surface before downgrading. There is no stock-footage fallback on this pipeline.