# NextHire / Redrob Ranker v2.0 — System Report

**Product name:** NextHire (UI brand) · **Engine name:** Redrob Ranker v2.0 — "The Council of Nine"
**Tagline:** _Precision in every hire._

This document explains, end to end, an explainable candidate-discovery-and-ranking system: its approach, every component that was built, the reasoning behind each major design decision, and a precise walkthrough of how a raw resume becomes a ranked, justified recommendation. Every claim below is grounded in the actual source (`src/`, `api/`, `web/`, the CLI entry points, and the data schema).

---

## 1. Approach

### 1.1 The core idea — read a profile the way a senior recruiter does

The system's central thesis is that **keyword overlap is a trap**. A naive ranker rewards a profile that lists the right buzzwords; a good recruiter instead asks _"has this person actually built and shipped the kind of system we need, and is the title/skill story real?"_ NextHire encodes that judgement as an **interpretable ensemble of nine sub-scorers — the "Council of Nine" (Navaratna)** — defined in `src/council.py`. Each council member maps one principle of hiring judgement to one concrete, measurable feature, returns a score in `[0, 1]` (or a bounded multiplier), and emits a short honest rationale fragment.

The nine members (`src/council.py` docstring):

| # | Council member | Principle | What it measures | Role in the score |
|---|----------------|-----------|------------------|-------------------|
| 1 | **Semantic Seer** | Daoism / Wu Wei | dense JD↔profile semantic similarity | additive weight |
| 2 | **Name-Rectifier** | Confucius / Zhengming | does the title match the reality? | additive weight |
| 3 | **Evidence Scout** | Kautilya / Arthashastra | demonstrated "built/shipped a system" | additive weight |
| 4 | **Mask-Piercer** | Honne vs Tatemae | verified skill-trust (anti keyword-stuffer) | additive weight |
| 5 | **Path-Reader** | Shu-Ha-Ri / Ship of Theseus | experience band + tenure stability | additive weight |
| 6 | **Terrain Master** | Sun Tzu | product-vs-services + domain proximity | additive weight |
| 7 | **Neti-Neti Gatekeeper** | Vedanta | negative screen (define excellence by what to reject) | multiplicative gate |
| 8 | **Integrity Warden** | Yaksha Prashna | logical plausibility / honeypot detection | hard exclude + multiplier |
| 9 | **Availability Oracle** | I Ching / Yin-Yang | behavioural readiness / reachability | bounded multiplier |

Six members are **additive weights** (semantic fit, title-vs-reality, shipped-systems evidence, verified skill, experience/tenure, product/domain depth); three are **multiplicative gates** (negative screen, integrity, availability). A separate **JD Disqualifier Screen** (`disqualifier_screen` in `src/council.py`) acts as an additional multiplicative gate for the role's explicit "we will not move forward" conditions.

### 1.2 How resumes and job descriptions are understood and compared

- **The job description is pre-interpreted into structured intent.** Rather than parse a `.docx` at run time, the JD is frozen as a static artifact, `src/jd_intent.json`, whose every field maps to a council scorer: `query_text` (a dense natural-language description of the ideal hire), `must_have_capabilities`, `nice_to_have`, `positive_titles`, `negative_titles`, `evidence_verbs` + `evidence_domain`, `product_industries`, `services_companies`, `offdomain_skills`, `ir_nlp_skills`, disqualifier vocabularies (`research_titles`, `wrapper_skills`, `core_ml_skills`, `leadership_titles`, `eval_skills`, `external_validation_markers`), `preferred_locations`, and the `experience` band. This makes the comparison **auditable and network-free** at rank time.

- **Each candidate is turned into two representations** (`src/features.py`):
  1. a **clean text document** (`build_document`) — headline, summary, current title/industry, every career-role title/industry/description (descriptions weighted ×2 because that is where real "built/shipped" evidence lives), the skills list, and education fields — used for retrieval; and
  2. a **flat dictionary of derived numeric/categorical features** (`compute_features`) — years of experience, tenure stability, product-vs-services ratio, title identity flags, domain-anchored evidence hits, verified skill-trust, off-domain vs in-domain skill counts, recency/behavioural signals, and the disqualifier signals.

- **The comparison is hybrid, not purely semantic.** A hybrid retriever (`src/retrieve.py`) measures JD↔profile similarity using **both** a lexical signal (TF-IDF word 1–2-grams) **and** a dense semantic signal (LSA / Truncated SVD, or sentence-transformer embeddings when available), fused with **Reciprocal Rank Fusion (RRF)**. That single semantic-similarity number feeds the Semantic Seer; the rest of the decision is made by the structured features.

### 1.3 What ML / NLP techniques are used, and why those specifically

- **TF-IDF (1–2-gram, sublinear) lexical retrieval** — captures exact domain phrases the JD cares about ("vector search", "recsys", "learning to rank") that a purely dense model can blur. CPU-cheap, deterministic, no model download.
- **Latent Semantic Analysis (Truncated SVD over TF-IDF)** as the default **dense** embedding — gives a semantic similarity signal with zero external model weights, so the rank step is fully offline and reproducible. A **sentence-transformer bi-encoder** (`BAAI/bge-small-en-v1.5`) is a drop-in upgrade used during the offline precompute step.
- **Reciprocal Rank Fusion (RRF, k=60)** — combines the lexical and dense rankings without needing calibrated score scales; robust and parameter-light.
- **An optional cross-encoder re-ranker** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores only the top of the list for sharper ordering, with a deterministic feature-based fallback (`src/rerank.py`).
- **Rule-based, feature-driven scoring (the Council)** rather than a single learned end-to-end model — because the decision must be **explainable and inspectable** (each weight and threshold is documented in `src/config.py`), and because the most decisive signals (real delivery evidence, verified skill, title honesty) are better expressed as transparent features than hidden in opaque weights.
- **A grounded, template-with-variants reasoning generator** (`src/reasoning.py`) — produces a per-candidate justification that only ever names *verified* skills (no hallucination), seeded deterministically by `candidate_id`.

