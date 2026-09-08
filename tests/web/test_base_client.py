# -*- coding: utf-8 -*-
"""Unit tests for web/base_client.py — command construction, JSON parsing and
error mapping. Never invokes the real lark-cli binary."""

import pytest

import web.base_client as bc


def _settings(**overrides):
    base = {
        "lark": {"base_url_or_token": "appfakeBaseToken", "table_id": "tbl_demo"},
        "fields": {
            "content_field": "口播文案",
            "date_field": "日期",
            "status_field": "状态",
            "attachment_field": "成片",
            "date_sort": "asc",
        },
        "poll": {"enabled": True, "interval_seconds": 60, "max_records_per_batch": 20},
        "video": {"pending_if": "待处理"},
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


# ---------------------------------------------------------------------------
# error mapping
# ---------------------------------------------------------------------------
def test_readable_error_known_hint():
    assert "token" in bc._readable_error("param baseToken is invalid")
    assert bc._readable_error("1254045 字段不存在") == "字段不存在，请检查字段映射"
    assert bc._readable_error("has error 1254015 x") == "字段值类型不匹配"


def test_readable_error_fallback():
    assert bc._readable_error("") == "lark-cli 调用失败"
    assert bc._readable_error("boom") == "lark-cli 失败：boom"


# ---------------------------------------------------------------------------
# resolve_base
# ---------------------------------------------------------------------------
def test_resolve_token_passthrough(monkeypatch):
    assert bc.resolve_base("appfakeBaseToken") == "appfakeBaseToken"


def test_resolve_url(monkeypatch):
    monkeypatch.setattr(bc, "_run_json", lambda *a, **k: {
        "items": [{"base_token": "resolved_token", "block_type": "table"}],
    })
    assert bc.resolve_base("https://x.feishu.cn/base/app_xx?table=tbl_y") == "resolved_token"


def test_resolve_url_no_token(monkeypatch):
    monkeypatch.setattr(bc, "_run_json", lambda *a, **k: {"items": [{"name": "x"}]})
    with pytest.raises(bc.BaseClientError):
        bc.resolve_base("https://x.feishu.cn/base/app_xx")


def test_resolve_url_calls_url_resolve(monkeypatch):
    captured = {}
    def fake_run_json(args, **kw):
        captured["args"] = args
        return {"items": [{"base_token": "t"}]}
    monkeypatch.setattr(bc, "_run_json", fake_run_json)
    bc.resolve_base("https://x.feishu.cn/base/app_xx?table=tbl_y")
    assert "+url-resolve" in captured["args"]
    assert "--as" in captured["args"] and "user" in captured["args"]


# ---------------------------------------------------------------------------
# scan_records → normalization
# ---------------------------------------------------------------------------
def test_scan_args_builds_filter_and_sort(monkeypatch):
    monkeypatch.setattr(bc, "resolve_base", lambda v: "resolved_base")
    args = bc._scan_args(_settings())
    assert args[:2] == ["base", "+record-list"]
    assert "resolved_base" in args
    assert "--table-id" in args and args[args.index("--table-id") + 1] == "tbl_demo"
    assert "--limit" in args and args[args.index("--limit") + 1] == "20"
    fi = args[args.index("--filter-json") + 1]
    import json
    filt = json.loads(fi)
    assert filt["logic"] == "or"
    assert ["状态", "empty"] in filt["conditions"]
    assert ["状态", "intersects", ["待处理"]] in filt["conditions"]
    si = json.loads(args[args.index("--sort-json") + 1])
    assert si == [{"field": "日期", "desc": False}]


def test_scan_args_desc_sort(monkeypatch):
    s = _settings(); s["fields"]["date_sort"] = "desc"
    monkeypatch.setattr(bc, "resolve_base", lambda v: "t")
    args = bc._scan_args(s)
    import json
    assert json.loads(args[args.index("--sort-json") + 1])[0]["desc"] is True


def test_scan_args_no_status_no_sort(monkeypatch):
    s = _settings()
    s["fields"]["status_field"] = ""
    s["fields"]["date_field"] = ""
    monkeypatch.setattr(bc, "resolve_base", lambda v: "t")
    args = bc._scan_args(s)
    assert "--filter-json" not in args
    assert "--sort-json" not in args


def test_scan_records_projects_fields(monkeypatch):
    data = {"items": [
        {"record_id": "rec_1", "fields": {
            "标题": "北美峰会", "口播文案": "开场文案内容。", "日期": "2026-06-01 10:00:00",
            "状态": "",
        }},
        {"record_id": "rec_2", "fields": {
            "标题": "欧洲观察", "口播文案": "第二段文案。", "日期": "2026-06-02 08:00:00",
            "状态": "待处理",
        }},
    ]}
    monkeypatch.setattr(bc, "_run_json", lambda *a, **k: data)
    rows = bc.scan_records(_settings())
    assert [r["record_id"] for r in rows] == ["rec_1", "rec_2"]
    assert rows[0]["title"] == "北美峰会"
    assert rows[0]["content"] == "开场文案内容。"
    assert rows[0]["date"] == "2026-06-01 10:00:00"


def test_scan_records_empty_list(monkeypatch):
    monkeypatch.setattr(bc, "_run_json", lambda *a, **k: {"items": []})
    assert bc.scan_records(_settings()) == []


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------
def test_update_records_body():
    body = bc._update_records_body(["rec_a", "rec_b"], "状态", "成功")
    assert body == {"update_records": {"rec_a": {"状态": "成功"}, "rec_b": {"状态": "成功"}}}


def test_update_status_builds_batch_command(monkeypatch):
    captured = {}
    def fake_run_json(args, **kw):
        captured["args"] = args
        return {}
    monkeypatch.setattr(bc, "_run_json", fake_run_json)
    bc.update_status("bt", "tbl_x", ["rec_1"], "状态", "成功")
    a = captured["args"]
    assert a[:2] == ["base", "+record-batch-update"]
    assert "--record-batch-update" not in a  # placeholder guard
    import json
    assert json.loads(a[a.index("--json") + 1]) == {
        "update_records": {"rec_1": {"状态": "成功"}}}


def test_update_status_empty_is_noop(monkeypatch):
    captured = []
    monkeypatch.setattr(bc, "_run_json", lambda *a, **k: captured.append(a) or {})
    bc.update_status("bt", "tbl_x", [], "状态", "成功")
    assert captured == []


def test_upload_video_builds_upload_command(monkeypatch):
    captured = {}
    def fake_run_json(args, **kw):
        captured["args"] = args
        captured["timeout"] = kw.get("timeout")
        return [{"file_token": "f_token"}]
    monkeypatch.setattr(bc, "_run_json", fake_run_json)
    out = bc.upload_video("bt", "tbl_x", "rec_1", "成片", r"c:\out\final.mp4")
    a = captured["args"]
    assert a[:2] == ["base", "+record-upload-attachment"]
    assert a[a.index("--record-id") + 1] == "rec_1"
    assert a[a.index("--field-id") + 1] == "成片"
    assert a[a.index("--file") + 1] == r"c:\out\final.mp4"
    assert captured["timeout"] == 600


def test_upload_video_missing_config(monkeypatch):
    with pytest.raises(bc.BaseClientError):
        bc.upload_video("bt", "tbl_x", "", "成片", "x.mp4")