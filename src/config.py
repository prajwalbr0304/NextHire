"""
Central configuration for the Redrob Ranker v2.0 ("Council of Nine").

All tunable knobs live here so the pipeline is auditable end-to-end
(an EU AI Act requirement: every weight that influences a hiring decision
must be documented and inspectable).
"""
from __future__ import annotations

import os

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts")
COMPLIANCE_DIR = os.path.join(REPO_ROOT, "compliance", "audit_trail")
JD_INTENT_PATH = os.path.join(HERE, "jd_intent.json")

# ----------------------------------------------------------------------------
# Retrieval
# ----------------------------------------------------------------------------
SHORTLIST_SIZE = 4000        # candidates kept after hybrid retrieval (recall stage)
RERANK_SIZE = 200            # head size re-scored by the two-stage re-ranker

# Score the ENTIRE candidate pool with the Council of Nine, not just the RRF
# retrieval shortlist. The JD explicitly wants candidates whose profiles lack the
# surface buzzwords (a "Tier-5" who shipped a recsys at a product company) to
# still be considered, so the recall stage must never decide who gets scored.
# Retrieval still supplies each candidate's semantic-similarity signal; it just
# no longer gates scoring. Set False to restore the faster shortlist-only path.
SCORE_FULL_POOL = True
DENSE_DIM = 256              # LSA / Matryoshka dimension for the "dense" signal
TFIDF_MAX_FEATURES = 50000
TFIDF_NGRAM = (1, 2)         # uni+bigrams capture "vector search", "recsys" (capped by max_features)
SVD_FIT_SAMPLE = 40000       # fit LSA on a sample, transform all (big speed win)
SVD_N_ITER = 4
RRF_K = 60                   # Reciprocal Rank Fusion constant

# ----------------------------------------------------------------------------
# Cold-path insurance (live-fit fallback ONLY — never affects the committed
# index path, which loads a PrecomputedRetriever and never calls fit()).
# If the sandbox's candidates.jsonl ever mismatches the committed index (different
# order/subset), rank.py refits live; these reduced knobs keep that fallback under
# the 5-min budget. The ranking is still valid but may differ slightly from the
# committed-index output (a documented, acceptable trade-off for an edge case).
#   - unigrams only (skip bigrams): ~halves TF-IDF tokenization time
#   - fewer SVD iterations + smaller sample: ~halves LSA fit time
# Measured: full fit ~285s -> fast fit ~150s, leaving ample budget for scoring.
# ----------------------------------------------------------------------------
FAST_FIT_TFIDF_NGRAM = (1, 1)
FAST_FIT_SVD_N_ITER = 2
FAST_FIT_SVD_FIT_SAMPLE = 20000
FAST_FIT_POOL_THRESHOLD = 20000   # only use fast fit above this pool size

# Embedding backend: "auto" uses sentence-transformers for SMALL pools when it
# is installed, and the always-available LSA backend otherwise; "st" forces
# sentence-transformers (used by the offline precompute step); "lsa" forces LSA.
EMBED_BACKEND = os.environ.get("REDROB_EMBED_BACKEND", "auto")
ST_MODEL_NAME = os.environ.get("REDROB_ST_MODEL", "BAAI/bge-small-en-v1.5")
# In "auto" mode, live-encode with sentence-transformers only up to this many
# docs (protects the 5-min rank budget). Larger pools get ST via precompute.
ST_LIVE_MAX = int(os.environ.get("REDROB_ST_LIVE_MAX", "20000"))

