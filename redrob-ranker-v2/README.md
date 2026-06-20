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

# 2. produce the top-100 submission CSV (≈90s on the full 100K pool, CPU)
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# 3. validate against the official rules
python validate_submission.py submission.csv      # -> "Submission is valid."

# 4. run the test suite (traps, format, honeypots)
pytest tests/ -q
```

`rank.py` is the **single reproduce command**. It runs the whole pipeline
end-to-end, CPU-only, with **no network calls**, comfortably inside the
5-minute / 16 GB budget (measured ~90s for 100,000 candidates).

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

**Final score** = `council_core × integrity × negative_screen × availability + soft_nudges`,
calibrated to a clean monotone band, sorted, and tie-broken by `candidate_id`
ascending (exactly the validator's invariants).

---

## Architecture (two-phase, blueprint Section 5)

```
OFFLINE (optional precompute, may exceed 5 min)
  candidates.jsonl ─► docs ─► hybrid retriever (TF-IDF lexical + LSA dense) ─► artifacts/

ONLINE  (rank.py, ≤5 min, CPU, no network)
  [0] load + feature engineering        src/load.py, src/features.py
  [1] JD interpretation (static)         src/jd_intent.json
  [2] hybrid retrieval → shortlist       src/retrieve.py   (RRF over lexical+dense)
  [3] Council of Nine scoring            src/council.py
  [6] integrity / honeypot guard         src/integrity.py
  [7] fairness audit (EU AI Act)         src/fairness.py
  [8] behavioural-availability modifier  src/council.py (Availability Oracle)
  [9] calibrate + tie-break              src/score.py
 [10] grounded reasoning → top 100 CSV   src/reasoning.py
      + audit trail                      src/compliance.py
```

The retrieval/embedding backend is **pluggable**. The default is a zero-download,
fully offline TF-IDF + LSA stand-in (fast, deterministic). To enable the heavier
2026 backends from the blueprint (Nomic Embed v1.5 / SPLADE v3 / Qwen3-Reranker),
install the optional deps in `requirements.txt` and run `precompute.py`.

---

## Repository layout

```
redrob-ranker-v2/
├── rank.py                 # entrypoint — produces submission.csv
├── precompute.py           # offline: build & cache retriever artifacts
├── onnx_optimize.py        # optional: ONNX INT8 quantization (upgrade path)
├── app.py                  # Streamlit sandbox demo (mandatory sandbox link)
├── requirements.txt
├── submission_metadata.yaml
├── src/
│   ├── config.py           # all tunable weights (auditable)
│   ├── jd_intent.json      # structured JD interpretation
│   ├── load.py  features.py  retrieve.py  council.py
│   ├── integrity.py  fairness.py  reasoning.py  score.py
│   ├── compliance.py  skills_verify.py
├── agents/                 # agentic orchestration (blueprint Section 8)
│   ├── orchestrator.py  specialists.py
├── compliance/             # EU AI Act technical docs + audit trail
└── tests/                  # test_traps.py, test_format.py
```

---

## Why this wins (the five stages)

1. **Format** — `tests/test_format.py` enforces the validator rules in CI.
2. **Scoring** — evidence-over-claims + trap resistance protects the top-10
   (50% of the composite). Top ranks are real engineers, not stuffers.
3. **Reproduction** — CPU-only, offline, deterministic, ~90s on 100K; 0.04%
   honeypot flag rate (well under the 10% disqualification line).
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
