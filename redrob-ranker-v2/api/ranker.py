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
import uuid
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
from src.score import _soft_nudge, finalize_ranking           # noqa: E402
from src.skills_verify import verified_relevant_skills         # noqa: E402
from src.load import load_candidates                           # noqa: E402
from api import supabase_store                                 # noqa: E402

COUNCIL_KEYS = ["semantic_seer", "name_rectifier", "evidence_scout",
                "mask_piercer", "path_reader", "terrain_master"]
COUNCIL_LABELS = {
    "semantic_seer": "Role-Signal Alignment", "name_rectifier": "Title Calibration Index",
    "evidence_scout": "Delivery Velocity", "mask_piercer": "Declared vs. Demonstrated Skill",
    "path_reader": "Tenure & Progression Depth", "terrain_master": "Domain Density",
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
    "params": {},                # ranking params used (yoe bands, notice, toggles)
    "rows": [],                  # [(score, candidate, features, dec, integ), ...]
    "honeypots": [],             # [(candidate, integ), ...]
    "id_index": {},              # candidate_id -> row index
    "task_id": None,             # unique id for the current ranking run
    "task_name": None,           # human-friendly label
    "persisted": False,          # whether this run was saved to Supabase
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


# Let the Supabase client write into the same activity log.
supabase_store.set_logger(log)


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
        "task_id": s["task_id"], "task_name": s["task_name"],
        "persisted": s["persisted"],
    }


# ---------------------------------------------------------------------------
# Get staged file info (for frontend state persistence on refresh)
# ---------------------------------------------------------------------------
def staged() -> dict:
    return {
        "name": STAGED.get("name"),
        "size_mb": STAGED.get("size_mb"),
        "path": STAGED.get("path"),
    }



