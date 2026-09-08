# 001-03: 可复用横屏"图片轮播背景 + 遮罩 + 前景卡"渲染 builder

**What to build:** 新增可复用 HyperFrames builder（继承 `_military-shared/composition.mjs` 的 1920×1080 契约与 GSAP 时间轴），输入为 manifest 图片清单 + 前景内容（标题/关键词/数字/图表）。逐节轮播背景图：crossfade ~0.6s + 轻微 Ken Burns 推拉；前景深色渐变遮罩保证文字对比度，标题/关键词条/大数字/图表叠加其上。深底回退节走原 `build_title_card`/`build_data_viz`。作为 skil 资产落位并附带 SKILL.md 使用说明，供后续系列复用。

**Blocked by:** 001-02

**Status:** ready-for-agent

- [ ] builder 输出 1920×1080 横屏 MP4
- [ ] 背景按 manifest 顺序轮播，两时刻画面确实切换（非静态）
- [ ] 前景文字/数字叠加可读（白字像素带存在，参照既有 dev-validator 检查）
- [ ] 深底回退节渲染接近 `#070b12`
- [ ] SKILL.md 记录输入契约（manifest schema + 前景参数）