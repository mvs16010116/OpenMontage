# Compose Director - Narration Montage Pipeline

## When To Use

The edit decisions exist with a cut list, subtitle style, and audio
layout. You now render the final master: force-align subtitles to the
real narration audio, burn them onto the B-roll cut, mux narration +
music, and prove the output is correct. You produce TWO artifacts:
`render_report` (render evidence) and `final_review` (structured
self-review of the rendered output).

## Runtime Routing (HARD CONSTRAINT)

This pipeline REQUIRES `render_runtime="ffmpeg"`. narration-montage
renders via `video_compose`'s ffmpeg path: static ASS subtitle burn +
narration/music mux. **Remotion and HyperFrames are NOT valid runtimes
here.**

- If `edit_decisions.render_runtime` is anything other than `ffmpeg`,
  stop. This is a CRITICAL governance violation. Surface the conflict,
  route the decision back to proposal to re-lock `render_runtime="ffmpeg"`,
  log a `render_runtime_selection` correction, and resume.
- Never silently proceed by rewriting `render_runtime` in
  edit_decisions. The narration promise (words are the spine, subtitles
  match speech) is preserved by the ffmpeg burn path.
- Pass `proposal_packet` to `video_compose.execute()` so the in-tool
  `runtime_swap_detected` check actively confirms the runtime stayed
  `ffmpeg` end-to-end. A `skipped` check means you forgot the artifact.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Render evidence |
| Schema | `schemas/artifacts/final_review.schema.json` | Post-render self-review |
| Prior artifact | `state.artifacts["edit"]["edit_decisions"]` | Cuts, subtitles, audio, render grammar |
| Prior artifact | `state.artifacts["assets"]["asset_manifest"]` | Clip/narration/music paths + real durations |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, tone |
| Tool | `video_compose` (ffmpeg) | Cut + subtitle burn + audio mux |
| Tool | `transcriber` | Force-align subtitles to real narration audio |
| Tool (optional) | `subtitle_gen` | Build subtitle file from aligned timings |
| Tool (optional) | `video_trimmer`, `video_stitch` | Helpers if a render needs splitting |

## Mental Model

Compose is where the CONTRACT between words and image is sealed. The
narration audio is real; the section timings in the script were
estimates. Your job: make the on-screen text match what is actually
said, at the moment it is said. Then render and PROVE it.

Never trust estimated timings for the final burn. Always force-align.

## Process

### 0. Hard Requirement Check

Read `brief` and `edit_decisions` for hard requirements. STOP and
surface if:

- `brief.metadata.narration_plan.enabled` is true but no narration
  assets exist in the manifest. Render would be silent on a narration
  spine — a contract violation.
- `edit_decisions.renderer_family` is not `"narration-montage"`.
- `edit_decisions.render_runtime` is not `"ffmpeg"`.

### 1. Force-Align Subtitles To Real Audio (CRITICAL)

The edit stage set the subtitle STYLE. You produce the TIMING from the
real narration audio:

1. Collect every narration asset from the manifest (`type:
   "narration"`), each with its REAL `duration_seconds` (probed at the
   asset stage).
2. Align each narration asset's text (from `script.sections[].text`,
   matched via the section/scene linkage) to its actual audio using
   `transcriber` (whisper, offline) or `subtitle_gen`. The alignment
   must produce per-line timestamps that match the audio's real
   boundaries.
3. Build the subtitle file (SRT or ASS) with `subtitle_gen`. Static
   whole-line entries — **NO `\k` karaoke markers**, no word-by-word.
   Lines follow the brief's subtitle style (font size, color, position
   from `edit_decisions.subtitles`).
4. Write it to `projects/<project-name>/assets/subtitles.srt` (the
   workspace convention).

The timeline start for each narration segment is its scene window
start (`scene.start_seconds`); alignment refines the offsets inside the
window. If a narration file's probed duration differs from the script
estimate by more than 15%, the section timing should be re-checked
against the scene window — flag it in `warnings`.

