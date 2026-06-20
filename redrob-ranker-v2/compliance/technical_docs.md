# Technical Documentation — Redrob Ranker v2.0

*Prepared in the spirit of the EU AI Act (Regulation 2024/1689), Annex IV
technical-documentation requirements for high-risk AI systems used in employment
(Annex III, point 4). This is a hackathon proof-of-concept, not a placed-on-market
product, but the documentation discipline is part of the design.*

## 1. System purpose & classification
- **Purpose:** rank candidates for a specific job description, returning an
  ordered top-100 shortlist with human-readable justifications.
- **Classification:** high-risk (employment / worker management).
- **Role of the system:** decision *support*. Output is a ranked
  **recommendation**; a human recruiter makes the actual hiring decision
  (Art. 14 human oversight).

## 2. Data
- **Input:** `candidates.jsonl` — 100,000 synthetic candidate profiles
  (profile, career history, education, skills, 23 behavioural signals).
- **No personal data leaves the machine.** The ranking step makes zero network
  calls; no candidate data is sent to any hosted LLM.
- **Known data-quality issues handled:** missing GitHub (~65%), missing/optional
  skill durations, sparse behavioural signals — all defaulted defensively.

## 3. Algorithm
- **Council of Nine** ensemble of nine interpretable sub-scorers (see
  `src/council.py`). Each scorer's weight is documented in `src/config.py`.
- **Fusion:** `core = Σ wᵢ·scorerᵢ`, gated by integrity and negative-screen
  multipliers and a bounded behavioural-availability multiplier.
- **No opaque deep model is used in the default pipeline** — every score is
  attributable to named features (interpretability by construction).

## 4. Risk management
- **Honeypot / fraud risk:** conservative integrity layer (`src/integrity.py`)
  floors logically impossible profiles; flag rate monitored per run.
- **Keyword-stuffing / gaming risk:** skills are gated by an
  endorsement × duration × assessment trust factor; wrong-role titles with
  unverified skills are penalised.
- **Metric degradation:** unit tests (`tests/`) encode the JD's own trap
  examples and run in CI.

## 5. Fairness & non-discrimination
- Per-run **disparate-impact audit** across region and institution tier
  (`src/fairness.py`), logged to the audit trail.
- **Design choice:** we audit and log rather than forcibly re-rank, to avoid
  silently overriding genuine merit; a bounded DELTR-style adjustment is
  available where legal parity is mandated.
- We deliberately **do not infer gender** for scoring.
- **Note:** a strong region skew toward India is *expected and lawful here*
  because the JD explicitly targets Pune/Noida and Tier-1 Indian cities; the
  audit records this rather than masking it.

## 6. Logging & traceability
- Every run writes an immutable JSON record to `compliance/audit_trail/`
  (input fingerprint, weights, honeypot count, runtime, fairness report).

## 7. Human oversight
- The system never auto-rejects or auto-hires. Confidence language in the
  reasoning flags lower-certainty rankings for closer human review.

## 8. Accuracy, robustness, reproducibility
- Deterministic (fixed seeds, stable sorts); reproduced from a single command.
- CPU-only, offline, ~90s on 100K candidates within a 16 GB budget.
