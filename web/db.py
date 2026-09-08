# -*- coding: utf-8 -*-
"""SQLite persistence for the narration-synth web service.

Stores task metadata (status, narration text, output path, timestamps). The
video/media artifacts themselves live in ``projects/<slug>/`` (project dirs)
exactly as the CLI pipeline produces them; this DB only tracks task bookkeeping.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "narration_synth.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'queued',
    narration_text TEXT NOT NULL,
    summary      TEXT NOT NULL,
    project_dir  TEXT,
    output_path  TEXT,
    error_message TEXT,
    created_at   REAL NOT NULL,
    started_at   REAL,
    finished_at  REAL,
    record_id    TEXT UNIQUE,
    base_record_title TEXT
);
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    id    INTEGER PRIMARY KEY CHECK (id = 1),
    data  TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""

# columns added after the original schema shipped (004-02/004-04); SQLite
# lacks ADD COLUMN IF NOT EXISTS so migrations are applied against pragma.
_MIGRATIONS = {
    "record_id": "ALTER TABLE tasks ADD COLUMN record_id TEXT UNIQUE",
    "base_record_title": "ALTER TABLE tasks ADD COLUMN base_record_title TEXT",
    "stage_timings": "ALTER TABLE tasks ADD COLUMN stage_timings TEXT",
    "llm_usage": "ALTER TABLE tasks ADD COLUMN llm_usage TEXT",
    "total_elapsed_s": "ALTER TABLE tasks ADD COLUMN total_elapsed_s REAL",
    "base_sync_status": "ALTER TABLE tasks ADD COLUMN base_sync_status TEXT",
    "base_sync_error": "ALTER TABLE tasks ADD COLUMN base_sync_error TEXT",
}

_JSON_COLUMNS = ("stage_timings", "llm_usage")


def _decode(row) -> dict:
    """Row -> dict with the JSON columns materialized to dicts."""
    task = dict(row)
    for col in _JSON_COLUMNS:
        raw = task.get(col)
        if raw:
            try:
                task[col] = json.loads(raw)
            except (ValueError, TypeError):
                task[col] = None
        else:
            task[col] = None
    return task


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        for column, ddl in _MIGRATIONS.items():
            if column not in existing:
                conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _summarize(text: str, limit: int = 50) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def create_task(
    narration_text: str,
    *,
    status: str = "queued",
    record_id: str | None = None,
    base_record_title: str | None = None,
) -> dict:
    task_id = _new_id()
    now = time.time()
    rid = (record_id or "").strip() or None
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO tasks (id, status, narration_text, summary, created_at, "
            "record_id, base_record_title) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, status, narration_text, _summarize(narration_text), now,
             rid, (base_record_title or "").strip() or None),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        if rid:
            return get_task_by_record_id(rid) or {"id": task_id}
        raise
    finally:
        conn.close()
    return get_task(task_id)


def get_task_by_record_id(record_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE record_id = ?", (record_id,)
        ).fetchone()
        return _decode(row) if row else None
    finally:
        conn.close()


def get_task(task_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _decode(row) if row else None
    finally:
        conn.close()


def update_task(task_id: str, **fields) -> dict | None:
    if not fields:
        return get_task(task_id)
    allowed = {
        "status", "project_dir", "output_path", "error_message",
        "started_at", "finished_at",
        "stage_timings", "llm_usage", "total_elapsed_s",
        "base_sync_status", "base_sync_error",
    }
    cols = [k for k in fields if k in allowed]
    if not cols:
        return get_task(task_id)
    conn = _connect()
    try:
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        values = [fields[c] for c in cols] + [task_id]
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()
    return get_task(task_id)


def list_tasks(limit: int = 50) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_decode(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
def get_user(username: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT username, password_hash, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_password(username: str, password_hash: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash",
            (username, password_hash, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# settings (single JSON row, id = 1)
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    """Return stored settings merged over defaults (api_key still obfuscated)."""
    from web.config import DEFAULT_SETTINGS, deep_merge
    conn = _connect()
    try:
        row = conn.execute("SELECT data FROM settings WHERE id = 1").fetchone()
    finally:
        conn.close()
    if row is None:
        return deep_merge(DEFAULT_SETTINGS, {})
    try:
        stored = json.loads(row["data"])
    except (ValueError, TypeError):
        return deep_merge(DEFAULT_SETTINGS, {})
    return deep_merge(DEFAULT_SETTINGS, stored)


def save_settings(data: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO settings (id, data, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data, "
            "updated_at = excluded.updated_at",
            (json.dumps(data, ensure_ascii=False), time.time()),
        )
        conn.commit()
    finally:
        conn.close()
