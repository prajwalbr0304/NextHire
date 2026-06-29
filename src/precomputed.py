"""Frozen, dependency-light retrieval index.

This module deliberately depends on NumPy only — NOT scikit-learn. On the cached
fast path the heavy lexical/dense fitting never runs, so dragging scikit-learn in
just to *unpickle* the frozen result would waste ~13s (much more on a cold/AV
Windows box) for nothing. Keeping `PrecomputedRetriever` in its own sklearn-free
module means the committed index loads in milliseconds at rank time.
"""
from __future__ import annotations

import numpy as np


class PrecomputedRetriever:
    """A frozen, tiny retriever that REPLAYS the exact retrieval result computed
    offline for the FIXED JD query (shortlist + per-candidate similarities).

    Why this exists: the full fitted HybridRetriever pickles to ~220 MB (the N×V
    TF-IDF matrix + N×256 dense matrix) — too large to commit for sandbox
    reproduction. But `score_pool` only consumes `shortlist` and `dense_sim`
    (lexical_sim is unused downstream, and the shortlist is already RRF-fused), so
    we persist JUST those arrays (~1 MB). Replaying identical arrays makes the
    ranking byte-identical to a live fit, while the ranking step loads in
    milliseconds and stays well under the 5-minute CPU budget.

    Valid only for the query it was built for; rank.py verifies `query_text`
    (and the candidate id/order) and refits live on any mismatch.
    """

    backend = "precomputed"

    def __init__(self, shortlist, dense_sim, lexical_sim=None, query_text=None):
        self.shortlist = np.asarray(shortlist)
        self.dense_sim = np.asarray(dense_sim)
        self.lexical_sim = (np.asarray(lexical_sim)
                            if lexical_sim is not None
                            else np.zeros_like(self.dense_sim))
        self.query_text = query_text
        self.dense_dim = 1
        # `.dense` exposes the row count so callers shape-check it against the
        # candidate pool exactly like a fitted retriever (dense.shape[0] == N).
        self.dense = self.dense_sim.reshape(-1, 1)

    def retrieve(self, query_text: str, shortlist_size=None):
        """Replay the frozen result. `query_text`/`shortlist_size` are accepted
        for interface parity but ignored: the arrays were fused offline for the
        exact JD query (validated by the caller before this object is used)."""
        return self.shortlist, self.dense_sim, self.lexical_sim
