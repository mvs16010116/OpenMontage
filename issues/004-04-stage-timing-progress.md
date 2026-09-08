# 004-04 - 阶段计时 + SSE 扩展 + 前端进度展示

**Status:** ready-for-agent  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-03（05 依赖本票）

## 目标

给管线每个阶段计时并落库，SSE 推送扩展阶段耗时与总耗时；前端进度条显示各阶段耗时、总耗时与 LLM token 统计。

## 验收标准

1. `pipeline.py` 每步累计 `stage_timings`（阶段名 → 秒），`progress(stage, message, phase_duration_s, total_elapsed_s)` 上报；`done` 汇总总耗时。
2. `tasks` 增加 `stage_timings`（JSON）、`llm_usage`（JSON）、`total_elapsed_s`（REAL）。
3. SSE payload：`{stage, message, phase_duration_s, total_elapsed_s}`；`done` 事件携带 `llm_usage` 与最终耗时。
4. `GET /api/tasks/{id}` 返回含 `stage_timings`/`llm_usage`/`total_elapsed_s` 的任务详情。
5. 前端任务卡：进度条 + 当前阶段文字（含本阶段耗时、总耗时），完成后展示阶段耗时表与 token 统计。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/pipeline.py` | 改造 | 阶段计时上报 |
| `web/worker.py` | 改造 | SSE 推送扩展、落库扩展字段 |
| `web/db.py` | 改造 | tasks 扩展字段 |
| `web/server.py` | 改造 | SSE 事件扩展、详情接口 |
| `web/templates/index.html` | 改造 | 进度条/耗时/token 展示 |

## 验证

手动生成任务，前端看到随阶段推进的耗时数据与完成后的阶段耗时表、token 统计。