# ---------------------------------------------------------------------------
# Ranking (mirrors app.rank_all — ranks the WHOLE pool, not just top 100)
# ---------------------------------------------------------------------------
def _do_rank(file_path: str, role_name: str, weights: dict, params: dict):
    try:
        t_run = time.time()
        size_mb = round(os.path.getsize(file_path) / 1e6, 1) if os.path.exists(file_path) else None
        task_id = "t_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        task_name = f"{role_name} · {_dt.datetime.now().strftime('%b %d, %H:%M')}"
        with _lock:
            STATE.update(status="running", message="Loading candidates…",
                         role=role_name, file=file_path, rows=[], honeypots=[],
                         id_index={}, started_at=t_run, ingested=0,
                         task_id=task_id, task_name=task_name, persisted=False,
                         params=dict(params or {}))
            STATE["file_size_mb"] = size_mb

        log("info", "─" * 3 + " New ranking run started " + "─" * 3)
        log("info", f"Task ID: {task_id}")
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
        enable_disq = params.get("disqualifiers", True)
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
            dq = dec["disqualifier_mult"] if enable_disq else 1.0
            fit = dec["core"] * im * dec["neg_mult"] * dq * am + _soft_nudge(f)
            rows.append([max(0.0, fit), c, f, dec, integ])
        if enable_integrity:
            log("warn", f"Integrity Warden excluded {len(honeypots)} impossible honeypot profiles")
        log("success", f"Scored {len(rows):,} candidates in {time.time()-t:.1f}s")

        log("info", "Re-ranking the head and applying 3-band tier calibration…")
        # Reuse the EXACT submission-path final stage (two-stage re-rank + 3-band
        # tier calibration) so the dashboard ordering matches rank.py exactly.
        _scored = [{"raw": r[0], "candidate": r[1], "f": r[2], "dec": r[3],
                    "integ": r[4], "candidate_id": r[1].get("candidate_id") or ""}
                   for r in rows]
        _ranked = finalize_ranking(_scored, jd, top_n=None, verbose=False)
        rows = [[rr["score"], rr["candidate"], rr["f"], rr["dec"], rr["integ"]]
                for rr in _ranked]

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

        # Persist this run to Supabase (best-effort; never blocks the result).
        _persist_run(task_id, task_name)
    except Exception as e:  # pragma: no cover
        with _lock:
            STATE["status"] = "error"
            STATE["message"] = f"{type(e).__name__}: {e}"
        log("error", f"Ranking failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Persist a completed ranking to Supabase (task + top200 / shortlisted / honeypot)
# ---------------------------------------------------------------------------
def _store_row(rank: int, score: float, c: dict, f: dict, dec: dict, integ, jd: dict) -> dict:
    p = c.get("profile", {}) or {}
    yoe = p.get("years_of_experience")
    return {
        "rank": rank,
        "candidate_id": c.get("candidate_id"),
        "score": round(float(score) * 100, 1),
        "current_title": p.get("current_title"),
        "current_company": p.get("current_company"),
        "years_experience": float(yoe) if yoe is not None else None,
        "location": p.get("location"),
        "country": p.get("country"),
        "verified_skills": ", ".join(verified_relevant_skills(c, jd, top=8)),
        "council": {k: round(float(dec["parts"][k]), 3) for k in COUNCIL_KEYS},
        "notice_days": int(f["notice_days"]),
        "reasoning": gen_reason(c, f, dec, integ, score, rank, jd),
    }


def _persist_run(task_id: str, task_name: str) -> None:
    if not supabase_store.enabled():
        log("info", "Supabase not configured — skipping cloud persistence "
                    "(run supabase_schema.sql and set .env to enable).")
        return
    try:
        rows = STATE["rows"]
        jd = _jd()
        strong = sum(1 for r in rows if r[0] * 100 >= 85)
        meta = {
            "task_id": task_id,
            "name": task_name,
            "role": STATE["role"],
            "file_name": os.path.basename(STATE["file"]) if STATE["file"] else None,
            "file_size_mb": STATE["file_size_mb"],
            "ingested": STATE["ingested"],
            "ranked": len(rows),
            "honeypots": len(STATE["honeypots"]),
            "strong_matches": strong,
            "runtime": STATE["runtime"],
            "weights": STATE["weights"],
            "params": STATE.get("params", {}),
        }
        top200 = [_store_row(i + 1, r[0], r[1], r[2], r[3], r[4], jd)
                  for i, r in enumerate(rows[:200])]
        shortlisted = [_store_row(i + 1, r[0], r[1], r[2], r[3], r[4], jd)
                       for i, r in enumerate(rows) if r[0] * 100 >= 85][:200]
        honey = []
        for hp_rank, (c, integ) in enumerate(STATE["honeypots"][:200], 1):
            p = c.get("profile", {}) or {}
            honey.append({
                "rank": hp_rank,
                "candidate_id": c.get("candidate_id"),
                "score": 0,
                "current_title": p.get("current_title"),
                "current_company": p.get("current_company"),
                "years_experience": p.get("years_of_experience"),
                "location": p.get("location"),
                "country": p.get("country"),
                "verified_skills": None,
                "council": None,
                "notice_days": None,
                "reasoning": "; ".join(integ[2]) if integ and len(integ) > 2 else None,
            })
        res = supabase_store.save_ranking(meta, top200, shortlisted, honey)
        if res.get("ok"):
            with _lock:
                STATE["persisted"] = True
    except Exception as e:  # pragma: no cover
        log("error", f"Supabase persistence error: {type(e).__name__}: {e}")


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


def _candidate_insights(c: dict, f: dict, dec: dict, integ, score: float, jd: dict) -> dict:
    """Derive recruiter-facing insight sections from the real scoring features.

    Everything here is grounded in computed signals (no hallucination): council
    parts/rationales, integrity flags, JD must-haves and title intent.
    """
    p = c.get("profile", {}) or {}
    parts = dec.get("parts", {}) or {}
    rats = dec.get("rationales", {}) or {}
    weights = STATE.get("weights") or dict(config.COUNCIL_WEIGHTS)
    yoe = float(f.get("yoe") or 0.0)
    skill_names = [(s.get("name") or "").lower() for s in (c.get("skills") or [])]

    def _skill_covers(term: str) -> bool:
        t = term.lower()
        return any(t in sn or sn in t for sn in skill_names if sn)

    # ---- weighted score breakdown (council contributions) ----
    breakdown = []
    for k in COUNCIL_KEYS:
        part = float(parts.get(k, 0.0))
        w = float(weights.get(k, 0.0))
        breakdown.append({
            "key": k, "label": COUNCIL_LABELS.get(k, k),
            "score": round(part * 100), "weight": round(w * 100),
            "points": round(part * w * 100, 1),
        })

    # ---- strengths (highest signals + positive flags) ----
    strengths: list[dict] = []
    for k, v in sorted(parts.items(), key=lambda kv: -kv[1]):
        if v >= 0.6:
            strengths.append({"label": COUNCIL_LABELS.get(k, k),
                              "detail": rats.get(k) or f"Scores {v*100:.0f}/100 on this dimension."})
    if f.get("cur_title_pos"):
        strengths.append({"label": "On-track job title",
                          "detail": f"Current title “{p.get('current_title','')}” matches the target role family."})
    if f.get("product_ratio", 0) > 0.5:
        strengths.append({"label": "Product-company pedigree",
                          "detail": "Most experience is at product (vs. services) companies."})
    if f.get("evidence_hits", 0) >= 3:
        strengths.append({"label": "Demonstrated delivery",
                          "detail": f"{int(f['evidence_hits'])} concrete build/ship signals found in role descriptions."})
    if f.get("relevant_skill_count", 0) >= 3:
        strengths.append({"label": "Verified relevant skills",
                          "detail": f"{int(f['relevant_skill_count'])} role-relevant skills backed by usage/endorsements."})
    if f.get("location_match"):
        strengths.append({"label": "Location fit", "detail": "Based in a preferred hiring region."})
    if f.get("days_inactive", 999) <= 30:
        strengths.append({"label": "Actively engaged",
                          "detail": f"Active within the last {int(f['days_inactive'])} days."})
    if f.get("notice_days", 90) <= 30:
        strengths.append({"label": "Quick availability",
                          "detail": f"Short notice period (~{int(f['notice_days'])} days)."})

    # ---- weaknesses (lowest signals + honest concerns) ----
    weaknesses: list[dict] = []
    for k, v in sorted(parts.items(), key=lambda kv: kv[1]):
        if v < 0.4:
            weaknesses.append({"label": COUNCIL_LABELS.get(k, k),
                              "detail": rats.get(k) or f"Low signal ({v*100:.0f}/100) on this dimension."})
    if f.get("cur_title_neg"):
        weaknesses.append({"label": "Off-track current title",
                          "detail": "Current role title sits outside the target track."})
    if f.get("services_only"):
        weaknesses.append({"label": "Services-only background",
                          "detail": "Career concentrated in services/consulting firms."})
    if f.get("avg_tenure_months") and f["avg_tenure_months"] < 18 and f.get("n_roles", 0) > 1:
        weaknesses.append({"label": "Short tenures",
                          "detail": f"Average tenure ~{f['avg_tenure_months']:.0f} months across {int(f['n_roles'])} roles."})
    if f.get("response_rate", 1) < 0.2:
        weaknesses.append({"label": "Low recruiter response",
                          "detail": f"Responds to ~{f['response_rate']*100:.0f}% of recruiter outreach."})

    # ---- risk factors + composite risk score ----
    risk_factors: list[dict] = []
    integ_score = float(integ[0]) if integ else 1.0
    is_honeypot = bool(integ[1]) if integ and len(integ) > 1 else False
    for r in (integ[2] if integ and len(integ) > 2 else []):
        risk_factors.append({"label": r, "severity": "high" if is_honeypot else "medium"})
    if f.get("expert_zero_dur", 0) >= 1:
        risk_factors.append({"label": f"{int(f['expert_zero_dur'])} ‘expert’ skills with no recorded usage", "severity": "medium"})
    if f.get("services_only"):
        risk_factors.append({"label": "Services-only company history", "severity": "low"})
    if f.get("days_inactive", 0) > 120:
        risk_factors.append({"label": f"Profile inactive ~{int(f['days_inactive'])} days", "severity": "medium"})
    if f.get("notice_days", 0) > 60:
        risk_factors.append({"label": f"Long notice period (~{int(f['notice_days'])} days)", "severity": "low"})
    if not f.get("verified_email") and not f.get("verified_phone"):
        risk_factors.append({"label": "Contact details unverified", "severity": "low"})
    if f.get("avg_tenure_months") and f["avg_tenure_months"] < 12 and f.get("n_roles", 0) > 2:
        risk_factors.append({"label": "Frequent job changes", "severity": "medium"})

    sev_pts = {"low": 8, "medium": 18, "high": 34}
    risk_points = sum(sev_pts.get(rf["severity"], 10) for rf in risk_factors)
    risk_points += round((1.0 - integ_score) * 40)
    risk_score = max(0, min(100, risk_points))
    risk_level = "high" if risk_score >= 55 else "medium" if risk_score >= 25 else "low"
    if not risk_factors:
        risk_factors.append({"label": "No material risk signals detected", "severity": "low"})

    # ---- missing qualifications + must-have coverage ----
    musts = [m for m in jd.get("must_have_capabilities", []) if m]
    covered = [m for m in musts if _skill_covers(m)]
    missing_caps = [m for m in musts if m not in covered]
    missing: list[dict] = []
    exp = jd.get("experience", {}) or {}
    req_low = exp.get("required_low")
    if req_low is not None and yoe < req_low:
        missing.append({"label": f"Experience below role minimum ({yoe:.0f}y vs {req_low}y)", "kind": "experience"})
    if f.get("relevant_skill_count", 0) == 0:
        missing.append({"label": "No verified role-relevant skills", "kind": "skill"})
    for m in missing_caps[:8]:
        missing.append({"label": m, "kind": "skill"})
    coverage_pct = round(len(covered) / (len(musts) or 1) * 100)

    # ---- similar role match (other roles this profile fits) ----
    all_titles = [(p.get("current_title") or "").lower()] + \
                 [(r.get("title") or "").lower() for r in (c.get("career_history") or [])]
    cur_role = STATE.get("role")
    similar: list[dict] = []
    for name in roles.role_names():
        if name == cur_role:
            continue
        rj = roles.get_role(name)
        rmust = [m.lower() for m in rj.get("must_have_capabilities", [])]
        pos = [t.lower() for t in rj.get("positive_titles", [])]
        title_hit = any(any(t in title for t in pos) for title in all_titles if title)
        cov = (sum(1 for m in rmust if _skill_covers(m)) / len(rmust)) if rmust else 0.0
        match = 0.65 * cov + (0.35 if title_hit else 0.0)
        similar.append({"role": rj.get("role_title", name), "match": round(match * 100)})
    similar.sort(key=lambda x: -x["match"])

    return {
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:6],
        "risk": {"score": risk_score, "level": risk_level, "factors": risk_factors[:6]},
        "missing_qualifications": missing[:10],
        "must_have_coverage": coverage_pct,
        "must_have_total": len(musts),
        "must_have_covered": len(covered),
        "score_breakdown": breakdown,
        "similar_roles": similar[:4],
    }


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
        **_candidate_insights(c, f, dec, integ, score, jd),
    }


