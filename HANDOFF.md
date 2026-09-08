# Handoff — OpenMontage

**Date:** 2026-09-08
**Branch:** main (head `078809f`, pushed)
**Next-session focus:** issues/003 (narration-synth web service) shipped and verified end-to-end; run the service (`python -m web.server`) for live use, or take new-feature requests. Tracker: issues/001 (Pexels carousel), issues/002 (subtitle scale + keyword glow), issues/003 (web service).

---

## 1. What this session accomplished

Delivered a new reusable capability for narration-led videos: **Pexels keyword-relevant photo carousel** as the visual layer under title-card foregrounds, applied end-to-end to the `us-iran-hormuz-strike` landscape video. Full 5-stage workflow (grill → spec → tickets → implement → handoff) completed.

Tracker: `issues/001-pexels-keyword-image-carousel.md` (spec) + `issues/001-01..06` (tickets, t01→t06). All tickets DONE:
- **001-01** `tools/graphics/pexels_image.py` — added multi-download (`count` + `output_dir`), returns per-photo `candidates` (photo_id/alt/dims/src/output); legacy single-download unchanged. Tests: `tests/tools/test_pexels_image.py` (3).
- **001-02** `pexels_searches.json` (8×2-3 English queries) → `physics`-side alt-score curation → `pexels_manifest.json` (32 relevant photos across 8 sections; section_08 deep-card fallback by design).
- **001-03** New reusable skill `.agents/skills/military-photo-carousel/` (`build_photo_carousel.mjs` + SKILL.md): landscape 1920×1080, crossfade 0.6s + Ken Burns, dark mask, title/kw/number foreground, `--no-carousel` fallback.
- **001-04** section_02 sample baked + pixel-verified (photo bg, white headline, carousel motion confirmed by frame hashes).
- **001-05** All 10 scenes baked (opener + 8 sections + 3s end-card); **breathing pauses** inserted (silence after number cues in `narration_section_02/04`); timeline/subtitles re-synced to 173.07s.
- **001-06** Assembled `renders/final.mp4`, verified **16/16** (see below), pushed.

Then a visual-revision round (spec + tickets `issues/002-subtitle-size-keyword-glow.md` + `002-01..04`), all DONE:
- **002-01** kwtag → **dark translucent pill** (rgba(7,11,18,.62) rounded) + **amber breathing glow** (bg alpha .50↔.72, box-shadow .20↔.45, 2.6s sine yoyo, pinned to main paused timeline — deterministic/seek-safe). **No text glow** — that was the gaza comma-tag merge defect (3078077). Hex accent → rgba helper added to builder.
- **002-02** subtitles scaled 1.8×: FontSize 44→**80**, Outline 3→**5**, MarginV 58→**90** in both `.ass` Style and burn `force_style`.
- **002-03** all 10 scenes re-baked (durations hit windows).
- **002-04** re-assembled `final.mp4`: verified 16/16, pytest 9 passed, pushed.

### Final deliverable (after revisions)
`projects/us-iran-hormuz-strike/renders/final.mp4`:
1920×1080 · h264 · aac · yuv420p · 30fps · **173.07s**. Photo-carousel backgrounds at sampled times; **enlarged subtitles** (white-glyph px 4004–4851 vs 1297–1626 before), **kwtag dark pill + breathing glow** confirmed in final frames (s02/s04/s06); narration −25.8/−25.9/−27.0 dB; per-section crossfade confirmed.

### Commits (each referenced by its ticket)
001: `c608f45` → `e667e07` → `65b52b3` → `148d9dc` → `342491a` (001-06) → `3cc9335` (handoff).
002: `3bc9c69` (002-01) → `5add2db` (002-02) → `970ef76` (002-03) → `abe2f53` (002-04).
003: `aa2b884` (spec+tickets) → `514c4a5` (003-01) → `6aee00f` (003-02) → `a4f5d14` (003-03) → `11e733a` (003-04) → `bef005c` (003-05) → `078809f` (.gitignore, chore). Pushed to origin/main.

## 1b. issues/003: narration-synth 口播视频生成 Web 服务 (shipped)

Turned the CLI narration-synth flow into a single-user web service. Full 5-stage workflow done (grill → spec `issues/003-narration-synth-web-service.md` → tickets `003-01..05` → implement → handoff). All 5 tickets DONE, verified E2E.

