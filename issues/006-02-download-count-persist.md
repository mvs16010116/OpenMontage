# 006-02: 下载次数持久化与计数

**What to build:** 记录每个任务被「下载」的次数，持久化�?SQLite（重启服务不丢），并�?`/download` 触发时递增；任务列�?详情自然带出 `download_count` 供前端展示。预览（�?Range 播放）不计次数�?
**Blocked by:** 006-01 服务端预�?下载端点拆分（`/download` 端点已存在）

**Status:** done

- [ ] `tasks` 表新�?`download_count` 列（`INTEGER NOT NULL DEFAULT 0`），通过既有 `_MIGRATIONS` 机制迁移
- [ ] 新增 `increment_download_count(task_id) -> int`（返回递增后值）；`update_task` 允许字段�?`download_count`
- [ ] `/download` 每调用一次计�?+1，响应带 `X-Download-Count` �?- [ ] 新增测试：done 任务 `/download` 两次 �?`download_count == 2`；`/video`（含 Range）不增计