_PROF_LEVELS = ["beginner", "intermediate", "advanced", "expert"]
_PROF_LABELS = {"beginner": "Beginner", "intermediate": "Intermediate",
                "advanced": "Advanced", "expert": "Expert"}


def analytics() -> dict:
    rows = STATE["rows"]
    if not rows:
        return {}
    n = len(rows)
    scores = np.array([r[0] * 100 for r in rows])
    yoe = np.array([float(r[2]["yoe"] or 0) for r in rows])
    sh, sb = np.histogram(scores, bins=10, range=(35, 100))
    yh, yb = np.histogram(yoe, bins=8, range=(0, 16))
    prod = sum(1 for r in rows if r[2]["product_ratio"] > 0.5)
    serv = sum(1 for r in rows if r[2]["services_only"])
    avg = {k: float(np.mean([r[3]["parts"][k] for r in rows])) for k in COUNCIL_KEYS}

    # --- skills: frequency + proficiency heatmap -------------------------------
    skill_counts: Counter = Counter()
    skill_verified: Counter = Counter()
    skill_prof: dict[str, Counter] = {}
    deg_counts: Counter = Counter()
    field_counts: Counter = Counter()
    tier_counts: Counter = Counter()
    loc_counts: Counter = Counter()
    for _, c, _f, _dec, _ in rows:
        for s in (c.get("skills") or []):
            name = (s.get("name") or "").strip()
            if not name:
                continue
            skill_counts[name] += 1
            prof = (s.get("proficiency") or "").lower()
            if prof in _PROF_LEVELS:
                skill_prof.setdefault(name, Counter())[prof] += 1
            endo = float(s.get("endorsements") or 0)
            dur = float(s.get("duration_months") or 0)
            if endo > 0 or dur > 0:
                skill_verified[name] += 1
        for e in (c.get("education") or []):
            deg = (e.get("degree") or "").strip()
            fld = (e.get("field_of_study") or "").strip()
            tier = (e.get("tier") or "unknown").strip() or "unknown"
            if deg:
                deg_counts[deg] += 1
            if fld:
                field_counts[fld] += 1
            tier_counts[tier] += 1
        p = c.get("profile", {}) or {}
        loc = (p.get("location") or p.get("country") or "").strip()
        if loc:
            loc_counts[loc] += 1

    top_skill_names = [name for name, _ in skill_counts.most_common(15)]
    top_skills = [{"name": name, "count": skill_counts[name],
                   "verified": skill_verified.get(name, 0)} for name in top_skill_names]
    heat_names = top_skill_names[:10]
    heatmap = {
        "skills": heat_names,
        "levels": [_PROF_LABELS[l] for l in _PROF_LEVELS],
        "matrix": [[skill_prof.get(name, Counter()).get(lvl, 0) for lvl in _PROF_LEVELS]
                   for name in heat_names],
    }

    # --- tiers (quality bands) -------------------------------------------------
    elite = int((scores >= 90).sum())
    strong = int(((scores >= 80) & (scores < 90)).sum())
    moderate = int(((scores >= 65) & (scores < 80)).sum())
    weak = int((scores < 65).sum())

    # --- funnel ----------------------------------------------------------------
    strong_total = int((scores >= 85).sum())
    funnel = [
        {"stage": "Ingested", "count": STATE["ingested"]},
        {"stage": "Passed integrity", "count": n},
        {"stage": "Strong (≥85)", "count": strong_total},
        {"stage": "Top 100", "count": min(100, n)},
        {"stage": "Top 10", "count": min(10, n)},
    ]

    return {
        "score_hist": [{"bucket": f"{int(sb[i])}–{int(sb[i+1])}", "count": int(sh[i])}
                       for i in range(len(sh))],
        "yoe_hist": [{"bucket": f"{int(yb[i])}–{int(yb[i+1])}", "count": int(yh[i])}
                     for i in range(len(yh))],
        "company": {"product": prod, "services": serv, "mixed": n - prod - serv},
        "council_avg": [{"key": k, "label": COUNCIL_LABELS[k], "avg": round(avg[k], 3)}
                        for k in COUNCIL_KEYS],
        "top_skills": top_skills,
        "skills_heatmap": heatmap,
        "education": {
            "degrees": [{"label": k, "count": v} for k, v in deg_counts.most_common(6)],
            "fields": [{"label": k, "count": v} for k, v in field_counts.most_common(8)],
            "tiers": [{"label": k, "count": v} for k, v in tier_counts.most_common(6)],
        },
        "tiers": [
            {"label": "Elite (90+)", "count": elite},
            {"label": "Strong (80–90)", "count": strong},
            {"label": "Moderate (65–80)", "count": moderate},
            {"label": "Weak (<65)", "count": weak},
        ],
        "funnel": funnel,
        "locations": [{"label": k, "count": v} for k, v in loc_counts.most_common(8)],
    }


