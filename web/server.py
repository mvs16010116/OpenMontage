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

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import web.auth as auth
import web.config as cfg
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
    auth.ensure_admin_user()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="narration-synth-web", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=auth.get_session_secret())

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(auth.AuthError)
async def _auth_error_handler(request: Request, exc: auth.AuthError):
    return auth.unauthorized()


def require_user(request: Request) -> str:
    """FastAPI dependency — 401 if not logged in."""
    return auth.require_user(request)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------
@app.post("/api/login")
def login(payload: dict, request: Request) -> dict:
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if not auth.authenticate(username, password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    request.session[auth.SESSION_USER_KEY] = username
    return {"ok": True, "username": username}


@app.post("/api/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
def me(username: str = Depends(require_user)) -> dict:
    return {"username": username}


@app.post("/api/change-password")
def change_password(
    payload: dict,
    request: Request,
    username: str = Depends(require_user),
) -> dict:
    old = payload.get("old_password") or ""
    new = payload.get("new_password") or ""
    if len(new) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    user = db.get_user(username)
    if user is None or not auth.verify_password(old, user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码错误")
    db.set_password(username, auth.hash_password(new))
    return {"ok": True}


# ---------------------------------------------------------------------------
# settings (config center)
# ---------------------------------------------------------------------------
@app.get("/api/settings")
def get_settings(username: str = Depends(require_user)) -> dict:
    s = db.load_settings()
    if cfg.deobfuscate((s.get("llm") or {}).get("api_key") or ""):
        s["llm"]["api_key"] = "****"
    return s


@app.put("/api/settings")
def put_settings(
    payload: dict,
    username: str = Depends(require_user),
) -> dict:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="配置格式错误")
    stored = db.load_settings()
    llm_in = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}
    new_key = (llm_in.get("api_key") or "").strip()
    if new_key == "****":
        # masked placeholder echoed back -> keep the existing stored key
        llm_in["api_key"] = (stored.get("llm") or {}).get("api_key") or ""
    elif new_key:
        llm_in["api_key"] = cfg.obfuscate(new_key)
    else:
        llm_in["api_key"] = ""
    payload["llm"] = llm_in
    normalized = cfg.normalize_settings(payload)
    db.save_settings(normalized)
    s = db.load_settings()
    if cfg.deobfuscate((s.get("llm") or {}).get("api_key") or ""):
        s["llm"]["api_key"] = "****"
    return s


@app.post("/api/generate")
def generate(payload: dict, username: str = Depends(require_user)) -> dict:
    narration_text = (payload.get("narration_text") or "").strip()
    if not narration_text:
        raise HTTPException(status_code=400, detail="narration_text is required")
    task = db.create_task(narration_text, status="queued")
    return {"task_id": task["id"], "status": task["status"]}


@app.get("/api/tasks")
def list_tasks(username: str = Depends(require_user)) -> list[dict]:
    return db.list_tasks(limit=100)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, username: str = Depends(require_user)) -> dict:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/api/tasks/{task_id}/video")
def get_video(task_id: str, username: str = Depends(require_user)) -> FileResponse:
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
async def task_events(
    task_id: str,
    request: Request,
    username: str = Depends(require_user),
):
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
