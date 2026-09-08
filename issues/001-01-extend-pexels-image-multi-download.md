# 001-01: 扩展 PexelsImage 支持多张候选下载

**What to build:** `pexels_image` 工具现在每个 query 只下载 `photos[0]` 一张，无法支撑"轮播多张"。扩展它：一次搜索可下载多张候选图并存到指定 `output_dir`，返回候选列表（每张含 `photo_id/alt/url/width/height`）；保持免费、幂等键字段（`query, orientation, size, color, page`）、`estimate_cost=0` 不变，且对既有调用（不传新参数时仍单张下载）**向后兼容** —— gaza 项目渲染链路不回归。相关度筛选不进工具，是 agent 层决策。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 已知 `query` 下，请求多张下载时输出文件数 = 请求张数
- [ ] 返回值候选列表含 `photo_id/alt/url/width/height`
- [ ] 不传新增参数时行为与旧版一致（单张，`photos[0]`）
- [ ] `estimate_cost` 仍为 0，幂等键字段未变
- [ ] `tests/tools/test_stock_source_adapters.py` 同类测试扩充通过