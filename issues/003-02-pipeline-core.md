# 003-02 - Pipeline Core: text → final.mp4

**Status:** done  **Spec:** issues/003-narration-synth-web-service.md  **Blocking:** 依赖 003-01（DB schema 确认）

## 目标

将 narration-synth pipeline 的 6 个步骤抽取为 `web/pipeline.py` 中的独立函数，输入一段口播文案，输出 `final.mp4`。

## Pipeline 步骤

```
Step 1: parse_script(text)       → script.json (8 sections with timing)
Step 2: generate_tts(script)     → assets/audio/narration_section_0X.mp3
Step 3: fetch_images(script)     → assets/images/ + pexels_manifest.json
Step 4: render_scenes(script, tts, images) → assets/video/section_0X.mp4
Step 5: generate_subtitles(script) → assets/subtitles.ass
Step 6: assemble(script, subtitles) → renders/final.mp4
```

## 验收标准

1. `web/pipeline.py` 中 `run_pipeline(task_id, narration_text, progress_callback) → str` 函数完整实现上述 6 步。
2. 每步完成后调用 `progress_callback(stage_name)` 通知调用方（供 T03 SSE 推送）。
3. 生成的视频质量与 CLI 路径一致：1920×1080、h264+aac、字幕白像素 ≥4000。
4. `projects/<slug>/` 目录结构与 CLI 路径一致（artifacts/、assets/、renders/）。
5. 可独立运行：`python -m web.pipeline --text "..." --output-dir projects/test/` 产出 `final.mp4`。

**验证证据（2026-09-08）：** CLI 冒烟 `python -m web.pipeline --task-id mt-smoketest1 --text "美军打击..."` → `renders/final.mp4` 1920×1080 h264+aac，字幕白像素 6186/5055，背景 photo 色数 8363 全 OK。`tests/web/test_pipeline.py` 7 用例通过。

## 关键实现细节

### Step 1: parse_script
- 将口播文案按句号/分号/换行分割为 8 段（或自动分段，每段 ~4-5 字/秒中文语速）。
- 每段估算时长（字符数 / 4.0），计算 `start_seconds/end_seconds`。
- 输出 `artifacts/script.json`（与现有格式一致）。

### Step 2: generate_tts
- 调用 `edge-tts`（微软 Edge TTS，免费）`Communicate(text, voice="zh-CN-YunxiNeural")`，每节独立生成 `assets/audio/narration_section_0X.mp3`。
- 用 ffprobe 探测真实时长，`rewindow_script()` 重建 `start_seconds/end_seconds`（节间 0.6s 停顿，尾段丢弃）。
- 每段独立生成 → `assets/audio/narration_section_0X.mp3`，manifest `scene_id = scene_0X`（build_ass 依赖 `scene_` 前缀）。

### Step 3: fetch_images
- 复用 `tools/graphics/pexels_image.py` 的多下载能力（`count=3, output_dir=assets/images/<section>`）。
- 中文关键词 → 英文搜索词映射（硬编码常见军事/政治关键词表，或由 LLM 辅助扩写）。
- 每段 2-4 张图，存入 `pexels_manifest.json`。

### Step 4: render_scenes
- 为每段调用 HyperFrames builder（`military-photo-carousel` 或简化版）。
- CLI: `node .agents/skills/military-photo-carousel/scripts/build_photo_carousel.mjs --project ... --slug section_0N --title ... --keyword ... --images a.jpg;b.jpg;c.jpg --duration X --accent "#fbbf24"`。
- 然后 `npx hyperframes render projects/<name>/hyperframes -o projects/<name>/renders/section_0N.mp4 --fps 30 -q standard --workers 1 --quiet`。

### Step 5: generate_subtitles
- 调用 `.agents/skills/ass-subtitle-generator/scripts/build_ass.py`。
- `python .agents/skills/ass-subtitle-generator/scripts/build_ass.py --script artifacts/script.json --manifest artifacts/pexels_manifest.json --output assets/subtitles.ass --font-size 80 --outline 5 --margin-v 90`。

### Step 6: assemble
1. concat 所有 `section_0X.mp4` → `_base_silent.mp4`
2. adelay + amix 混合所有 `narration_section_0X.mp3` → `narration_mix.m4a`
3. mux `_base_silent.mp4` + `narration_mix.m4a`（含 `apad=pad_dur=10`）→ `_with_narration.mp4`
4. burn subtitles → `final.mp4`

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/pipeline.py` | 新增 | Pipeline 核心逻辑 |
