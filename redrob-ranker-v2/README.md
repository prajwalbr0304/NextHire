# Redrob Ranker v2.0 — "Council of Nine"

An intelligent candidate **ranking engine** for the Redrob *Intelligent Candidate
Discovery & Ranking Challenge*. It **reads profiles instead of counting keywords**:
career evidence and role identity dominate the score, the self-declared skills
list is deliberately down-weighted and gated by a verification trust factor, a
conservative integrity layer floors impossible **honeypots**, and a bounded
behavioural modifier separates engaged candidates from dormant ones.

> Top ranks on the full 100K pool are genuine Staff/Lead/Senior ML, AI, NLP and
> Search engineers with **verified** retrieval/ranking skills — not the
> keyword-stuffing "HR Manager with 9 AI skills" that the sample submission
> (deliberately) puts at rank 1.

---

## Quick start

```bash
# 1. install (CPU-only, offline at rank time)
pip install -r requirements.txt

# 2. produce the top-100 submission CSV (~25s on the full 100K pool, CPU)
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# 3. validate against the official rules
python validate_submission.py submission.csv      # -> "Submission is valid."

# 4. run the test suite (traps, format, honeypots)
pytest tests/ -q
```

`rank.py` is the **single reproduce command**. It loads the small committed
retrieval index (`artifacts/`, ~1 MB) and runs the whole pipeline end-to-end,
CPU-only, with **no network calls**, in **~25s** for 100,000 candidates — far
inside the 5-minute / 16 GB budget. See **Performance & reproduction** below for
how the index is built and the from-scratch fallback.

### Performance & reproduction (Stage-3 sandbox)

The ranking step is reproduced in a CPU-only, no-network, ≤16 GB, ≤5-min Docker
sandbox, so the one-time retrieval fit (TF-IDF + LSA over 100K docs, ~285s) is
done **offline** and its result is **committed** as a tiny, deterministic index:

```bash
# offline, once (compute allowed here): build & commit the frozen index
python precompute.py --candidates candidates.jsonl --backend lsa --gzip
#   -> artifacts/retriever.pkl.gz      (~1 MB: JD-specific shortlist + similarities)
#   -> artifacts/candidate_ids.pkl.gz  (row-alignment guard)
```

At rank time `rank.py` loads that index and **replays the exact retrieval**, so
the output is byte-identical to a from-scratch run while the step finishes in ~25s:

| stage (100K pool) | cold (no index) | with committed index |
|------|------|------|
| load candidates | ~14s | ~14s |
| retriever fit (TF-IDF + LSA) | ~285s | — *(skipped)* |
| index load | — | ~0.3s |
| Council scoring (4000 shortlist) | ~8s | ~8s |
| rerank + bands + reasoning + audit | <1s | <1s |
| **total** | **~5.9 min** | **~25s** |

Guarantees: the index is **deterministic** from the data (`RANDOM_SEED=13`) so a
reviewer can regenerate it identically; `rank.py` verifies the candidate
**ids/order** and the **JD query** before using it and otherwise **refits live**
(correct, but ~5.9 min — so keep the committed index to stay in budget). The
frozen index is `numpy`-only (`src/precomputed.py`), so loading it does **not**
import scikit-learn.

---

## Reproduce in a clean container (Stage-3)

A `Dockerfile` builds a CPU-only, offline image that runs the ranking step with the
committed index. `candidates.jsonl` is the organisers' data, so it is **mounted at
run time** (never baked into the image):

```bash
docker build -t redrob-ranker .

docker run --rm --network none \
  -v /abs/path/to/candidates.jsonl:/data/candidates.jsonl \
  -v "$PWD/out":/out \
  redrob-ranker
# -> ./out/submission.csv   (~25s, CPU-only; --network none proves no API calls)

# validate the result inside the same image
docker run --rm -v "$PWD/out":/out redrob-ranker \
  python validate_submission.py /out/submission.csv
```

The image installs only the pinned `requirements.txt` (no GPU / no torch), so it
builds fast and reproduces the CSV bit-for-bit.

## Hosted sandbox (small-sample demo, §10.5)

`app.py` is a Streamlit app that satisfies the mandatory sandbox requirement:
upload a small candidate sample (≤100), rank end-to-end on CPU in seconds, and
download the ranked **CSV** (`candidate_id,rank,score,reasoning`). Run locally or
deploy free to Streamlit Community Cloud or Hugging Face Spaces:

```bash
streamlit run app.py            # local
# Streamlit Community Cloud: new app -> point at app.py (installs requirements.txt).
# HuggingFace Spaces: create a Streamlit Space, push the repo; app.py is the entry.
```

---

## How it works — the Council of Nine

Nine interpretable sub-scorers, each mapping a strategic-judgement principle to a
concrete, measurable feature (see `src/council.py`):

| # | Scorer | Principle | What it measures |
|---|--------|-----------|------------------|
| 1 | Semantic Seer | Daoism / Wu Wei | dense JD↔profile semantic similarity |
| 2 | Name-Rectifier | Confucius / *Zhengming* | does the title match reality? (anti-stuffer) |
| 3 | Evidence Scout | Kautilya / *Arthashastra* | demonstrated "built / shipped a system" evidence |
| 4 | Mask-Piercer | *Honne* vs *Tatemae* | verified skill-trust (endorsements × duration × assessment) |
| 5 | Path-Reader | *Shu-Ha-Ri* / Ship of Theseus | experience-band fit + tenure stability (anti job-hopper) |
| 6 | Terrain Master | Sun Tzu | product-vs-services company + NLP/IR domain proximity |
| 7 | Neti-Neti Gatekeeper | Vedanta | negative screen (services-only, off-domain) — multiplier |
| 8 | Integrity Warden | *Yaksha Prashna* | plausibility / honeypot detection — gate |
| 9 | Availability Oracle | I Ching / Yin-Yang | behavioural availability — bounded multiplier |