COUNCIL_DESC = {
    "semantic_seer": "Dense semantic similarity between the role's query and the candidate's evidence text.",
    "name_rectifier": "Whether current/past job titles genuinely match the target role (anti title-inflation).",
    "evidence_scout": "Concrete 'built/shipped a system' evidence mined from career descriptions.",
    "mask_piercer": "Verified skill-trust — endorsements & real usage temper self-declared skills.",
    "path_reader": "Experience-band fit plus tenure stability (penalises chronic job-hopping).",
    "terrain_master": "Product-vs-services background and domain (NLP/IR) proximity.",
}


def _fairness_metrics(rows, fair) -> dict:
    """Augment the disparate-impact audit with score gaps + per-group means."""
    sel_n = min(100, len(rows))
    metrics: dict = {}
    for attr, rep in fair.items():
        # mean composite score per group across the ranked pool
        group_scores: dict[str, list] = {}
        for score, c, *_ in rows:
            g = fairness._group_keys(c).get(attr, "unknown")
            group_scores.setdefault(g, []).append(score * 100)
        groups = {}
        for g, info in rep["groups"].items():
            ss = group_scores.get(g, [])
            groups[g] = {
                **info,
                "n_pool": len(ss),
                "avg_score": round(float(np.mean(ss)), 1) if ss else 0.0,
            }
        rates = [v["selection_rate"] for v in rep["groups"].values() if v["selection_rate"] > 0]
        spd = round(max(rates) - min(rates), 4) if len(rates) >= 2 else 0.0
        avgs = [v["avg_score"] for v in groups.values() if v["n_pool"] >= 5]
        score_gap = round(max(avgs) - min(avgs), 1) if len(avgs) >= 2 else 0.0
        metrics[attr] = {
            "disparate_impact_ratio": rep["disparate_impact_ratio"],
            "passes_four_fifths": rep["passes_four_fifths"],
            "statistical_parity_diff": spd,
            "score_gap": score_gap,
            "selected_n": sel_n,
            "groups": groups,
        }
    return metrics


