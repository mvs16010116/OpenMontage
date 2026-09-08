# 001 - Pexels 关键词相关图片轮播（横屏口播）

## Problem Statement

当前的 `us-iran-hormuz-strike` 横屏口播视频，每个 section 只有一张静态深底卡片（`#070b12`）铺满整个 17–27s 的叙事窗口。画面单调、没有真实影像流动感，作为军政口播视频缺少"新闻画面在文字下流动"的视觉支撑。用户希望为口播视频新增一种效果：**按关键词从 Pexels 搜索真实图片，在文字前景下方实现图片轮播（carousel）**，且图片必须与关键词相关。

现状约束（已核实）：

- `PEXELS_API_KEY` 已在 `.env` 配置。
- `tools/graphics/pexels_image.py`（`PexelsImage`，capability=`image_generation`，provider=pexels，免费）**每个 query 只下载 `photos[0]` 一张** —— 不满足"轮播多张"需求，需扩展。
- 现有场景由 `.agents/skills/military-title-card/scripts/build_title_card.mjs` 与 `.agents/skills/military-data-viz/scripts/build_data_viz.mjs` 生成（HyperFrames，`_military-shared/composition.mjs` 输出 1920×1080 横屏）。
- gaza 项目曾用 Pexels 图片做背景，产物 `projects/junzheng-gaza-pursuit/artifacts/_pexels_fetch.json` 记录每个场景的 `query/photo_id/alt` 校验。

## Solution

为本项目引入"关键词 → 英文搜索词 → Pexels 候选图 → 相关度筛选 → 图片轮播背景"资产流水线，并在 HyperFrames 场景中加入**背景图轮播 + 深色遮罩 + 前景标题/图表叠加**的横屏渲染。音频、字幕、8 段叙事结构、174.8s 总时长全部保留，只替换视觉层（并按需补呼吸感与片尾引导卡）。

## User Stories

1. 作为视频作者，我希望每个 section 的画面不再是一张死卡片，而是在文字下方轮播 2-4 张与关键词相关的真实图片，让口播视频有画面流动感。
2. 作为视频作者，我希望图片轮播是**背景层**，前景的标题、关键词条、大数字、图表仍可读，通过深色渐变遮罩保证文字对比度。
3. 作为视频作者，我希望图片切换是**交叉淡化（~0.6s）+ 轻微 Ken Burns 推拉**，不跳帧、不呆板，符合军政沉稳调性。
4. 作为视频作者，我希望中文关键词（如"霍尔木兹海峡""油轮""防空阵地"）被**扩写为多个英文搜索词**喂给 Pexels（Pexels 以英文搜索质量最高），每个英文词产出候选图。
5. 作为视频作者，我希望对候选图按 Pexels 返回的 `alt`/标签做**相关度筛选**，只有相关度足够的图才进场，杜绝"看图不相关"的凑数。
6. 作为视频作者，我希望每个 section 的图片数按时长自适应（短节 2 张、长节 3-4 张）。
7. 作为视频作者，我希望某节的候选图与关键词都相关度不足时，**该节回退到纯深底卡片**（不硬凑图），并在 manifest 记录 `reason`。
8. 作为审查者，我希望有一份 `pexels_manifest.json` 记录每张图的 `query / photo_id / alt / 筛选理由 / 来源 URL`，使"图片与关键词相关"可被审计。
9. 作为审查者，我希望结果约束在一个可复用资产（新 builder/脚本/BOM）里，后续"候哥军情"系列视频可直接复用同一套图片轮播背景流水线。
10. 作为视频作者，我希望最终视频仍是 1920×1080 横屏、~174.8s、h264+aac、字幕与音频与原版一致。
11. 作为视频作者，我希望能顺带获得数字后停顿（呼吸感）与片尾关注引导卡（上轮已确认"其他可以"，仅这两项，无 BGM）。

## Implementation Decisions

