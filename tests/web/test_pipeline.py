# -*- coding: utf-8 -*-
"""Unit tests for web.pipeline (narration-synth core)."""
import json
from pathlib import Path

from web import pipeline


def test_parse_script_splits_sentences():
    s = pipeline.parse_script("第一句。第二句！第三句？第四句；", "标题")
    assert len(s["sections"]) == 4
    assert s["sections"][0]["id"] == "section_01"
    assert s["sections"][0]["text"] == "第一句。"
    # back-to-back windows
    for a, b in zip(s["sections"], s["sections"][1:]):
        assert a["end_seconds"] == b["start_seconds"]


def test_parse_script_min_duration():
    s = pipeline.parse_script("短。", "标题")
    assert s["sections"][0]["end_seconds"] - s["sections"][0]["start_seconds"] >= 4.0


def test_parse_script_empty_falls_back_to_whole_text():
    s = pipeline.parse_script("  ", "标题")
    # no splittable punctuation -> single whole section with the unsplit text
    assert len(s["sections"]) == 1


def test_section_keywords_filters_blanks():
    sec = {"keywords": ["Hormuz strait", "", "  ", "oil tanker"]}
    assert pipeline.section_keywords(sec) == ["Hormuz strait", "oil tanker"]


def test_section_keywords_missing():
    assert pipeline.section_keywords({"text": "x"}) == []


def test_build_script_from_llm_keeps_order_and_keywords():
    parsed = {"title": "T", "sections": [
        {"text": "第一句。", "keywords": ["warship", "navy"]},
        {"text": "第二句。", "keywords": ["oil tanker"]},
    ]}
    s = pipeline.build_script_from_llm("T", parsed, usage={
        "model": "m", "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
    })
    assert len(s["sections"]) == 2
    assert s["sections"][0]["keywords"] == ["warship", "navy"]
    assert s["sections"][1]["keywords"] == ["oil tanker"]
    assert s["meta"]["source"] == "llm"
    assert s["meta"]["llm_usage"]["total_tokens"] == 30


def test_build_script_from_llm_windows_back_to_back():
    parsed = {"title": "T", "sections": [
        {"text": "第一句。第二句。", "keywords": []},
        {"text": "第三句。", "keywords": []},
    ]}
    s = pipeline.build_script_from_llm("T", parsed)
    for a, b in zip(s["sections"], s["sections"][1:]):
        assert a["end_seconds"] == b["start_seconds"]


def test_slugify_is_fs_safe():
    slug = pipeline._slugify("美军打击伊朗革命卫队 霍尔木兹")
    assert slug == slug.lower()
    assert all(c.isalnum() for c in slug)
    assert len(slug) <= 24


def test_parse_script_writes_valid_json():
    s = pipeline.parse_script("第一句。第二句。", "t")
    d = json.loads(json.dumps(s, ensure_ascii=False))
    assert "sections" in d and "total_duration_seconds" in d