def _bias_flags(metrics) -> list:
    flags = []
    pretty = {"region": "Region", "institution_tier": "Institution tier"}
    for attr, m in metrics.items():
        label = pretty.get(attr, attr)
        if not m["passes_four_fifths"]:
            flags.append({
                "attribute": label,
                "severity": "high" if m["disparate_impact_ratio"] < 0.6 else "medium",
                "metric": "Disparate impact (4/5ths rule)",
                "value": m["disparate_impact_ratio"],
                "message": f"{label}: disparate-impact ratio {m['disparate_impact_ratio']} "
                           f"is below the 0.80 legal threshold — selection rates differ materially across groups.",
            })
        if m["score_gap"] >= 12:
            flags.append({
                "attribute": label,
                "severity": "medium",
                "metric": "Mean score gap",
                "value": m["score_gap"],
                "message": f"{label}: a {m['score_gap']}-point average score gap exists between "
                           f"the strongest and weakest represented groups — review for proxy bias.",
            })
    return flags


def compliance() -> dict:
    rows = STATE["rows"]
    if not rows:
        return {}
    candidates = [r[1] for r in rows] + [h[0] for h in STATE["honeypots"]]
    sel = list(range(min(100, len(rows))))
    fair = fairness.audit(candidates, sel)
    metrics = _fairness_metrics(rows, fair)
    flags = _bias_flags(metrics)
    weights_pct = [{"key": k, "label": COUNCIL_LABELS[k],
                    "pct": round(STATE["weights"].get(k, 0) * 100)} for k in COUNCIL_KEYS]
    return {
        "fairness": fair,
        "metrics": metrics,
        "bias_flags": flags,
        "overall": {
            "passes": len(flags) == 0,
            "n_flags": len(flags),
            "summary": ("No statistical bias detected against the audited attributes."
                        if not flags else
                        f"{len(flags)} potential bias signal(s) flagged for human review."),
        },
        "scoring": {
            "formula": "composite = ( Σ councilₖ · weightₖ ) × integrity × negative_screen "
                       "× disqualifier_screen × availability + bonuses",
            "explanation": "Six additive sub-scorers are fused by your weights to form a core fit, "
                           "then multiplicative gates (Integrity Warden, Neti-Neti negative screen, "
                           "the JD Disqualifier Screen, and the Availability Oracle) adjust it. "
                           "Bounded additive bonuses reward JD nice-to-have skills and evaluation "
                           "rigor without ever dominating the core. Scores are finally calibrated to "
                           "a 0–100 scale. Every weight and threshold is inspectable and user-tunable.",
            "weights": weights_pct,
            "council": [{"key": k, "label": COUNCIL_LABELS[k],
                         "description": COUNCIL_DESC[k],
                         "weight": round(STATE["weights"].get(k, 0) * 100),
                         "avg": round(float(np.mean([r[3]["parts"][k] for r in rows])), 3)}
                        for k in COUNCIL_KEYS],
            "gates": [
                {"name": "Integrity Warden", "type": "hard exclude + multiplier",
                 "detail": "Flags logically impossible profiles (honeypots) and excludes them; "
                           "soft inconsistencies lower the integrity multiplier."},
                {"name": "Neti-Neti Gatekeeper", "type": f"multiplier ≥ {config.NEGSCREEN_MIN}",
                 "detail": "Penalises services-only careers, off-domain specialisation without NLP/IR, "
                           "and keyword-stuffer signatures (including off-list fake titles)."},
                {"name": "JD Disqualifier Screen", "type": f"multiplier ≥ {config.DISQUAL_MULT_FLOOR}",
                 "detail": "Applies the JD's explicit 'we will not move forward' gates — pure "
                           "research/no production, recent LLM-wrapper-only, leadership/no-code drift, "
                           "and 5y+ closed-source with no external validation — each requiring "
                           "multiple corroborating signals."},
                {"name": "Availability Oracle", "type": f"multiplier {config.AVAIL_MIN}–{config.AVAIL_MAX}",
                 "detail": "Bounded behavioural modifier from recency, responsiveness, offer history "
                           "and engagement; a hard ghost-gate demotes dormant + unresponsive profiles."},
            ],
        },
        "audit": {
            "system": "Redrob Ranker v2.0 (Council of Nine)",
            "task_id": STATE.get("task_id"),
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


def _tech_age_skill(skills: list):
    """The worst skill used for longer than its technology has existed — mirrors
    the HARD-4 rule in src/integrity.py so the dashboard compares the claim
    against the TECHNOLOGY's first year, not the candidate's career length.
    Returns (name, duration_months, implied_start_year, tech_first_year) or None."""
    margin = config.HONEYPOT_TECH_AGE_MARGIN_YEARS
    worst = None
    for s in skills:
        dur = float(s.get("duration_months") or 0)
        first = integrity.TECH_FIRST_YEAR.get((s.get("name") or "").strip().lower())
        if first and dur > 0:
            implied_start = integrity.REFERENCE_DATE.year - dur / 12.0
            if implied_start < first - margin and (worst is None or dur > worst[1]):
                worst = (s.get("name") or "—", dur, implied_start, first)
    return worst


def _classify_honeypot(c: dict, integ) -> dict:
    """Turn an integrity flag into a structured violation record for the
    Integrity dashboard — grounded in the candidate's own declared data."""
    p = c.get("profile", {}) or {}
    career = c.get("career_history") or []
    skills = c.get("skills") or []
    yoe = float(p.get("years_of_experience") or 0.0)
    career_months = int(round(yoe * 12))
    reasons = list(integ[2]) if integ and len(integ) > 2 else []
    reason_blob = " ".join(reasons).lower()
    is_hard = bool(integ[1]) if integ and len(integ) > 1 else False
    cap = yoe * 12 + 36

    # A skill used for more years than its technology has existed (the most
    # common honeypot). Detected from the Warden's own reason so we never relabel
    # a profile flagged by a different rule. Compared against the TECHNOLOGY's
    # first year — NOT career length.
    tech_skill = _tech_age_skill(skills) if "technology only existed" in reason_blob else None

    worst_skill = None
    for s in skills:
        dur = float(s.get("duration_months") or 0)
        if dur > cap and dur > 24 and (worst_skill is None or dur > worst_skill[1]):
            worst_skill = (s.get("name") or "—", dur)
    worst_role = None
    for r in career:
        dur = float(r.get("duration_months") or 0)
        if dur > cap and dur > 24 and (worst_role is None or dur > worst_role[1]):
            worst_role = (r.get("title") or "—", dur)
    expert_zero = sum(1 for s in skills
                      if float(s.get("duration_months") or 0) == 0
                      and (s.get("proficiency") or "").lower() == "expert")
    timeline_bad = any(("starts after it ends" in r or "starts in the future" in r)
                       for r in reasons)

    rec = {
        "candidate_id": c.get("candidate_id"),
        "title": p.get("current_title", "—"),
        "company": p.get("current_company", ""),
        "violation_key": "logic",
        "violation_type": "Logical inconsistency",
        "flagged_skill": None,
        "claimed_label": "Claimed", "claimed_value": "—",
        "baseline_label": "Career length", "baseline_value": f"{career_months} mo",
        "delta": None,
        "severity": "high" if is_hard else "medium",
        "reasons": reasons,
    }
    if tech_skill:
        name, dur, implied_start, first = tech_skill
        start_year = int(round(implied_start))
        years_early = first - start_year
        rec.update({
            "violation_key": "tech_age",
            "violation_type": "Skill older than its technology",
            "flagged_skill": name,
            "claimed_label": "Claimed use", "claimed_value": f"{int(dur)} mo (since ~{start_year})",
            "baseline_label": "Tech exists since", "baseline_value": f"~{first}",
            "delta": (f"{years_early}y too early" if years_early > 0 else None),
            "severity": "critical",
        })
    elif worst_skill:
        claimed = int(worst_skill[1])
        rec.update({
            "violation_key": "skill_duration",
            "violation_type": "Skill duration exceeded career length",
            "flagged_skill": worst_skill[0],
            "claimed_label": "Claimed", "claimed_value": f"{claimed} mo",
            "baseline_value": f"{career_months} mo",
            "delta": f"+{claimed - career_months} mo", "severity": "critical",
        })
    elif worst_role:
        claimed = int(worst_role[1])
        rec.update({
            "violation_key": "career_anomaly",
            "violation_type": "Role longer than entire career",
            "flagged_skill": worst_role[0],
            "claimed_label": "Role tenure", "claimed_value": f"{claimed} mo",
            "baseline_value": f"{career_months} mo",
            "delta": f"+{claimed - career_months} mo", "severity": "critical",
        })
    elif timeline_bad:
        rec.update({
            "violation_key": "career_anomaly",
            "violation_type": "Career timeline anomaly",
            "claimed_label": "Timeline", "claimed_value": "Contradictory",
            "severity": "critical",
        })
    elif expert_zero >= 3:
        rec.update({
            "violation_key": "keyword_stuffing",
            "violation_type": "Keyword stuffing",
            "flagged_skill": f"{expert_zero} ‘expert’ skills",
            "claimed_label": "Expert skills", "claimed_value": str(expert_zero),
            "baseline_label": "With usage", "baseline_value": "0",
            "severity": "high" if expert_zero >= 5 else "medium",
        })
    return rec


def honeypots(limit: int = 200) -> dict:
    all_hp = STATE["honeypots"]
    items = [_classify_honeypot(c, integ) for c, integ in all_hp[:limit]]
    type_counter = Counter(_classify_honeypot(c, integ)["violation_type"] for c, integ in all_hp)
    total = len(all_hp)
    ingested = STATE.get("ingested", 0) or (total + len(STATE.get("rows") or []))
    most_common = type_counter.most_common(1)[0][0] if type_counter else "—"
    inflation = round((total / ingested) * 100, 1) if ingested else 0.0
    return {
        "items": items,
        "total": total,
        "showing": len(items),
        "most_common_violation": most_common,
        "inflation_rate": inflation,
        "violation_counts": [{"type": t, "count": n} for t, n in type_counter.most_common()],
    }


ROLE_MODEL_VERSION = "Council-of-Nine v2.0"

# Broad/ambiguous positive-title terms that can pull in adjacent-domain candidates.
_AMBIGUOUS_TITLES = {
    "mobile developer": "may surface React Native / cross-platform candidates outside the core track",
    "full stack": "is broad — can admit front-end-heavy profiles with thin back-end depth",
    "fullstack": "is broad — can admit front-end-heavy profiles with thin back-end depth",
    "full-stack": "is broad — can admit front-end-heavy profiles with thin back-end depth",
    "developer": "is generic — may match junior or off-track engineering profiles",
    "sde": "is generic — may match candidates across unrelated engineering domains",
    "analytics": "overlaps data-analyst and BI roles; verify domain alignment",
    "research scientist": "may surface academic profiles without production delivery",
}


def _slugify(name: str) -> str:
    s = (name or "role").lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in s)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return "role-" + (slug.strip("-")[:40] or "custom")


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _role_confidence(jd: dict) -> dict:
    """Grounded confidence in the model's interpretation, derived from the
    richness of the extracted signals (must-haves, title filters, anti-noise)."""
    must = [m for m in jd.get("must_have_capabilities", []) if m]
    nice = [m for m in jd.get("nice_to_have", []) if m]
    pos = [t for t in jd.get("positive_titles", []) if t]
    neg = [t for t in jd.get("negative_titles", []) if t]
    off = [s for s in jd.get("offdomain_skills", []) if s]
    skill_coverage = _clamp01(0.45 + 0.035 * len(must) + 0.015 * len(nice))
    title_clarity = _clamp01(0.35 + 0.045 * len(pos) + (0.10 if neg else 0.0))
    noise_rejection = _clamp01(0.30 + 0.05 * len(neg) + 0.03 * len(off))
    overall = 0.40 * skill_coverage + 0.30 * title_clarity + 0.30 * noise_rejection
    score = round(overall * 100)
    label = ("Strong interpretation" if score >= 75
             else "Ambiguous" if score >= 55 else "Weak interpretation")
    ready = score >= 65 and len(must) >= 4 and bool(neg)
    return {
        "score": score, "label": label,
        "skill_coverage": round(skill_coverage * 100),
        "title_clarity": round(title_clarity * 100),
        "noise_rejection": round(noise_rejection * 100),
        "status": "Ready to rank" if ready else "Needs review",
        "status_ok": ready, "model_version": ROLE_MODEL_VERSION,
    }


def _signal_conflicts(jd: dict) -> list:
    seen, out = set(), []
    for t in jd.get("positive_titles", []):
        tl = (t or "").lower().strip()
        for term, note in _AMBIGUOUS_TITLES.items():
            if (term == tl or (len(term) > 4 and term in tl)) and t not in seen:
                seen.add(t)
                out.append({"signal": t, "severity": "warning",
                            "message": f"Positive signal “{t}” {note}."})
                break
    return out[:5]


def _role_activity(jd: dict) -> list:
    started = STATE.get("started_at")
    n = len(STATE.get("rows") or [])
    musts = len([m for m in jd.get("must_have_capabilities", []) if m])
    base = _dt.datetime.fromtimestamp(started) if started else _dt.datetime.now()
    acts = []
    if n:
        acts.append({"type": "ranking", "ts": base.isoformat(),
                     "label": f"Ranking run · {n:,} candidates scored ({STATE.get('runtime', 0)}s)"})
        acts.append({"type": "index", "ts": base.isoformat(),
                     "label": f"Vector index rebuilt · {musts} must-have signals embedded"})
    acts.append({"type": "edit", "ts": base.isoformat(),
                 "label": "Role interpretation loaded from catalogue"})
    return acts


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
        # --- enriched model-interpretation fields (Role dashboard) ---
        "role_id": _slugify(jd.get("role_title") or STATE.get("role") or "role"),
        "last_indexed": (_dt.datetime.fromtimestamp(STATE["started_at"]).isoformat()
                         if STATE.get("started_at") else _dt.datetime.now().isoformat()),
        "confidence": _role_confidence(jd),
        "stats": {
            "candidates_in_pool": STATE.get("ingested", 0) or len(STATE.get("rows") or []),
            "must_have_count": len([m for m in jd.get("must_have_capabilities", []) if m]),
            "nice_to_have_count": len([m for m in jd.get("nice_to_have", []) if m]),
            "positive_title_count": len([t for t in jd.get("positive_titles", []) if t]),
            "blocked_title_count": len([t for t in jd.get("negative_titles", []) if t]),
        },
        "retrieval": {
            "embedding_model": config.ST_MODEL_NAME,
            "embedding_backend": config.EMBED_BACKEND,
            "vector_store": "Hybrid TF-IDF (lexical) + LSA dense, fused via RRF",
            "top_k": config.SHORTLIST_SIZE,
            "rerank_size": config.RERANK_SIZE,
            "dense_dim": config.DENSE_DIM,
        },
        "weights": [{"key": k, "label": COUNCIL_LABELS[k],
                     "pct": round(STATE["weights"].get(k, config.COUNCIL_WEIGHTS.get(k, 0)) * 100)}
                    for k in COUNCIL_KEYS],
        "signal_conflicts": _signal_conflicts(jd),
        "activity_log": _role_activity(jd),
    }


