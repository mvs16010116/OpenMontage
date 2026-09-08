# 002-02: 字幕参数放大 + 组装脚本 mux 修正

**What to build:** 字幕渲染字号放大 1.8 倍（44→80）并按比例放大描边（3→5）与底边距（58→90）；`.ass` Style 与组装脚本 burn `force_style` 两处同步一致。同时修正组装脚本 mux 步：音频 mix 止于最后一段旁白（≈168.6s），`-shortest` 无 `apad` 会把成片截到 168.6s——给 mux 加 `pad_dur` 使其回到 ~173.07s。详见 issues/002「决策 1」「决策 3」。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `.ass` Style：FontSize=80, Outline=5, MarginV=90（其余颜色/字距/BorderStyle/Alignment 不变）
- [ ] burn `force_style` 与 `.ass` 同步（FontSize=80, Outline=5, MarginV=90）
- [ ] mux 步带 `apad`，且不依赖音频自身长度截断成片
- [ ] 单发 probe：烧出一帧字幕验证字号变大、白像素显著多于旧值、无越界