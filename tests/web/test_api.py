# -*- coding: utf-8 -*-
"""API tests for the narration-synth web service (FastAPI TestClient).

DB is isolated to a temp file so tests don't pollute the real task table.
All business/settings routes require login; a helper logs in as the admin
user created by the app lifespan.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import web.config as cfg
import web.db as db
import web.server as server

ADMIN = server.auth.INITIAL_USERNAME
PASSWORD = server.auth.INITIAL_PASSWORD


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # isolate the sqlite db to a temp file
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    from web import auth
    auth.ensure_admin_user()
    with TestClient(server.app) as c:
        yield c


def login(client):
    r = client.post("/api/login", json={"username": ADMIN, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r


# ---------------------------------------------------------------------------
# health / index
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "口播视频生成器" in r.text


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------
def test_business_routes_require_login(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.get("/api/me").status_code == 401
    r = client.post("/api/generate", json={"narration_text": "你好。"})
    assert r.status_code == 401


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": ADMIN, "password": "nope"})
    assert r.status_code == 401


def test_login_empty_fields(client):
    r = client.post("/api/login", json={"username": "", "password": ""})
    assert r.status_code == 400


def test_login_then_logout(client):
    r = client.post("/api/login", json={"username": ADMIN, "password": PASSWORD})
    assert r.status_code == 200
    assert client.get("/api/me").json()["username"] == ADMIN
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_change_password_flow(client):
    login(client)
    # wrong old password
    r = client.post("/api/change-password", json={
        "old_password": "wrong",
        "new_password": "newpass123",
    })
    assert r.status_code == 400
    # too short
    r = client.post("/api/change-password", json={
        "old_password": PASSWORD,
        "new_password": "ab",
    })
    assert r.status_code == 400
    # ok
    r = client.post("/api/change-password", json={
        "old_password": PASSWORD,
        "new_password": "newpass123",
    })
    assert r.status_code == 200
    # old password no longer works
    assert client.post("/api/logout").status_code == 200
    r = client.post("/api/login", json={"username": ADMIN, "password": PASSWORD})
    assert r.status_code == 401
    r = client.post("/api/login", json={"username": ADMIN, "password": "newpass123"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# tasks
# ---------------------------------------------------------------------------
def test_generate_creates_queued_task(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "第一句。第二句。"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert len(body["task_id"]) == 12


def test_generate_requires_text(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "   "})
    assert r.status_code == 400


def test_generate_then_get_task(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "你好。世界。"})
    tid = r.json()["task_id"]
    r2 = client.get(f"/api/tasks/{tid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == tid
    assert "你好" in r2.json()["narration_text"]


def test_get_unknown_task_404(client):
    login(client)
    assert client.get("/api/tasks/nope").status_code == 404


def test_video_not_ready_until_done(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "测试内容。"})
    tid = r.json()["task_id"]
    # default queue -> video not ready
    assert client.get(f"/api/tasks/{tid}/video").status_code == 404


def test_list_tasks(client):
    login(client)
    client.post("/api/generate", json={"narration_text": "甲。"})
    client.post("/api/generate", json={"narration_text": "乙。"})
    tasks = client.get("/api/tasks").json()
    assert len(tasks) >= 2


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------
def test_settings_defaults_masked(client):
    login(client)
    r = client.get("/api/settings")
    assert r.status_code == 200
    s = r.json()
    assert s["llm"]["api_key"] == ""
    assert s["poll"]["enabled"] is False
    assert s["fields"]["date_sort"] == "asc"
    assert s["video"]["pending_if"] == "待处理"


def test_settings_save_obfuscates_key(client):
    login(client)
    payload = {
        "lark": {"base_url_or_token": "appfake_base_token", "table_id": "tbl_build"},
        "fields": {"content_field": "口播文案", "date_sort": "asc"},
        "llm": {"base_url": "https://api.openai.com/v1", "api_key": "sk-test-key",
                "model": "gpt-4o-mini"},
        "poll": {"enabled": True, "interval_seconds": 60},
    }
    r = client.put("/api/settings", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["llm"]["api_key"] == "****"
    assert body["lark"]["base_url_or_token"] == "appfake_base_token"
    assert body["poll"]["enabled"] is True
    # stored value is obfuscated, not plaintext, and round-trips
    stored = db.load_settings()
    assert stored["llm"]["api_key"] != "sk-test-key"
    assert cfg.deobfuscate(stored["llm"]["api_key"]) == "sk-test-key"
    # defaults filled in for untouched keys
    assert body["video"]["pending_if"] == "待处理"


def test_settings_preserves_key_when_masked_echoed(client):
    login(client)
    client.put("/api/settings", json={
        "llm": {"api_key": "sk-secret-1", "model": "gpt-4o-mini"},
    })
    # echo back the masked key with a changed model -> key must be preserved
    r = client.put("/api/settings", json={
        "llm": {"api_key": "****", "model": "deepseek-chat"},
    })
    assert r.status_code == 200
    stored = db.load_settings()
    assert cfg.deobfuscate(stored["llm"]["api_key"]) == "sk-secret-1"
    assert stored["llm"]["model"] == "deepseek-chat"
    # clearing the key works too
    r = client.put("/api/settings", json={"llm": {"api_key": ""}})
    assert r.status_code == 200
    assert db.load_settings()["llm"]["api_key"] == ""


def test_settings_rejects_non_dict(client):
    login(client)
    r = client.put("/api/settings", json="nope")
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# base scan
# ---------------------------------------------------------------------------
def test_base_scan_requires_login(client):
    assert client.post("/api/base/scan").status_code == 401


def test_base_scan_unconfigured_returns_readable_error(client):
    login(client)
    r = client.post("/api/base/scan")
    assert r.status_code == 400
    assert "配置" in r.json()["detail"]


# ---------------------------------------------------------------------------
# task detail: 004-04 timing / llm usage fields
# ---------------------------------------------------------------------------
def test_task_detail_includes_timing_and_llm_usage(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "第一句。第二句。"})
    tid = r.json()["task_id"]
    db.update_task(
        tid,
        status="done",
        output_path=r"c:\out\final.mp4",
        stage_timings=json.dumps({"llm_parse": 1.2, "generating_tts": 3.4},
                                 ensure_ascii=False),
        llm_usage=json.dumps({"model": "m", "total_tokens": 5}, ensure_ascii=False),
        total_elapsed_s=7.5,
    )
    d = client.get(f"/api/tasks/{tid}").json()
    assert d["status"] == "done"
    assert d["stage_timings"] == {"llm_parse": 1.2, "generating_tts": 3.4}
    assert d["llm_usage"] == {"model": "m", "total_tokens": 5}
    assert d["total_elapsed_s"] == 7.5


def test_task_list_new_tasks_have_empty_stats(client):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "第一句。"})
    tid = r.json()["task_id"]
    d = client.get(f"/api/tasks/{tid}").json()
    assert d["stage_timings"] is None
    assert d["llm_usage"] is None
    assert d["total_elapsed_s"] is None


# ---------------------------------------------------------------------------
# 004-05: create task via POST /api/tasks + batch enqueue
# ---------------------------------------------------------------------------
def test_create_task_by_narration_text(client):
    login(client)
    r = client.post("/api/tasks", json={"narration_text": "直录文案。"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert "task_id" in body
    assert "duplicate" not in body


def test_create_task_requires_text_or_record(client):
    login(client)
    r = client.post("/api/tasks", json={})
    assert r.status_code == 400
    assert "record_id" in r.json()["detail"] or "narration_text" in r.json()["detail"]


def _configure_base() -> None:
    db.save_settings({
        "lark": {"base_url_or_token": "appfakeBaseToken", "table_id": "tbl_demo"},
        "fields": {"content_field": "口播文案", "status_field": "状态",
                   "attachment_field": "成片"},
    })


def test_create_task_by_record_id_unknown(client, monkeypatch):
    login(client)
    _configure_base()
    monkeypatch.setattr(server.base_client, "scan_records", lambda settings: [])
    r = client.post("/api/tasks", json={"record_id": "rec_not_there"})
    assert r.status_code == 400


def test_create_task_by_record_id(client, monkeypatch):
    login(client)
    _configure_base()
    monkeypatch.setattr(server.base_client, "scan_records", lambda settings: [{
        "record_id": "rec_A", "title": "标题A",
        "content": "记录文案。",
        "date_value": None,
    }])
    r = client.post("/api/tasks", json={"record_id": "rec_A"})
    assert r.status_code == 200
    body = r.json()
    assert body["record_id"] == "rec_A"
    task = client.get(f"/api/tasks/{body['task_id']}").json()
    assert task["record_id"] == "rec_A"
    assert "记录文案" in task["narration_text"]
    # second call is deduped
    r2 = client.post("/api/tasks", json={"record_id": "rec_A"})
    assert r2.status_code == 200
    assert r2.json()["task_id"] == body["task_id"]
    assert r2.json().get("duplicate") is True


def test_create_tasks_batch(client, monkeypatch):
    login(client)
    _configure_base()
    monkeypatch.setattr(server.base_client, "scan_records", lambda settings: [
        {"record_id": "rec_1", "title": "一", "content": "文案一。", "date_value": None},
        {"record_id": "rec_2", "title": "二", "content": "文案二。", "date_value": None},
        {"record_id": "rec_empty", "title": "空", "content": "", "date_value": None},
    ])
    r = client.post("/api/tasks/batch", json={"record_ids": ["rec_1", "rec_2", "rec_empty", "rec_missing"]})
    assert r.status_code == 200
    body = r.json()
    assert [c["record_id"] for c in body["created"]] == ["rec_1", "rec_2"]
    assert [c["record_id"] for c in body["empty"]] == ["rec_empty", "rec_missing"]
    # re-batch dedupes into existing
    r2 = client.post("/api/tasks/batch", json={"record_ids": ["rec_1"]})
    body2 = r2.json()
    assert body2["created"] == []
    assert body2["existing"][0]["record_id"] == "rec_1"


def test_create_tasks_batch_requires_record_ids(client):
    login(client)
    assert client.post("/api/tasks/batch", json={}).status_code == 400


def test_batch_and_tasks_require_login(client):
    assert client.post("/api/tasks", json={"narration_text": "x"}).status_code == 401
    assert client.post("/api/tasks/batch", json={"record_ids": ["a"]}).status_code == 401


# ---------------------------------------------------------------------------
# 004-05: video endpoint ranges
# ---------------------------------------------------------------------------
def test_video_range_request(client, tmp_path):
    login(client)
    r = client.post("/api/generate", json={"narration_text": "视频测试。"})
    tid = r.json()["task_id"]
    video = tmp_path / "final.mp4"
    video.write_bytes(b"0123456789abcdef")
    db.update_task(tid, status="done", output_path=str(video))
    # full stream
    r = client.get(f"/api/tasks/{tid}/video")
    assert r.status_code == 200
    assert "Accept-Ranges" in r.headers
    assert r.content == b"0123456789abcdef"
    # byte range
    r = client.get(f"/api/tasks/{tid}/video", headers={"Range": "bytes=2-5"})
    assert r.status_code == 206
    assert r.headers["Content-Range"] == "bytes 2-5/16"
    assert r.content == b"2345"
    # suffix range
    r = client.get(f"/api/tasks/{tid}/video", headers={"Range": "bytes=-4"})
    assert r.status_code == 206
    assert r.content == b"cdef"
    # unsatisfiable range
    r = client.get(f"/api/tasks/{tid}/video", headers={"Range": "bytes=100-200"})
    assert r.status_code == 416