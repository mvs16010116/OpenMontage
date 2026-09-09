# -*- coding: utf-8 -*-
"""Lark Base integration layer for the narration-synth web service.

Wraps the ``lark-cli base +...`` shortcuts as subprocess calls (user
identity). Read paths: URL/token resolution and pending-record scanning.
Write paths: status field batch updates and attachment uploads.

lark-cli is resolved through ``shutil.which``; npm ``.cmd`` shims are unwrapped
to the native ``lark-cli.exe`` (via ``_unwrap_shim``) so arguments such as
``...&view=vew…`` share URLs are passed to the CLI instead of being mis-parsed
by ``cmd.exe``.
"""

from __future__ import annotations

import json
import glob
import os
import re
import shutil
import subprocess
from typing import Any

_RE_BASE_TOKEN = re.compile(r"^[A-Za-z0-9_\-]{4,}$")


class BaseClientError(Exception):
    """Raised when lark-cli fails (bad config, permission, parse error…)."""


def _resolve_bin() -> str:
    exe = shutil.which("lark-cli")
    if not exe:
        raise BaseClientError("未找到 lark-cli，请先安装并配置（lark-cli auth login）")
    return _unwrap_shim(exe)


def _unwrap_shim(exe: str) -> str:
    """Resolve an npm ``.cmd``/``.bat`` shim to its native binary.

    Running the shim goes through ``cmd.exe``, which splits arguments on
    ``&`` — and Base share URLs contain ``...&view=vew…``, so the CLI "ran"
    while cmd also tried to execute ``view`` and stderr carried that shell
    error. When a sibling native binary exists we call it directly; otherwise
    fall back to the shim (argument quoting caveat still applies).
    """
    if not (exe.lower().endswith(".cmd") or exe.lower().endswith(".bat")):
        return exe
    base = os.path.dirname(exe)
    candidates: list[str] = [
        os.path.join(base, "lark-cli.exe"),
        os.path.join(base, "node_modules", "lark-cli", "bin", "lark-cli.exe"),
    ]
    scope_dir = os.path.join(base, "node_modules")
    if os.path.isdir(scope_dir):
        for entry in os.listdir(scope_dir):
            if not entry.startswith("@"):
                continue
            candidates.extend(glob.glob(
                os.path.join(scope_dir, entry, "*", "bin", "lark-cli.exe")))
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    return exe


