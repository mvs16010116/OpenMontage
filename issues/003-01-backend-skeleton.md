# 003-01 - Backend Skeleton + SQLite + FastAPI Routes

**Status:** done  **Spec:** issues/003-narration-synth-web-service.md  **Blocking:** 无（T2/T3 依赖本票）

## 目标

搭建 Web 服务骨架：FastAPI 应用、SQLite 表结构、REST API 路由、静态文件挂载。

## 验收标准

1. `web/server.py` 启动后访问 `http://localhost:8000` 返回 `index.html`。
2. `POST /api/generate` 接受 `{"narration_text": "..."}` → 创建 SQLite 记录 → 返回 `{"task_id": "...", "status": "queued"}`。
3. `GET /api/tasks` 返回任务列表（按 created_at 降序）。
4. `GET /api/tasks/{id}` 返回单个任务状态。
5. `GET /api/tasks/{id}/video` 在任务完成时返回 `final.mp4` 下载（404 如果未完成）。
6. `GET /api/tasks/{id}/events` 返回 SSE 流（占位，T03 实现推送）。
7. SQLite 表结构：`tasks(id TEXT PK, status TEXT, narration_text TEXT, created_at TEXT, started_at TEXT, finished_at TEXT, output_path TEXT, error_message TEXT)`。
8. `web/requirements.txt` 包含 `fastapi, uvicorn, apscheduler`。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/server.py` | 新增 | FastAPI app + 路由 |
| `web/db.py` | 新增 | SQLite init + CRUD |
| `web/templates/index.html` | 新增 | 占位 HTML（T04 完善） |
| `web/requirements.txt` | 新增 | 依赖 |
