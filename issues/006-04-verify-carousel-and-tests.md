# 006-04: 图片轮播验证 + 全量测试回归

**What to build:** 验证已完成任务的成片确实包含「图片素材轮播」（Pexels 素材多图交替）画面，作为流水线该能力存在的实证；并对 006-01/02/03 的改动做全量回归，确保无破坏。

**Blocked by:** 006-01 服务端预览/下载端点拆分、006-02 下载次数持久化与计数、006-03 前端预览/下载交互拆分

**Status:** ready-for-agent

- [x] 抽查至少一个已生成任务成片的若干帧，确认包含多图轮播（帧画面在多张 Pexels 图之间交替）
- [x] `python -m pytest tests/web -q` 全绿（现有案例 + 006 新增案例）
- [x] 回归检查：生成/SSE/扫描/登录等既有路径未被破坏

**验证证据（2026-09-11）：**
- 抽查 `projects/narration-mt-smoketest1`（成片 8.7s，section_02 为 3s 轮播场景）：
  - `hyperframes/index.html` 含 3 张 Pexels 图（id=bg-0/1/2，`alt="carousel"`），timeline 明确 `tl.to("#bg-0",{opacity:1},0)` → bg-1 0.7s 入→bg-0 1.3s 出 → bg-2 1.7s 入→bg-1 2.3s 出，每张配 scale 1→1.08 推镜（Ken Burns）。三图依次交叉淡化交替 = 照片轮播真实生效。
  - 帧对比：section_02 源图互差 diff 0.18–0.29（明显不同），成片帧间 diff 0.08–0.13（有可见运动），证实动画非静态。
- 早期任务 `narration-4d1358bbf203` 的 section_01 走 `no-carousel: static dark card`（配图不足时降级路径，符合 `--no-carousel` 设计）。
- 全量 `python -m pytest tests/web -q`：**105 passed**（006-01/02 新增 6 用例 + 既有案例，覆盖 /video inline、/download attachment、计数递增、预览不计次、未完成 404）。