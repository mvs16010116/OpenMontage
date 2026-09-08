# 001-06: 组装 final.mp4 + 整片验证 + 提交推送

**What to build:** concat 全部场景 → 烧字幕（沿用 ASS，白字黑边）→ mux 叙事混音（含新呼吸感 TTS），产出最终 `renders/final.mp4`。跑整片验证：ffprobe 确认 1920×1080 h264 aac 30fps、时长 ≈174.8s（±3s）、白字带像素在 3 个采样时刻存在、narration RMS>500；确认 gaza 渲染链路未回归。提交（消息引用 `issues/001`）并推送 origin/main。

**Blocked by:** 001-05

**Status:** ready-for-agent

- [ ] final.mp4：1920×1080 · h264 · aac · ~174.8s（±3s）
- [ ] 字幕烧录、叙事清晰（白带像素 + RMS 采样通过）
- [ ] 图片轮播背景在多个采样时刻存在（非纯深底占比多地）
- [ ] gaza 项目渲染验证通过（回归检查）
- [ ] commit 引用 `issues/001`，push 成功到 origin/main