# 002-04: 重组装 + 重烧字幕 + 全量验证 + 提交推送

**What to build:** 用重烘焙的场景 + 放大参数的新字幕，按 script.json 时间窗全量重组装出 `renders/final.mp4`（concat → narration mix → mux → burn），执行 issues/002 spec「验收标准」全部 6 项帧采样/像素/ffprobe 验证，按票提交（消息引用 issues/002）、推送，并刷新仓库根 `HANDOFF.md`。

**Blocked by:** 002-02 (字幕参数+组装脚本), 002-03 (重烘焙场景)

**Status:** ready-for-agent

- [ ] `final.mp4` 生成：1920×1080 · h264 · aac · yuv420p · 30fps · **~173.07s**（±3s）
- [ ] 字幕：3 个叙事时刻白色 glyph 像素显著大于旧值、无越界
- [ ] 关键词胶囊 + 呼吸灯：≥3 节帧采样可见暗色胶囊带 + 琥珀文字 + 两帧呼吸差异
- [ ] 旁白可闻（-25~-35dB）、轮播仍在（同节两帧差异>60%）
- [ ] 回归：`pytest tests/tools/test_pexels_image.py tests/tools/test_stock_source_adapters.py` 全绿
- [ ] 提交推送 + HANDOFF.md 刷新提交