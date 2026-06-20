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
import os
import sys
import time

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

    # fast path: use a precomputed retriever if available and sizes match
    retriever = None
    cache = os.path.join(config.ARTIFACTS_DIR, "retriever.pkl")
    if args.limit is None and os.path.exists(cache):
        try:
            import pickle
            with open(cache, "rb") as fh:
                cand = pickle.load(fh)
            if getattr(cand, "dense", None) is not None and cand.dense.shape[0] == len(candidates):
                retriever = cand
        except Exception:
            retriever = None

    records, stats = score_pool(candidates, jd, retriever=retriever, verbose=verbose)

    # fairness audit + EU AI Act audit trail
    fair = fairness.audit(candidates, stats["selected_idx"])
    backend = "lsa (sklearn TF-IDF + TruncatedSVD)"
    audit_path = compliance.write_audit(
        args.candidates, len(candidates), stats["n_honeypots"],
        time.time() - t0, fair, backend,
    )

    write_csv(records, args.out)

    dt = time.time() - t0
    if verbose:
        print("-" * 64)
        print(f"[done] wrote {len(records)} rows -> {args.out}")
        print(f"       honeypots detected & excluded: {stats['n_honeypots']}")
        print(f"       region disparate-impact: "
              f"{fair['region']['disparate_impact_ratio']} "
              f"(pass={fair['region']['passes_four_fifths']})")
        print(f"       audit trail: {os.path.relpath(audit_path)}")
        print(f"       total runtime: {dt:.1f}s")
        print("=" * 64)


if __name__ == "__main__":
    main()