- **抓图工具扩展（`PexelsImage`）**：扩展 `tools/graphics/pexels_image.py` 支持一次查询返回并下载**多张**候选图（新增输入如 `output_dir` + 需要下载的最大张数/`select_all` 语义），同时**返回候选列表**（每张的 `photo_id/alt/url/维度`），由 agent 依据 `alt` 相关度挑选。保持免费、幂等键字段（`query, orientation, size, color, page`）与 `estimate_cost=0` 不变；相关度筛选是 agent 决策，不进工具。此改动为"改装核心工具"，已在 grill 阶段获用户同意。
- **英文搜索词扩写**：本文关键词（`主体：霍尔木兹海峡,油轮,防空阵地；区域：中东`）由 agent 按 section 内容扩写成 2-3 个英文搜索词（如 `Hormuz strait tanker sea`, `oil tanker deck`, `air defense radar military`），落盘为项目内 `artifacts/pexels_searches.json`。搜索执行走扩展后的 `PexelsImage` 工具（Rule Zero：不改写直连脚本）。
- **相关度筛选（agent in the loop）**：对每张候选图读取 Pexels 返回的 `alt` 文本，与 section 语义关键词做匹配（中文语义 + 英文词根）；相关度评分不足的淘汰；整节无合格图 → 回退深底。每张入选图记录 `reason` 字段。
- **图片轮播背景渲染**：新增可复用 HyperFrames 场景构建（在 `_military-shared` 系 builders 附近新增一个"背景图轮播 + 遮罩 + 前景卡"横屏 builder；复用 `composition.mjs` 的 1920×1080 契约与 GSAP 时间轴）。背景层按 `pexels_manifest` 顺序轮播：crossfade 0.6s + 轻微 scale 推拉；前景叠加现有标题/关键词/数字/图表（复用 `build_title_card`/`build_data_viz` 的前景部分逻辑或同源样式 token）。若某节为深底回退，则直接沿用现有纯深底 builder。
- **视觉层替换，音频/字幕/时长保留**：`render_final`/concat 流程复用上一版证明过的组装（concat 场景 → 烧字幕 → mux `narration_mix.m4a`），只替换 body 场景源。总时长维持在 174.8s。
- **呼吸感（仅当 Q7=B 时）**：在数字密集句（`50000`、`20%`、`2 艘`）后于叙事文本中插入停顿提示，重新生成对应 section TTS 时长（会轻微伸缩该节窗口，字幕/场景随之对齐）。
- **片尾引导卡**：正文最后一 section 之后固定追加 3s 深底引导卡（"关注 · 评论区聊聊"），不占叙事时长。
- **产出物**：`projects/us-iran-hormuz-strike/artifacts/pexels_searches.json`（英文搜索词）、`pexels_manifest.json`（选图+理由）、复用 builder 源文件、重新烘焙的 9 场景 MP4、`renders/final.mp4`；复用能力落在 `.agents/skills/military-photo-carousel/`（builder 脚本 + SKILL.md）。

## Testing Decisions

- **单位级**（外部行为优先）：
  - `PexelsImage` 多张下载：给定已知 `query`，断言输出文件数 = 请求张数、返回候选列表含 `photo_id/alt/url`、幂等字段生效。现有 `tests/tools/test_stock_source_adapters.py` 为同类先例。
  - 相关度筛选函数：用 mock 候选（含强相关/弱相关/无关 `alt`），断言选中集与评分正确。
- **场景级**：
  - 每节头帧/中帧/尾帧截图；用画面像素检查验证：背景存在照片（非纯 `#070b12`）、前景文字卡仍在（白字带像素存在，参照上一版 dev-validator 的白字检查）、轮播确实切换（两时刻背景差异）。
  - 深底回退节：断言背景接近 `#070b12` 且 manifest 有 `reason`。
- **整片级**：`ffprobe` 断言 1920×1080 h264 aac 30fps、时长 ≈174.8s（呼吸感改造后允许偏差 ±3s）；白字像素在 3 个采样时刻存在；narration RMS 在 3 个采样点 >500（沿用上版验证脚本模式）。
- **回退检查**：确认 gaza 项目渲染链路不因 `PexelsImage` 扩展而回归（工具签名向后兼容）。

## Out of Scope

- 不新增 BGM/音乐轨（用户明确不需要）。
- 不做竖屏样式（本项目锁定横屏；竖屏轮播留作后续）。
- 不改叙事文本内容与 8 段结构（仅按需微调停顿）。
- 不接入付费图库、不引入除 Pexels 外的新图源。
- 不做图片自动生成（词义 GIF/合成图）；只用 Pexels 真实照片。
- 不重构 `pexels_image` 的搜索（`per_page`/`page`/颜色滤镜）以外行为。

## Further Notes

- grill 阶段决策记录（Q1→A，Q2→A，Q3→A，Q4→A，Q5→A，Q6→A，Q7→B，Q8→A）：轮播粒度=节内 2-4 张背景；过渡=crossfade 0.6s+Ken Burns；前景=遮罩+文字/图表叠加；相关性=中文关键词→英文扩写→alt 筛选→manifest 可审计；交付=可复用能力+应用到当前横屏项目；实现=改装 `PexelsImage` 工具（已同意）；呼吸感+片尾引导卡并入本轮；宁缺毋滥回退深底。
- 具体英文搜索词清单、选中图、每节张数属实现细节，落地时以 `pexels_searches.json`/`pexels_manifest.json` 呈现供审查。
- 本项目遵循 AGENTS.md 五步链：spec 原文即本文件；后续拆票（to-tickets）与逐票实现（implement）。git 提交引用 `issues/001`。