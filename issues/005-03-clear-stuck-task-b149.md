# 005-03 — 处理卡死任务 b149087c33bd

**What to build:** 把卡住 30+ 分钟的 running 任务 b149087c33bd 置为 `error`（带可读 error_message），释放串行 worker 锁，让队列恢复接收新任务；用户可后续在 UI 重提该文案。

**Blocked by:** 005-01（先让代码具备超时语义，再清理历史任务，语义一致）

**Status:** ready-for-agent

- [ ] 提供（或复用现有）把 running 任务置 error 的接口，不重启服务进程（PID 9428 不变）
- [ ] b149087c33bd 状态变为 `error`，`error_message` 可读（如 "edge-tts hang; superseded by timeout fix"）
- [ ] `GET /api/tasks` 中该任务不再 `running`，worker 锁释放，可接受新任务
- [ ] 项目目录产物保留，未删除（可后续重提）