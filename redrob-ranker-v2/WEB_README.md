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

## New capabilities (this build)

- **Insights & Analytics** — score distribution (area), experience (bars), skills
  heatmap (proficiency grid), education analysis (degrees/fields/tiers), top skills
  (verified vs claimed), recruitment funnel, Council radar, geographic & company mix.
- **Governance & Compliance** — fairness checks, bias detection (4/5ths rule + score
  gaps), per-group fairness metrics, and a full **explainable-scoring** breakdown.
- **Compare** — pick up to 4 candidates (from the leaderboard or by search) and compare
  them in vertical category tables (overview, experience, Council scores, signals,
  skills, education, reasoning) with best-in-row highlighting.
- **Pipeline** — pick a stored ranking task from a dropdown, then create shortlists and
  add candidates to them. Backed by Supabase.
- **NextAI** — chat assistant grounded in the live rank list (provider-agnostic LLM).

## Persistence & setup (Supabase)

Every ranking run is stored automatically with a unique `task_id`: the task metadata,
the **top 200**, **shortlisted** (score ≥ 85) and **honeypot** candidates, plus three
auto-seeded shortlists.

1. In the Supabase SQL Editor, run `supabase_schema.sql` (project root) — once.
2. Copy `.env.example` → `.env` (project root) and set `NEXT_PUBLIC_SUPABASE_URL` and
   `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY`.
3. (Optional) Set `NEXTAI_PROVIDER` + `NEXTAI_API_KEY` to enable the NextAI assistant.
4. Restart the API server. New endpoints: `GET /api/db-status`, `GET /api/tasks`,
   `GET /api/tasks/{id}`, `GET /api/tasks/{id}/candidates`, `GET /api/tasks/{id}/shortlists`,
   `POST /api/shortlists`, `POST /api/shortlists/{id}/members`, `DELETE /api/shortlist-members/{id}`,
   `GET /api/nextai/status`, `POST /api/nextai/chat`.

## API endpoints

`GET /api/roles` · `POST /api/rank` · `POST /api/upload` · `GET /api/status` ·
`GET /api/summary` · `GET /api/leaderboard` · `GET /api/candidate/{id}` ·
`GET /api/analytics` · `GET /api/compliance` · `GET /api/honeypots` ·
`GET /api/job-intent` · `GET /api/export?n=`
