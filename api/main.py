"""
FastAPI backend for THE AI RECRUITING BRAIN — Council edition.

Exposes the Council-of-Nine ranking engine to the Next.js frontend.
Run:  uvicorn api.main:app --port 8000   (from the NextHire root)
"""
from __future__ import annotations

import os
import shutil
import sys

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src import roles                       # noqa: E402
from api import ranker                      # noqa: E402
from api import nextai                      # noqa: E402

app = FastAPI(title="Redrob Ranker API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class RankRequest(BaseModel):
    file_path: str | None = None
    role: str
    weights: dict | None = None
    yoe_ideal: list | None = None
    yoe_ok: list | None = None
    notice_pref: int | None = None
    integrity: bool = True
    availability: bool = True


def _params(req: RankRequest) -> dict:
    return {"yoe_ideal": req.yoe_ideal, "yoe_ok": req.yoe_ok,
            "notice_pref": req.notice_pref, "integrity": req.integrity,
            "availability": req.availability}


DEFAULT_WEIGHTS = {"semantic_seer": 0.16, "name_rectifier": 0.20,
                   "evidence_scout": 0.22, "mask_piercer": 0.14,
                   "path_reader": 0.12, "terrain_master": 0.16}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/roles")
def get_roles():
    return {"roles": roles.role_names(), "default_file": ranker.DEFAULT_FILE,
            "default_file_exists": os.path.exists(ranker.DEFAULT_FILE)}


@app.post("/api/rank")
def rank(req: RankRequest):
    path = req.file_path or ranker.STAGED.get("path") or ranker.DEFAULT_FILE
    if not path or not os.path.exists(path):
        raise HTTPException(400, f"File not found: {path}")
    weights = req.weights or DEFAULT_WEIGHTS
    ok = ranker.start_ranking(path, req.role, weights, _params(req))
    if not ok:
        raise HTTPException(409, "A ranking is already running.")
    return {"started": True}


@app.post("/api/stage")
async def stage(file: UploadFile = File(...)):
    """Drag-and-drop upload: stream the file to a writable, cross-platform
    location (chunked, so even a 500 MB pool never loads fully into RAM) and
    mark it for the next ranking. No hardcoded paths — uses ranker.UPLOAD_DIR
    (OS temp dir by default, overridable via REDROB_UPLOAD_DIR)."""
    name = os.path.basename(file.filename or "upload.jsonl")
    ext = ".jsonl" if name.lower().endswith(".jsonl") else ".json"
    dest = None
    try:
        os.makedirs(ranker.UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(ranker.UPLOAD_DIR, "staged" + ext)
        # stream in 1 MB chunks — memory-safe for very large files
        with open(dest, "wb") as out:
            shutil.copyfileobj(file.file, out, length=1024 * 1024)
        size = os.path.getsize(dest)
        if size == 0:
            raise ValueError("uploaded file is empty")
        ranker.set_staged(dest, name)
        return {"filename": name, "size_mb": round(size / 1e6, 1)}
    except Exception as e:
        if dest and os.path.exists(dest):
            try:
                os.unlink(dest)
            except OSError:
                pass
        ranker.log("error", f"Upload failed for '{name}': {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {type(e).__name__}: {e}")
    finally:
        try:
            await file.close()
        except Exception:
            pass


@app.get("/api/logs")
def get_logs():
    return {"logs": ranker.get_logs()}


@app.get("/api/status")
def get_status():
    return ranker.status()


@app.get("/api/staged")
def get_staged():
    return ranker.staged()


@app.get("/api/summary")
def get_summary():
    return ranker.summary()


@app.get("/api/leaderboard")
def get_leaderboard(page: int = 1, size: int = 100, q: str = ""):
    return ranker.leaderboard(page=page, size=size, query=q)


@app.get("/api/candidate/{candidate_id}")
def get_candidate(candidate_id: str):
    d = ranker.detail(candidate_id)
    if d is None:
        raise HTTPException(404, "Candidate not found in current ranking.")
    return d


@app.get("/api/analytics")
def get_analytics():
    return ranker.analytics()


@app.get("/api/compliance")
def get_compliance():
    return ranker.compliance()


@app.get("/api/honeypots")
def get_honeypots(limit: int = 200):
    return ranker.honeypots(limit=limit)


@app.get("/api/job-intent")
def get_job_intent():
    return ranker.job_intent()


@app.get("/api/export")
def export(n: int = Query(100, ge=1)):
    data = ranker.export_excel(n)
    ranker.log("success", f"Exported top {n} candidates to Excel ({round(len(data)/1024)} KB)")
    role = (ranker.STATE.get("role") or "candidates").split()[0].lower()
    fname = f"ranked_{role}_{n}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ---------------------------------------------------------------------------
# Tasks & shortlists (Supabase-backed — Pipeline page)
# ---------------------------------------------------------------------------
class ShortlistCreate(BaseModel):
    task_id: str
    name: str


class MemberCreate(BaseModel):
    candidate_id: str
    rank: int | None = None
    score: float | None = None
    current_title: str | None = None
    current_company: str | None = None
    years_experience: float | None = None
    task_id: str | None = None


@app.get("/api/db-status")
def db_status():
    return ranker.db_status()


@app.get("/api/tasks")
def list_tasks():
    return ranker.list_tasks()


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    t = ranker.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found.")
    return t


@app.get("/api/tasks/{task_id}/candidates")
def get_task_candidates(task_id: str, category: str = "top200", limit: int = 200):
    return ranker.get_task_candidates(task_id, category=category, limit=limit)


@app.get("/api/tasks/{task_id}/shortlists")
def list_shortlists(task_id: str):
    return ranker.list_shortlists(task_id)


@app.post("/api/shortlists")
def create_shortlist(req: ShortlistCreate):
    if not ranker.db_status().get("enabled"):
        raise HTTPException(400, "Supabase is not configured.")
    return ranker.create_shortlist(req.task_id, req.name)


@app.delete("/api/shortlists/{shortlist_id}")
def delete_shortlist(shortlist_id: str):
    return ranker.delete_shortlist(shortlist_id)


@app.post("/api/shortlists/{shortlist_id}/members")
def add_member(shortlist_id: str, req: MemberCreate):
    if not ranker.db_status().get("enabled"):
        raise HTTPException(400, "Supabase is not configured.")
    return ranker.add_shortlist_member(shortlist_id, req.model_dump(exclude_none=True))


@app.delete("/api/shortlist-members/{member_id}")
def remove_member(member_id: int):
    return ranker.remove_shortlist_member(member_id)


# ---------------------------------------------------------------------------
# NextAI assistant
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    history: list | None = None


@app.get("/api/nextai/status")
def nextai_status():
    return nextai.status()


@app.post("/api/nextai/chat")
def nextai_chat(req: ChatRequest):
    context = ranker.nextai_context(top=25)
    return nextai.chat(req.question, req.history or [], context)


# ---------------------------------------------------------------------------
# Static frontend (production / single-container deployment)
# ---------------------------------------------------------------------------
# When the Next.js app has been statically exported to ``web_out/`` (done in
# Dockerfile.web), serve it from FastAPI so the entire app runs as ONE process
# on ONE port. Mounted LAST so every /api/* route above keeps precedence. In
# local dev this directory does not exist, so nothing changes.
_WEB_OUT = os.path.join(REPO_ROOT, "web_out")
if os.path.isdir(_WEB_OUT):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_WEB_OUT, html=True), name="web")
