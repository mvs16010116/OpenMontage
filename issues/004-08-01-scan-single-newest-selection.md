# 004-08-01 — 扫描单选最新文案（策略层 + server/worker 接线）

**Parent:** `issues/004-08-scan-single-newest.md`

**What to build:**

用户点击「扫描多维表格」（或自动轮询触发）时，系统从待处理文案中**只取最新一篇**来生成视频：

- 最新判定 = 日期降序，日期相同按文案内容升序（空日期排最后）。
- 最新候选无任务 → 新建任务；已有 `done` 任务 → 跳过并取下一条；已有 `error`/`interrupted` → 重置该任务为排队重试（复用原任务，不新建）；已有 `queued`/`running` → 跳过并取下一条。
- 全部候选都不可做时本轮不建任务，并给出可读提示（如「最新 N 条都已生成视频」）。
- 同一规则同时用于自动轮询：一轮至多新建/重置 1 个任务。

**Blocked by:** `issues/004-08-scan-single-newest.md`（决策已定）; `issues/004-07-base-text-field-filter-operator.md`（done，扫描链路可用）

**Status:** done

- [x] 新增一个无 CLI/DB 依赖的纯函数选择器：输入 `rows`（`{record_id,title,content,date}` 列表）+ `task_lookup(record_id) → task|None`，返回最新可做的 `{record, action: create|retry, task_id?}` 或 `None`；顺序 = date 降序、content 升序（稳定排序），空日期排最后。
- [x] 手动扫描接线：/api/base/scan 用同一选择器；action=create 建任务，action=retry 将该任务重置为 queued 并清 error_message；响应含 `pending/created/retried/picked/message`，`skipped` 带中文原因（「已生成视频」「生成中」「文案字段为空」「缺少记录号」），created/retried 至多 1 条。
- [x] 自动轮询接线：`_poll` 用同一选择器，一轮至多 1 个任务；无候选或全部跳过时不建。
- [x] 既有测试收敛 + 新测试：`tests/web/test_scan_policy.py`（排序平局、done 跳过取下一条、error 重试、全部 done 返回 None、空日期排最后）；`test_worker` 的 poll 用例收敛为「每轮只建最新一条」；`test_api` 补 scan 成功路径断言响应形状。
- [x] `tests/web/` 全绿（100 passed）；真实 Base 手动扫描返回 picked/retried 且至多 1 个任务（已验：pending=1 → retried 一条，二次扫描 pending=0 无新建）。