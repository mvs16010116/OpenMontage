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

import web.base_client as base_client
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

    def publish(
        self, task_id: str, stage: str, message: str,
        phase_duration_s: float = 0.0,
        total_elapsed_s: float | None = None,
        stage_timings: dict | None = None,
        llm_usage: dict | None = None,
    ) -> None:
        with self._lock:
            queues = list(self._subs.get(task_id, ()))
        if not queues or self._loop is None:
            return
        payload = json.dumps({
            "stage": stage,
            "message": message,
            "phase_duration_s": phase_duration_s,
            "total_elapsed_s": total_elapsed_s,
            "stage_timings": stage_timings or {},
            "llm_usage": llm_usage,
        }, ensure_ascii=False)
        data = f"data: {payload}\n\n"
        for q in queues:
            try:
                asyncio.run_coroutine_threadsafe(q.put(data), self._loop)
            except Exception:
                pass


progress_hub = ProgressHub()
_scheduler: BackgroundScheduler | None = None
_job_lock = threading.Lock()
_last_poll_at: float = 0.0


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
    _scheduler.add_job(
        _poll,
        IntervalTrigger(seconds=5),
        id="narration-poll",
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


def _config_word(key: str) -> str | None:
    settings = db.load_settings()
    video = settings.get("video") or {}
    return (video.get(key) or "").strip() or None


def _poll() -> None:
    """Auto-enqueue pending Base records, honoring poll.enabled + interval."""
    global _last_poll_at
    settings = db.load_settings()
    poll = settings.get("poll") or {}
    if not poll.get("enabled"):
        return
    interval = float(poll.get("interval_seconds") or 10)
    now = _now()
    if now - _last_poll_at < interval:
        return
    _last_poll_at = now
    try:
        rows = base_client.scan_records(settings)
    except base_client.BaseClientError:
        return
    for row in rows:
        rid = row.get("record_id")
        content = row.get("content") or ""
        if not rid or not content.strip():
            continue
        if db.get_task_by_record_id(rid) is None:
            try:
                db.create_task(content, status="queued", record_id=rid,
                               base_record_title=row.get("title") or "")
            except Exception:  # noqa: BLE001
                pass


def _sync_base(task: dict, status_word: str | None, output_path: str | None = None) -> None:
    """Best-effort status writeback + final video upload to the Base record.

    Never raises: any failure is recorded on base_sync_status/base_sync_error so
    the task's own state stays authoritative.
    """
    try:
        s = db.load_settings()
        lark = s.get("lark") or {}
        fields = s.get("fields") or {}
        video = s.get("video") or {}
        status_field = (fields.get("status_field") or "").strip()
        attach_field = (fields.get("attachment_field") or "").strip()
        rid = task.get("record_id") or ""
        if not rid or not (lark.get("base_url_or_token") or "").strip() or not (lark.get("table_id") or "").strip():
            return
        if status_word and not status_field and not attach_field:
            return
        token = base_client.resolve_base(lark["base_url_or_token"])
        if status_word and status_field:
            base_client.update_status(
                token, lark["table_id"], [rid], status_field, status_word)
        if output_path and attach_field:
            base_client.upload_video(
                token, lark["table_id"], rid, attach_field, output_path)
        db.update_task(task["id"], base_sync_status="ok", base_sync_error="")
    except Exception as exc:  # noqa: BLE001
        db.update_task(task["id"], base_sync_status="failed",
                       base_sync_error=str(exc)[:300])


def _mark_processing(task: dict) -> None:
    """Set the Base record's status to 处理中 when a record-backed task starts."""
    try:
        s = db.load_settings()
        lark = s.get("lark") or {}
        fields = s.get("fields") or {}
        video = s.get("video") or {}
        status_field = (fields.get("status_field") or "").strip()
        processing = (video.get("status_processing") or "").strip()
        rid = task.get("record_id") or ""
        if not rid or not status_field or not processing:
            return
        if not (lark.get("base_url_or_token") or "").strip() or not (lark.get("table_id") or "").strip():
            return
        token = base_client.resolve_base(lark["base_url_or_token"])
        base_client.update_status(token, lark["table_id"], [rid], status_field, processing)
    except Exception:  # noqa: BLE001
        pass


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
        _mark_processing(task)

        run_stats = {"stage_timings": {}, "total_elapsed_s": 0.0, "llm_usage": None}

        def progress(stage, message, phase_duration_s=0.0, total_elapsed_s=0.0,
                     stage_timings=None, llm_usage=None):
            if stage_timings:
                run_stats["stage_timings"] = stage_timings
            if total_elapsed_s:
                run_stats["total_elapsed_s"] = total_elapsed_s
            if llm_usage:
                run_stats["llm_usage"] = llm_usage
            progress_hub.publish(
                task_id, stage, message,
                phase_duration_s=phase_duration_s,
                total_elapsed_s=total_elapsed_s,
                stage_timings=stage_timings,
                llm_usage=llm_usage,
            )

        try:
            final = run_pipeline(
                task_id, task["narration_text"],
                progress=progress, llm_settings=db.load_settings(),
            )
            db.update_task(
                task_id, status="done", output_path=final, finished_at=_now(),
                stage_timings=json.dumps(run_stats["stage_timings"], ensure_ascii=False),
                llm_usage=json.dumps(run_stats["llm_usage"], ensure_ascii=False),
                total_elapsed_s=run_stats["total_elapsed_s"],
            )
            _sync_base(task, _config_word("status_success"), final)
            progress_hub.publish(task_id, "done", "生成完成")
            progress_hub.publish(task_id, "__close__", "")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            db.update_task(
                task_id, status="error", error_message=str(exc)[:500],
                finished_at=_now(),
                stage_timings=json.dumps(run_stats["stage_timings"], ensure_ascii=False),
                total_elapsed_s=run_stats["total_elapsed_s"],
            )
            _sync_base(task, _config_word("status_failed"))
            progress_hub.publish(task_id, "error", str(exc)[:200])
            progress_hub.publish(task_id, "__close__", "")
    finally:
        _job_lock.release()
