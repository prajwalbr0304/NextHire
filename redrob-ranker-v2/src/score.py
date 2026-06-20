"""
Stages [3]->[9] — Fusion, calibration, gating and final ordering.

final_fit  = council_core * integrity * neg_screen          (merit, gated)
final      = final_fit * availability_modifier + soft_nudges (readiness)

Then calibrate to a presentable [0,1] band, sort by (score desc, candidate_id
asc), assign ranks 1..N, and guarantee the validator's invariants
(non-increasing score by rank; equal scores broken by candidate_id ascending).
"""
from __future__ import annotations

import json
from typing import Dict, List

import numpy as np

from . import config, council as council_mod, integrity as integrity_mod
from .features import build_document, compute_features
from .reasoning import generate as gen_reason


def load_jd(path: str = config.JD_INTENT_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _soft_nudge(f: Dict) -> float:
    """Small additive bonus for logistics fit (location, notice). Bounded ±0.04."""
    bonus = 0.0
    if f["location_match"]:
        bonus += 0.025
    if f["notice_days"] <= config.NOTICE_PREF_DAYS:
        bonus += 0.015
    elif f["notice_days"] > 90:
        bonus -= 0.015
    return bonus


def score_pool(candidates: List[dict], jd: dict, retriever, verbose=True):
    """Return (records, stats). records sorted best-first, len == TOP_N."""
    n = len(candidates)
    docs = [build_document(c) for c in candidates]

    if retriever is None:
        if verbose:
            print(f"  [retrieve] fitting hybrid retriever over {n} docs ...", flush=True)
        from .retrieve import build_retriever
        retriever = build_retriever(docs, verbose=verbose)
    elif verbose:
        print("  [retrieve] using precomputed retriever from artifacts/", flush=True)

    shortlist, dense_sim, lexical_sim = retriever.retrieve(jd["query_text"])
    shortlist = list(shortlist)
    if verbose:
        print(f"  [retrieve] shortlist = {len(shortlist)} candidates", flush=True)

    # normalise semantic similarity to [0,1] across the shortlist
    sl_sims = dense_sim[shortlist]
    lo, hi = float(sl_sims.min()), float(sl_sims.max())
    rng = (hi - lo) or 1.0

    scored = []
    n_honeypots = 0
    for idx in shortlist:
        c = candidates[idx]
        f = compute_features(c, jd)
        sem = (dense_sim[idx] - lo) / rng
        integ = integrity_mod.check(c)          # (score, is_honeypot, reasons)
        if integ[1]:
            n_honeypots += 1
            continue                            # honeypot -> excluded entirely
        dec = council_mod.deliberate(f, sem)
        final_fit = dec["core"] * integ[0] * dec["neg_mult"]
        final = final_fit * dec["avail_mult"] + _soft_nudge(f)
        final = max(0.0, final)
        scored.append({
            "idx": idx,
            "candidate_id": c.get("candidate_id"),
            "raw": final,
            "f": f, "dec": dec, "integ": integ, "candidate": c,
        })

    # sort by merit, then candidate_id ascending (validator tie-break)
    scored.sort(key=lambda r: (-r["raw"], r["candidate_id"]))
    top = scored[:config.TOP_N]

    # calibrate the top-N raw scores into a clean, monotone [0.35, 0.99] band
    raws = np.array([r["raw"] for r in top], dtype=float)
    if len(raws) > 1 and raws.max() > raws.min():
        cal = 0.35 + 0.64 * (raws - raws.min()) / (raws.max() - raws.min())
    else:
        cal = np.full(len(raws), 0.8)
    for r, s in zip(top, cal):
        r["score"] = round(float(s), 4)

    # re-sort on the ROUNDED score to keep the validator's invariants exact
    top.sort(key=lambda r: (-r["score"], r["candidate_id"]))

    records = []
    for rank, r in enumerate(top, start=1):
        reason = gen_reason(r["candidate"], r["f"], r["dec"], r["integ"],
                            r["score"], rank, jd)
        records.append({
            "candidate_id": r["candidate_id"],
            "rank": rank,
            "score": r["score"],
            "reasoning": reason,
        })

    stats = {
        "n_scored": len(scored),
        "n_honeypots": n_honeypots,
        "shortlist_size": len(shortlist),
        "selected_idx": [r["idx"] for r in top],
    }
    return records, stats
