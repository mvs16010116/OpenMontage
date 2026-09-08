# -*- coding: utf-8 -*-
"""SQLite persistence for the narration-synth web service.

Stores task metadata (status, narration text, output path, timestamps). The
video/media artifacts themselves live in ``projects/<slug>/`` (project dirs)
exactly as the CLI pipeline produces them; this DB only tracks task bookkeeping.
"""

from __future__ import annotations

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
    finished_at  REAL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _summarize(text: str, limit: int = 50) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def create_task(narration_text: str, *, status: str = "queued") -> dict:
    task_id = _new_id()
    now = time.time()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO tasks (id, status, narration_text, summary, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (task_id, status, narration_text, _summarize(narration_text), now),
        )
        conn.commit()
    finally:
        conn.close()
    return get_task(task_id)


def get_task(task_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_task(task_id: str, **fields) -> dict | None:
    if not fields:
        return get_task(task_id)
    allowed = {
        "status", "project_dir", "output_path", "error_message",
        "started_at", "finished_at",
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
        return [dict(r) for r in rows]
    finally:
        conn.close()
