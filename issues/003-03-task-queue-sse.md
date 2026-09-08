# 003-03 - Task Queue + SSE Progress

**Status:** done  **Spec:** issues/003-narration-synth-web-service.md  **Blocking:** 依赖 003-01（路由）、003-02（pipeline 核心）

## 目标

用 APScheduler 驱动后台任务执行 pipeline，通过 SSE 向前端推送进度。

## 验收标准

1. `POST /api/generate` 提交文案后，任务立即在后台开始执行（不阻塞 HTTP 响应）。
2. 同一时间只跑一个任务（队列串行，第二个任务进入 `queued` 状态）。
3. `/api/tasks/{id}/events` SSE 端点推送 JSON 事件：`{"stage": "generating_tts", "message": "正在生成配音..."}`。
4. 前端通过 `EventSource` 连接后实时收到阶段更新。
5. 任务完成后 SSE 推送 `{"stage": "done", "message": "生成完成"}` 并关闭连接。
6. 任务失败时 SQLite 标记 `error`，SSE 推送 `{"stage": "error", "message": "..."}`。
7. 重启服务后，未完成任务标记为 `interrupted`，不自动恢复。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/worker.py` | 新增 | APScheduler job + pipeline runner |
| `web/server.py` | 修改 | 集成 scheduler + SSE 端点 |
