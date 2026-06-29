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
import time
from collections import Counter
from typing import Dict, List

import numpy as np

from . import config, council as council_mod, integrity as integrity_mod
from . import rerank as rerank_mod
from .features import build_document, compute_features
from .reasoning import generate as gen_reason


def load_jd(path: str = config.JD_INTENT_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _honeypot_rule(reasons: List[str]) -> str:
    """Classify an integrity flag into the HARD rule that fired (for the audit
    breakdown). Matches the reason strings emitted by integrity.check."""
    txt = " ".join(reasons).lower()
    if "expert" in txt:
        return "expert_zero"
    if "impossible tenure" in txt:
        return "tenure_over_span"
    if "starts after it ends" in txt or "starts in the future" in txt:
        return "timeline"
    if "technology only existed" in txt:
        return "tech_age"
    return "other"


def _soft_nudge(f: Dict) -> float:
    """Small, bounded ADDITIVE bonuses layered on the gated core fit:
    logistics (location, notice) + JD nice-to-haves + evaluation rigor.
    These live OUTSIDE the normalized council core so they nudge, never dominate.
    """
    bonus = 0.0
    if f["location_match"]:
        bonus += 0.025
    if f["notice_days"] <= config.NOTICE_PREF_DAYS:
        bonus += 0.015
    elif f["notice_days"] > 90:
        bonus -= 0.015
    # JD "nice to have" (LoRA/QLoRA/LTR/XGBoost/HR-tech/distributed/OSS): boost,
    # never reject. Scaled by verified trust, capped at NICE_TO_HAVE_BONUS_MAX.
    bonus += min(f.get("nice_trust", 0.0) / 6.0, 1.0) * config.NICE_TO_HAVE_BONUS_MAX
    # Evaluation-framework rigor (NDCG/MRR/MAP/A-B) — a stated core competency.
    bonus += min(f.get("eval_framework_hits", 0) / 4.0, 1.0) * config.EVAL_RIGOR_BONUS_MAX
    return bonus


def relevance_band(f: Dict, dec: Dict, integ) -> int:
    """Coarse, grounded relevance band used ONLY to order output so higher-
    relevance candidates always outrank lower ones (the MAP/P@10 requirement).
    2=strong, 1=standard, 0=weak/unqualified. Bands are floored, never exclusions.
    """
    disq = dec.get("disqualifier_mult", 1.0)
    trust = f.get("relevant_trust", 0.0)
    ev = f.get("evidence_hits", 0)
    # engineering identity = a positive title now OR anywhere in career history
    # (robust to exact-string gaps, e.g. "Recommendation Systems Engineer").
    eng_identity = bool(f.get("cur_title_pos") or f.get("title_pos"))
    # WEAK: career non-engineer (non-eng title AND no eng role ever — the keyword
    # trap), strongly disqualified, or no relevant signal at all.
    if (disq <= config.BAND_DISQUAL_WEAK
            or (f.get("cur_title_neg") and not f.get("title_pos"))
            or (trust < config.BAND_WEAK_TRUST and ev < 1 and not eng_identity)):
        return 0
    # STRONG: verified relevant depth + demonstrated delivery + engineering
    # identity, not services-dominated, not gated. (Not tied to the exact title.)
    if (trust >= config.BAND_STRONG_TRUST and ev >= config.BAND_STRONG_EV
            and eng_identity and not f.get("services_only")
            and not f.get("cur_title_neg") and disq >= 1.0):
        return 2
    return 1


def _assign_banded_scores(top: List[dict]) -> None:
    """Assign each record a 4-dp score inside its band's DISJOINT sub-range, by
    intra-band min-max on the re-ranked 'order'. Guarantees the full list is
    non-increasing across bands (STRONG > STANDARD > WEAK) and fine-grained
    within each band, so position sensitivity (NDCG) is preserved.
    """
    for band_val in sorted(config.BAND_RANGES, reverse=True):
        lo, hi = config.BAND_RANGES[band_val]
        members = [r for r in top if r["band"] == band_val]
        if not members:
            continue
        orders = [r["order"] for r in members]
        mn, mx = min(orders), max(orders)
        rng = (mx - mn)
        for r in members:
            if rng:
                r["score"] = round(lo + (hi - lo) * (r["order"] - mn) / rng, 4)
            else:
                r["score"] = round(hi, 4)   # single/equal members -> top of band


def finalize_ranking(scored: List[dict], jd: dict, top_n: int | None = None,
                     verbose: bool = False) -> List[dict]:
    """Shared final stage for BOTH the submission (rank.py) and the dashboard
    (api/ranker.py), so they always produce identical orderings.

    Input: scored records, each a dict with keys raw, f, dec, integ, candidate,
    candidate_id. Applies the two-stage HEAD re-rank, the 3-band relevance gate,
    and tier-banded calibration; returns the ordered list (len == top_n if given)
    with r["band"] and a 4-dp, globally non-increasing r["score"] set.
    """
    # Stage [3b] — re-rank the HEAD for sharper top-N ordering.
    scored.sort(key=lambda r: (-r["raw"], r["candidate_id"]))
    for r in scored:
        r["order"] = r["raw"]
    head = scored[:config.RERANK_SIZE]
    ce = rerank_mod.rerank(jd, head, verbose=verbose)
    if ce:
        # map re-rank scores into the head's OWN raw range so the head reorders
        # internally but never crosses below the (unre-ranked) tail.
        cs = np.array(ce, dtype=float)
        cs = (cs - cs.min()) / ((cs.max() - cs.min()) or 1.0)
        hr = np.array([r["raw"] for r in head], dtype=float)
        m, span = float(hr.min()), float(hr.max() - hr.min())
        for r, c in zip(head, cs):
            r["order"] = m + float(c) * span

    # Stage [9b] — relevance bands so higher-relevance ALWAYS outranks lower.
    for r in scored:
        r["band"] = relevance_band(r["f"], r["dec"], r["integ"])
    scored.sort(key=lambda r: (-r["band"], -r["order"], r["candidate_id"]))
    ranked = scored[:top_n] if top_n else scored

    _assign_banded_scores(ranked)
    ranked.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    return ranked


def score_pool(candidates: List[dict], jd: dict, retriever, verbose=True):
    """Return (records, stats). records sorted best-first, len == TOP_N."""
    n = len(candidates)

    if retriever is None:
        # docs are ONLY needed to FIT the retriever. When a precomputed retriever
        # is supplied we skip building all N candidate documents entirely
        # (~15-20s saved on 100K), which is sound because nothing downstream
        # consumes this list (the head re-ranker builds its own head docs).
        t = time.time()
        docs = [build_document(c) for c in candidates]
        if verbose:
            print(f"[TIMING] doc_build ({n}): {time.time()-t:.2f}s", flush=True)
            print(f"  [retrieve] fitting hybrid retriever over {n} docs ...", flush=True)
        from .retrieve import build_retriever
        t = time.time()
        retriever = build_retriever(docs, verbose=verbose)
        if verbose:
            print(f"[TIMING] retriever_fit: {time.time()-t:.2f}s", flush=True)
    elif verbose:
        print("  [retrieve] using precomputed retriever from artifacts/", flush=True)

    t = time.time()
    shortlist, dense_sim, lexical_sim = retriever.retrieve(jd["query_text"])
    shortlist = list(shortlist)
    if verbose:
        print(f"[TIMING] retrieve+shortlist: {time.time()-t:.2f}s", flush=True)
        print(f"  [retrieve] shortlist = {len(shortlist)} candidates", flush=True)

    # Which candidates get the full Council scoring. By default we score the ENTIRE
    # pool so no qualified candidate is ever dropped by the recall stage (the JD's
    # explicit ask: a buzzword-light "Tier-5" who actually shipped a system must
    # still be reachable). Retrieval still supplies the per-candidate semantic
    # signal (dense_sim) used by the Semantic Seer below.
    score_idx = list(range(n)) if config.SCORE_FULL_POOL else shortlist
    if verbose:
        scope = "FULL POOL" if config.SCORE_FULL_POOL else "shortlist"
        print(f"  [score] scoring {len(score_idx):,} candidates ({scope})", flush=True)

    # normalise semantic similarity to [0,1] across the scored set
    sl_sims = dense_sim[score_idx]
    lo, hi = float(sl_sims.min()), float(sl_sims.max())
    rng = (hi - lo) or 1.0

    t = time.time()
    scored = []
    n_honeypots = 0
    honeypot_rules: Counter = Counter()
    for idx in score_idx:
        c = candidates[idx]
        f = compute_features(c, jd)
        sem = (dense_sim[idx] - lo) / rng
        integ = integrity_mod.check(c)          # (score, is_honeypot, reasons)
        if integ[1]:
            n_honeypots += 1
            honeypot_rules[_honeypot_rule(integ[2])] += 1
            continue                            # honeypot -> excluded entirely
        dec = council_mod.deliberate(f, sem)
        final_fit = dec["core"] * integ[0] * dec["neg_mult"] * dec["disqualifier_mult"]
        final = final_fit * dec["avail_mult"] + _soft_nudge(f)
        final = max(0.0, final)
        scored.append({
            "idx": idx,
            "candidate_id": c.get("candidate_id"),
            "raw": final,
            "f": f, "dec": dec, "integ": integ, "candidate": c,
        })

    if verbose:
        print(f"[TIMING] score_loop ({len(scored)} scored): {time.time()-t:.2f}s",
              flush=True)

    # ---- Stages [3b]+[9b]: two-stage re-rank + 3-band tier calibration ----
    t = time.time()
    top = finalize_ranking(scored, jd, top_n=config.TOP_N, verbose=verbose)
    if verbose:
        print(f"[TIMING] finalize_rerank: {time.time()-t:.2f}s", flush=True)

    t = time.time()
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
    if verbose:
        print(f"[TIMING] reasoning: {time.time()-t:.2f}s", flush=True)

    stats = {
        "n_scored": len(scored),                    # survived honeypot exclusion
        "n_considered": len(score_idx),             # candidates put through scoring
        "n_honeypots": n_honeypots,                 # flagged across the scored set (excluded)
        "honeypot_rules": dict(honeypot_rules),     # per-rule breakdown of those flags
        "shortlist_size": len(shortlist),           # RRF recall shortlist (informational)
        "selected_idx": [r["idx"] for r in top],
    }
    return records, stats
