# NextHire — AI Candidate Intelligence

> Precision in every hire.

NextHire is an explainable candidate ranking engine that reads a job description
the way a senior recruiter would — weighing demonstrated delivery, role identity,
domain fit and verified skill over keyword stuffing — and returns a ranked
shortlist with a grounded, per-candidate rationale. It runs **CPU-only and fully
offline** at rank time, scores the **entire candidate pool** (not just a
shortlist), and ships with an **integrity (honeypot) screen** and an
**EU AI Act fairness audit** baked in.

- **Source:** https://github.com/prajwalbr0304/NextHire
- **Live sandbox:** https://huggingface.co/spaces/prajwalbr/NextHire
- **Container image:** `ghcr.io/prajwalbr0304/nexthire:latest`

---

## Highlights

- **The Council of Nine** — nine interpretable sub-scorers, each mapping a
  hiring-judgement principle to a measurable feature. Six are additive weights
  (semantic fit, title-vs-reality, shipped-systems evidence, verified skill,
  experience/tenure, product/domain depth); three are multiplicative gates
  (negative screen, integrity, availability).
- **Reads intent, not buzzwords** — career evidence and role identity dominate;
  the self-declared skills list is deliberately down-weighted and gated by an
  endorsement × duration × assessment trust factor (anti keyword-stuffer).
- **Integrity screen** — high-precision impossibility rules flag planted
  "honeypot" profiles (e.g. *expert in a skill with 0 months of use*, *tenure
  longer than the company has existed*, *a tool used before it was released*).
- **Fairness & compliance** — every run emits a disparate-impact (4/5ths) report
  and an immutable, timestamped audit record.
- **Fast & deterministic** — a ~1 MB frozen hybrid-retrieval index (TF-IDF + LSA,
  RRF-fused) is committed, so a full 100K-candidate run finishes in ~1–2 minutes
  on a CPU with no network calls.

## Repository layout

```
NextHire/                     # repo root (github.com/prajwalbr0304/NextHire)
├─ src/                       # Council-of-Nine engine (scoring, retrieval, integrity, fairness…)
├─ api/                       # FastAPI backend (rank API + NextAI assistant)
├─ web/                       # Next.js + Tailwind dashboard
├─ artifacts/                 # committed frozen retrieval index (~1 MB)
├─ compliance/                # fairness/audit-trail output + bias template
├─ deploy/huggingface/        # Hugging Face Spaces image
├─ rank.py                    # CLI entrypoint → submission.csv
├─ precompute.py              # offline index builder
├─ validate_submission.py     # official format validator (challenge §2–3)
├─ submission_metadata.yaml   # submission metadata (repo root, per spec §10.3)
├─ requirements.txt           # pinned, CPU-only runtime deps
├─ Dockerfile(.web)           # reproduction / full-app images
└─ .github/workflows/         # CI: build & publish the container to GHCR
```

## Quickstart — produce & validate the submission

Requires Python 3.13. Run from the repo root:

```bash
pip install -r requirements.txt
```

**1. Produce the top-100 ranking** (CPU-only, offline, ~1–2 min):

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Replace `./candidates.jsonl` with the path to the candidate pool, e.g.:

```bash
python rank.py --candidates "/path/to/candidates.jsonl" --out ./submission.csv
```

This loads the pool, runs the full Council-of-Nine over **every** candidate,
excludes honeypots, writes the top 100 (`candidate_id, rank, score, reasoning`),
and records a fairness + compliance audit. The committed index keeps the run
deterministic and offline; if the pool doesn't match the index it transparently
re-fits within the time budget.

**2. Validate the generated CSV** against the challenge format rules:

```bash
python validate_submission.py ./submission.csv
# -> "Submission is valid."
```

### Rebuilding the frozen index (optional, offline)

```bash
python precompute.py --candidates ./candidates.jsonl --backend lsa --gzip
```

## Run the web app

The dashboard (upload → pick a role → tune Council weights → rank → explore) runs
as a single container, or as API + UI in dev:

```bash
# One container (Next.js static export served by FastAPI on :7860)
docker build -f Dockerfile.web -t nexthire .
docker run --rm -p 7860:7860 nexthire        # -> http://localhost:7860
```

```bash
# Dev mode (two processes)
uvicorn api.main:app --port 8000             # backend, from repo root
cd web && npm install && npm run dev          # frontend → http://localhost:3000
```

## Configuration

- **Scoring weights, thresholds and gates** live in `src/config.py` — a single,
  documented source of truth for every knob that influences a ranking.
- **Environment** (Supabase persistence, the optional NextAI assistant) is read
  from `.env`; copy `.env.example` and fill in real values. **Never commit `.env`.**

## Deployment

`.github/workflows/deploy-web.yml` builds `Dockerfile.web` and pushes
`ghcr.io/<owner>/nexthire` to GitHub Container Registry on every push to `main`.
The Hugging Face Space pulls that same image.

## License

MIT.
