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
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import web.auth as auth
import web.base_client as base_client
import web.config as cfg
import web.db as db
from web.worker import progress_hub, start_scheduler, shutdown_scheduler

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    progress_hub.bind_loop(asyncio.get_running_loop())
    db.init_db()
    auth.ensure_admin_user()
    interrupted = db.mark_interrupted()
    if interrupted:
        print(f"[startup] marked {interrupted} stale task(s) as interrupted")
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


@app.post("/api/base/scan")
def scan_base(username: str = Depends(require_user)) -> dict:
    """Scan pending records from the configured Base and enqueue new tasks."""
    s = db.load_settings()
    lark = s.get("lark") or {}
    if not (lark.get("base_url_or_token") or "").strip() or not (lark.get("table_id") or "").strip():
        raise HTTPException(status_code=400, detail="未配置 Base 链接及数据表，请先在「配置」页填写")
    try:
        pending = base_client.scan_records(s)
    except base_client.BaseClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    created: list[dict] = []
    skipped: list[dict] = []
    for rec in pending:
        if not rec["record_id"]:
            skipped.append({"record_id": "", "title": rec["title"], "reason": "缺少记录号"})
            continue
        if db.get_task_by_record_id(rec["record_id"]):
            skipped.append({"record_id": rec["record_id"], "title": rec["title"], "reason": "已存在任务"})
            continue
        if not rec["content"]:
            skipped.append({"record_id": rec["record_id"], "title": rec["title"], "reason": "文案字段为空"})
            continue
        task = db.create_task(
            rec["content"],
            record_id=rec["record_id"],
            base_record_title=rec["title"],
        )
        created.append({"record_id": rec["record_id"], "task_id": task["id"], "title": rec["title"]})
    return {
        "pending": len(pending),
        "created": created,
        "skipped": skipped,
    }


@app.post("/api/generate")
def generate(payload: dict, username: str = Depends(require_user)) -> dict:
    narration_text = (payload.get("narration_text") or "").strip()
    if not narration_text:
        raise HTTPException(status_code=400, detail="narration_text is required")
    task = db.create_task(narration_text, status="queued")
    return {"task_id": task["id"], "status": task["status"]}


@app.post("/api/tasks")
def create_task(payload: dict, username: str = Depends(require_user)) -> dict:
    """Create an enqueued task from a narration_text, or a scanned record_id."""
    narration_text = (payload.get("narration_text") or "").strip()
    record_id = (payload.get("record_id") or "").strip()
    if not narration_text and not record_id:
        raise HTTPException(status_code=400, detail="narration_text 或 record_id 必填")
    if record_id:
        existing = db.get_task_by_record_id(record_id)
        if existing:
            return {"task_id": existing["id"], "status": existing["status"], "duplicate": True}
        content = _record_content_by_id(record_id)
        if not content:
            raise HTTPException(status_code=400, detail="该记录未找到或文案字段为空")
        task = db.create_task(content, status="queued", record_id=record_id)
        return {"task_id": task["id"], "status": task["status"], "record_id": record_id}
    task = db.create_task(narration_text, status="queued")
    return {"task_id": task["id"], "status": task["status"]}


@app.post("/api/tasks/batch")
def create_tasks_batch(payload: dict, username: str = Depends(require_user)) -> dict:
    """Batch-enqueue Base records by record_id (dedupe against existing tasks)."""
    record_ids = payload.get("record_ids") or []
    if not isinstance(record_ids, list) or not record_ids:
        raise HTTPException(status_code=400, detail="record_ids 必填且非空")
    by_id = _pending_records_map()
    created: list[dict] = []
    existing: list[dict] = []
    empty: list[dict] = []
    for rid in record_ids:
        rid = (rid or "").strip()
        if not rid:
            continue
        task = db.get_task_by_record_id(rid)
        if task:
            existing.append({"record_id": rid, "task_id": task["id"], "status": task["status"]})
            continue
        rec = by_id.get(rid)
        if not rec or not rec.get("content"):
            empty.append({"record_id": rid, "reason": "未找到或文案为空"})
            continue
        task = db.create_task(rec["content"], status="queued", record_id=rid,
                              base_record_title=rec["title"])
        created.append({"record_id": rid, "task_id": task["id"], "status": task["status"]})
    return {"created": created, "existing": existing, "empty": empty}


def _pending_records_map() -> dict[str, dict]:
    """Scan the configured Base once and index pending records by record_id."""
    s = db.load_settings()
    lark = s.get("lark") or {}
    if not (lark.get("base_url_or_token") or "").strip() or not (lark.get("table_id") or "").strip():
        return {}
    try:
        rows = base_client.scan_records(s)
    except base_client.BaseClientError:
        return {}
    return {r["record_id"]: r for r in rows if r["record_id"]}


def _record_content_by_id(record_id: str) -> str:
    rec = _pending_records_map().get(record_id)
    return (rec or {}).get("content") or ""


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
def get_video(task_id: str, request: Request, username: str = Depends(require_user)) -> Response:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task["status"] != "done" or not task["output_path"]:
        raise HTTPException(status_code=404, detail="video not ready")
    path = Path(task["output_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="video file missing")
    size = path.stat().st_size
    media_type = "video/mp4"

    def _chunks(start: int, end: int):
        with path.open("rb") as fh:
            fh.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    range_header = request.headers.get("range")
    if range_header:
        match = re.match(r"bytes=(\d*)-(\d*)$", range_header)
        if match:
            start_s, end_s = match.groups()
            if start_s == "" and end_s == "":
                start, end = 0, size - 1
            elif start_s == "":
                suffix = int(end_s)
                start, end = max(0, size - suffix), size - 1
            elif end_s == "":
                start, end = int(start_s), size - 1
            else:
                start, end = int(start_s), min(int(end_s), size - 1)
            if start > end or start >= size:
                return Response(content=b"", status_code=416,
                                headers={"Content-Range": f"bytes */{size}"})
            headers = {"Content-Range": f"bytes {start}-{end}/{size}",
                       "Accept-Ranges": "bytes", "Content-Length": str(end - start + 1)}
            return StreamingResponse(_chunks(start, end), status_code=206,
                                     media_type=media_type, headers=headers)
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(size),
               "Content-Disposition": f'attachment; filename="{task_id}.mp4"'}
    return StreamingResponse(_chunks(0, size - 1), media_type=media_type, headers=headers)


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
            init = {
                "stage": stage,
                "message": stage,
                "phase_duration_s": 0.0,
                "total_elapsed_s": None,
                "stage_timings": {},
                "llm_usage": None,
            }
            yield f"data: {json.dumps(init, ensure_ascii=False)}\n\n"
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
