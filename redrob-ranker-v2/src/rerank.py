"""
Stage [3b] — Two-stage top-N re-rank.

A small CPU neural cross-encoder re-scores the HEAD of the ranking (the top
`RERANK_SIZE` candidates) for sharper NDCG@10 ordering. It runs on the head ONLY,
loads weights offline (no network at rank time), and is time-guarded; if the
model is unavailable, errors, or would breach the budget it falls back to a
deterministic, dependency-free feature re-rank. Either way `rerank()` returns one
relevance score per head record (higher = better), or None = "keep base order".
"""
from __future__ import annotations

import os
import time
from typing import List, Optional

from . import config
from .features import build_document

# load the cross-encoder once per process
_CE_CACHE: dict = {}


def _feature_scores(head) -> List[float]:
    """Deterministic, dependency-free sharpened re-rank: emphasise verified skill
    trust + demonstrated (domain) evidence + semantic + title identity, with
    availability BOUNDED so it cannot decide the head. Pure function of features
    already computed during scoring."""
    out = []
    for r in head:
        dec = r["dec"]
        parts = dec["parts"]
        s = (0.34 * parts["semantic_seer"]
             + 0.30 * parts["evidence_scout"]
             + 0.22 * parts["mask_piercer"]
             + 0.14 * parts["name_rectifier"])
        s *= dec.get("disqualifier_mult", 1.0) * dec.get("neg_mult", 1.0)
        # bounded availability nudge (cannot dominate at the head)
        s *= 0.9 + 0.1 * min(dec.get("avail_mult", 1.0), config.AVAIL_MAX)
        out.append(float(s))
    return out


def _load_cross_encoder():
    name = config.RERANK_MODEL
    if name in _CE_CACHE:
        return _CE_CACHE[name]
    # NEVER touch the network at rank time (spec: "Network Off"). Force offline
    # mode and construct CrossEncoder with local_files_only=True so an uncached
    # model raises immediately instead of retrying against HuggingFace for ~235s.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import CrossEncoder  # may raise -> caught upstream
    try:
        model = CrossEncoder(name, max_length=512, device="cpu",
                             model_kwargs={"local_files_only": True})
    except TypeError:
        # older sentence-transformers has no model_kwargs passthrough; rely on the
        # env vars above (still offline, just without the explicit kwarg guard).
        model = CrossEncoder(name, max_length=512, device="cpu")
    _CE_CACHE[name] = model
    return model


def _cross_encoder_scores(jd, head, verbose=False) -> Optional[List[float]]:
    t0 = time.time()
    model = _load_cross_encoder()
    if time.time() - t0 > config.RERANK_TIME_BUDGET_S:
        return None  # model load alone blew the budget -> fall back
    query = jd.get("query_text", "") or jd.get("role_title", "")
    pairs = [[query, build_document(r["candidate"])[:2000]] for r in head]
    scores = model.predict(pairs, batch_size=32, show_progress_bar=False,
                           convert_to_numpy=True)
    if time.time() - t0 > config.RERANK_TIME_BUDGET_S:
        return None
    return [float(x) for x in scores]


def rerank(jd, head, verbose=False) -> Optional[List[float]]:
    """Relevance scores for the head records (higher = better), or None to keep
    the base order. Never raises; never exceeds the time budget."""
    backend = (config.RERANK_BACKEND or "auto").lower()
    if backend == "off" or not head:
        return None
    if backend in ("auto", "cross-encoder"):
        try:
            scores = _cross_encoder_scores(jd, head, verbose=verbose)
            if scores is not None:
                if verbose:
                    print(f"  [rerank] cross-encoder re-ranked {len(head)} head "
                          f"candidates", flush=True)
                return scores
        except Exception as e:  # missing dep/weights/OOM -> deterministic fallback
            if verbose:
                print(f"  [rerank] cross-encoder unavailable "
                      f"({type(e).__name__}: {e}); using feature re-rank", flush=True)
    # feature fallback (also the path when backend == "feature")
    return _feature_scores(head)
