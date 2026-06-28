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
# Re-export so `from src.retrieve import PrecomputedRetriever` keeps working; the
# class itself lives in a sklearn-free module so unpickling the frozen index at
# rank time does not import scikit-learn (see src/precomputed.py).
from .precomputed import PrecomputedRetriever  # noqa: F401

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
    def fit(self, docs, verbose=False, fast=False):
        if not _HAVE_SKLEARN:
            raise RuntimeError(
                "scikit-learn is required for the default retriever. "
                "pip install scikit-learn"
            )
        import time as _t
        import numpy as _np

        # fast mode: reduced knobs for the live-fit fallback so a cold run still
        # finishes < 5 min. Only used when build_retriever decides the pool is
        # large enough to risk the budget; the committed-index path never fits.
        ngram = config.FAST_FIT_TFIDF_NGRAM if fast else config.TFIDF_NGRAM
        svd_iter = config.FAST_FIT_SVD_N_ITER if fast else config.SVD_N_ITER
        svd_sample = config.FAST_FIT_SVD_FIT_SAMPLE if fast else config.SVD_FIT_SAMPLE
        if verbose and fast:
            print("    [retrieve] FAST fit mode (cold-path insurance)", flush=True)

        t = _t.time()
        self.vectorizer = TfidfVectorizer(
            max_features=config.TFIDF_MAX_FEATURES,
            ngram_range=ngram,
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
            n_components=k, n_iter=svd_iter, random_state=config.RANDOM_SEED
        )
        n = self.tfidf.shape[0]
        if n > svd_sample:
            rng = _np.random.RandomState(config.RANDOM_SEED)
            sample = rng.choice(n, svd_sample, replace=False)
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
        # Reciprocal rank fusion across the lexical + dense signals. Vectorized
        # via an inverse-rank scatter (inv[order] = arange): inv[i] is the 0-based
        # rank of candidate i within a signal, so 1/(k+inv+1) is that signal's RRF
        # contribution for every candidate at once. Bit-for-bit identical to
        # ranking each signal and summing in a Python loop, but ~100K× cheaper.
        lex_rank = np.argsort(-lexical)
        den_rank = np.argsort(-dense)
        inv = np.empty(n, dtype=np.intp)
        inv[lex_rank] = np.arange(n)
        rrf = 1.0 / (k + inv + 1.0)
        inv[den_rank] = np.arange(n)
        rrf += 1.0 / (k + inv + 1.0)

        shortlist = np.argsort(-rrf)[:shortlist_size]
        return shortlist, dense, lexical


class STRetriever(HybridRetriever):
    """Dense backend = sentence-transformers (Nomic / BGE / E5); lexical = TF-IDF.

    Reuses HybridRetriever.retrieve() (the RRF fusion) unchanged — only the dense
    representation and the query encoder differ, so the contract is identical.
    Used via the OFFLINE precompute step for the full pool (encoding 100K docs is
    allowed to exceed the 5-min budget there); rank.py then loads the cache.
    """

    def __init__(self, model_name: str = config.ST_MODEL_NAME, local_only: bool = True):
        super().__init__()
        # may raise (missing dep / weights) -> caught by build_retriever -> LSA.
        # In "auto" (rank-time) mode local_only=True means we NEVER touch the
        # network: an uncached model fails fast (no retries) and we fall back to
        # LSA. Only the explicit "st" precompute path (network allowed) downloads.
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, device="cpu",
                                         trust_remote_code=True,
                                         local_files_only=local_only)
        self.backend = "st"

    def fit(self, docs, verbose=False):
        if not _HAVE_SKLEARN:
            raise RuntimeError("scikit-learn is required for the lexical signal.")
        import time as _t
        import numpy as _np

        t = _t.time()
        self.vectorizer = TfidfVectorizer(
            max_features=config.TFIDF_MAX_FEATURES,
            ngram_range=config.TFIDF_NGRAM,
            min_df=2, sublinear_tf=True, dtype=_np.float32,
        )
        self.tfidf = self.vectorizer.fit_transform(docs)
        if verbose:
            print(f"    [tfidf] {self.tfidf.shape} fit in {_t.time()-t:.1f}s", flush=True)

        t = _t.time()
        emb = self.model.encode(
            docs, batch_size=64, convert_to_numpy=True,
            normalize_embeddings=True, show_progress_bar=verbose,
        )
        self.dense = emb.astype(_np.float32)
        self.dense_dim = int(self.dense.shape[1])
        if verbose:
            print(f"    [st]    {self.dense.shape} encoded in {_t.time()-t:.1f}s", flush=True)
        self._fitted = True
        return self

    def _query_vecs(self, query_text: str):
        q_tfidf = self.vectorizer.transform([query_text])
        q_dense = self.model.encode([query_text], convert_to_numpy=True,
                                    normalize_embeddings=True)
        return q_tfidf, q_dense


def build_retriever(docs, verbose=False, backend=None):
    """Resolve the dense backend safely and deterministically.

    - "lsa"  : TF-IDF + TruncatedSVD (no downloads, always available).
    - "st"   : sentence-transformers (explicit; used by precompute.py).
    - "auto" : ST for SMALL pools when it is installed, else LSA. Large pools get
               ST via the offline precompute step, never live at rank time, so the
               5-minute budget is always protected. Any failure falls back to LSA.
    """
    backend = (backend or getattr(config, "EMBED_BACKEND", "auto") or "auto").lower()
    n = len(docs)
    want_st = backend == "st" or (
        backend == "auto" and n <= getattr(config, "ST_LIVE_MAX", 20000))
    if want_st:
        try:
            # explicit "st" (precompute) may download; "auto" stays strictly offline
            local_only = backend != "st"
            return STRetriever(local_only=local_only).fit(docs, verbose=verbose)
        except Exception as e:  # missing dep / weights / OOM -> graceful LSA fallback
            if verbose:
                print(f"    [retrieve] ST backend unavailable "
                      f"({type(e).__name__}: {e}); falling back to LSA", flush=True)
    # Cold-path insurance: for large pools, use the reduced fast-fit knobs so a
    # live fit still finishes < 5 min. Small pools fit quickly with full knobs.
    fast = n >= getattr(config, "FAST_FIT_POOL_THRESHOLD", 20000)
    return HybridRetriever().fit(docs, verbose=verbose, fast=fast)
