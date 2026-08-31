# Handoff — OpenMontage / junzheng-gaza-pursuit

**Date:** 2026-08-31
**Branch:** main
**Next-session focus per user:** none provided beyond "write handoff + commit & push this code". Continue the narration-synth vertical video work if new feedback arrives; otherwise the pipeline is complete.

---

## 1. What this session accomplished (REV2-grilling)

The narration-synth vertical video `projects/junzheng-gaza-pursuit` was delivered as REV2 and re-rendered after a grilling round where the user chose **A / A / A** and **in-place revision** for three items. All three are DONE, verified, and the artifacts/checkpoints updated with `revision: rev2-grilling`.

### The three REV2 fixes
1. **#2 Subtitle overflow fixed.** Root cause: `assets/subtitles.ass` had `PlayResX:1920/PlayResY:1080` (landscape) on a 1080×1920 vertical video → libass scaled text ~1.78× → ~121px glyphs overflowed. Fix: rebuilt ASS at `PlayResX:1080 / PlayResY:1920`, Fontsize 42. Pixel-verified: narration frames White(>200)=4166px share 1.1%, **0 px on any frame edge**; opener/chapter-card frames have 0 white subtitle pixels.
2. **#3 Word-level subtitle/audio sync.** Used the local offline `faster-whisper-base` model (`.models/whisper/faster-whisper-base/model.bin`, 138MB) to transcribe all 8 narration MP3s (`assets/audio/narration_section_01..08.mp3`) with `word_timestamps=True`. The 56 subtitle lines now snap start→real word onset, end→next word boundary. First line starts at 2.00s (= actual "大家好" onset), last ends 150.81s.
3. **#1 Keyword motion.** Enhanced `build_vertical.mjs` (temp script) — headline sprites now use `back.out(1.6)` stagger entry + a **deterministic persistent vertical float** (GSAP timeline tweens spread across the full scene duration, seek-safe under HyperFrames' paused/seeked timeline). All 25 scene MP4s re-baked; duration check 0/25 mismatches; `scene_section_02_1` frame diff 14269px confirms motion.

