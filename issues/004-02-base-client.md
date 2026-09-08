# 004-02 - Base 集成层（扫描/回填/上传）

**Status:** ready-for-agent  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-01（05 依赖本票）

## 目标

封装 lark-cli（subprocess，user 身份）的多维表格读/写能力：按日期字段排序扫描待处理记录、批量回填状态字段、上传视频附件；提供 `/api/base/scan`；tasks 按 record_id 去重。

## 验收标准

1. `web/base_client.py` 封装：`resolve_base`（URL 或 token）、`scan_records`（按日期字段排序、过滤状态为空/待处理、限 `max_records_per_batch`）、`update_status`（批量写状态字段）、`upload_video`（附件字段追加视频）。
2. Windows 下 lark-cli 通过 `.cmd` 解析调用（沿用 `_windows_cmd` 模式），错误输出转为可读中文错误。
3. `POST /api/base/scan` 读取配置后扫描并返回 `[{record_id, title, content, date}]`；重复扫描已入队/运行/完成的任务不重复创建。
4. `tasks` 表增加 `record_id`（唯一）与 `base_record_title`，`record_id` 冲突时返回既有任务。
5. 未配置 base/table 时返回可读提示而非崩溃。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/base_client.py` | 新增 | lark-cli subprocess 封装 |
| `web/base_client_test.py` | 新增 | 命令构造/错误解析单测（不实调 lark-cli） |
| `web/db.py` | 改造 | tasks 表扩展字段 |
| `web/server.py` | 改造 | `/api/base/scan` 路由 |
| `web/templates/index.html` | 改造 | 任务视图「扫描」按钮与结果列表 |

## 验证

配置 base 后调用 `/api/base/scan` 返回按日期排序的待处理记录；重复扫描无重复任务。