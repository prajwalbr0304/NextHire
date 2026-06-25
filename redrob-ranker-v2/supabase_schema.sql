-- =============================================================================
-- Redrob Ranker v2.0 — Supabase schema
-- Run this ONCE in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
-- It is idempotent: safe to re-run.
--
-- Tables
--   ranking_tasks     one row per ranking run (the unique "task")
--   task_candidates   ranked results per task (top200 / shortlisted / honeypot)
--   shortlists        named shortlists linked to a task (auto-seeds 3 per task)
--   shortlist_members candidates a recruiter adds to a shortlist (Pipeline page)
-- =============================================================================

create extension if not exists "pgcrypto";

-- 1) One row per ranking run -------------------------------------------------
create table if not exists public.ranking_tasks (
  task_id        text primary key,
  name           text,
  role           text,
  file_name      text,
  file_size_mb   numeric,
  ingested       integer default 0,
  ranked         integer default 0,
  honeypots      integer default 0,
  strong_matches integer default 0,
  runtime        numeric default 0,
  weights        jsonb,
  params         jsonb,
  created_at     timestamptz default now()
);

-- 2) Ranked results captured per task (export-style payload) -----------------
--    category ∈ ('top200', 'shortlisted', 'honeypot')
create table if not exists public.task_candidates (
  id               bigint generated always as identity primary key,
  task_id          text references public.ranking_tasks(task_id) on delete cascade,
  category         text not null,
  rank             integer,
  candidate_id     text,
  score            numeric,
  current_title    text,
  current_company  text,
  years_experience numeric,
  location         text,
  country          text,
  verified_skills  text,
  council          jsonb,
  notice_days      integer,
  reasoning        text,
  created_at       timestamptz default now()
);
create index if not exists idx_task_candidates_task
  on public.task_candidates (task_id, category, rank);

-- 3) Named shortlists per task (auto-seeded: "Shortlist 1/2/3") --------------
create table if not exists public.shortlists (
  id         uuid primary key default gen_random_uuid(),
  task_id    text references public.ranking_tasks(task_id) on delete cascade,
  name       text not null,
  created_at timestamptz default now()
);
create index if not exists idx_shortlists_task on public.shortlists (task_id);

-- 4) Candidates a recruiter adds to a shortlist (Pipeline page) ---------------
create table if not exists public.shortlist_members (
  id               bigint generated always as identity primary key,
  shortlist_id     uuid references public.shortlists(id) on delete cascade,
  task_id          text,
  candidate_id     text,
  rank             integer,
  score            numeric,
  current_title    text,
  current_company  text,
  years_experience numeric,
  added_at         timestamptz default now(),
  unique (shortlist_id, candidate_id)
);
create index if not exists idx_shortlist_members_sl
  on public.shortlist_members (shortlist_id);

-- The backend uses the service_role key, which bypasses Row Level Security.
-- RLS is left disabled on these tables (single-tool, server-side access only).
