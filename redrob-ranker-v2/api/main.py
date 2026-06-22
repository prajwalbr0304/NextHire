"""
FastAPI backend for THE AI RECRUITING BRAIN — Council edition.

Exposes the Council-of-Nine ranking engine to the Next.js frontend.
Run:  uvicorn api.main:app --port 8000   (from the redrob-ranker-v2 root)
"""
from __future__ import annotations

import os
import sys
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src import roles                       # noqa: E402
from api import ranker                      # noqa: E402

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
    """Drag-and-drop upload: save the file and mark it for the next ranking."""
    name = file.filename or "upload.jsonl"
    suffix = ".jsonl" if name.lower().endswith("l") else ".json"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    data = await file.read()
    tmp.write(data)
    tmp.close()
    ranker.set_staged(tmp.name, name)
    return {"filename": name, "size_mb": round(len(data) / 1e6, 1)}


@app.get("/api/logs")
def get_logs():
    return {"logs": ranker.get_logs()}


@app.get("/api/status")
def get_status():
    return ranker.status()


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
