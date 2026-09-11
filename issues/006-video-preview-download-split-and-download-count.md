# 006 - 预览/下载拆分 + 下载次数统计

**Date:** 2026-09-11  **Status:** spec-ready  **Branch:** main

## 问题陈述（Problem Statement�?
当前 Web 服务的「预览」和「下载」是同一个功能：`GET /api/tasks/{id}/video` 一个端点同时承担浏览器 `<video>` 内嵌播放和「下载成�?final.mp4」链接、以及历史列表的「预�?下载」按钮，且响应头�?`Content-Disposition: attachment`，导致浏览器行为不可区分、语义混乱。同时系统完全不统计下载次数，用户无法知道成片被下载了几次�?
另外需要确认：生成的视频是否真的具备「图片素材轮播」能力（该能力在流水线代码中已有，需验证其在产物中真实生效）�?
## 解决方案（Solution�?
将视频产出拆成两个语义明确的端点�?
- **预览**：`GET /api/tasks/{id}/video` —�?�?inline 流（去掉 `Content-Disposition: attachment`），保留 `Range` 支持，供 `<video controls>` 在线播放�?- **下载**：`GET /api/tasks/{id}/download` —�?真正的下载（`attachment; filename="{id}.mp4"`），每次调用把该任务的下载计�?+1�?- 「图片素材轮播」能力已内建于流水线渲染阶段，本次通过抽查成品帧验证其真实生效，不新增实现�?
下载计数持久化到任务记录，并�?*历史任务列表**�?*生成完成面板**同时展示「下�?N 次」�?
## 用户故事（User Stories�?
1. 作为视频生成用户，我希望生成完成后能在页面内直接在线播放成片，以便快速检查效果，而不会被强制下载保存�?2. 作为视频生成用户，我希望有一个明确的「下载」按钮，把成片以文件形式保存到本地，以便分发或归档�?3. 作为视频生成用户，我希望下载按钮给到的是真正�?`attachment` 下载（浏览器保存文件），而不是打开一个新播放标签页�?4. 作为视频生成用户，我希望预览（播放）行为不影响下载计数，以便计数反映真实的下载意愿�?5. 作为视频生成用户，我希望每次点击下载，该任务的下载次�?+1，以便追踪成片的传播�?6. 作为视频生成用户，我希望在历史任务列表的每一行看到该任务的「下�?N 次」，以便概览哪些成片被下载最多�?7. 作为视频生成用户，我希望在生成完成的成功面板上立即看到本次成片的下载次数，以便确认下载已生效�?8. 作为视频生成用户，我希望历史列表里的每行同时提供「预览」与「下载」两个独立链接，以便预览和下载互不影响�?9. 作为视频生成用户，我希望未完成任务（�?done）无法通过下载端点取到文件�?04），以便不会下载到不完整的成片�?10. 作为视频生成用户，我希望范围播放（Range 请求，浏览器拖进度条）不增加下载计数，以便计数只统计整片下载�?11. 作为系统管理员，我希望下载计数持久化存储（重启服务不丢失），以便历史统计可靠�?12. 作为视频生成用户，我希望确认系统生成的成片真实的包含图片轮播画面，以便对流水线质量有信心�?
## 方案与决策点（Implementation Decisions�?
### 已确认的现状事实
- 轮播能力已存在于 `render_scenes`（pipeline 通过 `build_photo_carousel.mjs` 为每节渲染轮播场景，`--no-carousel` 可显式关闭），本�?*不实现新能力，只验证**�?- 当前 `GET /api/tasks/{id}/video` 响应头带 `attachment; filename="{id}.mp4"`，浏览器可能直接下载而非播放——这是「预�?下载同一功能」的根因�?
### 数据�?- `tasks` 表新�?`download_count` 列（`INTEGER NOT NULL DEFAULT 0`），通过既有迁移机制追加（沿�?`_MIGRATIONS` + `PRAGMA table_info` 的模式，�?`stage_timings`、`llm_usage` 等先例一致）�?- 新增 `increment_download_count(task_id) -> int`，返回递增后的值；`update_task` 允许字段加入 `download_count`；`list_tasks` / `get_task` 天然带出该列�?
### API 契约
- `GET /api/tasks/{id}/video` �?inline（`Content-Disposition: attachment` **移除**）；保留 `Range`/206/416 逻辑�?`Accept-Ranges`；未完成或文件缺失仍 404�?- `GET /api/tasks/{id}/download` �?校验任务存在�?done + 文件存在（否�?404），�?`increment_download_count`，再返回 `attachment; filename="{id}.mp4"` 的完整流（不�?Range 协商，整片下载）。返回头可带 `X-Download-Count` 便于前端读取�?- `GET /api/tasks` 列表项新�?`download_count` 字段（前端展示用）。不改其它字段�?
### 前端
- 生成完成面板：内�?`<video controls>` �?`/video` 预览；「下载成片」按钮用 `download="final.mp4"` 指向 `/download`；完成后展示「已下载 N 次」�?- 历史任务列表：每一行拆为「预览�?新标�?`/video`) 与「下载�?`/download`)，并展示「下�?N 次」�?- SSE `done` 事件不额外推�?count（前端展示时用任务列�?/ 打开面板时拉取的最新任务数据即可），保持事件契约不变�?
### 被否决的替代方案
| 替代 | 否决原因 |
|------|---------|
| 仅复�?`/video` 端点 + `<a download>` 属�?| 无法区分触发来源、不能可靠计数；且现�?attachment 头会让预�?播放行为混乱，语义依旧模�?|
| 前端 JS fetch �?Blob �?手动下载 | 重新实现 Range/异常/进度处理，且�?SSE `done` 时序耦合；后端一�?attachment 头即是全部需�?|
| 每个 `/video` 请求�?+1 | 预览播放、拖进度条（Range）、扫库都会被误计为下载，计数失去意义 |
| 下载计数只存内存 | 服务重启即丢失，不符持久化要�?|