### 1.4 What fundamentally decides that one candidate outranks another

For every candidate, the system computes a single composite "fit" value and then orders by it. The fusion (in `src/score.py`, `score_pool` + `src/council.py`, `deliberate`) is:

```text
core       = Σ(councilₖ · weightₖ) / Σweightₖ           # 6 additive scorers, normalised
final_fit  = core · integrity · negative_screen · disqualifier_screen   # merit, gated
final      = final_fit · availability_modifier + soft_nudges            # readiness + logistics
```

So **relevance is decided by demonstrated delivery and role identity first** (Evidence Scout `0.24` and Name-Rectifier `0.20` carry the largest weights in `COUNCIL_WEIGHTS`), **tempered by verified-skill trust** (the self-declared skills list is deliberately down-weighted to `0.14` and gated by an endorsement × duration × assessment trust factor), and **then gated** — a logically impossible profile is removed outright, a wrong-role/keyword-stuffer profile is multiplicatively penalised, and a dormant-and-unreachable profile is demoted. Two candidates with similar paper credentials are separated by **who actually shipped systems, whose skills are verified, and who is genuinely reachable** — not by who listed more keywords.

---

## 2. What Was Built

### 2.1 The end-to-end pipeline architecture

```text
                ┌──────────────────────── OFFLINE (network allowed, one-time) ────────────────────────┐
                │  precompute.py  →  build_document() ×N  →  build_retriever() (TF-IDF + LSA/ST)        │
                │                 →  retrieve(JD query)  →  freeze shortlist + dense_sim (~1 MB)         │
                │                 →  artifacts/retriever.pkl.gz + artifacts/candidate_ids.pkl.gz         │
                └───────────────────────────────────────────────────────────────────────────────────────┘
                                                     │  committed to repo
                                                     ▼
 candidates.jsonl ──[0a load]──► [0b feature eng] ──► [2 hybrid retrieve] ──► [3 Council of Nine] ──► [6 integrity]
   (100K profiles)   load.py        features.py          retrieve.py /            council.py            integrity.py
                                  build_document          precomputed.py        (6 additive + gates)   (hard exclude)
                                  compute_features                                      │
                                                                                        ▼
 submission.csv ◄─[10 reasoning]◄─[9b band+calibrate]◄─[3b head re-rank]◄─[3→9 fuse + gate]──────────────┘
   top-100         reasoning.py       score.py             rerank.py            score.py (score_pool)
   + audit trail   gen_reason      finalize_ranking      feature/cross-enc     core·integ·neg·disq·avail
   compliance.py                                                                + soft_nudge
        │
        └──► fairness.py (4/5ths audit) ──► compliance/audit_trail/audit_<ts>.json
```

The same engine powers two front doors: a **CLI** (`rank.py`) that produces a top-100 CSV, and a **FastAPI + Next.js web app** (`api/` + `web/`) that ranks the whole pool interactively. Both call the identical final stage (`finalize_ranking` in `src/score.py`) so their orderings match.

### 2.2 Core engine modules (`src/`)

