"""
Ranking service for the Next.js frontend.

Wraps the existing `src/` Council-of-Nine engine (no logic changes) and keeps
the full ranked result in memory so the API can serve the leaderboard, detail,
analytics, compliance, honeypots and Excel export. Ranking runs in a background
thread; the frontend polls /api/status.
"""
from __future__ import annotations

import datetime as _dt
import io
import os
import sys
import tempfile
import threading
import time
from collections import Counter, deque

import numpy as np
import pandas as pd

# make `src` importable regardless of cwd
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src import council, integrity, fairness, roles          # noqa: E402
import src.config as config                                   # noqa: E402
from src.features import build_document, compute_features      # noqa: E402
from src.reasoning import generate as gen_reason               # noqa: E402
from src.retrieve import build_retriever                       # noqa: E402
from src.score import _soft_nudge                              # noqa: E402
from src.skills_verify import verified_relevant_skills         # noqa: E402
from src.load import load_candidates                           # noqa: E402

COUNCIL_KEYS = ["semantic_seer", "name_rectifier", "evidence_scout",
                "mask_piercer", "path_reader", "terrain_master"]
COUNCIL_LABELS = {
    "semantic_seer": "Semantic Seer", "name_rectifier": "Name-Rectifier",
    "evidence_scout": "Evidence Scout", "mask_piercer": "Mask-Piercer",
    "path_reader": "Path-Reader", "terrain_master": "Terrain Master",
}

DEFAULT_FILE = os.environ.get("REDROB_CANDIDATES",
                              os.path.join(REPO_ROOT, "sample_candidates.jsonl"))

# Cross-platform, non-hardcoded upload location (overridable via env).
# Defaults to the OS temp dir so it is writable on any device/OS.
UPLOAD_DIR = os.environ.get("REDROB_UPLOAD_DIR",
                            os.path.join(tempfile.gettempdir(), "redrob_uploads"))

# ---------------------------------------------------------------------------
# In-memory state (single active ranking — this is a local single-user tool)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
STATE = {
    "status": "idle",            # idle | running | done | error
    "message": "Ready.",
    "role": None,
    "file": None,
    "file_size_mb": None,
    "ingested": 0,
    "runtime": 0.0,
    "started_at": None,
    "weights": dict(config.COUNCIL_WEIGHTS),
    "rows": [],                  # [(score, candidate, features, dec, integ), ...]
    "honeypots": [],             # [(candidate, integ), ...]
    "id_index": {},              # candidate_id -> row index
}


# ---------------------------------------------------------------------------
# Structured activity log (proof of how the system works)
# ---------------------------------------------------------------------------
LOGS: deque = deque(maxlen=800)
_seq = {"n": 0}
STAGED = {"path": None, "name": None, "size_mb": None}


def log(level: str, msg: str, source: str = "backend"):
    _seq["n"] += 1
    LOGS.append({
        "seq": _seq["n"],
        "ts": _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "level": level, "source": source, "msg": msg,
    })


def get_logs() -> list:
    return list(LOGS)


def set_staged(path: str, name: str):
    size = round(os.path.getsize(path) / 1e6, 1) if os.path.exists(path) else None
    STAGED.update(path=path, name=name, size_mb=size)
    log("info", f"Staged upload '{name}' ({size} MB) ready for ranking.")


def status() -> dict:
    s = STATE
    elapsed = (time.time() - s["started_at"]) if (s["started_at"] and s["status"] == "running") else s["runtime"]
    return {
        "status": s["status"], "message": s["message"], "role": s["role"],
        "file": os.path.basename(s["file"]) if s["file"] else None,
        "file_size_mb": s["file_size_mb"], "ingested": s["ingested"],
        "ranked": len(s["rows"]), "honeypots": len(s["honeypots"]),
        "runtime": round(elapsed, 1),
    }