### 2. Resolve The Canvas

Read `brief.target_platform`:

| Target | Canvas |
|--------|--------|
| `youtube` / `generic` / `linkedin` | 1920x1080 (16:9) |
| `instagram` / `tiktok` | 1080x1920 (9:16) |

Every clip scales/crops to this canvas (center-crop for 9:16). Commit
it in `render_report.metadata.canvas`.

### 3. Render Via video_compose (ffmpeg)

Pass the full contract to `video_compose`:

```python
video_compose.execute({
    "operation": "render",
    "output_path": "projects/<name>/renders/final.mp4",
    "edit_decisions": edit_decisions,      # renderer_family=narration-montage, render_runtime=ffmpeg
    "asset_manifest": asset_manifest,
    "proposal_packet": proposal_packet,     # so runtime_swap_detected runs
    "subtitles_path": "projects/<name>/assets/subtitles.srt",
})
```

The exact field names come from the live `video_compose` schema at
render time — consult the tool's `agent_skills` (`ffmpeg`, `video-toolkit`)
before writing the call. Do not invent parameters. If the tool exposes
subtitle burn via `edit_decisions.subtitles` instead of a separate
param, follow that path.

Encoder spec:

| Field | Value |
|-------|-------|
| Codec | `libx264` |
| Pixel format | `yuv420p` |
| CRF | `18` |
| Audio codec | `aac` |
| Audio bitrate | `192k` |

### 4. Verify The Render (Do Not Skip)

After render succeeds, PROBE the output file (ffprobe) and SAMPLE
frames. This is the evidence that becomes `final_review`:

- **Duration** — within ±1s of the planned total.
- **Resolution** — matches the canvas.
- **Audio** — narration present and music present (or planned silent).
- **Subtitles** — extract 3+ frames from the subtitle region; text is
  readable, not clipped, no `\k` markers visible.
- **Frame variety** — sample opening/middle/closing frames; no repeated
  frames from a reused clip.
- **Sync spot-check** — at a known narration line, the on-screen text
  matches the spoken words within ~1s.

### 5. Emit The Render Report

```json
{
  "version": "1.0",
  "outputs": [
    {
      "path": "projects/<name>/renders/final.mp4",
      "format": "mp4",
      "codec": "h264",
      "audio_codec": "aac",
      "resolution": "1920x1080",
      "fps": 24,
      "duration_seconds": 78.2,
      "file_size_bytes": 21458944,
      "platform_target": "youtube"
    }
  ],
  "render_time_seconds": 31.5,
  "warnings": [
    "section_04 narration probed 18.2s vs 15.5s estimate — timing re-aligned against scene window"
  ],
  "verification_notes": [
    "Subtitle burn verified: 4 frames sampled, text readable, no karaoke markers",
    "Narration present and sync spot-checked within 1s at section_02 line",
    "Duration within +0.2s of planned 78s"
  ],
  "render_grammar": "narration-montage",
  "final_review_ref": "projects/<name>/artifacts/final_review.json",
  "metadata": {
    "pipeline": "narration-montage",
    "canvas": { "width": 1920, "height": 1080 },
    "subtitles_force_aligned": true,
    "subtitles_path": "projects/<name>/assets/subtitles.srt",
    "narration_present": true,
    "music_present": true
  }
}
```

### 6. Emit The Final Review

Run the self-review (per `skills/meta/reviewer.md`) against the
RENDERED FILE — not against your intent. Use the
`schemas/artifacts/final_review.schema.json` shape. Key checks:

- `technical_probe` — ffprobe facts (duration, resolution, fps,
  has_audio, codec, size).
- `visual_spotcheck` — ≥4 sampled frames (opening/middle/climax/
  ending); flag black frames, broken overlays, missing assets,
  unreadable text.
- `audio_spotcheck` — narration_present, music_present, unexpected
  silence, clipping, mix_intelligible.
