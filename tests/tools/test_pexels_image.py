# -*- coding: utf-8 -*-
"""Tests for tools.graphics.pexels_image multi-download candidate support."""
from tools.graphics.pexels_image import _to_candidate

PHOTO = {
    "id": 123456,
    "photographer": "Tester",
    "photographer_url": "https://example.com/p",
    "alt": "A large red oil tanker docked at a harbor",
    "width": 8000,
    "height": 4000,
    "url": "https://www.pexels.com/photo/123456",
    "src": {"large2x": "https://images.pexels.com/x/1.jpg", "original": "https://images.pexels.com/x/2.jpg"},
}


def test_candidate_normalization_carries_output_path():
    cand = _to_candidate("oil tanker", PHOTO, r"D:\proj\assets\images\123456.jpg")
    assert cand["query"] == "oil tanker"
    assert cand["photo_id"] == 123456
    assert cand["output"] == r"D:\proj\assets\images\123456.jpg"
    assert "tanker" in cand["alt"].lower()


def test_candidate_uses_large2x_src_fallback():
    photo_no2x = dict(PHOTO)
    photo_no2x["src"] = {"original": "https://images.pexels.com/x/2.jpg"}
    cand = _to_candidate("oil tanker", photo_no2x)
    assert cand["src"] == "https://images.pexels.com/x/2.jpg"


def test_default_output_path_is_empty_string():
    cand = _to_candidate("oil tanker", PHOTO)
    assert cand["output"] == ""