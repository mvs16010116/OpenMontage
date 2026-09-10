# Handoff — OpenMontage

**Date:** 2026-09-10
**Branch:** main (004-07 与 004-08 改动将各自单独提交；已提交到 `c669020` merged+pushed)
**Next-session focus:** 提交本次 004-07 + 004-08 改动（先 base_client/test_base_client/issues-004-07，再 scan_policy+server+worker+tests+issues-004-08，再 pipeline+index.html+issues-004-08-02，最后 HANDOFF）。之后走通真机全流程并验证 poll.enabled 自动轮询。Tracker: issues/001..004。

---

## 1. What this session accomplished

### 004-07 — Base 扫描链路三根因修复（done，待提交）
修复 `/api/base/scan` 在真实多维表格上的 502。三个相互独立根因（`web/base_client.py`）：
1. 状态字段是**文本字段**时 `intersects` 数组过滤必失败（`800010507`）→ 改 `==`（保留 OR 空 语义）。
2. lark-cli `+record-list` 返回**行式** `{data:{data:[[..]],field_id_list:[..]}}`，旧 `_records_from` 只认 dict 列表 → 静默 0 条 → 重写解析（`_field_map`/`_record_id_field`/`_resolve_field_ids`/`_rows_from`）。
3. `_run` 无 `encoding="utf-8"` → 服务（无 `-X utf8`）按 GBK 解码乱码 → `字段「优化文案」不存在` → 显式 `encoding="utf-8"`。
新增回归 `test_run_decodes_utf8_stdout`；全套件 **85 passed**；HTTP E2E 200。

### 004-08 — 扫描单选最新文案 + 语义化进度（done，待提交）
- **004-08-01** 新模块 `web/scan_policy.py`（纯函数 `pick_candidate(rows, task_lookup)`，无 CLI/DB 依赖）：
  - 顺序 = date **降序**（空日期排最后）→ 同日按 content **升序**（稳定二段排序）。
  - 遍历最新→最旧，首个可做项：无任务→`create`；`error`/`interrupted`→`retry`（复用原任务置 queued 并清 error_message）；`done`/`queued`/`running`→`skip`（带中文原因：已生成视频/生成中/文案字段为空/缺少记录号）。
  - server `/api/base/scan` 与 worker `_poll` 共用；每轮**至多 1 个任务**；响应新增 `retried/picked/message`。
- **004-08-02** 阶段消息语义化：文案整理中→配音生成中→配图检索中→渲染中→生成字幕中→合成成片中→生成完成（pipeline emit 与前端 `STAGE_LABEL` 同步）；前端 `listen` 优先用 `ev.message`；扫描按钮在 `created[0]`/`retried` 时自动 `listen(task_id)` 订阅 SSE。
- 测试：新增 `tests/web/test_scan_policy.py`（11 例），worker poll 收敛为新规则，API 补 4 例成功路径。**`tests/web/` = 100 passed**。
- HTTP E2E（服务 PID 9428，`python -X utf8 -m web.server`）：首次 scan `pending=1` → `retried={recvuNBBjoMci8, b149087c33bd}`（该任务此前 error/interrupted）；二次 scan `pending=0, message=当前没有待处理文案`（worker 已把它置 Base「处理中」）；重试任务 `GET /api/tasks/b149087c33bd` → `status=running, error_message=''`。中文经 python -X utf8 直连无乱码（先前 PowerShell 显示乱码为控制台伪象）。

## 2. Key gotchas learned (do not re-hit)

（沿用 004-07 起补齐的全部既有条目；本节新增本次教训）

- **乱码先分清「服务端 vs 控制台」**：服务端 FastAPI 是干净 UTF-8，PowerShell `Invoke-RestMethod` 回显中文会变 `?`——用 `python -X utf8` + urllib 直连验证正文，勿据此误判服务端编码回归。
- **服务重启砍进程前先确认 PID**：`Stop-Process -Id <服务PID>` 可能连带杀掉工具链自身 shell（上次 `-Name python` 已踩）。用 `Get-Process python` 区分，按 Id 精确杀。
- **PowerShell 无 heredoc**（`python - <<'PY'` 会当缺文件规范报错）：临时脚本一律写 `%TEMP%\opencode\*.py` 再跑。
- **HTTP 405 别慌**：FastAPI 对未定义 method 返回 405。脚本 `post()` 只支持 POST，取任务详情要 GET。

## 3. Artifacts / files (reference these, don't duplicate)

- 004-08 新增/改动：`web/scan_policy.py`（新）、`web/server.py`（scan 单选+retry+message）、`web/worker.py`（`_poll` 单选）、`web/pipeline.py`（语义化 stage message）、`web/templates/index.html`（STAGE_LABEL + 自动订阅）、`tests/web/test_scan_policy.py`（新）、`tests/web/test_worker.py`、`tests/web/test_api.py`。
- 004-07 仍待提交：`web/base_client.py`、`tests/web/test_base_client.py`、`issues/004-07-…….md`。
- 票据：`issues/004-08-scan-single-newest.md`（spec+done 验证回填）、`issues/004-08-01-…-selection.md`、`issues/004-08-02-…-subscribe.md`（均 done）。
- 验证脚本：`%TEMP%\opencode\verify_scan_00408*.py`。

## 4. Suggested skills for next agent

- `implement`（按票实现）、`handoff`（格式同本文件）、`code-review`（提交前复查 004-08 diff）、`grilling`/`to-spec`/`to-tickets`（新 feature）。Web：FastAPI+APScheduler+SSE，见 `issues/003-03`。

## 5. Open items / hygiene

- 提交顺序（git 身份 `Dannyhiccpet <danny@hiccpet.com>`，只 stage 相关文件，工作区大量 `_tmp_*.py`/`.reasonix`/`.agents`/`projects` 无关）：
  1. `issues/004-07`：`web/base_client.py` + `tests/web/test_base_client.py` + `issues/004-07-….md`。
  2. `issues/004-08-01`：`web/scan_policy.py` + `web/server.py` + `web/worker.py` + `tests/web/test_scan_policy.py` + `tests/web/test_worker.py` + `tests/web/test_api.py` + `issues/004-08-scan-single-newest.md` + `issues/004-08-01-….md`。
  3. `issues/004-08-02`：`web/pipeline.py` + `web/templates/index.html` + `issues/004-08-02-….md`。
  4. 本 HANDOFF.md。
- 真机待办：配置真实多维表格 + LLM（base_url/model/api_key）后走通「扫描→单选最新→进度→成功回填/上传→预览」；开 `poll.enabled` 验证自动单任务轮询（当前 poll.enabled=False）。lark-cli `--as user`（user=侯辉聪，openId `ou_bec77ebe8e7a0d5a6c41d620af4116a6`）。默认登录 admin / `shiping@shiping`。
- 真实表（base_token `OZsLb287vaT2j8srKYXcyw05nkc`，table `tbl6rLRt9fdRbNa7`）：record_id=`fldC5GNO9A`(formula)；`content_field` 当前显示「优化文案」（曾见「新闻改写」，漂移中）；`date_field=创建时间`；`status_field=调用智能体`(text)；`attachment_field=附件`；`date_sort=desc`；进展字段与状态词在 settings `video` 区。
- 任务表现状：历史多次 error/interrupted 属旧轮次遗留；004-08 起扫描按「只跳 done、失败重试」处置，无需人工清理。
- 服务器当前：PID 9428（`python -X utf8 -m web.server`）；日志 `%TEMP%\opencode\webserver.log/.err.log`；运行时 db `web/narration_synth.db` gitignored。