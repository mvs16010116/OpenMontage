# 004-08-02 — 语义化进度文案 + 扫描后自动订阅进度

**Parent:** `issues/004-08-scan-single-newest.md`

**What to build:**

用户点击「扫描多维表格」后，能立刻看到新任务/重试任务的实时进度，且进度条显示的是能看懂的中文阶段：

- 阶段文案统一为：文案整理中 → 配音生成中 → 配图检索中 → 渲染中 → 生成字幕中 → 合成成片中 → 生成完成（替换现「正在解析分节…」等机器化措辞）。
- 手动扫描返回 created/retried 任务时，前端自动订阅该任务的 SSE 事件，进度条实时滚动到「生成完成」。

**Blocked by:** `issues/004-08-01-scan-single-newest-selection.md`（scan 响应需带 task_id 供订阅）

**Status:** done

- [x] pipeline 各阶段 emit 的 message 与前端 `STAGE_LABEL` 对齐为语义化中文文案（文案整理中…/配音生成中…/配图检索中…/渲染中…/生成字幕中…/合成成片中…/生成完成）。
- [x] 前端扫描成功后自动 `listen(created[0].task_id)` 或 `listen(retried.task_id)`，进度框展示并实时更新；scan 响应 `message` 展示在结果区。
- [x] `tests/web/` 全绿（100 passed；无测试锁定旧 stage message，无需收敛）。