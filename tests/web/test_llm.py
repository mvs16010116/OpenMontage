# -*- coding: utf-8 -*-
"""Unit tests for web/llm.py — request construction and response parsing.
Network calls are mocked; never hits a real LLM endpoint."""

import json

import requests as requests_mod
import pytest

import web.llm as llm


def _settings(**llm_overrides):
    base = {
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-test",
        "model": "gpt-test",
        "temperature": 0.2,
        "max_tokens": 2000,
    }
    base.update(llm_overrides)
    return {"llm": base}


class _Resp:
    def __init__(self, status_code, payload, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload)

    def json(self):
        return self._payload


def _ok_payload(content):
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def _hook(monkeypatch, content, status_code=200):
    """Make the requests.post used by llm return a canned completion."""
    fake = lambda *a, **k: _Resp(status_code, _ok_payload(content))
    monkeypatch.setattr(llm.requests, "post", fake)


def test_call_builds_request(monkeypatch):
    captured = {}

    dumps = json.dumps

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        content = dumps({
            "title": "T",
            "sections": [{"text": "第一句。", "keywords": ["warship"]}],
        }, ensure_ascii=False)
        return _Resp(200, _ok_payload(content))

    monkeypatch.setattr(llm.requests, "post", fake_post)
    parsed, usage = llm.parse_script_with_llm(
        _settings(), "第一句。\n第二句。", "标题")
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["json"]["model"] == "gpt-test"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["temperature"] == 0.2
    assert parsed["sections"][0]["keywords"] == ["warship"]
    assert parsed["sections"][0]["text"] == "第一句。"
    assert usage["total_tokens"] == 30
    assert captured["timeout"] == 120


def test_parse_ignores_json_fences(monkeypatch):
    raw = json.dumps({"title": "T", "sections": [
        {"text": "甲。", "keywords": ["k1", "k2"]}]})
    _hook(monkeypatch, "```json\n" + raw + "\n```")
    parsed, _ = llm.parse_script_with_llm(_settings(), "文", "T")
    assert parsed["sections"][0]["keywords"] == ["k1", "k2"]


def test_keywords_can_be_comma_string(monkeypatch):
    raw = json.dumps({"title": "T", "sections": [
        {"text": "甲。", "keywords": "oil tanker, navy"}]})
    _hook(monkeypatch, raw)
    parsed, _ = llm.parse_script_with_llm(_settings(), "文", "T")
    assert parsed["sections"][0]["keywords"] == ["oil tanker, navy"]


def test_keywords_filtered_to_six(monkeypatch):
    raw = json.dumps({"title": "T", "sections": [
        {"text": "甲。", "keywords": [f"k{i}" for i in range(9)]}]})
    _hook(monkeypatch, raw)
    parsed, _ = llm.parse_script_with_llm(_settings(), "文", "T")
    assert len(parsed["sections"][0]["keywords"]) == 6


def test_title_falls_back_to_given(monkeypatch):
    _hook(monkeypatch, json.dumps({"sections": [
        {"text": "甲。", "keywords": []}]}))
    parsed, _ = llm.parse_script_with_llm(_settings(), "文", "标题X")
    assert parsed["title"] == "标题X"


def test_missing_config_raises_readable():
    with pytest.raises(llm.LlmError, match="未配置 LLM"):
        llm.parse_script_with_llm({}, "文", "T")


def test_blank_key_raises_readable():
    with pytest.raises(llm.LlmError, match="未配置 LLM"):
        llm.parse_script_with_llm(_settings(api_key="  "), "文", "T")


def test_http_401_raises_readable(monkeypatch):
    _hook(monkeypatch, "{}", status_code=401)
    with pytest.raises(llm.LlmError, match="认证失败"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_http_429_raises_readable(monkeypatch):
    _hook(monkeypatch, "{}", status_code=429)
    with pytest.raises(llm.LlmError, match="超限"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_http_500_raises_readable(monkeypatch):
    _hook(monkeypatch, "{}", status_code=500)
    with pytest.raises(llm.LlmError, match="服务端错误"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_network_error_raises_readable(monkeypatch):
    class BoomError(requests_mod.RequestException):
        pass

    def boom(*a, **k):
        raise BoomError("dns failed")

    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LlmError, match="网络错误"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_timeout_raises_readable(monkeypatch):
    def boom(*a, **k):
        raise requests_mod.Timeout()

    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LlmError, match="超时"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_non_json_response_raises_readable(monkeypatch):
    monkeypatch.setattr(
        llm.requests, "post",
        lambda *a, **k: _Resp(200, {"wrong": "shape"}))
    with pytest.raises(llm.LlmError, match="缺少 choices"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_missing_sections_raises_readable(monkeypatch):
    _hook(monkeypatch, json.dumps({"title": "T"}))
    with pytest.raises(llm.LlmError, match="sections"):
        llm.parse_script_with_llm(_settings(), "文", "T")


def test_section_without_text_raises_readable(monkeypatch):
    _hook(monkeypatch, json.dumps({"title": "T", "sections": [
        {"keywords": []}]}))
    with pytest.raises(llm.LlmError, match="text"):
        llm.parse_script_with_llm(_settings(), "文", "T")