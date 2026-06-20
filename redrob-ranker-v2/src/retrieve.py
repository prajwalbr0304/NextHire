"""
Stage [2] — Hybrid retrieval (the "Mottainai" recall guarantee).

Default backend (zero downloads, CPU, offline, deterministic):
  * Lexical  : TF-IDF word 1-2 grams  -> stand-in for SPLADE v3 learned-sparse
  * Dense    : TruncatedSVD (LSA)      -> stand-in for Nomic Embed v1.5
  * Fusion   : Reciprocal Rank Fusion  -> same RRF the blueprint specifies

Upgrade path (documented in the blueprint, swap-in via env var):
  REDROB_EMBED_BACKEND=st  ->  sentence-transformers (Nomic / BGE / E5)

The contract is identical either way: given a JD query and N candidate docs,
return a fused shortlist of indices + a per-candidate semantic similarity used
later by the 'Semantic Seer' council scorer.
"""
from __future__ import annotations

import numpy as np

from . import config

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    _HAVE_SKLEARN = True
except Exception:  # pragma: no cover
    _HAVE_SKLEARN = False


class HybridRetriever:
    """Builds lexical + dense representations and retrieves against a JD query."""

    def __init__(self, dense_dim: int = config.DENSE_DIM):
        self.dense_dim = dense_dim
        self.backend = "lsa"
        self._fitted = False

    # ------------------------------------------------------------------
    def fit(self, docs, verbose=False):
        if not _HAVE_SKLEARN:
            raise RuntimeError(
                "scikit-learn is required for the default retriever. "
                "pip install scikit-learn"
            )
        import time as _t
        import numpy as _np

        t = _t.time()
        self.vectorizer = TfidfVectorizer(
            max_features=config.TFIDF_MAX_FEATURES,
            ngram_range=config.TFIDF_NGRAM,
            min_df=2,
            sublinear_tf=True,
            dtype=_np.float32,
        )
        self.tfidf = self.vectorizer.fit_transform(docs)          # sparse (N x V)
        if verbose:
            print(f"    [tfidf] {self.tfidf.shape} fit in {_t.time()-t:.1f}s", flush=True)

        # dense semantic representation via LSA (truncated SVD on TF-IDF).
        # Fit on a random sample for speed, then transform ALL rows (cheap matmul).
        t = _t.time()
        k = min(self.dense_dim, self.tfidf.shape[1] - 1, max(2, self.tfidf.shape[0] - 1))
        self.svd = TruncatedSVD(
            n_components=k, n_iter=config.SVD_N_ITER, random_state=config.RANDOM_SEED
        )
        n = self.tfidf.shape[0]
        if n > config.SVD_FIT_SAMPLE:
            rng = _np.random.RandomState(config.RANDOM_SEED)
            sample = rng.choice(n, config.SVD_FIT_SAMPLE, replace=False)
            self.svd.fit(self.tfidf[sample])
            dense = self.svd.transform(self.tfidf)
        else:
            dense = self.svd.fit_transform(self.tfidf)
        self.dense = normalize(dense).astype(_np.float32)
        if verbose:
            print(f"    [lsa]   {self.dense.shape} fit+transform in {_t.time()-t:.1f}s", flush=True)
        self._fitted = True
        return self

    # ------------------------------------------------------------------
    def _query_vecs(self, query_text: str):
        q_tfidf = self.vectorizer.transform([query_text])
        q_dense = normalize(self.svd.transform(q_tfidf))
        return q_tfidf, q_dense

    # ------------------------------------------------------------------
    def retrieve(self, query_text: str, shortlist_size: int = config.SHORTLIST_SIZE):
        """Return (shortlist_idx, dense_sim, lexical_sim) for the JD query.

        dense_sim / lexical_sim are full-length arrays (one score per candidate)
        in [0, 1]; shortlist_idx is the RRF-fused top-`shortlist_size` indices.
        """
        assert self._fitted, "call fit() first"
        q_tfidf, q_dense = self._query_vecs(query_text)

        # lexical similarity = cosine on (already L2-normalised) tf-idf rows
        lexical = (self.tfidf @ q_tfidf.T).toarray().ravel()
        lexical = np.clip(lexical, 0.0, None)

        # dense similarity = cosine on LSA vectors
        dense = (self.dense @ q_dense.T).ravel()
        dense = np.clip(dense, 0.0, None)

        n = len(lexical)
        k = config.RRF_K
        lex_rank = np.argsort(-lexical)
        den_rank = np.argsort(-dense)
        rrf = np.zeros(n)
        # reciprocal rank fusion across the two (three in the upgraded backend) signals
        for pos, idx in enumerate(lex_rank):
            rrf[idx] += 1.0 / (k + pos + 1)
        for pos, idx in enumerate(den_rank):
            rrf[idx] += 1.0 / (k + pos + 1)

        shortlist = np.argsort(-rrf)[:shortlist_size]
        return shortlist, dense, lexical


def build_retriever(docs, verbose=False):
    return HybridRetriever().fit(docs, verbose=verbose)
