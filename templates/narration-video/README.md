# OpenMontage — 文案成片模板 (Narration → Video Template)

一句话版：把文案粘贴进 `input/script.txt`（可带分段标记），配好 `input/queries.json`（每段对应的 Pexels 画面关键词），然后：

```bash
cd <OpenMontage 根目录>
python templates/narration-video/run_pipeline.py \
    --text templates/narration-video/input/script.txt \
    --queries templates/narration-video/input/queries.json \
    --title "我的新视频"
```

成片输出到 `projects/<title>/renders/final.mp4`（同时保留分镜头素材、配音、字幕等中间产物）。

---

## 输入文件

### `input/script.txt` — 文案（唯一必填）

- 支持用 `###SEG1###`、`###SEG2###`... 手动分段（每段一段配音 + 一个画面主题）
- 不写分段标记也行：脚本会按段落/标点自动切成若干段

```
###SEG1###
大家好，我是侯哥军情。

###SEG2###
今天给大家扒个猛料……
```

### `input/queries.json` — 每段的 Pexels 画面关键词（数量须 ≥ 段数）

```json
{
  "scenes": [
    ["news studio", "television newsroom"],
    ["military armored vehicle", "army convoy recruits"],
    ...
  ]
}
```

每段给你列 2~4 个英文关键词，脚本会拉取**互不相同的素材**拼接该段，
同一视频绝不循环播放。段数不够可以留空的备用词，脚本会自动补默认军事类词。

## 2. 流程（模板帮你完成）

1. **init** 创建 `output/<title>/` 工作区
2. **配音**：edge-tts `zh-CN-YunxiNeural`（男声）逐段生成 → 拼接 `narration_full.mp3`
3. **字幕**：自动生成 `subtitles.srt`（句读拆分）
4. **卡拉OK字幕**：生成 `karaoke.ass`（大字加粗、去标点、黄色逐字高亮，默认 84 号字）
5. **画面采集**：逐段用 Pexels 关键词拉取多支互异素材
6. **拼接**：每段用不同素材时间窗拼接成无声主轨（无循环、无重复），统一 1920x1080@30fps
7. **合成**：画面 + 配音 + 卡拉OK字幕 → `renders/final.mp4`

## 3. 常见微调

| 想要的效果 | 怎么改 |
|---|---|
| 字幕更大/更小 | `run_pipeline.py` 内 `FONT_SIZE = 84` |
| 换配音声音 | `run_pipeline.py` 内 `VOICE = "zh-CN-云希Neural"`（可换其他 edge-tts 男声） |
| 每行最多字数 | `MAXLEN = 10`（卡拉OK短句上限） |
| 只换素材看看 | 改 `queries.json` 重跑，配音/字幕已缓存不会重复生成 |
| 多段画面更丰富 | 每段给 3~4 个关键词即可 |

## 4. 提示

- `input/queries.json` 缺失时使用内置默认军事风关键词（适合军情解说），会打印告警
- 需要 PEXELS_API_KEY（已在 `.env` 配置好就无需操作）
- 全程 0 成本（Pexels 免费、edge-tts 免费）