- **003-01** `web/db.py` (SQLite `tasks` CRUD, new-id, summarize), `web/requirements.txt` (fastapi/uvicorn/apscheduler/**edge-tts**).
- **003-02** `web/pipeline.py` — parse_script (sentence split) → TTS → pexels images → hyperframes scene render → ASS subtitles → ffmpeg assemble. Chain: `python -m web.pipeline --task-id X --text "…"`.
- **003-03** `web/worker.py` (APScheduler BackgroundScheduler IntervalTrigger 1s dispatch + `_job_lock` serial) + `web/server.py` (FastAPI routes: `/`, `/api/health`, `POST /api/generate`, `GET /api/tasks`, `/api/tasks/{id}`, `/api/tasks/{id}/video`, `/api/tasks/{id}/events` SSE). ProgressHub bound to uvicorn loop, cross-thread publish via `run_coroutine_threadsafe`.
- **003-04** `web/templates/index.html` + `web/static/.gitkeep` — dark single-page SPA (textarea, button, SSE stage text, history list, download link), no CDN.
- **003-05** `tests/web/test_pipeline.py` (7) + `test_api.py` (8) = **15 passed**. E2E: real server POST (UTF-8 Chinese) → SSE queued/parse/generating/fetching/rendering → done; `/api/tasks/{id}/video` returns video/mp4 3.1MB. CLI smoke `mt-smoketest1` final.mp4: 1920×1080, subtitle white px 6186/5055, bg colors 8363 (all OK).
- **TTS decision (user):** free **Edge TTS** (`edge-tts`, voice `zh-CN-YunxiNeural`, no key) — rejected over Doubao (key empty) and SiliconFlow (user asked, then switched). Runtime db + generated `projects/narration-*/` dirs are gitignored.

### How to run the service
```
.venv\Scripts\python.exe -m web.server          # 127.0.0.1:8000
```
Post Chinese text via a UTF-8-capable client (Python/curl, **not** PowerShell `ConvertTo-Json`). Stages: `queued → parse_script → generating_tts → fetching_images → rendering_scenes → subtitles → assembling → done/error`.

---

## 2. Key gotchas learned (do not re-hit)

- **Nested template-literal trap in hyperframes builders:** inside `build_photo_carousel.mjs` the `script:` string and its `${keyword ? \`…\` : ""}` branch are themselves backtick template literals. Writing a raw backtick inside the branch (e.g. `` boxShadow: `0 0 18px ${x}` ``) closes the branch early → `SyntaxError: Unexpected number`. Use double quotes + direct interpolation (`boxShadow: "0 0 18px ${accentRgba(0.2)}"`) instead.
- **Pill chip must shrink-wrap:** an absolutely-positioned `#kwtag` with `left:0;right:0` stretches the pill across the full row. Use `left:50%; transform:translateX(-50%)` (no width) so the dark capsule wraps the text.
- **Breathing glow stays on background/box-shadow ONLY.** The gaza kwtag textShadow breathing (3078077) visually merged comma-separated multi-tag keywords — never reintroduce text glow; animate `backgroundColor` + `boxShadow` with sine yoyo repeat on the paused main timeline (seek-safe, deterministic).
- **Subtitle burn params must live in two places:** `.ass` Style line AND burn `force_style` must match (FontSize/Outline/MarginV). Keep them in sync or the wrapped ASS self-consistency breaks.
- **ffmpeg `subtitles=` filter needs a RELATIVE path (no drive colon).** `subtitles=D:/….ass` → `original_size` parse error. Use `cwd=ROOT` + `subtitles=projects/.../subtitles.ass`. Also wrap the whole `force_style` value in single quotes inside the filter string or the commas get eaten.
- **ffmpeg amix hang trap (recurring):** do NOT put `atrim`/`apad` inside the amix filter chain. Mix first (plain `adelay` + `amix=inputs=N:normalize=0`), then if you need to reach full length, extend the audio at the **mux step** with `-af apad=pad_dur=...` and `-shortest` (video length governs). `amix` output ends at the last non-silent input — it does not pad to your `-t`; without apad at mux the film truncates to last-narration end (168.6s!).
- **HyperFrames media root = `hyperframes/` not project root.** Local `<img>` files must live at `projects/<name>/hyperframes/assets/images/<slug>/…` or the renderer 404s (visible only at capture → frame is black/empty; `hyperframes check` Runtime may still say 0 errors). The builder copies them there.
- **PexelsImage `.env` load:** scripts run via `.venv` python must load `.env` manually (`PEXELS_API_KEY` is not in env by default). Guard with `os.environ.setdefault` loop.
- **PowerShell inline `python -c` breaks on quotes/slashes/East-Asian chars.** Always write temp `.py` under `C:\Users\user\AppData\Local\Temp\opencode\` and run `& "$pwd\.venv\Scripts\python.exe" <file>`. Avoid `->`, `<unicode>` escapes in `-c`.
- **PowerShell `ConvertTo-Json` also eats CJK** → HTTP POST with `Invoke-RestMethod` sends `?` for Chinese text (server gets garbage → edge-tts "No audio was received"). Use Python `urllib` (`.encode('utf-8')`) or `curl` for task submissions.
- **`build_photo_carousel.mjs` arg parser only matches `--name value` (space-separated).** `--project=foo` is looked up as the literal token `--project` → falls back to project `demo` and writes there silently. Use `["--project", name, "--title", t, …]`.
- **`peexels_image.execute` candidates are dicts**, each with `output` (absolute path). `manifest[i]["photos"]` = list of these dicts, NOT strings — basename via `cand["output"]`.
- **`build_ass.py` narration manifest `scene_id` must be `scene_0N`** (it does `x["scene_id"].replace("scene_","")`), while script sections are `section_0N`. If you pass `section_0N` as scene_id → zero Dialogue events, silent subtitle loss.
- **Slug must be ASCII.** `npx hyperframes render projects/<CJK-name>/…` and even `Path` join resolve fine to create, but the hyperframes CLI can't find a CJK-named composition dir. `_slugify` strips non-ASCII; uniqueness comes from appended task_id.

## 3. Artifacts / files (reference these, don't duplicate)

- Web service: `web/{server,worker,db,pipeline}.py`, `web/templates/index.html`, `web/requirements.txt`, `tests/web/*.py`. Runtime db `web/narration_synth.db` (gitignored; tasks survive restart).

- Tracker: `issues/001-pexels-keyword-image-carousel.md` (spec) + `issues/001-01..06-*.md` (blocking edges); `issues/002-subtitle-size-keyword-glow.md` (spec) + `issues/002-01..04-*.md`.
- Skill: `.agents/skills/military-photo-carousel/` (`build_photo_carousel.mjs`, `SKILL.md`) — reusable for future landscape videos.
- Project artifacts: `projects/us-iran-hormuz-strike/artifacts/pexels_searches.json`, `pexels_manifest.json` (per-image `photo_id/alt/file/reason/score`), `pexels_fetch_raw.json`; `assets/images/<section>/*.jpg` (gitignored, refetches via manifest); `assets/subtitles.ass` (62 events, **Style FontSize=80/Outline=5/MarginV=90** — burn `force_style` must match); `assets/audio/narration_section_0X.mp3` (s02/s04 have breathing gaps); `artifacts/script.json` (windows 173.07s incl end-card 3s).
- Tool change: `tools/graphics/pexels_image.py` (+ `tests/tools/test_pexels_image.py`).
- Renders: `projects/us-iran-hormuz-strike/renders/final.mp4` (+ `.compose_tmp/_base_silent.mp4`, `narration_mix.m4a`, `_with_narration.mp4`, `concat.txt`).
- Smoke products: `projects/narration-*/` (gitignored, deletable).

## 4. Suggested skills for next agent

- Skill tool: `implement` (tickets), `handoff`, `ass-subtitle-generator` (build_ass.py), `hyperframes-core` / `hyperframes-cli` (render), `military-photo-carousel` (self), `dev-validator` (final checks), `grilling`/`to-spec`/`to-tickets` if opening a new feature.
- For the web service: FastAPI + uvicorn + APScheduler + SSE — see `issues/003-03` for the queue design if extending concurrency.

## 5. Open items / hygiene

- Uncommitted stale changes NOT related to this feature: root `AGENTS.md` (adds the 5-stage workflow rules — pre-dates this session, leave for its own commit), root `renders/`, `projects/junzheng-gaza-pursuit/artifacts/_pexels_fetch.json` + `_section_cuts.json`, `projects/junzheng-selfgen/`, `projects/junzheng-yasukuni/`, `chrome_wincheck.py`, `tmp_sort.json`, `tmp_view.json`, `events.jsonl`. Decide separately.
- Web service runtime: `web/narration_synth.db` + any `web/__pycache__/` are gitignored/regenerable. Smoke `projects/narration-*/` can be deleted anytime.
- Breathing pauses burned into narration MP3s (s02: +0.72s, s04: +0.37s) + scene durations +0.35/0.2 — if the script window math churns again, trust `script.json` `start/end_seconds` (already re-synced). Web-service path re-times windows from real edge-tts durations via `rewindow_script`.