# ---------------------------------------------------------------------------
# Supabase-backed tasks & shortlists (Pipeline page)
# ---------------------------------------------------------------------------
def db_status() -> dict:
    return supabase_store.status()


def list_tasks() -> dict:
    if not supabase_store.enabled():
        return {"enabled": False, "tasks": []}
    try:
        return {"enabled": True, "tasks": supabase_store.list_tasks()}
    except Exception as e:
        log("error", f"list_tasks failed: {e}")
        return {"enabled": True, "tasks": [], "error": str(e)}


def get_task(task_id: str) -> dict | None:
    try:
        task = supabase_store.get_task(task_id)
        if not task:
            return None
        task["candidates"] = supabase_store.task_candidates(task_id, "top200", limit=200)
        task["shortlisted"] = supabase_store.task_candidates(task_id, "shortlisted", limit=200)
        task["honeypot"] = supabase_store.task_candidates(task_id, "honeypot", limit=200)
        return task
    except Exception as e:
        log("error", f"get_task failed: {e}")
        return None


def get_task_candidates(task_id: str, category: str = "top200", limit: int = 200) -> dict:
    try:
        return {"items": supabase_store.task_candidates(task_id, category, limit=limit)}
    except Exception as e:
        log("error", f"get_task_candidates failed: {e}")
        return {"items": [], "error": str(e)}


