# Council — Next.js frontend + FastAPI backend

A Stripe-style dashboard UI for the Council-of-Nine ranking engine. The Python
ranking engine in `src/` is unchanged; it is exposed through a FastAPI service
(`api/`) and consumed by a Next.js app (`web/`).

```
web/   →  Next.js 14 + Tailwind UI  (port 3000)  ──proxy /api──▶  api/  FastAPI (port 8000)  ──▶  src/  Council of Nine
```

## Run it (two terminals)

**1. Backend** (from `redrob-ranker-v2/`):

```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

The default candidate file is read from the `REDROB_CANDIDATES` env var
(falls back to `C:\Users\prajbr\Desktop\candidates.jsonl`). Set it to your path:

```bash
set REDROB_CANDIDATES=C:\path\to\candidates.jsonl   # Windows
```

**2. Frontend** (from `redrob-ranker-v2/web/`):

```bash
npm install
npm run dev
```

Open **http://localhost:3000**, pick a role, and click **Rank candidates**.
The full 100K pool ranks in ~2 minutes (CPU, offline); the UI polls for status
and then populates the leaderboard, analytics, compliance, integrity and
job-intent views.

## Features (parity with the previous app)

- Job-role dropdown (6 roles) — ranks the whole pool best→least
- Leaderboard: composite bar, Council mini-bars, signal pills, search, pagination
- Candidate drawer: grounded reasoning, 9 Council scores + rationales, skills, career
- Analytics: score / experience distributions, company background, council averages
- Compliance & Fairness: disparate-impact tables + EU AI Act run log
- Integrity Warden: honeypot exclusion log with reasons
- Job Intent Explorer: must-have / positive / negative signals + query text
- Excel export with a selectable number of candidates
- Scoring-weights donut

## API endpoints

`GET /api/roles` · `POST /api/rank` · `POST /api/upload` · `GET /api/status` ·
`GET /api/summary` · `GET /api/leaderboard` · `GET /api/candidate/{id}` ·
`GET /api/analytics` · `GET /api/compliance` · `GET /api/honeypots` ·
`GET /api/job-intent` · `GET /api/export?n=`
