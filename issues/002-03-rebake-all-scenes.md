# 002-03: 重烘焙全部 10 场景

**What to build:** 用含胶囊+呼吸灯的新 builder 重烘焙全部 10 个场景（opener + 8 section + end_card），每个场景 MP4 时长命中 script.json 窗口 / 既有场景规格（见 issues/002「决策 2」与场景参数）。产出物为 `projects/us-iran-hormuz-strike/assets/video/*.mp4`。

**Blocked by:** 002-01 (关键词胶囊+呼吸灯 builder)

**Status:** ready-for-agent

- [ ] 10 场景全部重烘焙成功，时长与既有窗口一致（opener 9.0 / s01 27.3 / s02 24.4 / s03 17.0 / s04 26.75 / s05 17.1 / s06 18.4 / s07 18.5 / s08 11.6 / end 3.0 ±0.5s）
- [ ] 至少 3 个场景帧采样确认胶囊带可见且呼吸正常（暗色背景带 + 琥珀文字 + 两帧 alpha/发光差异）