### Re-render chain used
- Assets stage: each scene composed to `assets/video/scene_<id>.mp4` via `node build_vertical.mjs <scene_id>` (writes `hyperframes/index.html`) then `npx hyperframes render --output assets/video/<scene_id>.mp4`.
- Compose: `prepare_shots.py` (trim-to-window / `tpad stop_mode=clone` freeze) → `concat_video.py` → `render_final.py` (subtitle burn with **no force_style** — the vertical ASS's own styles must be honored).
- Audio mix (`narration_mix.m4a`) unchanged this round (narration MP3s untouched).

**Final:** `renders/final.mp4` = 1080×1920 h264 30fps, 150.8s, aac 48kHz mono, 46.4MB.

---

## 2. Key gotchas learned (do not re-hit these)

- **`build_vertical.mjs` must NOT use `process.cwd()` as ROOT.** It runs in a loop where `npx hyperframes render` needs cwd = `projects/junzheng-gaza-pursuit/hyperframes`, but the compositor needs the project root. A hardcoded absolute `ROOT` (already applied) is required. Symptom if broken: every rendered MP4 comes out at the SAME duration (stale leftover `index.html`).
- **`build_vertical.mjs` scene match is against full ids** (`scene_section_01_1`), NOT stripped (`section_01_1`). Passing the stripped id writes 0 compositions and the render silently re-reads stale `index.html`.
- **ffmpeg subtitle burn with `subtitles=` uses a RELATIVE path only.** An absolute path with a drive letter (`D:\...`) is misparsed as `original_size`. Set `cwd=PROJ` and pass `assets/subtitles.ass`.
- **Do NOT pass `force_style` overriding FontSize** when burning these subtitles — it clobbers the vertical ASS's own 1080×1920 geometry + font 42 (the original 68px override is what hid the vertical setup).
- **ID mapping mismatch past bug:** narration asset ids are `asset_narration_section_01` (prefix `asset_narration_`, not `asset_`), and grid lookup keys are `section_01` style. Re-derive from `edit_decisions.json` `audio.narration.segments` if re-running the subtitle timer.
- **PowerShell can't run inline python with `->` or here-strings reliably**; write temp `.py` files under `C:\Users\user\AppData\Local\Temp\opencode\` and run with `.venv\Scripts\python.exe`, after `$env:PYTHONPATH="D:\Danny\projects\animation\my_open_montage"`.
- **Schema strictness:** `render_report.schema.json` and `final_review.schema.json` have `additionalProperties:false`, `version` const `"1.0"`, and fixed check key sets. Do NOT add top-level `revision`/revision keys or custom check keys (`subtitle_overflow`, `word_level_sync`, etc.) — they fail validation. Put revision notes ONLY inside free-form `metadata`.

## 3. Artifacts / files (reference these, don't duplicate)

All under `projects/junzheng-gaza-pursuit/`:
- **Checkpoints:** `checkpoint_idea.json` … `checkpoint_compose.json` (compose has `revision: rev2-grilling`, `next_stage: null`, `pipeline_complete: true`).
- **Decisions:** `decision_log.json` (7 entries, full_auto pre-approval).
- **Artifacts:** `artifacts/{brief, source_script, script, scene_plan, asset_manifest, edit_decisions, render_report, final_review}.json` — all schema-valid (verified this session).
- **Renders:** `renders/final.mp4`, `renders/video_master.mp4`, `renders/.compose_tmp/` (`shot_*.mp4` ×25, `narration_mix.m4a`, `concat.txt`, `shot_plan.json`, `ws_cache.json`).
- **Assets:** `assets/video/scene_*.mp4` ×25, `assets/audio/narration_section_01..08.mp3` + `narration_mix.m4a`, `assets/images/*.jpg`, `assets/subtitles.ass` (vertical word-synced).
- **HyperFrames:** `hyperframes/index.html` + `hyperframes.json` (per-scene; last scene written is scene_section_08_3).

**Temp helper scripts** (in `C:\Users\user\AppData\Local\Temp\opencode\`, survive only while OS temp persists — re-reference, don't trust them permanently): `build_vertical.mjs` (compositor, edited for motion), `build_sub_v2.py` (vertical word-synced ASS generator; uses `.models/whisper/faster-whisper-base`), `prepare_shots.py`, `concat_video.py`, `render_final.py`, `build_mix.py`, `probe_shots.py`, `verify_pixels.py`, `compute_timeline.py`, `build_edit_gaza.py`, `write_cp_*.py`, `write_report_review.py`, `devval*.py`, `upd_cp.py`, test_ws.py.

**Pipeline definitions / skills** (uncommitted modifications present in `git status`): `pipeline_defs/narration-synth.yaml`, `schemas/artifacts/{asset_manifest,edit_decisions,scene_plan}.schema.json`, `skills/pipelines/narration-synth/*-director.md`. These were edited before this session; a fresh agent should review the diff before committing.

**Reference paradigm projects:** `projects/junzheng-yasukuni/` (untracked), and the narration-synth skill docs.

## 4. Current repo / git state

- Branch `main`, up to date with `origin/main` (`https://github.com/mvs16010116/OpenMontage.git`).
- **Modified (unstaged):** `pipeline_defs/narration-synth.yaml`, 3 schema files, 7 narration-synth skill markdown files.
- **Untracked:** `projects/junzheng-gaza-pursuit/`, `projects/junzheng-yasukuni/`, `renders/`, `tmp_sort.json`, `tmp_view.json`, `projects/junzheng-selfgen/script_flat.json`.

⚠️ Before committing: review these diffs (esp. the pipeline/skill edits predating this session and the untracked `tmp_*.json` scratch files — likely should be gitignored, not committed). Large media (`renders/`, `assets/video/*.mp4`) may bloat the repo; decide whether to commit or gitignore. `renders/.compose_tmp/ws_cache.json` and `narration_mix.m4a` are large intermediate outputs.

## 5. Suggested skills for the next agent
- **`hyperframes-cli`** — if any scene needs re-rendering or re-correction; all HyperFrames render/lint/validate/inspect commands.
- **`ffmpeg`** — media assembly (concat, subtitle burn, audio adelay/amix mux) and ffprobe verification.
- **`ass-subtitle-generator`** — if subtitles ever need short-line restyle; note the renderer family here uses a project-local vertical generator instead.
- **`dev-validator`** — mandatory at end of any code change (per AGENTS.md Phase 4), here applied as artifact/media validation.
- **`video-pipeline`** / reference `skills/pipelines/narration-synth/*` directors — for the broader narration-montage lineage and next-video reuse.
- **`grid`/`milestone`-style review** (e.g. `code-review` over the pending pipeline/skill diff) before committing the pre-existing edits.

## 6. Next steps if work resumes
1. Review + commit/push the pending diff (see git-state notes; decide on ignoring scratch/large-media).
2. If new grilling feedback arrives on the video: re-edit `build_vertical.mjs` / the temp ASS timer, re-bake only the affected scenes, and re-run `prepare_shots → concat → render_final`, then update the three artifacts + checkpoint with the new revision note (schema-conformant, revision notes in `metadata` only).
3. If whisper word-timing needs redoing, the model at `.models/whisper/faster-whisper-base` is complete and offline-usable; `ws_cache.json` caches prior transcriptions.