| File | What it does | Input | Output |
|------|--------------|-------|--------|
| `config.py` | **Single source of truth** for every tunable knob: retrieval sizes, council weights, availability/negative/disqualifier bounds, experience bands, honeypot thresholds, relevance-band ranges, output size, random seed. | — (constants; some via env vars) | module-level constants used everywhere |
| `jd_intent.json` | Structured interpretation of the role: `query_text`, must/nice capabilities, positive/negative titles, evidence verbs+domain nouns, product/services lists, off-domain vs IR/NLP skills, disqualifier vocabularies, preferred locations, experience band. | — (static artifact) | the `jd` dict consumed by every stage |
| `load.py` | Streams the candidate pool. `iter_candidates` / `load_candidates` parse JSONL line-by-line (or a JSON array), using `orjson` when available, with junk-line recovery (re-parses the `{…}` substring) and gzip support. | path to `.jsonl` / `.json` / `.gz` | `list[dict]` of raw candidate profiles |
| `features.py` | **Feature engineering.** `build_document(c)` → retrieval text (career descriptions weighted ×2). `compute_features(c, jd)` → flat feature dict: `yoe`, `avg_tenure_months`, `product_ratio`, `services_only`, `title_pos`/`cur_title_pos`/`cur_title_neg`, `evidence_hits` (domain-anchored), `relevant_trust`, `relevant_skill_count`, `raw_relevant_count`, `offdomain_hits`/`irnlp_hits`, `days_inactive`, `location_match`, `notice_days`, disqualifier signals, `nice_trust`, `eval_framework_hits`, and behavioural pass-throughs. Reference "today" is fixed at `2026-06-13` for deterministic recency. | one candidate dict + `jd` | a text document + a feature dict |
| `retrieve.py` | **Hybrid retrieval.** `HybridRetriever` fits TF-IDF (`max_features=50000`, ngram `(1,2)`, `min_df=2`, `sublinear_tf`) + Truncated SVD/LSA (`DENSE_DIM=256`, fit on a 40K sample, transform all); `retrieve()` computes lexical + dense cosine and fuses via **RRF (`k=60`)** returning a `SHORTLIST_SIZE=4000` shortlist plus full per-candidate `dense_sim`/`lexical_sim`. `STRetriever` swaps the dense signal for a sentence-transformer. `build_retriever()` resolves the backend safely (ST for small pools if installed, else LSA; fast-fit knobs for large live fits). | candidate documents + JD `query_text` | shortlist indices + similarity arrays |
| `precomputed.py` | `PrecomputedRetriever` — a frozen, **NumPy-only** (no scikit-learn) retriever that *replays* the offline-computed `shortlist` + `dense_sim` for the fixed JD query. Loads in milliseconds; ~1 MB on disk. | frozen arrays + `query_text` | same `(shortlist, dense_sim, lexical_sim)` contract |
| `council.py` | **The Council of Nine.** Functions `semantic_seer`, `name_rectifier`, `evidence_scout`, `mask_piercer`, `path_reader`, `terrain_master` (additive), `neti_neti`, `availability_oracle`, `disqualifier_screen` (multiplicative gates). `deliberate(f, sem_sim)` runs all of them and returns `parts`, normalised `core`, the gate multipliers, and per-scorer `rationales`. | a feature dict + semantic-similarity scalar | scores, multipliers, rationale fragments |
| `integrity.py` | **Integrity Warden.** `check(c)` applies four high-precision **HARD** impossibility rules (≥3 `expert` skills with 0 months use; role tenure exceeding its calendar span; self-contradictory/future-dated timeline; a skill used longer than its technology has existed via the `TECH_FIRST_YEAR` table) → honeypots are excluded; plus soft penalties that only lower the integrity multiplier. | one candidate dict | `(integrity_score, is_honeypot, reasons[])` |
| `skills_verify.py` | Anti-skillfishing. `verified_relevant_skills(c, jd)` returns the candidate's best JD-relevant skills that are actually backed by endorsements/usage (so reasoning never names an unverified keyword); `certification_credibility(c)` scores certs from `KNOWN_ISSUERS`. | candidate + `jd` | verified skill names; cert credibility `[0,1]` |
| `score.py` | **Fusion, gating, re-rank, calibration, ordering.** `score_pool()` orchestrates the whole rank: retrieve → score every candidate → exclude honeypots → fuse `core·integrity·neg·disqualifier·availability + soft_nudge`. `finalize_ranking()` runs the head re-rank, assigns 3 relevance bands (`relevance_band`), and calibrates scores into disjoint per-band ranges (`_assign_banded_scores`) so the output is globally non-increasing by rank. `_soft_nudge()` adds bounded location/notice/nice-to-have/eval-rigor bonuses. | candidates + `jd` + retriever | ranked records + run stats |
| `rerank.py` | **Two-stage head re-rank.** `rerank(jd, head)` returns a sharper relevance score for the top `RERANK_SIZE=200`. Default `feature` backend (`_feature_scores`: a deterministic blend of semantic/evidence/mask/name with bounded availability); optional offline `cross-encoder` backend, time-budgeted with automatic fallback. | the head records + `jd` | one relevance score per head record (or `None`) |
| `reasoning.py` | **Grounded reasoning.** `generate(...)` writes a 1–2-sentence justification per candidate: names only *verified* skills, surfaces the single most decisive driver, honestly states concerns (disqualifiers, integrity flags, services-only, dormancy, job-hopping, notice), and tone-matches the rank band. Variety via deterministic `md5(candidate_id)` variant selection (reproducible, non-templated). | candidate + features + council decision + rank/score | a reasoning string |
| `roles.py` | **Role catalogue for the UI.** Wraps `jd_intent.json` as the primary `BASE` role and defines five additional generalised roles (Software/Backend, Data Scientist, Frontend/Full-Stack, DevOps/Cloud, Product/Project Manager), each overriding the discriminative fields while sharing the generic ones, so the same engine serves any role. | role name | a role-specific `jd` dict |
| `fairness.py` | **Fairness audit.** `audit(pool, selected_idx)` computes representation and the **disparate-impact (4/5ths) ratio** for `region` and `institution_tier`; deliberately does **not** infer gender/name. | pool + selected indices | per-attribute DI report |
| `compliance.py` | **EU AI Act audit trail.** `write_audit(...)` writes an immutable, timestamped JSON record (input fingerprint, weights, all gate thresholds, honeypot counts by rule, fairness report, human-oversight note) to `compliance/audit_trail/`. | run metadata + fairness report | `audit_<timestamp>.json` |

### 2.3 Entry-point scripts (repo root)

- **`rank.py`** — the single documented command. Forces Hugging Face offline mode *before* any model import, loads the JD and candidates, opportunistically loads the committed index (`_load_cached_retriever` verifies pool size, `candidate_id` order, and `query_text` — refitting live on any mismatch), runs `score_pool`, performs the fairness + compliance audit, and writes `submission.csv` (`candidate_id, rank, score, reasoning`). Input/Output: `--candidates path.jsonl` → `--out submission.csv`.
- **`precompute.py`** — the offline half. Builds documents, fits the hybrid retriever (LSA or sentence-transformers via `--backend`), freezes the retrieval result for the fixed JD into a ~1 MB `PrecomputedRetriever`, and writes `artifacts/retriever.pkl(.gz)` + `artifacts/candidate_ids.pkl(.gz)`. Optional `--warm-reranker` caches the cross-encoder.
- **`onnx_optimize.py`** — optional upgrade path: exports a sentence-transformer/reranker to ONNX with INT8 dynamic quantization for faster CPU inference. Not required to run `rank.py`.
- **`validate_submission.py`** — the official format validator: header must equal `candidate_id,rank,score,reasoning`, exactly 100 data rows, `CAND_XXXXXXX` ids unique, ranks 1–100 unique, **score non-increasing by rank**, ties broken by `candidate_id` ascending.

### 2.4 Committed artifacts & compliance outputs

- **`artifacts/retriever.pkl.gz`** and **`artifacts/candidate_ids.pkl.gz`** — the ~1 MB frozen retrieval index + row-aligned id list, enabling a deterministic, offline rank.
- **`compliance/bias_audit_template.json`** — documents what the bias record contains (attributes audited: `region`, `institution_tier`; attributes explicitly *not* used: gender/name; metric: disparate-impact ratio; 4/5ths threshold `0.8`; audit-and-log intervention policy).
- **`compliance/audit_trail/audit_<ts>.json`** — the live per-run record (a committed example shows 100,000 scored, 80 honeypots by rule, weights, gate bounds, and the region/tier disparate-impact report).

### 2.5 API backend (`api/`)

