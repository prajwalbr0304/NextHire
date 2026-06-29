#!/usr/bin/env python3
"""
Redrob Ranker v2.0 — entrypoint.

Single command that produces the top-100 submission CSV from candidates.jsonl,
CPU-only and offline. Designed to finish well within the 5-minute budget.

    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

It runs the full Council-of-Nine pipeline end-to-end. If precomputed artifacts
exist they are used; otherwise everything is computed on the fly (still < 5 min
for 100K candidates on a 16 GB CPU box with the default LSA backend).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import os
import sys
import time

# The ranking step MUST be fully offline (spec: "Network Off"). Force Hugging
# Face into offline mode BEFORE any embedding backend imports, so an uncached
# model fails fast (no network retries) and falls back to LSA instantly.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# allow `python rank.py` from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import config, fairness, compliance
from src.load import load_candidates
from src.score import load_jd, score_pool


def write_csv(records, out_path: str):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for r in records:
            w.writerow([r["candidate_id"], r["rank"], f"{r['score']:.4f}", r["reasoning"]])


def _load_cached_retriever(candidates, jd, verbose=False):
    """Return a precomputed retriever from artifacts/ iff it matches the current
    pool EXACTLY (row count, candidate ids/order) AND the JD query it was frozen
    for; else None so we fit live. Supports a plain or gzipped pickle so the
    committed index can be compressed for the repo. The id/order gate is critical:
    the frozen arrays are row-aligned to the pool they were built on, so a
    different pool MUST refit or rows would be mis-attributed. The query gate
    guards the JD-specific PrecomputedRetriever (a changed JD must refit).
    """
    import pickle

    def _read(path):
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rb") as fh:
            return pickle.load(fh)

    def _find(stem):
        for name in (stem + ".pkl.gz", stem + ".pkl"):
            p = os.path.join(config.ARTIFACTS_DIR, name)
            if os.path.exists(p):
                return p
        return None

    rpath = _find("retriever")
    if rpath is None:
        return None
    try:
        retr = _read(rpath)
    except Exception:
        return None

    if getattr(retr, "dense", None) is None or retr.dense.shape[0] != len(candidates):
        if verbose:
            print("  [cache] retriever shape mismatch -> fitting live", flush=True)
        return None

    # query gate: a frozen PrecomputedRetriever is valid ONLY for the JD it was
    # built for (a fitted HybridRetriever has no query_text, so this is skipped).
    q = getattr(retr, "query_text", None)
    if q is not None and q != jd.get("query_text"):
        if verbose:
            print("  [cache] query_text changed -> fitting live", flush=True)
        return None

    ipath = _find("candidate_ids")
    if ipath is not None:
        try:
            cached_ids = list(_read(ipath))
        except Exception:
            return None
        if cached_ids != [c.get("candidate_id") for c in candidates]:
            if verbose:
                print("  [cache] candidate ids/order differ -> fitting live", flush=True)
            return None

    if verbose:
        print(f"  [cache] using precomputed retriever ({os.path.basename(rpath)})",
              flush=True)
    return retr


def main():
    ap = argparse.ArgumentParser(description="Redrob Ranker v2.0 (Council of Nine)")
    ap.add_argument("--candidates", required=True, help="path to candidates.jsonl(.gz)")
    ap.add_argument("--out", default="submission.csv", help="output CSV path")
    ap.add_argument("--limit", type=int, default=None, help="debug: only load N candidates")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    verbose = not args.quiet

    if verbose:
        print("=" * 64)
        print(" Redrob Ranker v2.0  ·  Council of Nine")
        print("=" * 64)

    jd = load_jd()
    if verbose:
        print(f"[1] JD intent loaded: {jd['role_title']}")

    if verbose:
        print(f"[0] loading candidates from {args.candidates} ...", flush=True)
    candidates = load_candidates(args.candidates, limit=args.limit)
    if verbose:
        print(f"[0] loaded {len(candidates):,} candidates "
              f"({time.time()-t0:.1f}s)", flush=True)

    # fast path: use a precomputed retriever iff it matches the pool EXACTLY.
    retriever = None
    if args.limit is None:
        t_stage = time.time()
        retriever = _load_cached_retriever(candidates, jd, verbose=verbose)
        if verbose and retriever is not None:
            print(f"[TIMING] cache_load: {time.time()-t_stage:.2f}s", flush=True)

    t_stage = time.time()
    records, stats = score_pool(candidates, jd, retriever=retriever, verbose=verbose)
    if verbose:
        print(f"[TIMING] score_pool TOTAL: {time.time()-t_stage:.2f}s", flush=True)

    # fairness audit + EU AI Act audit trail
    t_stage = time.time()
    fair = fairness.audit(candidates, stats["selected_idx"])
    backend = "lsa (sklearn TF-IDF + TruncatedSVD)"
    audit_path = compliance.write_audit(
        args.candidates, len(candidates), stats["n_honeypots"],
        time.time() - t0, fair, backend,
        honeypot_rules=stats.get("honeypot_rules"),
    )
    if verbose:
        print(f"[TIMING] fairness+audit: {time.time()-t_stage:.2f}s", flush=True)

    t_stage = time.time()
    write_csv(records, args.out)
    if verbose:
        print(f"[TIMING] write_csv: {time.time()-t_stage:.2f}s", flush=True)

    dt = time.time() - t0
    if verbose:
        print("-" * 64)
        print(f"[done] wrote {len(records)} rows -> {args.out}")
        print(f"       candidates scored: {stats.get('n_considered', stats['n_scored']):,}")
        print(f"       honeypots detected & excluded: {stats['n_honeypots']}")
        if stats.get("honeypot_rules"):
            by_rule = ", ".join(f"{k}={v}" for k, v in sorted(stats["honeypot_rules"].items()))
            print(f"         by rule: {by_rule}")
        print(f"       region disparate-impact: "
              f"{fair['region']['disparate_impact_ratio']} "
              f"(pass={fair['region']['passes_four_fifths']})")
        print(f"       audit trail: {os.path.relpath(audit_path)}")
        print(f"       total runtime: {dt:.1f}s")
        print("=" * 64)


if __name__ == "__main__":
    main()
