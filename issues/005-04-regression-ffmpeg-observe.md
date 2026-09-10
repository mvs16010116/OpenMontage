# 005-04 — 全链路回归验收与 FFmpeg 观察记录

**What to build:** 用一条最小端到端路径验证 005 的两个代码修复确实让「生成不再必失败」：单场景从 TTS → build → hyperframes render 全绿，产出非空 mp4 并有帧可抽查；同时记录 FFmpeg「无法启动」孤立案（47bae13b3528）的 `where ffmpeg` 证据供后续判断。

**Blocked by:** 005-01, 005-02（回归需两个修复都已落地）

**Status:** done

- [x] 用既有失败项目文案走 `step_tts`（单节），产出非空 mp3 — 005-01 验收：正常路径 23904B mp3 / dur 3.98s；端到端任务 `77bb61948077` `generating_tts` 15.78s 产出两节音频（section_01.mp4 4.8s / section_02.mp4 6.1s）
- [x] `build_photo_carousel.mjs` 单场景构建 + `npx hyperframes render` 产出非空 mp4，抽查 1 帧有画面 — 端到端任务 `77bb61948077`：`rendering_scenes` 129.38s，`renders/final.mp4` 513288B 非空，1920x1080 h264+aac 10.9s；抽帧 signalstats YMIN=16 / YAVG≈29.6 / YMAX=235（有高亮文字，非黑帧）；`_video_master.mp4` 已 burn 字幕（h264，YMAX=235）
- [x] TTS 超时路径单元验证通过（见 005-01 验收）— 0.1s 超时探针 3.2s 抛 `RuntimeError`，0 字节残留被 `_cleanup_stale` 清理
- [x] 记录 `where ffmpeg` / `ffmpeg -version` 现状 — `where ffmpeg` → Gyan.FFmpeg（winget，`ffmpeg-9.0-full_build\bin\ffmpeg.exe`），`ffmpeg -version` 正常返回；005 全链路回归中 ffmpeg 稳定可用。孤立案 47bae13b3528（探测失败）为一次性环境瞬态，未复现；保持观察项，若再次出现再转票

**验收证据（本 ticket）：** 全链路任务 `77bb61948077` 从 `llm_parse`(3.65s) → `generating_tts`(15.78s) → `fetching_images`(0.03s) → `rendering_scenes`(129.38s) → `subtitles`(0.66s) → `assembling`(12.31s) → `done`。005 断言「生成不再必失败」实证成立（本批 12 个失败任务后首个成功）。