## 测试决策（Testing Decisions�?
- **测试外部行为，不测实现细�?*：断言 HTTP 响应头与计数变化，不 mock SQL�?- **测试模块**：`tests/web/test_api.py`（含 fixture、Range 既有先例）�?- **数据�?seam**：沿用现�?`db.init_db()` + 任务 fixture 模式（先例：`test_mark_interrupted` �?`client.post("/api/generate")` + `db.update_task`）�?- **新增用例**�?  - `test_download_increments_count`：done 任务 �?�?`/download` 两次 �?`download_count == 2`（读 `db.get_task` �?`X-Download-Count` 头）�?  - `test_video_preview_does_not_increment`：调 `/video`（含 Range）后 `download_count` 仍为 0�?  - `test_download_before_done_404`：未完成/不存在任�?�?`/download` 404�?  - `test_video_inline_no_download`：`/video` 响应不含 `Content-Disposition: attachment`�?  - 前端 HTML 断言：`index.html` 含独立预�?下载链接与「下�?N 次」文案�?
## 验收标准（Acceptance Criteria�?
1. `GET /api/tasks/{id}/video` 返回可内嵌播放的 inline 流（�?attachment 头），Range 播放正常�?2. `GET /api/tasks/{id}/download` 返回 attachment 下载，且每次调用 `download_count +1`�?3. 预览（含 Range）不增加 `download_count`�?4. 未完成任�?文件缺失 �?下载 404�?5. 历史任务列表每行展示「预览」「下载」独立入口与「下�?N 次」�?6. 生成完成面板：可内嵌预览、有独立下载按钮、展示「已下载 N 次」�?7. `download_count` 持久化（重启服务不归零）�?8. 抽查一个已完成任务成片的若干帧，确认包含图片轮播画面（多张图交替）�?9. `tests/web` 全量测试通过（现�?100+ 用例 + 新增用例）�?
## 范围外（Out of Scope�?
- 不实现下载限�?配额、不统计下载者身份（单用户服务）�?- 不改变轮播渲染实现、不调整 Pexels 取图逻辑�?- 不做一次下载计数到余额/成本换算�?- 不改 SSE 事件契约、不动任务创�?执行路径�?
## 进一步说明（Further Notes�?
- 方案刻意保持「最小修改」：后端只改 Video 端点�?+ 加一�?Download 端点 + 一个迁移列 + 一个计数函数；前端只改两处展示。不触碰任务队列、worker、SSE、flutter 渲染路径�?- 下载文件命名沿用 `{task_id}.mp4`（与服务�?004-05 �?Range 下载命名一致），前�?`download="final.mp4"` 属性可改写为语义名�?
## 关联票（Tickets�?
- `issues/006-01-video-preview-download-split.md`
- `issues/006-02-download-count-persist.md`
- `issues/006-03-frontend-preview-download-ux.md`
- `issues/006-04-verify-carousel-and-tests.md`