| File | Role |
|------|------|
| `main.py` | FastAPI app + routes: `/api/roles`, `/api/stage` (chunked upload), `/api/rank`, `/api/status`, `/api/summary`, `/api/leaderboard`, `/api/candidate/{id}`, `/api/analytics`, `/api/compliance`, `/api/honeypots`, `/api/job-intent`, `/api/export` (Excel), Supabase-backed tasks/shortlists, and the NextAI chat endpoints. In production it also serves the statically-exported Next.js UI from `web_out/`. |
| `ranker.py` | The ranking **service**: runs the `src/` engine in a background thread (`_do_rank`), keeps the **entire** ranked pool in memory (`STATE`), and exposes derived views — leaderboard, candidate `detail` (with `_candidate_insights`: strengths/weaknesses, a composite risk score, must-have coverage, similar-role match, score breakdown), `analytics` (histograms, skill heatmap, tiers, funnel, education, locations), `compliance` (augmented fairness metrics + scoring explainer), `honeypots` (structured violation records via `_classify_honeypot`), `job_intent` (role confidence + retrieval config), and Excel export. Applies UI weight/param overrides per run and reuses `finalize_ranking` so the dashboard order equals the CLI order. |
| `nextai.py` | Provider-agnostic LLM assistant (OpenAI / Gemini / Anthropic, stdlib `urllib` only). Answers recruiter questions strictly from a compact JSON context built from the live ranking; if no key is configured it returns a local data snapshot. |
| `supabase_store.py` | Zero-dependency PostgREST client (stdlib `urllib`, service-role key) that persists each ranking run and its results/shortlists; reads `.env` searched upward from the module. |

### 2.6 Web dashboard (`web/` — Next.js 14 + React 18 + Tailwind)

A single-page app (`app/page.tsx`) with a typed API client (`lib/api.ts`, `lib/types.ts`) and a sidebar (`components/Sidebar.tsx`) exposing these views:

- **Candidates** — upload pool → pick role → tune weights → rank → paginated **Leaderboard** (`Leaderboard.tsx`) with search/filter/export, shortlist + compare actions, and a rich **CandidateDrawer** (`CandidateDrawer.tsx`: score ring, weighted score breakdown, strengths/weaknesses, risk assessment, missing-qualifications coverage, skills, similar roles, career timeline).
- **Insights** (`InsightsView.tsx`) — analytics charts: score & experience distributions, verified-vs-claimed top skills, quality tiers, proficiency heatmap, education breakdown, product-vs-services, council radar, recruitment funnel, geography.
- **Role** (`RoleView.tsx`) — the model's JD interpretation: a confidence ring (skill coverage / title clarity / noise rejection), parsed must/nice/positive/negative signals, the retrieval query and config, weight breakdown, and signal-conflict warnings.
- **Integrity** (`IntegrityView.tsx`) — the honeypot exclusion log: per-profile violation type, flagged skill, claimed-vs-baseline, severity, with filter/sort/CSV export and recruiter override/report actions.
- **Governance** (`GovernanceView.tsx`) — fairness status banner, disparate-impact metrics tables, bias-flag detection, the explainable-scoring formula + council/gate breakdown, and the immutable run-log JSON.
- **Compare** (`CompareView.tsx`) — up to 4 candidates side-by-side across overview, experience/availability, council scores, signals, verified skills, education, and reasoning.
- **Pipeline** (`PipelineView.tsx`) — Supabase-backed tasks and named shortlists with CSV/JSON export.
- **Audit** — the live merged frontend/backend activity log (`Logs.tsx`).
- **Controls** (`Controls.tsx`) — the weight sliders (the six additive scorers) and parameters (experience bands, notice preference, integrity/availability toggles).

### 2.7 Configuration, packaging & deployment

- **`requirements.txt`** — pinned CPU-only runtime deps (numpy, scipy, scikit-learn, orjson, PyYAML, pandas, openpyxl, FastAPI/uvicorn); **`requirements-embeddings.txt`** — optional sentence-transformers + torch for the neural backends.
- **`Dockerfile`** — the reproduction image for the **ranking step** (CPU-only, `--network none`, mounts `candidates.jsonl`, runs `rank.py`).
- **`Dockerfile.web`** — the full app in one container: builds the Next.js static export, then serves it + the FastAPI API on port `7860` (`REDROB_EMBED_BACKEND=lsa`, offline env).
- **`deploy/huggingface/`** — a thin wrapper image that pulls the GHCR build for a Hugging Face Space.
- **`.github/workflows/deploy-web.yml`** — CI that builds `Dockerfile.web` and publishes `ghcr.io/<owner>/nexthire` on every push to `main`.
- **`supabase_schema.sql`** — idempotent schema (`ranking_tasks`, `task_candidates`, `shortlists`, `shortlist_members`); **`.env.example`** — Supabase + NextAI configuration template.

---

## 3. Why It Was Built That Way

### 3.1 Why an interpretable "Council" instead of one learned end-to-end model

- **Hiring is a high-stakes, regulated decision.** The system self-classifies as EU AI Act Annex III "high-risk (employment)" (`src/compliance.py`). That regime requires that every factor influencing a decision be **documented and inspectable**. A single opaque learned ranker cannot meet that bar; nine named sub-scorers with documented weights in `src/config.py` can.
- **Each council member is a hypothesis about what matters**, expressed as a transparent function of a real feature. This makes failures debuggable (you can see exactly which scorer moved a candidate) and makes the weights **directly tunable** — the web UI literally exposes the six additive weights as sliders (`web/components/Controls.tsx`).
- **Trade-off accepted:** a hand-weighted ensemble may leave some accuracy on the table versus a fully learned model trained on labelled outcomes — but there are no trustworthy hiring-outcome labels here, and explainability + auditability are non-negotiable for the domain. The design favours transparency and correctness of *reasoning* over a black-box fit.

### 3.2 Why these weights and this feature set — what signals matter

The weights in `COUNCIL_WEIGHTS` encode the role's priorities explicitly:

