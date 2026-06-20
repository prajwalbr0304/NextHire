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
SHORTLIST_SIZE = 4000        # candidates kept after hybrid retrieval
RERANK_SIZE = 500            # candidates passed to the (optional) neural re-ranker
DENSE_DIM = 160              # LSA / Matryoshka dimension for the "dense" signal
TFIDF_MAX_FEATURES = 50000
TFIDF_NGRAM = (1, 1)         # unigrams keep the 100K vocab build well under budget
SVD_FIT_SAMPLE = 40000       # fit LSA on a sample, transform all (big speed win)
SVD_N_ITER = 4
RRF_K = 60                   # Reciprocal Rank Fusion constant

# Embedding backend: "auto" tries sentence-transformers, falls back to LSA.
EMBED_BACKEND = os.environ.get("REDROB_EMBED_BACKEND", "auto")
ST_MODEL_NAME = os.environ.get("REDROB_ST_MODEL", "nomic-ai/nomic-embed-text-v1.5")

# ----------------------------------------------------------------------------
# Council of Nine — fusion weights (sum need not be 1; normalised at runtime).
# These encode the JD's priorities: career evidence and role identity dominate;
# the self-declared skills list is deliberately down-weighted (anti-stuffer).
# ----------------------------------------------------------------------------
COUNCIL_WEIGHTS = {
    "semantic_seer":   0.16,   # dense/semantic JD<->profile similarity
    "name_rectifier":  0.20,   # title must match reality (Zhengming)
    "evidence_scout":  0.22,   # demonstrated "built/shipped a system" evidence
    "mask_piercer":    0.14,   # verified skill-trust (anti keyword-stuffer)
    "path_reader":     0.12,   # experience band + tenure stability
    "terrain_master":  0.16,   # product-vs-services + domain proximity
}
# scorers 7 (neti_neti), 8 (integrity), 9 (availability) act as
# gates / multipliers, not additive weights (see score.py).

# Behavioral-availability modifier bounds (Availability Oracle).
AVAIL_MIN = 0.75
AVAIL_MAX = 1.10

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
