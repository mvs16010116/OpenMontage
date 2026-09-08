# 002 - 字幕字号放大 + 关键词标签透明背景呼吸灯

**Date:** 2026-09-08  **Status:** ready-for-agent  **Branch:** main
**Related:** issues/001 (pexels carousel delivery, this spec revises its visual output)

## 目标与约束

- 对 `us-iran-hormuz-strike` 最终成片 `renders/final.mp4` 做两处视觉调整：
  1. **字幕字号**放大为当前的 **1.8 倍左右**（44 → 80px），描边与底边距按比例放大，保证大字号下的可读性与安全留白。
  2. **关键词标签（#kwtag）**增加**透明背景颜色**（暗色胶囊底）且背景有**呼吸灯效果**（琥珀色外发光 + 背景透明度呼吸），透明度参数参考业界最佳。
- 约束：
  - 保持叙事/音乐/8-section 结构、时长（~173.07s ±3s）、无 BGM、横屏 1920×1080 不变。
  - 呼吸灯只作用于**背景/外发光**，**不得**作用于文字光晕（规避 gaza `#kwtag textShadow` 辉光导致的逗号分隔多段关键词视觉粘连缺陷，见 3078077）。
  - 改动须可复现：builder 逻辑进入 `.agents/skills/military-photo-carousel/`，组装脚本落 temp 但产物入 `projects/<name>/renders/`。
  - 现有 `PexelsImage` 工具与既有测试不得回归。

## 方案与决策点

### 决策 1：字幕参数（用户已确认"按比例放大"）
- 字幕当前实际生效渲染参数来自 burn 的 `force_style`：`FontSize=44, Outline=3, MarginV=58, BorderStyle=1, Alignment=2`。`.ass` 文件 Style 行同值。
- 新值：**FontSize=80**（44×1.8≈79.2 取整）、**Outline=5**（随字号比例）、**MarginV=90**（底边安全距离随字号加大）。其余（颜色、字距、BorderStyle、Alignment、MarginL/R）不变。
- 两处同步：`subtitles.ass` Style 行 + 组装脚本 burn `force_style`。两者不一致以 burn 为准（user 观看到的是 burn 结果），但保持文件与脚本一致以便复现。
- 被否掉：只改字号不动描边/边距（会破坏大字号视觉比例，用户已否）；不动 ass 只动 burn（复现性差）。

### 决策 2：关键词标签样式（用户已确认"暗色胶囊+琥珀光"）
- `#kwtag` 由纯文字改为**胶囊呈现**：`display:inline-block; padding:<上> <左右>; border-radius:999px; background:rgba(7,11,18,.62)`，文字保持琥珀色 + 弱文字阴影。
- **呼吸灯**（GSAP，挂在主 `paused` timeline，确定性可 seek）：
  - 背景透明度 `rgba(7,11,18,.50)` ↔ `rgba(7,11,18,.72)`；
  - 外发光 `box-shadow 0 0 18px rgba(acc,.20)` ↔ `0 0 44px rgba(acc,.45)`；
  - 周期 **2.6s**、`sine.inOut`、`yoyo`、`repeat:-1`，起始于关键词入场完成后（≥1.6s 槽位）。
- 透明度取值依据业界最佳：视频上文字可读性兜底的胶囊底 alpha 常见 0.5-0.7，外发光 alpha 不超过 0.5 以免过曝夺目。
- 关键词入场动画（opacity 淡入）保留；呼吸在入场完成后再叠加，避免入场与呼吸争抢。
- 被否掉：琥珀淡底(`rgba(acc,.16)`)方案（可读性弱于暗底，且更接近被废弃的 gaza 风格，用户选了暗底）。文字辉光呼吸（历史缺陷，禁止）。

### 决策 3：组装链路 bug 修正（顺带）
- 现 `t6_assemble.py` mux 步 `-shortest` 且无 `apad`：音频 mix 产物止于最后一段旁白结束（≈168.6s），导致成片被截到 168.6s。上次已手动用 apad 修复，脚本未同步。
- 修正：mux 加 `-af apad=pad_dur=10` 并保留 `-shortest`（音频补足后由视频长度 173.07s 收尾）。

### 改动面（不列具体文件路径）
- 复用技能 `military-photo-carousel` 的 builder 脚本：`#kwtag` CSS 内联样式 + 主 timeline 增加呼吸 tween。
- 组装脚本：burn `force_style` 参数更新 + mux apad 修复。
- `subtitles.ass`：Style 行字号/描边/边距更新（events 文本不变）。
- `ass-subtitle-generator` 技能默认字号保持在 44，**本次不升**（仅本视频特调，避免改技能默认影响其他项目）；在本 spec 中记录此边界。

## 验收标准（帧采样/像素级）

1. **字幕**：final.mp4 采样 3 个叙事时刻，底部字幕带白色(glyph)像素数显著高于旧值（FontSize 80 覆盖约 1.8× 面积）；无越界（白像素不触画面左/右/上边缘，底边距≥60px 视觉成立）；时长 173.07±3s。
2. **关键词胶囊**：任意 section 场景中间帧采样，关键词行内存在暗色半透明背景带（比周围 photo 背景更暗、非纯黑），且前景文字仍为琥珀亮色。
3. **呼吸灯**：同一场景内两帧（间隔 ~1.3s，呼吸半周期）关键词胶囊区背景 alpha / 外发光亮度不同（像素统计存在可测差异），且不会让文字模糊粘连。
4. **回归**：`pytest tests/tools/test_pexels_image.py tests/tools/test_stock_source_adapters.py` 全绿；`PexelsImage` 未改动。
5. **结构**：1920×1080 · h264 · aac · yuv420p · 30fps；旁白 -25~-35dB 可闻；轮播仍在（同节两帧画面差异>60%）。
6. **提交**：按票提交，消息引用 `issues/002-xx`；提交后推送，并刷新仓库根 `HANDOFF.md`。

## 被否掉的替代方案（汇总）

- 文字辉光呼吸灯（gaza 粘连缺陷，明令禁止）
- 琥珀淡底半透明（可读性弱，用户否决）
- 只改字幕字号不动描边/边距（用户否决）
- 只改 burn 不改 .ass（复现性差，否决）

## Out of Scope

- 片头/标题/数字条/片尾卡的其他样式改动；BGM；时间线与旁白；新增/删除场景。
- 全局提升 ass-subtitle-generator 技能默认字号（本 spec 只改当前项目）。
- 非 `us-iran-hormuz-strike` 项目的应用。