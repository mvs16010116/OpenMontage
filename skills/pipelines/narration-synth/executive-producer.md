# Executive Producer - Narration Synth Pipeline (军政自生成素材)

## When To Use

The user has a written script (口播文案) or topic for **military-political
commentary** (军政) and wants a finished narrated video whose **visuals are
self-generated**, not stock footage. The voice-over is the spine, subtitles carry
the text, and every scene is a **procedurally generated HyperFrames animation**
produced by the `military-*` asset skills. This is NOT a stock-cut montage, NOT a
talking-head video, and NOT an externally-sourced B-roll explainer.

This is the right pipeline when the request includes:

- "军政" / "军事政治" / commentary with generated military graphics,
- "自己生成素材" / "self-generated visuals" / "不要用现成视频",
- a warship/drone/map/missile/title-card visual language,
- narration-led + generated animation (instead of fetched stock).

If the user wants stock footage B-roll, use `narration-montage`. If the user wants
generated AI *video* clips (VEO/Kling), use `animation`/`cinematic`. This pipeline
is the deterministic, code-generated animation path: identical inputs → identical
visuals, zero external footage, no AI video cost.

## Philosophy

`narration-synth` is **script-first, generated-visual-second**. Same spine as
narration-montage (words own the structure, duration, and timing), but the visual
contract changes: a story is many small stories — each section splits into
semantic sentences, each sentence is ONE SHOT, and each shot overlays MATERIALS
(each a `military-*` skill + exact CLI args + layer) in the same window,
executed deterministically at the asset stage.

1. **Protect the script.** Every downstream decision serves the words. Shot split
   follows the sentence arc; the material stack underlines the line being spoken.
2. **Route visuals to the right generator.** The `military-*` skills are:
   - `military-warship` — 军舰/舰艇剪影 + 雷达扫描 + 海浪 + 数据
   - `military-missile` — 导弹/弹道/火箭 flight + range/altitude stats
   - `military-map-deduction` — 战略态势图/推演 (D3 theatre map + arrows)
   - `military-data-viz` — 军费/装备对比 + 时间线 (D3 bars/lines/tree)
   - `military-title-card` — 标题/章节/数字 count-up (openers, chapter breaks)
   - `military-seal` — 红头文件/盖章 (documents, orders)
   - (full catalog under `.agents/skills/military-*/SKILL.md`)
   Every material names exactly one skill and its full determinism-safe arguments;
   a shot stacks them as background → midground → foreground.
3. **Determinism is a quality gate.** No random seeds, no `Date.now`, no
   network-dependent visuals. A material re-renders identically on every run.
4. **Subtitles stay a contract.** Regenerate `subtitles.ass` from real narration
   offsets via `ass-subtitle-generator`; short lines (≤16 chars), ASS colors,
   static whole-line burn, never karaoke.
5. **Final render runtime is ffmpeg.** Material layers are produced by
   `npx hyperframes render` at the assets stage; compose *overlays* them per shot,
   *concatenates* the shots, and burns subtitles + muxes audio via
   `video_compose`'s ffmpeg path — which keeps the ASS subtitle burn and
   narration/music mux native. Remotion is NOT used;
   HyperFrames is the asset *generator*, ffmpeg is the *finisher*.

## Stages

| Stage | Director skill | Produces |
|-------|----------------|----------|
| `idea` | `idea-director.md` | brief (hook, tone, narration voice, music plan) |
| `script` | `script-director.md` | script (sections + estimated timings) |
| `scene_plan` | `scene-director.md` | scene_plan (sentence-shots + materials[] with layers + specs) |
| `assets` | `asset-director.md` | asset_manifest (transparent material MP4s + narration audio + music) |
| `edit` | `edit-director.md` | edit_decisions (one slot per shot, materials in layer order, ASS subtitle contract, back-to-back narration layout) |
| `compose` | `compose-director.md` | render_report + final_review (final mp4) |

Read the director skill before starting each stage.

## Core Tools

| Tool | Role |
|------|------|
| `node` + `build_*.mjs` (per skill) | Generate HyperFrames composition HTML from a material spec |
| `hyperframes_compose` / `npx hyperframes` | lint → validate → render each material composition to transparent MP4 |
| `tts_selector` | Narration TTS (routes to configured provider) |
| `ass-subtitle-generator` | Builds short-line `.ass` subtitles from real narration offsets |
| `audio_mixer` (or ffmpeg adelay+amix) | Rebuilds the narration mix back-to-back (silence only at opener/cards) |
| `video_compose` (ffmpeg) | Overlays materials per shot, concats shot MP4s, burns `.ass`, muxes narration + music |

Read the relevant Layer 3 skills (`hyperframes-*` family, `text-to-speech`, plus
the specific `military-*` skill) before generating. Nearly all generation here is
local and free (node + hyperframes); the only priced step is TTS.

## Cross-Stage Rules

- **Narration is MANDATORY.** This pipeline exists to speak a script. Silent is a
  failed production unless the user explicitly opted out (recorded at idea time).
- **Visuals are SELF-GENERATED.** Every shot must resolve to a `materials[]` stack
  of `military-*` skills. Interpreting a shot as "find stock footage" is a
  pipeline violation.
- **Determinism everywhere.** Every generated composition passes
  `hyperframes lint` + `hyperframes validate` with 0 errors before render.
- **Subtitle timing comes from real narration offsets.** Never burn estimated
  section timings; regenerate `subtitles.ass` via `ass-subtitle-generator` from
  `script.sections[].start_seconds`.
- **Narration mixes back-to-back.** Rebuild the narration master contiguously;
  silence is reserved for opener + chapter cards. Dead air between chapters is a
  pacing failure, not a feature.
- **Final runtime stays ffmpeg.** Material overlay + concat + subtitle burn + mux.
  No silent swap to Remotion or to a free-running HyperFrames timeline at compose.
- **Keep the decision log.** Rejected material specs, changed accents/palettes,
  and voice swaps all get logged with `metadata.rejected_specs` or a
  `voice_selection`/`render_runtime_selection` decision.

## Common Pitfalls

- Routing a material to a `military-*` skill that doesn't fit the line — e.g. a
  "战略态势" line pointing to `military-seal`. Match the generator to the meaning.
- Leaving a material spec underspecified (no args), forcing the asset stage to
  guess — the scene stage owns the spec.
- Two adjacent shots sharing the same background skill family (two warship
  backdrops back to back) — the cut reads as a single long animation.
- Forgetting the title-card bookend — chapter breaks need the visual emphasis.
- Rendering materials WITHOUT alpha — the overlay can't composite and the shot
  looks flat/broken.
- Burning subtitles from estimated timings; or letting generated material
  durations drift far from shot windows (compose must re-check each narration
  against its scene window).