# ----------------------------------------------------------------------------
# Two-stage re-rank (Stage [3b]) — a small CPU neural cross-encoder re-scores the
# top-N HEAD only (so the 5-min budget is always safe), with an automatic,
# deterministic feature-based fallback if the model is missing/over-budget.
# Weights are loaded offline (local_files_only) at rank time.
# ----------------------------------------------------------------------------
# Default "feature" (NOT "auto"): the cross-encoder weights are not committed, so
# in the Stage-3 Docker an "auto" load would attempt a network call to HuggingFace
# (violating "Network Off") and time out ~235s before falling back. The feature
# re-rank is deterministic, dependency-free, instant, and produces byte-identical
# output. Set REDROB_RERANK_BACKEND=cross-encoder only where weights are cached.
RERANK_BACKEND = os.environ.get("REDROB_RERANK_BACKEND", "feature")   # feature|cross-encoder|auto|off
RERANK_MODEL = os.environ.get("REDROB_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_TIME_BUDGET_S = float(os.environ.get("REDROB_RERANK_TIME_BUDGET_S", "120"))

# ----------------------------------------------------------------------------
# Council of Nine — fusion weights (sum need not be 1; normalised at runtime).
# These encode the JD's priorities: career evidence and role identity dominate;
# the self-declared skills list is deliberately down-weighted (anti-stuffer).
# ----------------------------------------------------------------------------
COUNCIL_WEIGHTS = {
    "semantic_seer":   0.13,   # dense/semantic JD<->profile similarity (recall; JD warns surface match is a trap)
    "name_rectifier":  0.20,   # title must match reality (Zhengming)
    "evidence_scout":  0.24,   # demonstrated "built/shipped a system" evidence (JD's dominant signal)
    "mask_piercer":    0.14,   # verified skill-trust (anti keyword-stuffer)
    "path_reader":     0.12,   # experience band + tenure stability
    "terrain_master":  0.17,   # product-vs-services + domain proximity
}
# scorers 7 (neti_neti), 8 (integrity), 9 (availability) act as
# gates / multipliers, not additive weights (see score.py).

# Behavioral-availability modifier bounds (Availability Oracle).
# Floor lowered from 0.75 -> 0.55 so dormancy/non-responsiveness bites harder
# (the JD: a perfect-on-paper candidate who is unreachable is "not available").
AVAIL_MIN = 0.55
AVAIL_MAX = 1.10

# Hard availability gate — the "ghost candidate": perfect on paper but unreachable.
# Fires only when ALL three hold, and applies an EXTRA multiplier on top of the
# bounded modifier so such a profile reliably drops out of the top of the list
# (bounded, not zeroed, so a genuinely elite candidate is demoted, not erased).
AVAIL_HARD_DAYS = 150        # inactive longer than this ...
AVAIL_HARD_RESP = 0.10       # ... AND replies to < 10% of recruiter messages ...
AVAIL_HARD_MULT = 0.55       # ... AND not open-to-work -> this extra multiplier

# Negative-screen penalty bounds (Neti-Neti Gatekeeper) — multiplicative.
NEGSCREEN_MIN = 0.40

# ----------------------------------------------------------------------------
# Experience band (from the JD: 5-9 required, 6-8 ideal).
# ----------------------------------------------------------------------------
EXP_IDEAL_LOW, EXP_IDEAL_HIGH = 6.0, 8.0
EXP_OK_LOW, EXP_OK_HIGH = 5.0, 9.0

# Job-hopping: average tenure (months) below this is penalised (JD: "hop every 1.5y").
JOBHOP_TENURE_MONTHS = 18.0

# Notice period preference (JD: sub-30 preferred, buy out up to 30).
NOTICE_PREF_DAYS = 30

# ----------------------------------------------------------------------------
# Disqualifier screen (Stage [6b]) — the JD's explicit "we will not move
# forward" gates. Each is a bounded multiplier requiring MULTIPLE corroborating
# signals, so a single keyword never sinks a candidate (protects NDCG).
# ----------------------------------------------------------------------------
DISQUAL_MULT_FLOOR = 0.20          # a screened profile keeps >= 20% of its merit
RESEARCH_ONLY_MULT = 0.30          # pure research/academia with zero production
WRAPPER_ONLY_MULT = 0.50           # recent LangChain/OpenAI-wrapper only, no prior ML
LEADERSHIP_DRIFT_MULT = 0.60       # senior who stopped shipping code (architect/mgr drift)
CLOSED_SOURCE_MULT = 0.70          # 5y+ closed-source with no external validation

RESEARCH_RATIO_MIN = 0.5           # >= half of roles must be research-coded to fire
EVIDENCE_MIN_FOR_PROD = 3          # production-evidence hits that "save" a research CV
CORE_ML_TENURE_MONTHS = 24         # months of a core-ML skill proving pre-LLM depth
LEADERSHIP_MIN_MONTHS = 18         # months in a non-IC leadership role before drift fires
LEADERSHIP_GITHUB_MAX = 10.0       # github-activity below this corroborates "no code"
CLOSED_SOURCE_MIN_YOE = 5.0        # experience needed before "no validation" matters

# ----------------------------------------------------------------------------
# Integrity / honeypot detection (Stage [6]) — high-precision impossibility
# rules aligned to submission_spec Section 7. Conservative by design: flag only
# the genuinely impossible so legitimate strong candidates are never excluded.
# (Pool-wide these flag ~80, matching the documented honeypot count.)
# ----------------------------------------------------------------------------
HONEYPOT_EXPERT_ZERO_MIN = 3            # >= this many 'expert' skills with 0 months used (pattern b)
HONEYPOT_TENURE_OVER_SPAN_MONTHS = 24   # role duration exceeding its real start->end span by more (pattern a)
HONEYPOT_TENURE_MIN_MONTHS = 36         # ... and only when the claimed duration is at least this large
HONEYPOT_TECH_AGE_MARGIN_YEARS = 3      # a skill predating its technology's first year by more than this

# ----------------------------------------------------------------------------
# Bounded ADDITIVE bonuses (never enter the normalized council core, so the
# tested gem-vs-stuffer ordering is preserved). JD: nice-to-haves "boost" but
# "won't reject you"; evaluation rigor is a stated core competency.
# ----------------------------------------------------------------------------
NICE_TO_HAVE_BONUS_MAX = 0.05      # max additive lift from JD "nice to have" skills
EVAL_RIGOR_BONUS_MAX = 0.04        # max additive lift for NDCG/MRR/MAP/A-B evidence

# ----------------------------------------------------------------------------
# Relevance bands (Stage [9b]) — coarse, grounded ordering tiers so higher-
# relevance candidates ALWAYS outrank lower ones (the MAP / P@10 requirement).
# Used only to ORDER output and assign disjoint score sub-bands; never an
# exclusion (bands are floored). All thresholds tunable here for auditability.
# ----------------------------------------------------------------------------
BAND_STRONG_TRUST = 1.5            # verified relevant-skill trust for STRONG band
BAND_STRONG_EV = 4                 # domain-anchored evidence hits for STRONG band
BAND_WEAK_TRUST = 0.3              # below this (+ no evidence/title) -> WEAK band
BAND_DISQUAL_WEAK = 0.5            # disqualifier_mult <= this -> forced WEAK band
# disjoint output sub-bands (guarantee global non-increasing score across tiers)
BAND_RANGES = {2: (0.70, 0.99), 1: (0.45, 0.69), 0: (0.05, 0.44)}

# Preferred locations (JD: Pune/Noida + Tier-1 Indian cities).
PREFERRED_LOCATIONS = [
    "pune", "noida", "hyderabad", "mumbai", "delhi", "gurgaon",
    "gurugram", "bangalore", "bengaluru", "ncr",
]

# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
TOP_N = 100                  # the contest requires exactly the top 100
RANDOM_SEED = 13             # determinism (Stage-3 reproduction)
