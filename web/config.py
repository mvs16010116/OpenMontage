# -*- coding: utf-8 -*-
"""Web service configuration: default settings schema + api_key obfuscation.

Settings live in SQLite `settings` table as a JSON blob (see web/db.py). This
module owns the default shape, deep-merge on save, and the light obfuscation
used before storing secrets (not a security boundary — just avoiding plaintext
at rest in an accessible single-row table).
"""

from __future__ import annotations

import base64
import os

DEFAULT_SETTINGS: dict = {
    "lark": {
        "base_url_or_token": "",  # 分享链接 或 base_token
        "table_id": "",
    },
    "fields": {
        "content_field": "",      # 文案字段
        "date_field": "",         # 日期字段（兼排序字段）
        "status_field": "",       # 回填状态字段
        "attachment_field": "",   # 视频附件字段
        "date_sort": "asc",       # asc | desc
    },
    "llm": {
        "base_url": "",
        "api_key": "",
        "model": "",
        "temperature": 0.2,
        "max_tokens": 2000,
    },
    "poll": {
        "enabled": False,
        "interval_seconds": 300,
        "max_records_per_batch": 20,
    },
    "video": {
        "status_success": "成功",
        "status_failed": "失败",
        "status_processing": "处理中",
        "pending_if": "待处理",
    },
}

# fixed local XOR key for very-light at-rest obfuscation of secrets
_OBFUSCATION_KEY = bytes([0x5A, 0x3C, 0xE7, 0x91, 0x2B, 0x4D, 0x8F, 0xC6])


def _xor(data: bytes) -> bytes:
    key = _OBFUSCATION_KEY
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def obfuscate(value: str) -> str:
    if not value:
        return ""
    return base64.b64encode(_xor(value.encode("utf-8"))).decode("ascii")


def deobfuscate(value: str) -> str:
    if not value:
        return ""
    try:
        return _xor(base64.b64decode(value.encode("ascii"))).decode("utf-8")
    except Exception:
        return ""


def mask(value: str) -> str:
    return "****" if value else ""


def deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict with `override` merged over `base` (recursive)."""
    out = dict(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def normalize_settings(raw: dict | None) -> dict:
    """Merge an API payload over defaults, pruning unknown keys.

    Pure shape normalization (no I/O, no secret handling): the API layer
    decides how to store the api_key (obfuscate / keep / clear).
    """
    merged = deep_merge(DEFAULT_SETTINGS, raw or {})
    key = merged.get("llm", {}).get("api_key") or ""
    merged["llm"]["api_key"] = key.strip()
    return merged


def settings_for_store(settings: dict) -> dict:
    """Return the settings dict exactly as the DB should persist it."""
    return settings