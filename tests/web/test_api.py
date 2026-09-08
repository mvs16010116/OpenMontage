# -*- coding: utf-8 -*-
"""API tests for the narration-synth web service (FastAPI TestClient).

DB is isolated to a temp file so tests don't pollute the real task table.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import web.db as db
import web.server as server


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # isolate the sqlite db to a temp file
    db.DB_PATH = Path(tmp_path) / "test.db"
    db.init_db()
    with TestClient(server.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_creates_queued_task(client):
    r = client.post("/api/generate", json={"narration_text": "第一句。第二句。"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert len(body["task_id"]) == 12


def test_generate_requires_text(client):
    r = client.post("/api/generate", json={"narration_text": "   "})
    assert r.status_code == 400


def test_generate_then_get_task(client):
    r = client.post("/api/generate", json={"narration_text": "你好。世界。"})
    tid = r.json()["task_id"]
    r2 = client.get(f"/api/tasks/{tid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == tid
    assert "第一句" in r2.json()["narration_text"] or r2.json()["summary"]


def test_get_unknown_task_404(client):
    assert client.get("/api/tasks/nope").status_code == 404


def test_video_not_ready_until_done(client):
    r = client.post("/api/generate", json={"narration_text": "测试内容。"})
    tid = r.json()["task_id"]
    # default queue -> video not ready
    assert client.get(f"/api/tasks/{tid}/video").status_code == 404


def test_list_tasks(client):
    client.post("/api/generate", json={"narration_text": "甲。"})
    client.post("/api/generate", json={"narration_text": "乙。"})
    tasks = client.get("/api/tasks").json()
    assert len(tasks) >= 2


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "口播视频生成器" in r.text
