# 003-05 - E2E Integration Test + Verification

**Status:** done  **Spec:** issues/003-narration-synth-web-service.md  **Blocking:** 依赖 003-01~003-04（全部）

## 目标

端到端验证整个 Web 服务：粘贴文案 → 生成 → 下载 → 视频质量检查。

## 验收标准

1. 启动服务 `python -m web.server` → 浏览器访问 `http://localhost:8000` → 页面正常加载。
2. 粘贴一段口播文案（50-200 字）→ 点击生成 → 进度条依次显示阶段 → 完成后可下载。
3. 下载的 `final.mp4` 质量检查：
   - 1920×1080、h264、aac、30fps
   - 时长 > 30s（文案长度决定）
   - 字幕白像素 ≥ 4000（烧字幕成功）
   - narration dB 在正常范围（-25 ~ -30 dB）
4. REST API 验证：
   - `POST /api/generate` 返回 200 + `task_id`
   - `GET /api/tasks/{id}` 返回正确状态
   - `GET /api/tasks/{id}/video` 返回 mp4 下载
   - `GET /api/tasks` 返回历史列表
5. 历史列表显示正确（文案摘要、状态、时间、下载链接）。
6. 重启服务后历史记录保留（SQLite 持久化）。
7. 同时提交两个任务：第二个排队等待，第一个完成后自动开始第二个。

**验证证据（2026-09-08）：** `tests/web/test_api.py`（8）+ `test_pipeline.py`（7）共 15 用例全绿；真实服务启动后 `POST /api/generate`（UTF-8 中文）→ SSE 实时收到 queued/parse_script/generating_tts/fetching_images/rendering_scenes → done，`GET /api/tasks/{id}/video` 返回 video/mp4（3.1MB），历史列表正确。注意 PowerShell `ConvertTo-Json` 会吃掉中文（测试用 Python 客户端）；PowerShell 里发中文要用 `--% ` 或 Python。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/web/test_api.py` | 新增 | pytest API 测试 |
| `tests/web/test_pipeline.py` | 新增 | pytest pipeline 单元测试 |
