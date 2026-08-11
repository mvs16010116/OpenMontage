# Asset Director - Narration Montage Pipeline

## When To Use

The scene plan exists. You now produce all the raw material the edit
needs: Pexels B-roll per scene, the narration audio (TTS) per section,
and the music bed. The output is an `asset_manifest` with full
provenance on every asset.

This stage runs three workstreams. They are independent — run them in
parallel where the tools allow (per AGENT_GUIDE.md, fire off footage
search in background while generating narration and music).

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["scene_plan"]["scene_plan"]` | Scenes + per-scene queries |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, voice_performance, delivery cues |
| Prior artifact | `state.artifacts["idea"]["brief"]` | narration_plan, music_plan, shot_cadence_seconds |
| Tool | `pexels_video` | B-roll footage |
| Tool | `tts_selector` | Narration audio (routes to configured provider) |
| Tool (optional) | `music_gen` / user's `music_library/` | Music bed |
| Layer 3 | `text-to-speech` + provider skill from `tts_selector.agent_skills` | TTS prompting (MANDATORY before generating) |

## Workstream A — B-Roll Footage (pexels_video)

### A1. Compute Clips Needed Per Scene

Read `brief.metadata.shot_cadence_seconds` (default 3.0). For each
scene: `needed = ceil((end - start) / shot_cadence) + 3`. That +3 is
buffer so the edit director can reject a bad clip without re-fetching.

### A2. Fan Out Queries

For each scene, run its `metadata.queries[]` through `pexels_video`.
Target landscape orientation, `min_width` ≥ 1920 where supported,
`min_duration` ≥ `shot_cadence_seconds` (a clip shorter than the cadence
would flash-cut), and enough clips per query to reach `needed`.

```python
pexels_video.execute({
    "query": "data center server racks",
    "orientation": "landscape",
    "min_width": 1920,
    "min_duration": 3.0,
    "per_page": 15,
})
```

Save every downloaded clip under
`projects/<project-name>/assets/video/<scene_id>/`.

### A3. Global Dedup (CRITICAL)

Track a **global set of used video_ids** across the WHOLE piece, not
per scene. A Pexels result page repeats across similar queries; the same
clip must never be picked for two scenes (it reads as a render bug).
When `pexels_video` returns a video_id already used, record it in
`metadata.rejected_picks` and move to the next candidate.

### A4. Pick Clips Per Scene

For each scene, pick `needed` clips that:

- match the scene description (concrete nouns — a "server rack" scene
  gets server clips, not office shots),
- are all DIFFERENT video_ids (see dedup),
- are each ≥ `shot_cadence_seconds` long.

Record each pick as a `type: "video"` asset with:
`provider: "pexels"`, `original_url`, `license`, `resolution`,
`duration_seconds`, and `scene_id` linkage. Read the actual fields from
`pexels_video`'s result data — do not invent URLs.

## Workstream B — Narration Audio (tts_selector)

### B1. Read The Narration Plan

Read `brief.metadata.narration_plan`. If `enabled: false` with an
`opt_out_reason`, skip this workstream entirely and record no narration
assets. If enabled, execute EXACTLY the recorded provider/model/voice —
do not substitute a provider here.

### B2. Generate One Audio File Per Section

Walk `script.sections[]`. For each section, generate TTS audio from
`section.text`, honoring `delivery_cues` (pace, pauses, emphasis) and
`script.voice_performance`. Save as:

```
projects/<project-name>/assets/audio/narration_<section_id>.mp3
```

Read the tool's Layer 3 skill first (per AGENT_GUIDE Rule Zero). Use the
`tts_selector` for routing; pass `language` from the narration plan.

### B3. Verify Each File

After generating, probe each narration file (e.g. via `video_analyzer`
or ffprobe): confirm it has audio, note its actual `duration_seconds`,
and store that in the asset. **Record the REAL duration** — it replaces
the script's estimated timings at compose time.

### B4. Record Narration Assets

Each narration file becomes a `type: "narration"` asset with
`voice_performance` filled from the script, `provider` from the plan,
`scene_id` = the section's scene, and `duration_seconds` = the real
probed duration.

## Workstream C — Music Bed

Read `brief.metadata.music_plan`. Execute EXACTLY the recorded source
(per AGENT_GUIDE.md → "Music Plan"):

- `source=library`: verify the file at `music_plan.source_path` exists.
  Record as `type: "music"`, `subtype: "library"`.
- `source=generated`: call the named tool (e.g. `music_gen`) with the
  seed prompt from the brief. Record provider and cost.
- `source=none` + `opt_out_reason`: skip. Do not generate a track
  because "the edit feels empty".

**Never switch music source at this stage** — that's a Decision
Communication Contract violation. A music-mode change needs user
approval at proposal time, logged in `decision_log`.

## Record The Asset Manifest

```json
{
  "version": "1.0",
  "assets": [
    {
      "id": "asset_scene_01_v1",
      "type": "video",
      "path": "projects/<name>/assets/video/scene_01/pexels_2837421.mp4",
      "source_tool": "pexels_video",
      "scene_id": "scene_01",
      "duration_seconds": 7.4,
      "resolution": "1920x1080",
      "format": "mp4",
      "provider": "pexels",
      "license": "Pexels License (free, no attribution required)",
      "original_url": "https://www.pexels.com/video/2837421",
      "subtype": "stock",
      "generation_summary": "Fetched for scene_01 (data center rack wide shot). video_id unique globally."
    },
    {
      "id": "asset_narration_section_01",
      "type": "narration",
      "path": "projects/<name>/assets/audio/narration_section_01.mp3",
      "source_tool": "tts_selector",
      "scene_id": "scene_01",
      "duration_seconds": 4.6,
      "format": "mp3",
      "provider": "openai_tts",
      "model": "gpt-4o-mini-tts",
      "voice": "alloy",
      "language": "zh-CN",
      "voice_performance": {
        "performance_intent": "calm authoritative",
        "pacing_profile": "technical"
      },
      "subtype": "narration_tts"
    }
  ],
  "metadata": {
    "pipeline": "narration-montage",
    "shot_cadence_seconds": 3.0,
    "clip_counts": { "scene_01": 6, "scene_02": 7 },
    "rejected_picks": [
      { "scene_id": "scene_02", "video_id": "pexels_2837421", "reason": "video_id already used by scene_01 (global dedup)" },
      { "scene_id": "scene_03", "video_id": "pexels_1000233", "reason": "clip 1.2s shorter than 3s cadence — would flash-cut" }
    ]
  }
}
```

## Quality Gate

- Every scene has ≥ `ceil(section_duration / shot_cadence) + 3` distinct
  video assets.
- No two assets share the same Pexels `video_id` (check
  `metadata.rejected_picks` for the audit trail).
- Every video asset carries `provider`, `original_url`, `license`,
  `resolution`, `duration_seconds`.
- Every narration section has a TTS asset with REAL probed
  `duration_seconds` (or narration was explicitly opted out).
- Music asset exists OR `music_plan.source = "none"` with an explicit
  opt-out reason.
- All file paths resolve.
- If a scene could not be filled with enough distinct clips, STOP and
  surface it — do not silently under-fill a scene (the edit needs the
  buffer).

## Common Pitfalls

- **Per-scene dedup only.** The dedup rule is global. The same clip
  leaking into two scenes is the #1 visible bug on this pipeline.
- **Picking by page order.** Pexels returns popular clips first; they
  are rarely the best match for the scene description. Look at the
  actual results, match to the description.
- **Ignoring clip duration.** A 2-second clip in a 3-second cadence
  forces a flash-cut. Filter by `min_duration` up front.
- **Substituting TTS provider/voice at this stage.** The voice was
  approved at idea time. Swapping it silently is a governance violation;
  if you must, log a `voice_selection` decision FIRST.
- **Trusting script estimates as final timing.** Record real audio
  durations in the manifest — compose force-aligns against them.
- **No narration files generated** because "the music will carry it."
  On this pipeline, narration is the spine. Generate it unless explicitly
  opted out.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact — the filmstrip shows each scene's clips), and **END YOUR TURN**. Do not start
the next stage in the same response. Approval is per-gate — an earlier "go ahead" does not
cover this gate.