- **Evidence Scout = `0.24` (highest).** The JD's dominant ask is "has shipped end-to-end systems to real users." So demonstrated delivery is weighted highest. Critically, evidence is **domain-anchored** (`compute_features`): a delivery verb ("built", "shipped", "scaled") only counts when it co-occurs with an ML/system domain noun ("recommendation system", "retrieval", "ranking"). This prevents generic management language ("led teams", "owned delivery") from inflating a non-engineer.
- **Name-Rectifier = `0.20`.** Title honesty is the second strongest signal because the classic failure mode is an off-track person (e.g. "HR Manager") wearing a wall of AI keywords. A genuine current engineering title scores `1.0`; an explicit non-engineering current title scores `0.08`.
- **Terrain Master = `0.17`.** Product-company background and NLP/IR domain proximity matter because the JD disprefers services-only consulting and off-domain (CV/speech/robotics) specialisation.
- **Mask-Piercer = `0.14` (deliberately low).** The self-declared skills list is the **easiest field to game**, so it is down-weighted and, crucially, **gated by verification**: `relevant_trust = proficiency × (0.5·duration + 0.3·endorsements + 0.2·assessment)`. A long list of "relevant" skills with near-zero verification is explicitly capped as likely keyword-stuffing.
- **Semantic Seer = `0.13`.** Pure semantic similarity is kept modest on purpose — the JD warns that surface match is a trap, so retrieval similarity informs but never dominates.
- **Path-Reader = `0.12`.** Experience-band fit (trapezoid around the JD's 6–8 ideal / 5–9 acceptable) plus tenure stability (penalising chronic job-hopping under `JOBHOP_TENURE_MONTHS=18`).

The behavioural and disqualifier signals exist because the dataset's `redrob_signals` block (see §4.1) carries real reachability data (recency, recruiter-response rate, interview/offer history) and because the JD names explicit deal-breakers.

### 3.3 Why gates are multiplicative and floored (not additive, not zeroing)

- **Multiplicative** so a serious problem scales down the *whole* merit score rather than subtracting a fixed amount — a keyword-stuffer's high semantic score shouldn't survive just because one additive penalty is small.
- **Floored** (`NEGSCREEN_MIN=0.40`, `DISQUAL_MULT_FLOOR=0.20`, availability floor `AVAIL_MIN=0.55`) so a single signal can **demote but never annihilate** a genuinely strong candidate. This protects ranking quality: a borderline signal shouldn't catapult an elite candidate to the bottom.
- **Each disqualifier requires multiple corroborating signals.** For example, "pure research / no production" only fires when the research-role ratio ≥ `0.5` **and** production evidence < `3` **and** product ratio < `0.34`. The "recent LLM-wrapper only" gate needs a wrapper skill **and** low core-ML tenure **and** thin evidence **and** few relevant skills. This is a deliberate guard so **no single keyword can sink a candidate**.

### 3.4 Why a conservative integrity layer (and what it intentionally does *not* do)

- The dataset seeds a small number of "subtly impossible" honeypot profiles. The Integrity Warden (`src/integrity.py`) flags **only the genuinely impossible** with high-precision HARD rules, so legitimate strong candidates are never excluded.
- A deliberate design choice documented in the module: it does **not** compare a skill's total usage against the candidate's *professional* years of experience, because the schema defines a skill's `duration_months` as total use (academic + personal + professional), distinct from `years_of_experience`. Conflating them would wrongly exclude e.g. an engineer with 7 years of total Elasticsearch use but 4 years of professional tenure. The `TECH_FIRST_YEAR` table only lists *recent, well-dated* tools (RAG 2020, QLoRA 2023, …), so mature/undated skills are never age-flagged.
- **Trade-off:** favouring precision over recall on honeypots means a cleverly disguised fake might slip through, but the cost of falsely excluding a real top candidate is judged far worse.

### 3.5 Why hybrid retrieval with a frozen LSA index (and not a big vector DB / live LLM)

- **Lexical + dense + RRF**: lexical TF-IDF preserves exact domain phrasing the JD depends on; dense LSA captures paraphrase/semantics; RRF (`k=60`) fuses them without needing comparable score scales. This is more robust than either signal alone.
- **LSA as the default dense backend** (not a downloaded transformer) so the rank step needs **zero network and zero model weights** — making it deterministic, reproducible, and fast on CPU. Hugging Face is forced offline in `rank.py` *before* imports so an uncached model fails fast and falls back instantly rather than hanging on network retries.
- **A ~1 MB frozen `PrecomputedRetriever`** is committed instead of the ~220 MB fitted matrices: `score_pool` only consumes the `shortlist` + `dense_sim` arrays, so freezing just those reproduces a byte-identical ranking while loading in milliseconds. It lives in a **scikit-learn-free module** so unpickling never drags in the heavy library.
- **Sentence-transformers / cross-encoder / ONNX are kept as optional, env-gated upgrades** — the architecture lets you swap in heavier 2026 backends as a config change, not a rewrite, without compromising the offline default.

### 3.6 Why score the entire pool, not just the retrieval shortlist

`SCORE_FULL_POOL=True` (`src/config.py`) deliberately routes **every** candidate through the full Council, using retrieval only to supply the per-candidate semantic signal — never to gate who gets scored. The reasoning (documented in `score.py`): the JD explicitly wants buzzword-light candidates who *actually shipped* a system (a "Tier-5" who built a recsys at a product company) to remain reachable, so the recall stage must not silently drop them. A faster shortlist-only path exists behind the same flag for when recall is acceptable.

### 3.7 Why a 3-band relevance gate + disjoint score calibration

`relevance_band` + `_assign_banded_scores` (`src/score.py`) sort candidates into STRONG / STANDARD / WEAK tiers and then map each tier's internal order into a **disjoint** score sub-range (`BAND_RANGES = {2:(0.70,0.99), 1:(0.45,0.69), 0:(0.05,0.44)}`). This guarantees two properties the output contract requires: a higher-relevance candidate **always** outranks a lower-relevance one, and the final per-rank score is **globally non-increasing** — exactly the invariants `validate_submission.py` enforces (non-increasing score by rank; ties broken by `candidate_id` ascending). Bands are floored, never exclusions.

### 3.8 Why grounded, deterministic reasoning

`src/reasoning.py` only names skills returned by `verified_relevant_skills` (never hallucinating an unverified keyword), surfaces the single highest council driver, and **honestly states concerns** (the "Kintsugi" idea — name the flaw rather than hide it). Phrasing variety comes from `md5(candidate_id)`-seeded variant selection, so the same candidate always reads the same way (reproducible) while neighbours read differently (not templated). Tone is calibrated to the rank band so a low-ranked candidate never reads as a "strong fit."

### 3.9 Why fairness is audit-and-log by default

`src/fairness.py` measures disparate impact (4/5ths rule) on in-data proxy attributes (`region`, `institution_tier`) but **does not forcibly re-rank** by default, so genuine merit is never silently overridden; a bounded DELTR-style nudge is available for production where legal parity is mandated. It deliberately **refuses to infer gender from names**, avoiding a noisy, ethically fraught signal. Every run emits an immutable audit record (`src/compliance.py`) to satisfy the logging/traceability and human-oversight requirements for high-risk hiring AI.

### 3.10 Why this two-front-door architecture (CLI + web), and shared finalisation

The CLI (`rank.py`) is the lean, offline, reproducible path that emits the CSV; the web app (`api/` + `web/`) is the interactive recruiter tool. Both deliberately call the **same** `finalize_ranking` so the dashboard's order is identical to the CSV's — there is one ranking truth, not two. The web layer adds operational value (upload, weight tuning, comparison, shortlists, governance views, export) without forking the scoring logic.

---

## 4. How It Works — full pipeline walkthrough

This section traces one run from raw input to ranked, justified output, naming the actual functions, files, and parameters involved.

### 4.1 The input — candidate profile schema

Each candidate (validated by `candidate_schema.json`) is a JSON object with:

- **`candidate_id`** — `CAND_XXXXXXX` (7 digits).
- **`profile`** — `anonymized_name`, `headline`, `summary`, `location`, `country`, `years_of_experience` (0–50), `current_title`, `current_company`, `current_company_size`, `current_industry`.
- **`career_history[]`** (1–10 roles) — `company`, `title`, `start_date`, `end_date`, `duration_months`, `is_current`, `industry`, `company_size`, `description`.
- **`education[]`** (0–5) — `institution`, `degree`, `field_of_study`, `start_year`, `end_year`, `grade`, `tier` (`tier_1…tier_4`/`unknown`).
- **`skills[]`** — `name`, `proficiency` (`beginner`/`intermediate`/`advanced`/`expert`), `endorsements`, `duration_months` (total months the skill has been used).
- **`certifications[]`**, **`languages[]`** (optional).
- **`redrob_signals`** — platform behaviour: `profile_completeness_score`, `signup_date`, `last_active_date`, `open_to_work_flag`, `profile_views_received_30d`, `applications_submitted_30d`, `recruiter_response_rate` (0–1), `avg_response_time_hours`, `skill_assessment_scores` (skill→0–100), `connection_count`, `endorsements_received`, `notice_period_days` (0–180), `expected_salary_range_inr_lpa`, `preferred_work_mode`, `willing_to_relocate`, `github_activity_score` (-1 if none), `search_appearance_30d`, `saved_by_recruiters_30d`, `interview_completion_rate`, `offer_acceptance_rate` (-1 if none), `verified_email`, `verified_phone`, `linkedin_connected`.

### 4.2 Step 0 — load (`src/load.py`)

`rank.py main()` calls `load_candidates(args.candidates)`. `load.py` detects a JSON array vs JSONL (`_looks_like_json_array`), then `iter_candidates` streams line by line, parsing with `orjson` if installed. Malformed lines are recovered by re-parsing the substring from the first `{` to the last `}`; truly unparseable lines are skipped rather than crashing a long run. Output: `list[dict]`.

### 4.3 Step 0b — feature engineering (`src/features.py`)

For retrieval, `build_document(c)` concatenates (lower-cased) the headline, summary, current title/industry, then for each career role its title, industry, and **description repeated twice** (descriptions carry the real evidence), then the joined skill names and education fields.

For scoring, `compute_features(c, jd)` derives the feature dict. Key computations:

- **Tenure:** `avg_tenure = Σ duration_months / n_roles`; `total_tenure_months`.
- **Product vs services:** `services_hits` counts companies matching `jd["services_companies"]`; `services_only` is true when essentially all named companies are services firms. `product_ratio = product_hits / industries`.
- **Title identity:** `title_pos` (any `positive_titles` term in any title), `cur_title_pos` (current title matches), `cur_title_neg` (current title matches a `negative_titles` term).
- **Domain-anchored evidence:** over the concatenated career descriptions + summary blob, `domain_hits = Σ(domain noun ∈ blob)` from `jd["evidence_domain"]`; if a delivery verb from `jd["evidence_verbs"]` also appears, `evidence_hits = domain_hits + 2`, else `domain_hits` (no domain noun → ~0).
- **Skill trust (anti-stuffer):** for each skill matching `must_have_capabilities`, `prof ∈ {beginner 0.4, intermediate 0.65, advanced 0.85, expert 1.0}`, and `verification = max(0.15, 0.5·min(dur/24,1) + 0.3·min(endo/20,1) + 0.2·min(assess/100,1))`; `relevant_trust += prof·verification`; a skill counts toward `relevant_skill_count` only when `verification > 0.35`. Also tracks `raw_relevant_count` and `expert_zero_dur`.
- **Domain mix:** `offdomain_hits` / `irnlp_hits` from `offdomain_skills` / `ir_nlp_skills`.
- **Recency:** `days_inactive = (REFERENCE_DATE(2026-06-13) − last_active_date).days` (365 if missing).
- **Disqualifier signals:** `research_ratio`, `wrapper_skill_count`, `core_ml_max_tenure`, `leadership_current`/`leadership_current_months`, `has_external_validation` (markers ∨ GitHub > 0 ∨ `certification_credibility` > 0).
- **Bonuses:** `nice_trust` (verified nice-to-have skills), `eval_framework_hits` (candidate's evaluation-methodology competency, e.g. A/B testing).
- **Behavioural pass-throughs:** `open_to_work`, `response_rate`, `saved_by_recruiters`, `interview_completion`, `offer_acceptance`, `avg_response_hours`, `applications_30d`, `search_appearance_30d`, `github`, `verified_email/phone`, `notice_days`, `location_match`.

### 4.4 Step 2 — hybrid retrieval (`src/retrieve.py` / `src/precomputed.py`)

In `score_pool` (`src/score.py`): if a retriever was supplied (the committed index), it is used directly; otherwise `build_retriever(docs)` fits one.

- **Fit** (`HybridRetriever.fit`): `TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2, sublinear_tf=True)` → sparse `N×V`; then `TruncatedSVD(n_components≈256, n_iter=4, random_state=13)` fit on a 40K sample and applied to all rows, L2-normalised → dense `N×256`.
- **Retrieve** (`retrieve(query_text)`): transforms the JD `query_text`, computes `lexical = tfidf · qᵀ` and `dense = denseMatrix · q_denseᵀ` (both clipped ≥ 0), then **RRF**: for each signal it scatters inverse ranks and adds `1/(k + rank + 1)` with `k=RRF_K=60`; returns the top-`SHORTLIST_SIZE=4000` shortlist plus full `dense_sim`/`lexical_sim` arrays.
- **Cached path** (`rank.py _load_cached_retriever`): loads `artifacts/retriever.pkl.gz`, and only uses it if `dense.shape[0] == len(candidates)`, the frozen `query_text` matches the JD, and `candidate_ids.pkl.gz` equals the pool's id order — otherwise it refits live (with reduced "fast-fit" knobs above `FAST_FIT_POOL_THRESHOLD=20000`). The `PrecomputedRetriever.retrieve` simply replays the frozen `(shortlist, dense_sim, lexical_sim)`.

### 4.5 Step 3 — the Council deliberates (`src/council.py`)

`score_pool` normalises `dense_sim` to `[0,1]` across the scored set, then for each candidate index it computes `f = compute_features(...)`, `sem = normalised dense_sim`, and runs `integrity.check` (Step 6, below) **before** scoring. Survivors go to `council.deliberate(f, sem)`, which evaluates:

- `semantic_seer(sem)` → the normalised similarity, with a banded rationale.
- `name_rectifier(f)` → `0.08` (non-eng current title) / `1.0` (eng current title) / `0.6` (eng title in history) / `0.3` (no signal).
- `evidence_scout(f)` → `min(evidence_hits/12, 1)`.
- `mask_piercer(f)` → `min(relevant_trust/4, 1)`, capped at `0.35` when ≥5 relevant skills are listed but trust < 1 (stuffing signature).
- `path_reader(f)` → `band × stability`, where band is the experience trapezoid (`EXP_IDEAL 6–8`, `EXP_OK 5–9`) and stability penalises avg tenure below `JOBHOP_TENURE_MONTHS=18`.
- `terrain_master(f)` → `0.55·product_ratio + 0.45·domain`, halved if `services_only`.
- `neti_neti(f)` (gate) → starts at `1.0`, multiplies down for services-only (`×0.7`), off-domain without IR/NLP (`×0.6`), non-eng title + unverified AI skills (`×0.45`), and off-list fake-title stuffers (`×0.5`); floored at `NEGSCREEN_MIN=0.40`.
- `availability_oracle(f)` (gate) → a weighted blend of exponential recency decay (`exp(−days/45)`), recruiter response, saves, open-to-work, interview completion, offer acceptance, response speed, and engagement, mapped to `[AVAIL_MIN 0.55, AVAIL_MAX 1.10]`; a **hard ghost gate** applies an extra `×0.55` when inactive > 150 days **and** response rate < 0.10.
- `disqualifier_screen(f)` (gate) → the JD's explicit deal-breakers, each requiring multiple corroborating signals: research-only (`×0.30`), recent-wrapper-only (`×0.50`), leadership/no-code drift (`×0.60`), 5y+ closed-source with no external validation (`×0.70`); floored at `DISQUAL_MULT_FLOOR=0.20`.

`deliberate` returns `parts` (the six additive scores), the normalised `core = Σ(partₖ·weightₖ)/Σweight`, the three gate multipliers, and the `rationales`.

### 4.6 Step 6 — integrity / honeypot exclusion (`src/integrity.py`)

`integrity.check(c)` runs before council scoring. Any HARD rule returns `(0.0, True, [reason])` and the candidate is **excluded entirely** (`score_pool` does `continue` and increments `n_honeypots`, bucketed by rule via `_honeypot_rule`):

1. **expert_zero** — ≥ `HONEYPOT_EXPERT_ZERO_MIN=3` skills marked `expert` with `duration_months == 0`.
2. **tenure_over_span** — a role whose `duration_months` exceeds its `start_date→end_date` calendar span by > `24` months while the claimed duration is > `36` months.
3. **timeline** — a role that starts after it ends, or starts > 60 days in the future.
4. **tech_age** — a skill whose implied first-use year precedes its technology's first year (from `TECH_FIRST_YEAR`) by more than `HONEYPOT_TECH_AGE_MARGIN_YEARS=3`.

Soft inconsistencies (duration vs dates off by > 18 months; 1–2 expert-zero skills; education ending before it starts) only multiply the integrity score down (`×0.9`/`×0.85`), they do not exclude.

### 4.7 Step 3→9 — fusion into a single fit (`src/score.py`)

For each surviving candidate, `score_pool` computes:

```text
final_fit = core × integ[0] × neg_mult × disqualifier_mult
final     = final_fit × avail_mult + _soft_nudge(f)
raw       = max(0.0, final)
```

`_soft_nudge(f)` adds bounded additive logistics that nudge but never dominate: `+0.025` location match, `+0.015` notice ≤ `NOTICE_PREF_DAYS=30` (or `−0.015` if > 90), up to `NICE_TO_HAVE_BONUS_MAX=0.05` from verified nice-to-have skills, and up to `EVAL_RIGOR_BONUS_MAX=0.04` from evaluation-methodology competency. Each record carries `{idx, candidate_id, raw, f, dec, integ, candidate}`.

### 4.8 Step 3b + 9b — head re-rank, banding, calibration (`src/score.py` → `finalize_ranking`)

1. **Sort** all records by `(−raw, candidate_id)` and set `order = raw`.
2. **Head re-rank** — take the top `RERANK_SIZE=200` and call `rerank.rerank(jd, head)` (`src/rerank.py`). The default `feature` backend (`_feature_scores`) blends `0.34·semantic + 0.30·evidence + 0.22·mask + 0.14·name`, times the disqualifier and negative-screen multipliers, with a **bounded** availability nudge (`0.9 + 0.1·min(avail, 1.10)`) so reachability can refine but not dominate the head. The optional `cross-encoder` backend (`ms-marco-MiniLM-L-6-v2`, offline, ≤ `RERANK_TIME_BUDGET_S=120`) scores `[query, candidate_doc]` pairs and falls back to the feature blend on any error/timeout. Re-rank scores are min-max mapped back into the head's own raw range, so the head reorders internally but never crosses below the tail.
3. **Relevance bands** — `relevance_band(f, dec, integ)` assigns `2=STRONG / 1=STANDARD / 0=WEAK`. WEAK = strongly disqualified (`disqualifier_mult ≤ 0.5`), or a career non-engineer (neg title and never an eng title), or no relevant signal at all. STRONG = verified depth (`relevant_trust ≥ 1.5`) + delivery (`evidence_hits ≥ 4`) + an engineering identity, not services-dominated, not gated. Else STANDARD.
4. **Order** by `(−band, −order, candidate_id)` and take the top `TOP_N=100` (for the CSV; the dashboard keeps all).
5. **Calibrate** — `_assign_banded_scores` min-max maps each band's internal `order` into its **disjoint** range (`BAND_RANGES = {2:(0.70,0.99), 1:(0.45,0.69), 0:(0.05,0.44)}`), rounded to 4 dp, then re-sorts by `(−score, candidate_id)`. This guarantees the output is globally non-increasing by rank with ascending-id tie-breaks.

### 4.9 Step 10 — grounded reasoning (`src/reasoning.py`)

For each of the final records, `gen_reason(candidate, f, dec, integ, score, rank, jd)`:

- picks the single highest council driver (`sorted(parts)…`) and its rationale fragment;
- names up to three **verified** relevant skills via `verified_relevant_skills` (never an unverified keyword);
- assembles honest concerns (disqualifier reason, integrity flag, `cur_title_neg`, `services_only`, `days_inactive > 120`, low `response_rate`, job-hopping, long `notice_days`);
- chooses a confidence word via `_confidence_word(score, rank)` (rank band dominates, so rank-95 never reads "strong");
- selects deterministic phrasing variants from `md5(candidate_id + salt)`, so output is reproducible yet varied.

### 4.10 Step 7 + audit — fairness & compliance (`src/fairness.py`, `src/compliance.py`)

Back in `rank.py`, `fairness.audit(candidates, stats["selected_idx"])` computes, for `region` and `institution_tier`, each group's pool share, selected share, and selection rate, and the **disparate-impact ratio** = `min(selection_rate)/max(selection_rate)` with `passes_four_fifths = ratio ≥ 0.8`. Then `compliance.write_audit(...)` writes `compliance/audit_trail/audit_<ts>.json` containing the input fingerprint (SHA-256 of the first 8 MB), candidate/honeypot counts, honeypot breakdown by rule, all council weights and gate thresholds, and the fairness report, with an explicit human-oversight note (Article 14).

### 4.11 Output — the submission CSV (`rank.py write_csv`)

`write_csv(records, out_path)` emits the header `candidate_id,rank,score,reasoning` and 100 rows, score formatted to 4 dp. Running `python validate_submission.py submission.csv` confirms the invariants (exactly 100 unique ranks 1–100, `CAND_XXXXXXX` ids, non-increasing score by rank, id-ascending tie-breaks).

### 4.12 The interactive path (`api/ranker.py`, `web/`)

In the web app, `POST /api/stage` streams an uploaded pool to disk; `POST /api/rank` starts `ranker._do_rank` on a background thread. That function applies the UI's weight/parameter overrides onto `config`, builds documents, fits a retriever, scores the **whole** pool through the same Council, excludes honeypots, then calls the **same** `finalize_ranking` so the order matches the CLI. The full result is held in memory (`STATE`) and served to the dashboard: `leaderboard`, `detail` (with `_candidate_insights`: strengths/weaknesses, composite risk score, must-have coverage, similar-role matches, score breakdown), `analytics`, `compliance` (augmented fairness + the scoring explainer), `honeypots` (structured `_classify_honeypot` records), `job_intent` (role-interpretation confidence + retrieval config), and Excel `export`. Completed runs are best-effort persisted to Supabase (`supabase_store.save_ranking`), and the optional NextAI assistant (`api/nextai.py`) answers questions strictly from a compact JSON snapshot of the live ranking.

### 4.13 Determinism & reproducibility, end to end

The run is deterministic because: the JD is a static artifact; the retriever is either the committed frozen index or a seeded fit (`RANDOM_SEED=13`); recency math uses a fixed `REFERENCE_DATE`; reasoning variants are `candidate_id`-seeded; Hugging Face is forced offline so no network call can perturb results; and the final ordering/tie-breaking is fully specified. The reproduction command is a single line:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```


