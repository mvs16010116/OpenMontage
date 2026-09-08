# 004-05 - 端到端总装（触发 / 轮询 / 回填 / 上传 / 预览）

**Status:** ready-for-agent  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-02, 004-04

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
| `web/server.py` | 改造 | 任务创建/批量路由、视频 preview 响应 |
| `web/worker.py` | 改造 | 手动队列 + 自动轮询 + 后置回填/上传 |
| `web/db.py` | 改造 | `base_sync_status` 字段 |
| `web/templates/index.html` | 改造 | 任务视图完整化（扫描→选择→生成→预览/下载、轮询状态） |

## 验证

配置真实多维表格与 LLM 后，走通「扫描 → 选中生成 → 进度推进 → 成功回填/上传 → 前端预览下载」全流程；开启轮询后自动建任务。