# ---------------------------------------------------------------------------
# Ranking (mirrors app.rank_all — ranks the WHOLE pool, not just top 100)
# ---------------------------------------------------------------------------
def _do_rank(file_path: str, role_name: str, weights: dict, params: dict):
    try:
        t_run = time.time()
        size_mb = round(os.path.getsize(file_path) / 1e6, 1) if os.path.exists(file_path) else None
        with _lock:
            STATE.update(status="running", message="Loading candidates…",
                         role=role_name, file=file_path, rows=[], honeypots=[],
                         id_index={}, started_at=t_run, ingested=0)
            STATE["file_size_mb"] = size_mb

        log("info", "─" * 3 + " New ranking run started " + "─" * 3)
        log("info", f"Target role: '{role_name}'")
        log("info", f"Dataset: {os.path.basename(file_path)} ({size_mb} MB) · streamed from disk")

        jd = roles.get_role(role_name)

        # apply UI weights + params
        tot = sum(weights.values()) or 1.0
        config.COUNCIL_WEIGHTS = {k: float(weights.get(k, 0)) / tot for k in COUNCIL_KEYS}
        wtxt = ", ".join(f"{COUNCIL_LABELS[k]} {round(config.COUNCIL_WEIGHTS[k]*100)}%" for k in COUNCIL_KEYS)
        log("info", f"Council weights → {wtxt}")
        if params.get("yoe_ideal"):
            config.EXP_IDEAL_LOW, config.EXP_IDEAL_HIGH = map(float, params["yoe_ideal"])
        if params.get("yoe_ok"):
            config.EXP_OK_LOW, config.EXP_OK_HIGH = map(float, params["yoe_ok"])
        if params.get("notice_pref"):
            config.NOTICE_PREF_DAYS = int(params["notice_pref"])
        enable_integrity = params.get("integrity", True)
        enable_avail = params.get("availability", True)
        log("info", f"Params → ideal YOE {config.EXP_IDEAL_LOW:.0f}-{config.EXP_IDEAL_HIGH:.0f}, "
                    f"acceptable {config.EXP_OK_LOW:.0f}-{config.EXP_OK_HIGH:.0f}, "
                    f"notice ≤ {config.NOTICE_PREF_DAYS}d, "
                    f"integrity {'ON' if enable_integrity else 'OFF'}, "
                    f"availability {'ON' if enable_avail else 'OFF'}")

        t = time.time()
        candidates = load_candidates(file_path)
        log("success", f"Ingested {len(candidates):,} candidate records in {time.time()-t:.1f}s")
        with _lock:
            STATE["ingested"] = len(candidates)
            STATE["message"] = f"Building index over {len(candidates):,} profiles…"

        t = time.time()
        log("info", "Building candidate documents (headline + summary + career evidence)…")
        docs = [build_document(c) for c in candidates]
        log("info", "Fitting hybrid retriever: TF-IDF lexical + LSA dense embeddings…")
        retr = build_retriever(docs)
        _, dense, _ = retr.retrieve(jd["query_text"], shortlist_size=len(candidates))
        log("success", f"Vector index ready ({getattr(retr, 'dense_dim', '?')}-dim LSA) in {time.time()-t:.1f}s")
        lo, hi = float(dense.min()), float(dense.max())
        rng = (hi - lo) or 1.0

        with _lock:
            STATE["message"] = f"Scoring {len(candidates):,} candidates through the Council of Nine…"
        log("info", "Scoring pool through the Council of Nine (9 sub-scorers)…")
        t = time.time()
        rows, honeypots = [], []
        for i, c in enumerate(candidates):
            f = compute_features(c, jd)
            integ = integrity.check(c)
            if enable_integrity and integ[1]:
                honeypots.append((c, integ))
                continue
            dec = council.deliberate(f, (dense[i] - lo) / rng)
            im = integ[0] if enable_integrity else 1.0
            am = dec["avail_mult"] if enable_avail else 1.0
            fit = dec["core"] * im * dec["neg_mult"] * am + _soft_nudge(f)
            rows.append([max(0.0, fit), c, f, dec, integ])
        if enable_integrity:
            log("warn", f"Integrity Warden excluded {len(honeypots)} impossible honeypot profiles")
        log("success", f"Scored {len(rows):,} candidates in {time.time()-t:.1f}s")

        log("info", "Calibrating composite scores and ordering the leaderboard…")
        rows.sort(key=lambda r: (-r[0], r[1].get("candidate_id") or ""))
        raws = np.array([r[0] for r in rows], dtype=float)
        if len(raws) > 1 and raws.max() > raws.min():
            cal = 0.35 + 0.64 * (raws - raws.min()) / (raws.max() - raws.min())
        else:
            cal = np.full(len(raws), 0.8)
        for r, s in zip(rows, cal):
            r[0] = float(s)
        rows.sort(key=lambda r: (-r[0], r[1].get("candidate_id") or ""))

        runtime = round(time.time() - t_run, 1)
        with _lock:
            STATE["rows"] = rows
            STATE["honeypots"] = honeypots
            STATE["id_index"] = {r[1].get("candidate_id"): idx for idx, r in enumerate(rows)}
            STATE["weights"] = dict(config.COUNCIL_WEIGHTS)
            STATE["runtime"] = runtime
            STATE["status"] = "done"
            STATE["message"] = "Ranking complete."
        if rows:
            top = rows[0][1].get("profile", {})
            log("success", f"Top pick: {top.get('current_title','?')} "
                           f"({rows[0][1].get('candidate_id')}) · score {rows[0][0]*100:.0f}")
        log("success", f"✓ Ranking complete · {len(rows):,} ranked · {runtime}s · CPU · offline")
    except Exception as e:  # pragma: no cover
        with _lock:
            STATE["status"] = "error"
            STATE["message"] = f"{type(e).__name__}: {e}"
        log("error", f"Ranking failed: {type(e).__name__}: {e}")