def _run(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run lark-cli; raise BaseClientError with a readable message on failure."""
    exe = _resolve_bin()
    cmd = [exe] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise BaseClientError("调用 lark-cli 超时") from None
    if proc.returncode != 0:
        raise BaseClientError(_readable_error(proc.stderr))
    return proc


def _run_json(args: list[str], *, timeout: int = 120) -> Any:
    proc = _run(args, timeout=timeout)
    out = (proc.stdout or "").strip()
    if not out:
        raise BaseClientError("lark-cli 返回了空输出")
    try:
        return json.loads(out)
    except ValueError:
        raise BaseClientError("lark-cli 输出不是有效 JSON") from None


def _readable_error(stderr: str) -> str:
    text = (stderr or "").strip()
    if not text:
        return "lark-cli 调用失败"
    low = text.lower()
    hints = [
        (r"base.?token", "Base 链接/token 无效，请检查「配置」页"),
        (r"1254045", "字段不存在，请检查字段映射"),
        (r"1254015", "字段值类型不匹配"),
        (r"91403|403|permission", "无权限访问该 Base（可运行 lark-cli auth login 重新授权）"),
        (r"1254291", "并发写入冲突，请稍后重试"),
    ]
    for pattern, msg in hints:
        if re.search(pattern, low):
            return msg
    return f"lark-cli 失败：{text[:300]}"


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------
def resolve_base(value: str) -> str:
    """Turn a share URL or a raw base token into a usable base_token."""
    value = (value or "").strip()
    if not value:
        raise BaseClientError("未配置 Base 链接或 token")
    if value.lower().startswith("http://") or value.lower().startswith("https://"):
        data = _run_json(["base", "+url-resolve", "--url", value, "--as", "user"])
        item = _first_item(data)
        token = (item or {}).get("base_token") or (item or {}).get("app_token")
        if not token:
            raise BaseClientError("无法从链接解析出 base_token，请检查链接或改填 base_token")
        return token
    if _RE_BASE_TOKEN.match(value):
        return value
    raise BaseClientError("Base 配置既不是链接也不是有效 token，请检查「配置」页")


def _first_item(data: Any) -> dict | None:
    if isinstance(data, dict):
        for key in ("items", "records", "data"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val[0]
            if isinstance(val, dict):
                return val
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
def _status_filter(status_field: str, pending_if: str) -> dict:
    conditions: list[Any] = [[status_field, "empty"]]
    if pending_if:
        conditions.append([status_field, "intersects", [pending_if]])
    return {"logic": "or", "conditions": conditions}


def _scan_args(settings: dict) -> list[str]:
    lark = settings.get("lark") or {}
    fields = settings.get("fields") or {}
    poll = settings.get("poll") or {}
    table_id = (lark.get("table_id") or "").strip()
    if not table_id:
        raise BaseClientError("未配置数据表 ID/名称，请先在「配置」页填写")
    args = [
        "base", "+record-list",
        "--base-token", resolve_base(lark.get("base_url_or_token")),
        "--table-id", table_id,
        "--as", "user",
        "--format", "json",
        "--limit", str(int(poll.get("max_records_per_batch") or 20)),
    ]
    status_field = (fields.get("status_field") or "").strip()
    if status_field:
        args += ["--filter-json", json.dumps(
            _status_filter(status_field, (settings.get("video") or {}).get("pending_if") or ""),
            ensure_ascii=False)]
    date_field = (fields.get("date_field") or "").strip()
    if date_field:
        args += ["--sort-json", json.dumps(
            [{"field": date_field, "desc": (fields.get("date_sort") or "asc") != "asc"}])]
    return args


def _records_from(data: Any) -> list[dict]:
    if isinstance(data, dict):
        for key in ("items", "records", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _field_value(record: dict, name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    fields = record.get("fields") or {}
    value = fields.get(name)
    return _stringify(value)


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, dict):
        if "text" in value:
            return str(value["text"])
        return ""
    if isinstance(value, list):
        parts = [_stringify(v) for v in value]
        return " ".join(p for p in parts if p)
    return ""


def _first_text(record: dict) -> str:
    fields = record.get("fields") or {}
    for _, value in fields.items():
        cell = _stringify(value)
        if cell:
            return cell
    return ""


def scan_records(settings: dict) -> list[dict]:
    """Return pending records as [{record_id, title, content, date, raw}].

    Filtering (status empty/pending) and date sorting run in Base via
    --filter-json / --sort-json; the local normalization just projects the
    configured fields.
    """
    fields = settings.get("fields") or {}
    content_field = (fields.get("content_field") or "").strip()
    date_field = (fields.get("date_field") or "").strip()
    status_field = (fields.get("status_field") or "").strip()

    data = _run_json(_scan_args(settings))
    out: list[dict] = []
    for record in _records_from(data):
        record_id = (record.get("record_id") or record.get("id") or "").strip()
        title = _first_text(record)
        content = _field_value(record, content_field) if content_field else ""
        date = _field_value(record, date_field) if date_field else ""
        # safety re-filter when no status_field is configured
        if status_field and not (record.get("fields") or {}).get(status_field):
            pass
        out.append({
            "record_id": record_id,
            "title": title,
            "content": content,
            "date": date,
            "raw": record,
        })
    return out


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------
def _update_records_body(record_ids: list[str], status_field: str, value: str) -> dict:
    update_records: dict[str, Any] = {}
    for rid in record_ids:
        update_records[rid] = {status_field: value}
    return {"update_records": update_records}


def update_status(
    base_token: str,
    table_id: str,
    record_ids: list[str],
    status_field: str,
    value: str,
) -> None:
    """Batch-set the status field on a list of records (max 200/call)."""
    if not record_ids or not status_field:
        return
    for chunk_start in range(0, len(record_ids), 200):
        chunk = record_ids[chunk_start:chunk_start + 200]
        _run_json([
            "base", "+record-batch-update",
            "--base-token", base_token,
            "--table-id", table_id,
            "--as", "user",
            "--json", json.dumps(_update_records_body(chunk, status_field, value),
                                 ensure_ascii=False),
        ])


def upload_video(
    base_token: str,
    table_id: str,
    record_id: str,
    attachment_field: str,
    file_path: str,
) -> dict:
    """Upload a local video and append it to the record's attachment cell."""
    if not attachment_field or not record_id or not file_path:
        raise BaseClientError("上传视频缺少配置（附件字段 / 记录号 / 文件）")
    data = _run_json([
        "base", "+record-upload-attachment",
        "--base-token", base_token,
        "--table-id", table_id,
        "--record-id", record_id,
        "--field-id", attachment_field,
        "--file", file_path,
        "--as", "user",
        "--format", "json",
    ], timeout=600)
    return data if isinstance(data, dict) else {"result": data}