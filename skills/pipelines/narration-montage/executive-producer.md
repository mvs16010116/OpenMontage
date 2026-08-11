# Executive Producer - Narration Montage Pipeline

## When To Use

The user has a written script (口播文案) — or a topic that needs one —
and wants it turned into a finished narrated video. The piece is a
**narration-led explainer**: the voice-over is the spine, subtitles
carry the text on screen, and stock footage provides supporting
visuals. This is NOT a talking-head video, NOT a motion-graphics
explainer built from generated clips, and NOT a silent montage.

This is the right pipeline when the request includes phrases like:

- "口播文案" / "here's my script",
- "voice-over", "narration", "read this text",
- "a talking-points video with B-roll",
- "subtitled explainer from my text",
- "make a video from this article/notes",
- "a video of me talking about X" (footage is secondary, words lead).

If the user wants a presentator on camera, generated animation, or a
speaker-driven screen capture, pick a different pipeline.

## Philosophy

Narration montage is **script-first, footage-second**. The words decide
the structure, the duration, and the timing; the footage exists to keep
the eye busy and underline the meaning. Your job across all stages:

1. **Protect the script.** Every downstream decision — scene split,
   clip pick, shot length, subtitle timing — exists to serve the words.
   If visuals fight the narration, the visuals lose.
2. **Sight-read the words.** The B-roll should be what a listener would
   SEE while hearing the line. Literal is fine; the best B-roll is
   concrete and noun-led ("server racks blinking in a dark room" for a
   line about the cloud).
3. **Hold a fixed rhythm.** A stable shot cadence (default 3s) keeps the
   video breathable and predictable — never let a single clip linger long
   enough to feel like a slideshow, never flash-cut beneath the voice.
4. **Subtitles are contract, not decoration.** The text on screen must
   match the words in the audio. Force-align subtitles to the real
   speech; static whole-line burn, never karaoke-style \k markers.

## Stages

| Stage | Director skill | Produces |
|-------|----------------|----------|
| `idea` | `idea-director.md` | brief (hook, tone, narration voice, music plan) |
| `script` | `script-director.md` | script (sections + estimated timings) |
| `scene_plan` | `scene-director.md` | scene_plan (one scene per section + Pexels queries) |
| `assets` | `asset-director.md` | asset_manifest (footage clips + narration audio + music) |
| `edit` | `edit-director.md` | edit_decisions (shot cadence, subtitle style, audio layout) |
| `compose` | `compose-director.md` | render_report + final_review (final mp4) |

Each director skill has its own quality gate. Read the director skill
before starting the stage.

## Core Tools

| Tool | Role |
|------|------|
| `pexels_video` | Stock B-roll footage (landscape, 1920x1080 target) |
| `tts_selector` | Narration TTS (routes to configured provider) |
| `transcriber` | Force-aligns subtitles to the real narration audio |
| `subtitle_gen` | Builds the subtitle file from aligned timestamps |
| `video_compose` (ffmpeg) | Renders the master: cut, subtitle burn, audio mux |

Route TTS through `tts_selector`, never call a provider adapter
directly. Read the selector's Layer 3 skills (`text-to-speech`, plus the
provider skill) before generating narration.

## Cross-Stage Rules

- **Narration is MANDATORY.** This pipeline exists to speak a script. A
  silent render with no voice-over is a failed production unless the
  user explicitly changed the brief at idea time (recorded as
  `narration: "none"` + an explicit `opt_out_reason`).
- **No generated footage.** B-roll comes from Pexels stock. Generated
  AI clips are off-pipeline for this budget/quality profile.
- **Dedup clips globally.** Every distinct Pexels video_id may be used
  exactly once across the whole piece. Reuse looks like a render bug.
- **Subtitle timing comes from real audio.** Do not trust estimated
  section timings for the final burn — force-align with `transcriber`.
- **Runtime is ffmpeg, always.** Lock `render_runtime="ffmpeg"` at
  edit and carry it unchanged. Remotion/HyperFrames are NOT valid
  runtimes here. A silent swap is a CRITICAL governance violation.
- **Keep a decision log of rejected picks.** When you pass on a clip
  with a good visual match, note why (wrong register, repeated video_id,
  too short for the cadence). The edit stage reads this.

## Common Pitfalls

- Treating this as a montage where the images choose the pace. The
  script owns the clock.
- Writing B-roll queries that are abstract moods ("success", "future",
  "growth") instead of concrete nouns. Pexels answers nouns.
- Letting one clip play for 10+ seconds while the narration continues.
  The eye gets bored; the cadence breaks.
- Burning subtitles from estimated timings and letting them drift off
  the actual audio. Always force-align.
- Quietly generating narration with a different voice than the one the
  user approved. Voice is a MAJOR production choice — record it in the
  brief and never swap it without logging a `voice_selection` decision.
- Reusing a video_id twice because "the shot is perfect for both".
  Fetch a second clip instead.
