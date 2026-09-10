# 004-08 — Base 扫描单选最新文案 + 语义化进度

**Status:** 进度：004-08-01 done / 004-08-02 done（实现完成，待提交）  **Spec:** 本文件  **Blocking:** 004-07（损坏方：扫描链路已修通）

## 目标与约束

- 每次「扫描多维表格」（手动或自动轮询）**只取一篇最新文案**生成视频，不再为整批待处理批量建任务。
- 最新排序：按日期**降序**（最新在前）；日期相同的按文案内容**升序**平局决胜。（决策：Date desc + Content asc）
- 同一条记录只存在一个任务（`record_id` UNIQUE 不变）。遍历最新的候选时：
  - 记录无任务 → 新建任务。
  - 记录已有任务且状态为 `done`（已生成视频）→ 跳过，取下一条。
  - 记录已有任务且状态为 `error`/`interrupted`（生成失败）→ **重置为 queued 重试**（复用原任务，不新建）。
  - 记录已有任务且状态为 `queued`/`running` 等其它 → 跳过，取下一条（进行中不重复）。
- 全部候选都被跳过时，本轮不建任务，返回明确提示。
- 进度文案语义化：`文案整理中 → 配音生成中 → 配图检索中 → 渲染中 → 生成字幕中 → 合成成片中 → 生成完成`；手动扫描后前端**自动订阅**新任务/重试任务的实时进度。
- 约束：过滤语义「状态为空 或 =待处理」不变；`scan_records` 契约 `[{record_id,title,content,date,raw}]` 不变；失败任务的重试不得破坏阶段统计/记录（重试不动 stage_timings/llm_usage 之外的历史字段之外其余字段仅清 error_message）。

## 方案与决策点

- **决策 1（跳过语义）**：用户拍板「只跳成功，失败重试」。因此选择器对每一条候选调 `task_lookup(record_id)` 判定动作：`create` / `retry` / `skip`（含原因）。
- **决策 2（同时间平局）**：用户拍板文案升序。用 Python 两次稳定排序实现「date 降序 + content 升序」联合序（先按 content 升序排，再按 date 降序稳定排），空日期排最后。
- **决策 3（轮询同规则）**：用户拍板自动轮询与手动扫描同规则，每轮最多建/重置一个任务。
- **决策 4（进度+订阅）**：用户拍板按语义化中文文案更新 + 扫描后自动订阅新任务 SSE。
- 方案分层：
  1. 新增**纯函数选择器**（新模块，无 CLI/DB 依赖，构造式可测）：入参 `rows` + `task_lookup`，返回 `{"record": row, "action": "create"|"retry", "task_id"?: str} | None`。
  2. server `/api/base/scan` 与 worker `_poll` 共用该选择器；`create` 时 `db.create_task(...)`，`retry` 时 `db.update_task(task_id, status="queued", error_message="")`。
  3. 扫描响应扩展原因字段：`skipped` 数组带 reason（「已生成视频」/「生成中」/「文案为空」），并新增 `picked`/`message` 供前端展示。
  4. 备选（被否）：把「最新一篇」下推到 Base `--sort-json` 多加一个文案排序键——文本字段排序 API 支持不稳，且平局只需本地一次稳定排序，收益低；选择器直接在 server/worker 各写一份——重复且不可测。
- 关键事实（来自 004-07 实测）：扫描只返回「状态空/待处理」的记录；Base 状态已回填成功(如「成功」)的记录不会出现在扫描集合里，因此 `done` 跳过主要兜底「任务成功但 Base 回填失败」的情形；`error/interrupted` 同理兜底「Base 未回填失败字样」的记录。

## 验收标准

1. 给定 `rows` 乱序（含相同日期多条、空日期、无任务/已 done/已 error/已 queued 各种），选择器稳定返回排序正确、动作正确的结果；全部 done 时返回 `None`。
2. `_poll` 一轮至多新建 **1** 个任务；已建后按 interval 再来一轮，无新候选时不新建；error 记录重置为 queued。
3. `/api/base/scan`：成功路径返回 `{pending, created, skipped, picked, message}`；created/retried 至多 1 条；skipped 带中文 reason。
4. 前端 `STAGE_LABEL` 与 pipeline 阶段消息同步为语义化中文；点「扫描多维表格」后立即监听新任务的 `events`，进度条依次显示 文案整理中/配音生成中/渲染中 等并最终「生成完成」。
5. `tests/web/` 全绿（新增 test_scan_policy.*；更新 test_worker/poll 与 test_api scan 成功路径）。

## 验证（实现后回填）

- **单测**：新增 `tests/web/test_scan_policy.py`（11 例：date 降序、日期相同按内容升序[乙<甲]、done 跳过取下一、error/interrupted 重试、queued/running 跳过、全部 done 返回 None、空日期排最后、broken 记录 skip 原因、比选中更旧记录不背原因）；`tests/web/` 全套 **100 passed**。
- **worker 回归**：`test_poll_enqueues_only_newest_pending`（一轮只建 1 个，"interval 内再 poll 不建"）、`test_poll_retries_failed_and_skips_done`（done 跳过、error 复用原任务置 queued 且清 error_message、不产生重复任务）。
- **API 回归**：`test_base_scan_picks_single_newest` / `test_base_scan_skips_done_and_takes_next` / `test_base_scan_retries_failed_newest` / `test_base_scan_all_done_returns_noop_message`。
- **HTTP E2E**（服务重启 PID 9428，`python -X utf8 -m web.server`）：登录 → `/api/base/scan` 首次返回 `pending=1, created=[], retried={recvuNBBjoMci8, b149087c33bd}, picked={...}, skipped=[], message=已定格最新文案…重试`；第二次扫描 `pending=0`（重试任务被 worker 立即置 Base「处理中」）、`message=当前没有待处理文案`；重试任务 `GET /api/tasks/b149087c33bd` → `status=running, error_message=''`。中文正文经 python -X utf8 直连验证无乱码（此前 PowerShell 显示乱码为控制台编码伪象）。
- 前端：`STAGE_LABEL` 已切换语义化文案；扫描按钮在 `body.created[0]`/`body.retried` 时自动 `listen(task_id)` 订阅 SSE。

## 拆票

- **004-08-01** 单选最新文案策略：新选择器模块 + server scan 接线 + worker `_poll` 接线 + 单测/回归（Status: done）。
- **004-08-02** 语义化进度 + 扫描自动订阅：pipeline 阶段消息、前端 `STAGE_LABEL`、scanBtn 自动 `listen`（Status: done）。