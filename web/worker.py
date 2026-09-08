# -*- coding: utf-8 -*-
"""Background task runner for the narration-synth web service.

Uses APScheduler (thread-based) to run pipeline jobs serially. A per-process
SSE hub fans task stage updates out to connected browsers through the server's
running event loop. Serial execution is intentional (single-user): one job
runs at a time; the rest wait in the queue.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import web.db as db
from web.pipeline import run_pipeline


class ProgressHub:
    """Fan-out of per-task stage events to SSE subscribers.

    Subscribers provide an ``asyncio.Queue``. Publishing happens from the
    worker thread, so it marshal the payload onto the owning loop via
    ``run_coroutine_threadsafe``. The loop is captured at server startup so
    publish can always reach the uvicorn loop.
    """

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, task_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        with self._lock:
            self._subs.setdefault(task_id, set()).add(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            subs = self._subs.get(task_id)
            if subs:
                subs.discard(q)
                if not subs:
                    self._subs.pop(task_id, None)

    def publish(self, task_id: str, stage: str, message: str) -> None:
        with self._lock:
            queues = list(self._subs.get(task_id, ()))
        if not queues or self._loop is None:
            return
        payload = f"data: {json.dumps({'stage': stage, 'message': message})}\n\n"
        for q in queues:
            try:
                asyncio.run_coroutine_threadsafe(q.put(payload), self._loop)
            except Exception:
                pass


progress_hub = ProgressHub()
_scheduler: BackgroundScheduler | None = None
_job_lock = threading.Lock()


def start_scheduler() -> None:
    """Idempotent; starts APScheduler if not already running."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _dispatch,
        IntervalTrigger(seconds=1),
        id="narration-dispatch",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _now() -> float:
    return time.time()


def _dispatch() -> None:
    """Pop the oldest queued task and run it serially under a lock."""
    if not _job_lock.acquire(blocking=False):
        return
    try:
        tasks = db.list_tasks(limit=200)
        task = next((t for t in tasks if t["status"] == "queued"), None)
        if task is None:
            return
        task_id = task["id"]
        db.update_task(task_id, status="running", started_at=_now())

        def progress(stage, message):
            progress_hub.publish(task_id, stage, message)

        try:
            final = run_pipeline(task_id, task["narration_text"], progress=progress)
            db.update_task(task_id, status="done", output_path=final, finished_at=_now())
            progress_hub.publish(task_id, "done", "生成完成")
            progress_hub.publish(task_id, "__close__", "")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            db.update_task(
                task_id, status="error", error_message=str(exc)[:500],
                finished_at=_now(),
            )
            progress_hub.publish(task_id, "error", str(exc)[:200])
            progress_hub.publish(task_id, "__close__", "")
    finally:
        _job_lock.release()
