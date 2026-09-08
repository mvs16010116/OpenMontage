# 004-05 - 端到端总装（触发 / 轮询 / 回填 / 上传 / 预览）

**Status:** done  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-02, 004-04

## 目标

把 Base 流水线全线接通：扫描 → 手动/批量触发 → 单任务串行执行 → 完成后回填状态字段与上传视频附件；自动轮询定时扫描；前端视频预览 + 下载；错误可读化。

## 验收标准

1. `POST /api/tasks` 接受 `record_id`（来自扫描）或直接 `narration_text`；`POST /api/tasks/batch` 批量入队。
2. worker 自动轮询：`poll.enabled` 时按 `interval_seconds` 扫描并创建待处理任务（受单任务串行约束排队）。
3. 任务完成后置步骤：状态字段写「成功/失败」；成功则上传 `final.mp4` 到附件字段；回填/上传失败记录 `base_sync_status=failed` 与错误，不影响任务本体状态。
4. `GET /api/tasks/{id}/video` 支持 Range（浏览器预览），前端 `<video controls>` 播放 + 下载按钮。
5. lark-cli / LLM / 管线任一环节失败均给出可读错误，任务 `error` 并回填「失败」。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/server.py` | 改造 | 任务创建/批量路由、视频 Range 流响应（206/416） |
| `web/worker.py` | 改造 | 手动队列 + 自动轮询 + 后置回填/上传（`_sync_base`/`_mark_processing`） |
| `web/db.py` | 改造 | `base_sync_status`、`base_sync_error` 字段 |
| `web/templates/index.html` | 改造 | `<video controls>` 预览 + 下载按钮（done 事件接线） |

## 验证

- 新增测试 +14 -> `tests/web/` 共 **75 passed**：
  - `test_api.py`：POST /api/tasks 按文案 / 按 record_id（含未知记录 400、重复去重）、batch 批量入队去重、任务/批量需登录、视频 Range（全量 / `bytes=2-5` / 后缀 / 超出 416）。
  - `test_worker.py`（新）：`_sync_base` 成功回填+上传（`base_sync_status=ok`）、无 record_id 跳过、失败记录 `failed`+错误；`_mark_processing` 写「处理中」；`_poll` 按 `interval_seconds` 入队待处理记录、空文案跳过、间隔内去重、`poll.enabled=false` 不扫描。
- commit：`ea658ab`（代码）、`3df82c1`（004-04 证据提交）后追加本票证据。
- 主动画：配置真实多维表格与 LLM 后，走通「扫描 → 选中生成 → 进度推进 → 成功回填/上传 → 前端预览下载」全流程；开启轮询后自动建任务（需真机 lark-cli 认证）。