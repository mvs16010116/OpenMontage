# -*- coding: utf-8 -*-
"""API tests for the narration-synth web service (FastAPI TestClient).

DB is isolated to a temp file so tests don't pollute the real task table.
All business/settings routes require login; a helper logs in as the admin
user created by the app lifespan.
"""

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