- `promise_preservation` — `render_runtime_used = "ffmpeg"`,
  `runtime_swap_detected = false`, `renderer_family_used =
  "narration-montage"`.
- `subtitle_check` — subtitles_expected=true, subtitles_present=true,
  coverage_ratio ≥ 0.9, timing_drift_detected=false.

If `status` is `revise` or `fail`, do NOT present the video as
complete — re-render / revise per `recommended_action`.

```json
{
  "version": "1.0",
  "output_path": "projects/<name>/renders/final.mp4",
  "status": "pass",
  "checks": {
    "technical_probe": {
      "valid_container": true,
      "duration_seconds": 78.2,
      "resolution": "1920x1080",
      "fps": 24,
      "has_audio": true,
      "codec": "h264",
      "file_size_bytes": 21458944,
      "issues": []
    },
    "visual_spotcheck": {
      "frames_sampled": 4,
      "frame_paths": [".../frame_01.png", ".../frame_02.png"],
      "black_frames_detected": false,
      "broken_overlays": false,
      "missing_assets": false,
      "unreadable_text": false,
      "issues": []
    },
    "audio_spotcheck": {
      "narration_present": true,
      "music_present": true,
      "unexpected_silence": false,
      "clipping_detected": false,
      "mix_intelligible": true,
      "issues": []
    },
    "promise_preservation": {
      "delivery_promise_honored": true,
      "renderer_family_used": "narration-montage",
      "render_runtime_used": "ffmpeg",
      "runtime_swap_detected": false,
      "runtime_swap_check": "ok — ffmpeg stayed locked end-to-end",
      "motion_ratio_actual": 1.0,
      "silent_downgrade_detected": false,
      "issues": []
    },
    "subtitle_check": {
      "subtitles_expected": true,
      "subtitles_present": true,
      "coverage_ratio": 0.97,
      "timing_drift_detected": false,
      "issues": []
    }
  },
  "issues_found": [],
  "recommended_action": "present_to_user",
  "metadata": {
    "pipeline": "narration-montage",
    "subtitle_style_used": "static_whole_line",
    "voice_used": "alloy"
  }
}
```

### 7. Quality Gate

- `render_report` and `final_review` both validate against their
  schemas.
- Output file exists and passes ffprobe validation.
- `render_report.metadata.subtitles_force_aligned = true`.
- `final_review.checks.subtitle_check.subtitles_present = true`.
- `final_review.checks.audio_spotcheck.narration_present = true` (or
  the brief's explicit opt-out is honored and recorded).
- `final_review.checks.promise_preservation.runtime_swap_detected =
  false`.
- `final_review.recommended_action` is present.
- Every substitution is listed in `warnings`.

## Common Pitfalls

- **Burning estimated timings.** The single most common defect. Always
  force-align against real narration audio.
- **Skipping the runtime check.** `runtime_swap_detected` exists to
  catch a silent remotion fallback. Pass `proposal_packet` and report
  the result honestly.
- **Word-by-word or karaoke subtitles slipping in.** Static whole-line
  only. `\k` in the subtitle file is an automatic fail.
- **Presenting a failed render.** If `final_review.status` is
  `revise`/`fail`, fix and re-render. Never present it as complete.
- **Editing at compose time.** Adjusting cuts, volumes, or trims inside
  the render call means you're editing during compose. Go back to the
  edit stage, fix the decisions, re-emit, re-render.
- **Skipping the sync spot-check.** A subtitle that drifts off the
  audio by 2+ seconds looks broken. Verify at least one known line.

## When The Render Fails

1. Categorize the error per the Decision Communication Contract
   (auth / provider / tool bug / plan quality).
2. Path errors → validate every asset_id → path resolution in the
   manifest.
3. Codec errors → normalize inputs through `video_trimmer` first.
4. Memory/timeout → split with `video_stitch`.
5. Surface before swapping to a lower-fidelity path. There is no
   generated-stills fallback on this pipeline.
