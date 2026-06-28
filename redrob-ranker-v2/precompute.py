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
import gzip
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json

from src import config
from src.load import load_candidates
from src.features import build_document
from src.retrieve import build_retriever
from src.precomputed import PrecomputedRetriever


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", default=config.ARTIFACTS_DIR)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--backend", choices=["auto", "st", "lsa"], default=None,
                    help="dense backend: 'st' = sentence-transformers (recommended "
                         "for precompute), 'lsa' = TF-IDF+SVD, 'auto' = config default")
    ap.add_argument("--warm-reranker", action="store_true",
                    help="download/cache the cross-encoder re-ranker model so the "
                         "rank step can use it fully offline (network allowed here)")
    ap.add_argument("--gzip", action="store_true",
                    help="gzip the cached index (smaller for committing to the repo; "
                         "rank.py auto-detects .pkl.gz)")
    args = ap.parse_args()

    if args.warm_reranker:
        print(f"[precompute] warming cross-encoder re-ranker '{config.RERANK_MODEL}' ...",
              flush=True)
        try:
            from sentence_transformers import CrossEncoder
            CrossEncoder(config.RERANK_MODEL, max_length=512, device="cpu")
            print("[precompute] re-ranker cached OK", flush=True)
        except Exception as e:  # never fatal: rank.py falls back to feature re-rank
            print(f"[precompute] re-ranker warm-up skipped ({type(e).__name__}: {e})",
                  flush=True)

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    print(f"[precompute] loading candidates from {args.candidates} ...", flush=True)
    candidates = load_candidates(args.candidates, limit=args.limit)
    print(f"[precompute] {len(candidates):,} candidates loaded "
          f"({time.time()-t0:.1f}s)", flush=True)

    print("[precompute] building candidate documents ...", flush=True)
    docs = [build_document(c) for c in candidates]

    backend = args.backend or config.EMBED_BACKEND
    print(f"[precompute] fitting hybrid retriever (lexical TF-IDF + '{backend}' dense) ...",
          flush=True)
    retriever = build_retriever(docs, verbose=True, backend=args.backend)
    print(f"[precompute] dense backend = {getattr(retriever, 'backend', '?')} "
          f"({getattr(retriever, 'dense_dim', '?')}-dim)", flush=True)

    # Replay the retrieval for the FIXED JD query and freeze ONLY the result
    # (shortlist + similarities). This index is ~1 MB vs ~220 MB for the full
    # fitted matrices, so it is committable for sandbox reproduction; the ranking
    # step then loads it in milliseconds. Output is byte-identical because
    # score_pool consumes exactly these arrays.
    with open(config.JD_INTENT_PATH, "r", encoding="utf-8") as f:
        jd = json.load(f)
    shortlist, dense_sim, lexical_sim = retriever.retrieve(jd["query_text"])
    frozen = PrecomputedRetriever(shortlist, dense_sim, lexical_sim,
                                  query_text=jd["query_text"])
    print(f"[precompute] froze retrieval for '{jd.get('role_title', '?')}': "
          f"shortlist={len(shortlist)}, sims={dense_sim.shape[0]}", flush=True)

    # cache the frozen retriever + the row-aligned candidate ids (rank.py verifies
    # both the ids/order AND the query before using it).
    suffix = ".pkl.gz" if args.gzip else ".pkl"
    opener = gzip.open if args.gzip else open

    def _dump(obj, stem):
        path = os.path.join(args.out, stem + suffix)
        with opener(path, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        return path

    rpath = _dump(frozen, "retriever")
    _dump([c.get("candidate_id") for c in candidates], "candidate_ids")

    print(f"[precompute] wrote {os.path.basename(rpath)} "
          f"({os.path.getsize(rpath)/1e6:.2f} MB)", flush=True)
    print(f"[precompute] done in {time.time()-t0:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
