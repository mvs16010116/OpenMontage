# 004-07 — Base 文本状态字段：过滤操作符 + 字段解析 + 编码解码

**Status:** done  **Spec:** 本文件（修复 004-02 引入）/ 目标 spec `issues/004-narration-synth-lark-llm.md`  **Blocking:** 004-02（损坏方）

## 目标与约束

- 让 `/api/base/scan` 在真实多维表格上成功返回待处理记录；修复三个相互独立的问题：
  1. 状态字段为**文本字段**时 `intersects` 数组过滤必失败（`800010507`）；
  2. lark-cli `+record-list` 返回**行式**数据，旧解析层只认 dict 列表 → 静默返回 0 条；
  3. CLI 输出为 UTF-8，`_run` 未指定 `encoding` → 服务器（无 `-X utf8`）按 GBK 解码 → 中文字段名乱码 → 配置字段「不存在」。
- 约束：不改变「状态为空 或 状态=待处理」的取数语义；过滤/排序仍在 Base 端完成（`--filter-json`/`--sort-json`）；`scan_records` 对外契约 `[{record_id, title, content, date, raw}]` 不变；配置字段名不存在时必须显式报错而非静默空值。

## 方案与决策点

- **根因 1（过滤操作符）**：`web/base_client.py` `_status_filter` 生成 `[status_field, "intersects", [pending_if]]`。lark-cli 的 `--filter-json` DSL 中，`intersects` 对**文本字段**只接受字符串（大小写敏感包含匹配）；传数组仅对多选/单选字段合法。真实 Base 的 `调用智能体` 是文本字段 → Feishu API 报 `800010507 invalid_request / "Only string values are supported"`。逐项 bisect 证据：无 filter/sort 均 OK；仅 `intersects` 数组 → 必败；`empty`、`== 待处理`、`== ""` 均 OK；组合 `empty OR ==待处理` 返回 9 条（全部为空状态，因当前无字面「待处理」行）。
- 备选（被否）：
  1. `intersects "待处理"`（字符串）——文本 contains（LIKE）匹配，会把「待处理中/已待处理」一并命中，语义过宽。
  2. 检测字段类型再选操作符——需额外的字段元数据调用，复杂度高、收益低。
- **方案 1**：`_status_filter` 第二个条件改 `[status_field, "==", pending_if]`，保持 `or` 语义为「空 或 等于待处理」。`==` 对文本与选项字段均可用，已在真实 Base 验证。
- **根因 2（行式解析）**：lark-cli `+record-list` 返回 `{"data": {"data": [[...]], "field_id_list": [...], "field_type_list": [...]}}`（行式，列序对齐 `field_id_list`）；旧 `_records_from` 只读 dict 列表（`items`/`records`）→ 真实数据静默解析为 0 条。
- **方案 2**：解析层重写——`_field_map`（`+field-list` 按名→字段元数据）→ `_record_id_field`（找名为 `record_id` 的字段或首个含 `RECORD_ID()` 的公式字段）→ `_resolve_field_ids`（配置字段名不存在抛 `BaseClientError(f"字段「{name}」不存在，请检查字段映射")`）→ `_scan_args(settings, ids)` 按 `--field-id` 投影 → `_rows_from` 按 `field_id_list` 定位列解析行式数据，输出仍为 `{record_id, title, content, date, raw}`。删除 `_records_from`/`_field_value`/`_first_text`。
- **根因 3（编码）**：CLI 输出固定 UTF-8，`_run` 用 `text=True, errors="replace"` 但未给 `encoding` → Python 按 locale 编码（GBK）解码 → 中文乱码。服务器启动命令不带 `-X utf8`，故仅服务器路径必现（复现时用 `-X utf8` 平行直跑被掩盖）。表现恰为此前的 502 `字段「优化文案」不存在`。
- **方案 3**：`_run` 显式 `encoding="utf-8"`；服务器启动命令统一带 `-X utf8` 兜底。
- 真实环境事实（表被自动化持续改列/写入）：record_id 是公式字段（`RECORD_ID()`，type=formula，id=`fldC5GNO9A`）；配置 `content_field=优化文案`、`status_field=调用智能体`、`date_field=创建时间`、`attachment_field=附件`；列名会漂移（自动化重建输出列），显式报错即正确契约。

## 验收标准

1. `_status_filter(field, "待处理")` 返回 `{"logic": "or", "conditions": [["<field>", "empty"], ["<field>", "==", "待处理"]]}`，不再出现 `intersects`。
2. 真实 Base 上执行 `_scan_args` 生成的命令返回 `rc=0` 且含空状态记录。
3. 回归测试改锁正确契约（`==`）并在 fix 前先红；`tests/web/` 全绿。
4. `/api/base/scan` 经登录会话返回 `items`（`pending/created/skipped`）而非 `lark-cli 失败` / `字段不存在` 错误。
5. 配置字段名不存在时返回可读错误（`502 {"detail": "字段「X」不存在，请检查字段映射"}`），不静默返回空。

## 验证（实现后回填）

- **红→绿**：先改写 `test_scan_args_builds_filter_and_sort` 断言 `==`，fix 前红；fix 后 `tests/web/` 82 passed。
- **真实 Base 直跑**（`python -X utf8` + `PYTHONPATH=<repo>`，直接调 `scan_records(db.load_settings())`）：当前配置 `content_field=优化文案` 与纠正配置 `content_field=新闻改写` 均返回 7 条完整记录（record_id/date/title 正确），确认行式解析与投影有效。
- **编码修复回归**：新增 `test_run_decodes_utf8_stdout`（断言 `_run` 传 `encoding="utf-8"` 且中文列名不被 GBK 乱码）。修复后全套件 **85 passed**。
- **HTTP 端到端**（重启服务 `python -X utf8 -m web.server`，PID 10796）：`POST /api/login` 200 → `POST /api/base/scan` **200**，`pending=6`，`skipped` 全部「已存在任务」（此前扫描已在本地建过任务），正文中文正常、无错误 detail。
- 修复前对比：旧服务（无 encoding fix）`/api/base/scan` 稳定返回 `502 {"detail":"字段「优化文案」不存在，请检查字段映射"}`。
- commit：`issues/004-07` 相关改动独立提交（见 git log）。