def start_ranking(file_path: str, role_name: str, weights: dict, params: dict):
    if STATE["status"] == "running":
        return False
    t = threading.Thread(target=_do_rank, args=(file_path, role_name, weights, params),
                         daemon=True)
    t.start()
    return True


# ---------------------------------------------------------------------------
# Data accessors for the API
# ---------------------------------------------------------------------------
def _jd():
    return roles.get_role(STATE["role"]) if STATE["role"] else roles.get_role(roles.role_names()[0])


def summary() -> dict:
    rows = STATE["rows"]
    n = len(rows)
    strong = sum(1 for r in rows if r[0] * 100 >= 85)
    notice = (sum(1 for r in rows[:100] if r[2]["notice_days"] <= config.NOTICE_PREF_DAYS)
              / max(1, min(100, n))) * 100 if n else 0
    weights_pct = [{"key": k, "label": COUNCIL_LABELS[k],
                    "pct": round(STATE["weights"].get(k, 0) * 100)} for k in COUNCIL_KEYS]
    return {
        "ranked": n, "ingested": STATE["ingested"],
        "strong_matches": strong, "honeypots": len(STATE["honeypots"]),
        "notice_pct": round(notice), "runtime": STATE["runtime"],
        "role": STATE["role"], "file": os.path.basename(STATE["file"]) if STATE["file"] else None,
        "file_size_mb": STATE["file_size_mb"],
        "weights": weights_pct,
    }


def _row_brief(score, c, f, dec, rank):
    p = c.get("profile", {})
    yoe = p.get("years_of_experience")
    return {
        "rank": rank, "candidate_id": c.get("candidate_id"),
        "score": round(float(score) * 100, 1),
        "title": p.get("current_title", "—"),
        "company": p.get("current_company", ""),
        "yoe": float(yoe) if yoe is not None else None,
        "location": p.get("location", ""), "country": p.get("country", ""),
        "council": {k: round(float(dec["parts"][k]), 3) for k in COUNCIL_KEYS},
        "verified_title": bool(f["cur_title_pos"]),
        "product": f["product_ratio"] > 0.5,
        "location_match": bool(f["location_match"]),
        "active": f["days_inactive"] <= 30,
        "notice_days": int(f["notice_days"]),
    }


