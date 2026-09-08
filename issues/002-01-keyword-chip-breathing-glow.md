# 002-01: 关键词标签胶囊底 + 琥珀呼吸灯

**What to build:** 在 `military-photo-carousel` builder 中，关键词标签（`#kwtag`）由纯文字改为**暗色透明胶囊**（圆角、半透明背景），并在标签入场完成后叠加**呼吸灯**：背景透明度与外发光（琥珀色 box-shadow）以 2.6s 周期 sine yoyo 呼吸（确定性、可 seek、随主 paused timeline）。详见 issues/002 spec「决策 2」。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 关键词标签呈现为胶囊：暗色半透明底（alpha 0.50–0.72 呼吸范围）+ 圆角 + 琥珀文字，文字可读性不因呼吸受损
- [ ] 呼吸灯仅作用于背景/外发光，**无文字光晕**（规避 gaza 粘连缺陷）
- [ ] 单场景小样（如 section_02）渲染后：关键词行存在暗色背景带；同场景两帧胶囊区 alpha/发光亮度存在可测差异；文字清晰不粘连