def list_shortlists(task_id: str) -> dict:
    try:
        return {"items": supabase_store.list_shortlists(task_id)}
    except Exception as e:
        log("error", f"list_shortlists failed: {e}")
        return {"items": [], "error": str(e)}


def create_shortlist(task_id: str, name: str) -> dict:
    return supabase_store.create_shortlist(task_id, name)


def delete_shortlist(shortlist_id: str) -> dict:
    supabase_store.delete_shortlist(shortlist_id)
    return {"ok": True}


def add_shortlist_member(shortlist_id: str, member: dict) -> dict:
    return supabase_store.add_shortlist_member(shortlist_id, member)


def remove_shortlist_member(member_id: int) -> dict:
    supabase_store.remove_shortlist_member(member_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# NextAI — compact context built from the live ranking for the LLM
# ---------------------------------------------------------------------------
def nextai_context(top: int = 25) -> dict:
    """Return a compact JSON summary of the current ranking for the assistant."""
    rows = STATE["rows"]
    if not rows:
        return {"ready": False}
    jd = _jd()
    n = len(rows)
    scores = [r[0] * 100 for r in rows]
    summary_obj = summary()
    leaders = []
    for i, (score, c, f, dec, integ) in enumerate(rows[:top], 1):
        p = c.get("profile", {}) or {}
        leaders.append({
            "rank": i,
            "candidate_id": c.get("candidate_id"),
            "title": p.get("current_title"),
            "company": p.get("current_company"),
            "score": round(score * 100, 1),
            "yoe": p.get("years_of_experience"),
            "location": p.get("location") or p.get("country"),
            "notice_days": int(f["notice_days"]),
            "verified_skills": verified_relevant_skills(c, jd, top=6),
            "council": {COUNCIL_LABELS[k]: round(float(dec["parts"][k]), 2) for k in COUNCIL_KEYS},
        })
    return {
        "ready": True,
        "task_id": STATE.get("task_id"),
        "role": STATE["role"],
        "role_title": jd.get("role_title", STATE["role"]),
        "must_have": jd.get("must_have_capabilities", []),
        "stats": {
            "ranked": n,
            "ingested": STATE["ingested"],
            "honeypots": len(STATE["honeypots"]),
            "strong_matches": summary_obj["strong_matches"],
            "avg_score": round(float(np.mean(scores)), 1) if scores else 0,
            "median_score": round(float(np.median(scores)), 1) if scores else 0,
        },
        "leaderboard": leaders,
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
