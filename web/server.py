# -*- coding: utf-8 -*-
"""narration-synth Web Service — FastAPI app.

Single-user service that takes an oral narration script and produces a video.

    python -m web.server            # serves at http://127.0.0.1:8000

Endpoints:
    GET  /                     frontend SPA
    POST /api/generate          -> {task_id, status:queued}
    GET  /api/tasks             -> list of task metadata
    GET  /api/tasks/{id}        -> single task
    GET  /api/tasks/{id}/events -> SSE stage feed
    GET  /api/tasks/{id}/video  -> final.mp4 (404 until done)
    GET  /api/health            -> ok
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import web.db as db
from web.worker import progress_hub, start_scheduler, shutdown_scheduler

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # capture the running loop so worker threads can publish SSE to it
    progress_hub.bind_loop(asyncio.get_running_loop())
    db.init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="narration-synth-web", lifespan=lifespan)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/generate")
def generate(payload: dict) -> dict:
    narration_text = (payload.get("narration_text") or "").strip()
    if not narration_text:
        raise HTTPException(status_code=400, detail="narration_text is required")
    task = db.create_task(narration_text, status="queued")
    return {"task_id": task["id"], "status": task["status"]}


@app.get("/api/tasks")
def list_tasks() -> list[dict]:
    return db.list_tasks(limit=100)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/api/tasks/{task_id}/video")
def get_video(task_id: str) -> FileResponse:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task["status"] != "done" or not task["output_path"]:
        raise HTTPException(status_code=404, detail="video not ready")
    path = Path(task["output_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="video file missing")
    return FileResponse(path, media_type="video/mp4", filename=f"{task_id}.mp4")


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request):
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    q: asyncio.Queue = progress_hub.subscribe(task_id)

    async def gen():
        try:
            # send current status snapshot first so a just-opened tab is in sync
            snapshot = db.get_task(task_id)
            stage = "queued" if snapshot["status"] == "queued" else snapshot["status"]
            yield f"data: {json.dumps({'stage': stage, 'message': stage})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if item == "":
                    break
                yield item
                if '"stage": "__close__"' in item:
                    break
        finally:
            progress_hub.unsubscribe(task_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="127.0.0.1", port=8000, log_level="info")
