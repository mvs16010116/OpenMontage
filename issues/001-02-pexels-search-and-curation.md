# 001-02: 英文搜索词扩写 + Pexels 选图与相关度筛选 → pexels_manifest.json

**What to build:** 为 8 个 section 各产出 2-3 个英文搜索词（如 `Hormuz strait tanker sea`、`oil tanker deck`、`air defense radar military`），走扩展后的 `pexels_image` 逐词抓候选图（横屏 oriented），按 Pexels 返回的 `alt` 文本与 section 语义做相关度筛选：强相关才入选，整节无合格图 → 回退深底并记录 `reason`。产 `pexels_searches.json`（search 词清单）与 `pexels_manifest.json`（每张入选图 `query/photo_id/alt/reason/URL`），后者的 schema 即 T3 渲染 builder 的图片清单契约。图存 `assets/images/`。

**Blocked by:** 001-01

**Status:** ready-for-agent

- [ ] `pexels_searches.json`：8 节 × 2-3 英文词，横屏取向
- [ ] `pexels_manifest.json`：每节 2-4 张入选图，字段 `query/photo_id/alt/reason/url`，与搜索词可追溯
- [ ] 每张入选图的 `alt` 与对应该节关键词语义相关（可被审查者复核）
- [ ] 无合格图节：manifest 标记回退深底 + `reason`
- [ ] 图片文件在 `assets/images/`，尺寸可支持 1920×1080 背景