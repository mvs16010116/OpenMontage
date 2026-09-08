# -*- coding: utf-8 -*-
"""OpenAI-compatible LLM client for the narration-synth pipeline.

Calls ``{base_url}/chat/completions`` with a Bearer api_key to turn the raw
narration into ``{title, sections:[{text, keywords}]}`` — sections drive
TTS/subtitles, English keywords drive Pexels image search.

Strict contract: on any failure (missing config, HTTP error, malformed JSON,
schema mismatch) this raises a readable ``LlmError``. It never falls back to
the old hardcoded keyword/split logic.
"""

from __future__ import annotations

import json
import re

import requests

from web import config as wcfg

_TIMEOUT_SECONDS = 120

_SYSTEM_PROMPT = (
    "你是中文口播视频的分镜导演。把用户给的口播文案按语义/停顿拆成若干段（每段约"
    "1-3 个完整句，保持原文不变），并为每段给出 1-3 个英文图片搜索关键词（每个"
    "2-5 个词，描述该段最核心的可视化主体，供图片库检索）。"
    '只输出一个 JSON 对象，禁止任何额外文字或 markdown，格式为：'
    '{"title": "不超过40字的标题", "sections": [{"text": "原文字段", "keywords": ["english keyword 1", "english keyword 2"]}]}'
    "sections 必须按原文顺序覆盖全部文案，不得改写或漏句。"
)


class LlmError(Exception):
    """Raised on LLM config/HTTP/parse failures with a readable Chinese message."""


def _readable_http_error(resp: requests.Response) -> str:
    status = resp.status_code
    if status == 401 or status == 403:
        return f"LLM 认证失败（HTTP {status}），请检查 API Key"
    if status == 404:
        return f"LLM 接口不存在（HTTP 404），请检查 Base URL 是否指向 /v1"
    if status == 429:
        return "LLM 请求超限（HTTP 429），请稍后重试或降低并发"
    if status == 400:
        body = resp.text[:300]
        return f"LLM 请求被拒绝（HTTP 400）：{body}"
    if status >= 500:
        return f"LLM 服务端错误（HTTP {status}），请稍后重试"
    return f"LLM 请求失败（HTTP {status}）：{resp.text[:300]}"


def _strip_json_fences(content: str) -> str:
    content = content.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.S)
    if m:
        return m.group(1).strip()
    return content


def _usage_from(data: dict, model: str) -> dict:
    usage = data.get("usage") or {}
    return {
        "model": model,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def parse_script_with_llm(settings: dict, text: str, title: str) -> tuple[dict, dict]:
    """Call the LLM and return (parsed: {title, sections}, usage: dict).

    ``parsed["sections"]`` entries are ``{"text": str, "keywords": [str, ...]}``.
    ``usage`` carries prompt/completion/total tokens plus the model name.
    """
    cfg = settings.get("llm") or {}
    base_url = (cfg.get("base_url") or "").strip().rstrip("/")
    model = (cfg.get("model") or "").strip()
    raw_key = (cfg.get("api_key") or "").strip()
    api_key = wcfg.deobfuscate(raw_key) or raw_key
    if not base_url or not model or not api_key:
        raise LlmError("未配置 LLM（Base URL / API Key / Model），请在「配置」页填写")

    user_content = (
        f"口播文案标题：{title}\n\n请按规则拆分以下文案：\n{text}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": float(cfg.get("temperature") or 0.2),
        "max_tokens": int(cfg.get("max_tokens") or 2000),
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        raise LlmError("LLM 请求超时，请检查网络或模型响应速度") from None
    except requests.RequestException as exc:
        raise LlmError(f"LLM 网络错误：{exc}") from None

    if resp.status_code != 200:
        raise LlmError(_readable_http_error(resp))
    try:
        data = resp.json()
    except ValueError:
        raise LlmError("LLM 响应不是有效 JSON") from None

    usage = _usage_from(data, model)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LlmError("LLM 响应缺少 choices[0].message.content") from None

    try:
        parsed = json.loads(_strip_json_fences(content))
    except ValueError as exc:
        raise LlmError(f"LLM 输出的 JSON 无法解析：{exc}") from None

    if not isinstance(parsed, dict):
        raise LlmError("LLM 输出的 JSON 不是对象")
    sections = parsed.get("sections")
    if not isinstance(sections, list) or not sections:
        raise LlmError("LLM 输出的 JSON 缺少 sections 数组")
    normalized = []
    for sec in sections:
        if not isinstance(sec, dict) or not (sec.get("text") or "").strip():
            raise LlmError("LLM 输出的 JSON 中 sections 项缺少有效 text")
        keywords = sec.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords = [k for k in keywords if isinstance(k, str) and k.strip()]
        normalized.append({"text": sec["text"], "keywords": keywords[:6]})
    return {"title": (parsed.get("title") or title)[:60], "sections": normalized}, usage