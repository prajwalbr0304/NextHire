#!/usr/bin/env python3
"""
Offline precompute (the OFFLINE half of the two-phase design).

Builds and caches the heavy artifacts (candidate documents + the fitted hybrid
retriever / embeddings) so the online `rank.py` step is fast. This step is
allowed to exceed the 5-minute budget; the ranking step that produces the CSV
is not.

    python precompute.py --candidates ./candidates.jsonl --out ./artifacts

Note: the default LSA backend is light enough that rank.py also runs fine
without precomputation. Precompute matters most when you swap in the heavier
sentence-transformers / ColBERT backends described in the blueprint.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import config
from src.load import load_candidates
from src.features import build_document
from src.retrieve import build_retriever


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", default=config.ARTIFACTS_DIR)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    print(f"[precompute] loading candidates from {args.candidates} ...", flush=True)
    candidates = load_candidates(args.candidates, limit=args.limit)
    print(f"[precompute] {len(candidates):,} candidates loaded "
          f"({time.time()-t0:.1f}s)", flush=True)

    print("[precompute] building candidate documents ...", flush=True)
    docs = [build_document(c) for c in candidates]

    print("[precompute] fitting hybrid retriever (TF-IDF + LSA) ...", flush=True)
    retriever = build_retriever(docs)

    # cache the fitted retriever (vectorizer + svd + matrices)
    with open(os.path.join(args.out, "retriever.pkl"), "wb") as f:
        pickle.dump(retriever, f)

    ids = [c.get("candidate_id") for c in candidates]
    with open(os.path.join(args.out, "candidate_ids.pkl"), "wb") as f:
        pickle.dump(ids, f)

    print(f"[precompute] done in {time.time()-t0:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