**Final score** = `council_core × integrity × negative_screen × disqualifier_screen × availability + bonuses`,
then a **two-stage head re-rank** and **3-band tier calibration** (below), sorted
and tie-broken by `candidate_id` ascending (exactly the validator's invariants).

### Metric-aware ordering (`src/score.py::finalize_ranking`)

The submission is scored on `0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`,
so *order* matters as much as *set*. Two stages enforce it:

- **Stage [3b] — neural cross-encoder re-rank of the head.** The top `RERANK_SIZE`
  (200) are re-scored by a small CPU cross-encoder (`src/rerank.py`,
  `cross-encoder/ms-marco-MiniLM-L-6-v2`) for sharper **NDCG@10** ordering. It runs
  on the head only, loads weights **offline**, is **time-guarded**, and falls back
  automatically to a deterministic feature re-rank if the model is absent/over-budget.
- **Stage [9b] — 3-band relevance gate + tier-banded calibration.** Every candidate
  is placed in a grounded band — STRONG `[0.70,0.99]` / STANDARD `[0.45,0.69]` /
  WEAK `[0.05,0.44]` — so **higher-relevance always outranks lower** (Tier-3+ above
  Tier-1/2 → **MAP**; no unqualified profile in the top-10 → **P@10**), while the
  continuous within-band score keeps fine-grained NDCG position sensitivity and a
  globally non-increasing, tie-free output.

### JD disqualifier screen (`src/council.py::disqualifier_screen`)

The JD's explicit *"we will not move forward"* cases are enforced as bounded,
multi-signal multiplicative gates. Each requires **several** corroborating
signals, so no single keyword can sink a candidate (protects ranking quality):

| Gate | Fires only when (all hold) |
|------|----------------------------|
| Pure research / no production | research-dominant career **and** no build/ship evidence **and** non-product |
| Recent LLM-wrapper only | LangChain/OpenAI-wrapper skills **and** no pre-LLM core-ML depth (<24 mo) **and** thin evidence |
| Leadership / no-code drift | non-IC title (architect/manager) ≥18 mo **and** low GitHub **and** thin recent coding evidence |
| Closed-source, unvalidated | 5y+ **and** no external validation (OSS/papers/talks/certs) **and** no demonstrated delivery |

Behavioural availability is also **hardened**: the floor is lowered and a **hard
ghost-gate** demotes profiles that are both long-dormant *and* unresponsive (the
JD's "perfect on paper but not actually available"). JD *nice-to-have* skills
(LoRA/LTR/XGBoost/HR-tech/OSS) and evaluation rigor (NDCG/MRR/MAP/A-B) add small,
bounded **bonuses** — they boost but never dominate the core fit. The
keyword-stuffer guard is **list-independent**: it also catches off-list fake
titles (e.g. "Marketing Technologist") via the title↔evidence mismatch.

---

## Architecture (two-phase, blueprint Section 5)

```
OFFLINE (precompute, may exceed 5 min — result COMMITTED as a ~1 MB index)
  candidates.jsonl ─► docs ─► hybrid retriever (TF-IDF + LSA) ─► freeze JD retrieval ─► artifacts/

ONLINE  (rank.py, ~25s, CPU, no network)
  [0] load + feature engineering        src/load.py, src/features.py
  [1] JD interpretation (static)         src/jd_intent.json
  [2] load frozen index / refit          src/precomputed.py (else src/retrieve.py RRF)
  [3] Council of Nine scoring            src/council.py
  [3b] neural cross-encoder head re-rank src/rerank.py (+ feature fallback)
  [6] integrity / honeypot guard         src/integrity.py
  [7] fairness audit (EU AI Act)         src/fairness.py
  [8] behavioural-availability modifier  src/council.py (Availability Oracle)
  [9] 3-band gate + tier calibration     src/score.py (finalize_ranking)
 [10] grounded reasoning → top 100 CSV   src/reasoning.py
      + audit trail                      src/compliance.py
```

The dense/embedding backend is **pluggable and default-on with automatic
fallback**. With `sentence-transformers` installed (see
`requirements-embeddings.txt`) the dense signal uses real embeddings
(`BAAI/bge-small-en-v1.5`, CPU); without it — or if the weights are not cached —
it falls back **instantly** to the zero-download, fully-offline TF-IDF + LSA
backend. Full-pool embeddings are produced **offline** (network allowed there)
and cached, so the rank step stays offline and within budget:

```bash
pip install -r requirements.txt -r requirements-embeddings.txt   # optional, recommended
# one-time offline setup (network allowed): cache the bi-encoder + cross-encoder
REDROB_EMBED_BACKEND=st python precompute.py --candidates candidates.jsonl --backend st --warm-reranker
python rank.py --candidates candidates.jsonl --out submission.csv  # loads caches; offline
```

Both the dense bi-encoder and the cross-encoder **re-ranker** are cached in that
one-time step; `rank.py` then forces Hugging Face into offline mode, so the
ranking step never makes a network call regardless of backend (spec: *Network
Off*). If either model is unavailable, the pipeline transparently falls back
(LSA dense + deterministic feature re-rank) — it always produces a valid CSV.

---

## Repository layout

```
redrob-ranker-v2/
├── rank.py                 # entrypoint — loads frozen index, produces submission.csv
├── precompute.py           # offline: build & commit the ~1 MB frozen JD retrieval index
├── artifacts/              # COMMITTED frozen index (retriever.pkl.gz + candidate_ids.pkl.gz)
├── onnx_optimize.py        # optional: ONNX INT8 quantization (upgrade path)
├── app.py                  # Streamlit sandbox demo (mandatory sandbox link)
├── requirements.txt
├── submission_metadata.yaml
├── src/
│   ├── config.py           # all tunable weights (auditable)
│   ├── jd_intent.json      # structured JD interpretation
│   ├── load.py  features.py  retrieve.py  precomputed.py  council.py
│   ├── integrity.py  fairness.py  reasoning.py  score.py
│   ├── compliance.py  skills_verify.py
├── agents/                 # agentic orchestration (blueprint Section 8)
│   ├── orchestrator.py  specialists.py
├── compliance/             # EU AI Act technical docs + audit trail
├── requirements.txt
├── requirements-embeddings.txt   # optional sentence-transformers backend
└── tests/                  # test_traps.py, test_format.py, test_disqualifiers.py
```

---

## Why this wins (the five stages)

1. **Format** — `tests/test_format.py` enforces the validator rules in CI.
2. **Scoring** — evidence-over-claims + trap resistance + the JD disqualifier
   screen protect the top-10 (50% of the composite). Top ranks are real
   engineers, not stuffers, research-only profiles, or unreachable ghosts.
3. **Reproduction** — CPU-only, offline, deterministic, **~25s** on 100K via the
   committed index (~5.9 min from scratch); 0.04% honeypot flag rate (well under
   the 10% disqualification line).
4. **Manual review** — grounded, varied, honest reasoning with named *verified*
   skills and acknowledged concerns (no hallucination).
5. **Defend-your-work** — the Council-of-Nine framing makes every decision
   explainable and clearly our own; an EU AI Act audit trail is written each run.

---

## Configuration

All weights live in `src/config.py` and the JD interpretation in
`src/jd_intent.json` — change them in one place; the change is reflected
everywhere and recorded in the audit trail.

## License / data

The candidate dataset is the property of the hackathon organisers and is not
included in this repository.
