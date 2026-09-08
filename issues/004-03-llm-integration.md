# 004-03 - LLM 集成（分节 + 关键词 + token 统计）

**Status:** ready-for-agent  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-01（04 依赖本票）

## 目标

接入 OpenAI 兼容 LLM：将文案解析为「标题 + 分节 + 英文图片关键词」，替换硬编码 `KEYWORD_MAP` 与句号正则分节；记录每次调用的 token 用量并把产出写入 `script.json`。

## 验收标准

1. `web/llm.py`：`requests` 调 `{base_url}/chat/completions`（Bearer api_key），`response_format` 求 JSON，解析 `usage` 并返回 `{title, sections:[{text, keywords}], usage}`。
2. JSON 响应容错：失败/Schema 不符时抛可读错误（提示检查 LLM 配置），不静默降级到硬编码。
3. `pipeline.py` 首步改为调用 LLM：产出的分节直接用于 TTS/字幕/片段窗口，关键词（英文）用于 Pexels 检索；`stage_timings` 增加 `llm_parse` 阶段。
4. LLM 原始响应与解析结果落 `artifacts/script.json`；token 用量（prompt/completion/total 与模型名）返回给 caller 供 04 落库。
5. 未配置 LLM 时任务以可读错误失败。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/llm.py` | 新增 | OpenAI 兼容客户端 |
| `web/pipeline.py` | 改造 | LLM 分节/关键词替代硬编码，新增 `llm_parse` 阶段 |
| `web/llm_test.py` | 新增 | 请求构造/响应解析单测（mock HTTP） |

## 验证

配置 LLM 后运行 `python -m web.pipeline --text "..."`，`script.json` 含 LLM 分节与 keywords，输出 token 用量。