def leaderboard(page: int = 1, size: int = 100, query: str = "") -> dict:
    rows = STATE["rows"]
    if query:
        q = query.lower()
        idxs = [i for i, r in enumerate(rows)
                if q in (r[1].get("candidate_id", "").lower())
                or q in (r[1].get("profile", {}).get("current_title", "").lower())]
    else:
        idxs = range(len(rows))
    idxs = list(idxs)
    total = len(idxs)
    start = (page - 1) * size
    page_idxs = idxs[start:start + size]
    items = [_row_brief(rows[i][0], rows[i][1], rows[i][2], rows[i][3], i + 1)
             for i in page_idxs]
    return {"items": items, "total": total, "page": page, "size": size,
            "pages": max(1, (total + size - 1) // size)}


def detail(candidate_id: str) -> dict | None:
    idx = STATE["id_index"].get(candidate_id)
    if idx is None:
        return None
    score, c, f, dec, integ = STATE["rows"][idx]
    jd = _jd()
    p = c.get("profile", {})
    return {
        **_row_brief(score, c, f, dec, idx + 1),
        "summary": p.get("summary", ""),
        "reasoning": gen_reason(c, f, dec, integ, score, idx + 1, jd),
        "rationales": {COUNCIL_LABELS.get(k, k): v for k, v in dec["rationales"].items()},
        "verified_skills": verified_relevant_skills(c, jd, top=14),
        "all_skills": [s.get("name") for s in c.get("skills", [])],
        "education": [
            {"degree": e.get("degree"), "field": e.get("field_of_study"),
             "institution": e.get("institution"), "tier": e.get("tier")}
            for e in c.get("education", [])],
        "career": [
            {"title": r.get("title"), "company": r.get("company"),
             "months": r.get("duration_months"), "start": r.get("start_date"),
             "end": r.get("end_date") or "Present", "description": r.get("description")}
            for r in c.get("career_history", [])],
    }


def analytics() -> dict:
    rows = STATE["rows"]
    if not rows:
        return {}
    scores = np.array([r[0] * 100 for r in rows])
    yoe = np.array([float(r[2]["yoe"] or 0) for r in rows])
    sh, sb = np.histogram(scores, bins=10, range=(35, 100))
    yh, yb = np.histogram(yoe, bins=8, range=(0, 16))
    prod = sum(1 for r in rows if r[2]["product_ratio"] > 0.5)
    serv = sum(1 for r in rows if r[2]["services_only"])
    avg = {k: float(np.mean([r[3]["parts"][k] for r in rows])) for k in COUNCIL_KEYS}
    return {
        "score_hist": [{"bucket": f"{int(sb[i])}–{int(sb[i+1])}", "count": int(sh[i])}
                       for i in range(len(sh))],
        "yoe_hist": [{"bucket": f"{int(yb[i])}–{int(yb[i+1])}", "count": int(yh[i])}
                     for i in range(len(yh))],
        "company": {"product": prod, "services": serv, "mixed": len(rows) - prod - serv},
        "council_avg": [{"key": k, "label": COUNCIL_LABELS[k], "avg": round(avg[k], 3)}
                        for k in COUNCIL_KEYS],
    }


def compliance() -> dict:
    rows = STATE["rows"]
    if not rows:
        return {}
    candidates = [r[1] for r in rows] + [h[0] for h in STATE["honeypots"]]
    sel = list(range(min(100, len(rows))))
    fair = fairness.audit(candidates, sel)
    return {
        "fairness": fair,
        "audit": {
            "system": "Redrob Ranker v2.0 (Council of Nine)",
            "target_role": STATE["role"],
            "eu_ai_act_classification": "high-risk (Annex III, employment)",
            "n_candidates_scored": STATE["ingested"],
            "n_ranked": len(rows),
            "honeypots_detected": len(STATE["honeypots"]),
            "council_weights": STATE["weights"],
            "human_oversight": "Ranks are RECOMMENDATIONS; final hiring decisions "
                               "require human review (Article 14).",
        },
    }


def honeypots(limit: int = 200) -> dict:
    out = []
    for c, integ in STATE["honeypots"][:limit]:
        p = c.get("profile", {})
        out.append({"candidate_id": c.get("candidate_id"),
                    "title": p.get("current_title", "—"),
                    "reasons": integ[2]})
    return {"items": out, "total": len(STATE["honeypots"])}


def job_intent() -> dict:
    jd = _jd()
    return {
        "role_title": jd.get("role_title", STATE["role"]),
        "must_have": jd.get("must_have_capabilities", []),
        "nice_to_have": jd.get("nice_to_have", []),
        "positive_titles": jd.get("positive_titles", []),
        "negative_titles": jd.get("negative_titles", []),
        "product_industries": jd.get("product_industries", []),
        "services_companies": jd.get("services_companies", []),
        "query_text": jd.get("query_text", ""),
    }


def export_excel(n: int) -> bytes:
    rows = STATE["rows"][:n]
    jd = _jd()
    recs = []
    for rank, (score, c, f, dec, integ) in enumerate(rows, 1):
        p = c.get("profile", {})
        recs.append({
            "rank": rank, "candidate_id": c.get("candidate_id"),
            "score": round(score * 100, 1), "current_title": p.get("current_title"),
            "years_experience": p.get("years_of_experience"),
            "location": p.get("location"), "country": p.get("country"),
            "current_company": p.get("current_company"),
            "verified_relevant_skills": ", ".join(verified_relevant_skills(c, jd, top=8)),
            **{k: round(dec["parts"][k], 3) for k in COUNCIL_KEYS},
            "notice_days": int(f["notice_days"]),
            "reasoning": gen_reason(c, f, dec, integ, score, rank, jd),
        })
    df = pd.DataFrame(recs)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Ranked Candidates")
        ws = w.sheets["Ranked Candidates"]
        for col in ws.columns:
            length = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(length + 2, 60)
    return buf.getvalue()
