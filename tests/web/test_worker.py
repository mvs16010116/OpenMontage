# -*- coding: utf-8 -*-
"""Unit tests for web/worker.py — Base status writeback, video upload and
record polling. All lark-cli calls are monkeypatched."""
# pylint: disable=protected-access

from pathlib import Path

import web.base_client as bc
import web.db as db
import web.worker as worker


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
        "video": {
            "pending_if": "待处理",
            "status_processing": "处理中",
            "status_success": "已完成",
            "status_failed": "生成失败",
        },
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


def test_sync_base_success(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings", lambda: _settings())
    task = db.create_task("文案。", record_id="rec_1")
    out = tmp_path / "final.mp4"
    out.write_bytes(b"mp4")
    calls = {"status": [], "upload": []}

    def fake_update(token, table, rids, field, word):
        calls["status"].append((token, table, rids, field, word))

    def fake_upload(token, table, rid, field, path):
        calls["upload"].append((token, table, rid, field, path))

    monkeypatch.setattr(bc, "resolve_base", lambda token: "appresolved")
    monkeypatch.setattr(bc, "update_status", fake_update)
    monkeypatch.setattr(bc, "upload_video", fake_upload)

    worker._sync_base(task, "已完成", str(out))

    assert calls["status"] == [("appresolved", "tbl_demo", ["rec_1"], "状态", "已完成")]
    assert calls["upload"] == [("appresolved", "tbl_demo", "rec_1", "成片", str(out))]
    stored = db.get_task(task["id"])
    assert stored["base_sync_status"] == "ok"
    assert stored["base_sync_error"] == ""


def test_sync_base_without_record_id_skips(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings", lambda: _settings())
    task = db.create_task("文案。")
    worker._sync_base(task, "已完成")
    stored = db.get_task(task["id"])
    assert stored["base_sync_status"] is None


def test_sync_base_failure_recorded(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings", lambda: _settings())
    task = db.create_task("文案。", record_id="rec_1")

    def boom(*_args, **_kwargs):
        raise bc.BaseClientError("token 失效")

    monkeypatch.setattr(bc, "resolve_base", boom)
    worker._sync_base(task, "已完成")
    stored = db.get_task(task["id"])
    assert stored["base_sync_status"] == "failed"
    assert "token" in (stored["base_sync_error"] or "")


def test_mark_processing_recorded(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings", lambda: _settings())
    task = db.create_task("文案。", record_id="rec_1")
    calls = []

    def fake_update(token, table, rids, field, word):
        calls.append((token, table, rids, field, word))

    monkeypatch.setattr(bc, "resolve_base", lambda token: "appresolved")
    monkeypatch.setattr(bc, "update_status", fake_update)
    worker._mark_processing(task)
    assert calls == [("appresolved", "tbl_demo", ["rec_1"], "状态", "处理中")]


def test_poll_enqueues_pending(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings", lambda: _settings())
    monkeypatch.setattr(worker, "_last_poll_at", 0.0)
    monkeypatch.setattr(bc, "scan_records", lambda settings: [
        {"record_id": "rec_p1", "title": "一",
         "content": "扫描文案一。", "date_value": None},
        {"record_id": "rec_p2", "title": "二",
         "content": "扫描文案二。", "date_value": None},
        {"record_id": "rec_stale", "title": "空", "content": "", "date_value": None},
    ])
    # force interval to pass
    monkeypatch.setattr(worker.time, "time", lambda: 1000.0)
    worker._poll()
    t1 = db.get_task_by_record_id("rec_p1")
    t2 = db.get_task_by_record_id("rec_p2")
    assert t1 is not None and t1["status"] == "queued"
    assert t2 is not None and t2["status"] == "queued"
    # empty content not enqueued
    assert db.get_task_by_record_id("rec_stale") is None
    # second poll within interval is skipped -> existing task remains single
    monkeypatch.setattr(worker.time, "time", lambda: 1005.0)
    worker._poll()
    same = [t for t in db.list_tasks() if t["id"] == t1["id"]]
    assert len(same) == 1


def test_poll_disabled_does_nothing(tmp_path, monkeypatch):
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    monkeypatch.setattr(db, "load_settings",
                        lambda: _settings(poll={"enabled": False}))
    scanned = []

    def fake_scan(settings):
        scanned.append(settings)
        return [{"record_id": "rec_x", "title": "x", "content": "唉。", "date_value": None}]

    monkeypatch.setattr(bc, "scan_records", fake_scan)
    monkeypatch.setattr(worker, "_last_poll_at", 0.0)
    worker._poll()
    assert scanned == []
    assert db.get_task_by_record_id("rec_x") is None