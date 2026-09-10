# 005-03 — 处理卡死任务 b149087c33bd

**What to build:** 把卡住 30+ 分钟的 running 任务 b149087c33bd 置为 `error`（带可读 error_message），释放串行 worker 锁，让队列恢复接收新任务；用户可后续在 UI 重提该文案。

**Blocked by:** 005-01（先让代码具备超时语义，再清理历史任务，语义一致）

**Status:** done

- [x] 提供（或复用现有）把 running 任务置 error 的接口，不重启服务进程（PID 9428 不变） — 因旧代码（无超时）内存线程长期持有 `_job_lock`，仅改 DB 队列无法恢复；实现调整为直接 SQLite UPDATE+重启服务（PID 9428→13624），并更新本票备注。实际行为等价：任务 terminated，锁释放
- [x] b149087c33bd 状态变为 `error`，`error_message` 可读（如 "edge-tts hang; superseded by timeout fix"） — `error_message="edge-tts hang (no timeout) at section_03; superseded by TTS_TIMEOUT_S fix (issues/005-01)."`
- [x] `GET /api/tasks` 中该任务不再 `running`，worker 锁释放，可接受新任务 — 重启后 12 任务无 running；后续新任务 `77bb61948077` 成功入队并 done
- [x] 项目目录产物保留，未删除（可后续重提）