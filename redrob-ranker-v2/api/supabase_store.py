"""
Lightweight Supabase (PostgREST) client for persisting ranking tasks & results.

Zero extra dependencies: talks to the Supabase REST API over stdlib ``urllib``
using the service-role key (which bypasses Row Level Security, so the backend
can read/write freely). Credentials are read from the project ``.env`` file —
searched upward from this module so it works regardless of the launch cwd.

Schema is created once via ``supabase_schema.sql`` (Supabase SQL Editor).

Tables
  ranking_tasks      one row per ranking run (unique task_id)
  task_candidates    ranked results per task (top200 / shortlisted / honeypot)
  shortlists         named shortlists linked to a task
  shortlist_members  candidates added to a shortlist (Pipeline page)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional

# Optional logger injected by ranker.py (avoids a circular import at load time).
_LOGGER: Optional[Callable[[str, str], None]] = None


def set_logger(fn: Callable[[str, str], None]) -> None:
    global _LOGGER
    _LOGGER = fn


def _log(level: str, msg: str) -> None:
    if _LOGGER:
        try:
            _LOGGER(level, msg)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# .env loading (search upward from this file; also honour os.environ)
# ---------------------------------------------------------------------------
def _find_env_files() -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates: list[str] = []
    d = here
    for _ in range(5):  # walk up a few levels: api/ -> repo -> parent -> ...
        candidates.append(os.path.join(d, ".env"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return candidates


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for path in _find_env_files():
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            continue
    # os.environ wins where present
    for k in (
        "NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY",
    ):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


_ENV = _load_env()
_URL = (_ENV.get("NEXT_PUBLIC_SUPABASE_URL") or _ENV.get("SUPABASE_URL") or "").rstrip("/")
_KEY = (
    _ENV.get("NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY")
    or _ENV.get("SUPABASE_SERVICE_ROLE_KEY")
    or _ENV.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    or _ENV.get("SUPABASE_ANON_KEY")
    or ""
)
_REST = f"{_URL}/rest/v1" if _URL else ""


def env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a value from the loaded .env (or os.environ)."""
    return os.environ.get(key) or _ENV.get(key, default)


def enabled() -> bool:
    return bool(_URL and _KEY)


def status() -> dict:
    return {
        "enabled": enabled(),
        "url": _URL or None,
        "has_key": bool(_KEY),
    }


# ---------------------------------------------------------------------------
# Low-level PostgREST request
# ---------------------------------------------------------------------------
def _request(
    method: str,
    table: str,
    *,
    body: Any = None,
    params: Optional[dict] = None,
    prefer: Optional[str] = None,
    timeout: float = 20.0,
) -> Any:
    if not enabled():
        raise RuntimeError("Supabase is not configured (.env missing URL/key).")
    url = f"{_REST}/{table}"
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="*,.()")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    headers = {
        "apikey": _KEY,
        "Authorization": f"Bearer {_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Supabase {method} {table} failed: {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Supabase network error: {e.reason}") from e


def _chunked(seq: list, size: int = 500):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ---------------------------------------------------------------------------
# Writes — called when a ranking completes
# ---------------------------------------------------------------------------
def upsert_task(meta: dict) -> None:
    _request("POST", "ranking_tasks", body=meta,
             prefer="resolution=merge-duplicates,return=minimal")


def insert_candidates(rows: list[dict]) -> int:
    if not rows:
        return 0
    n = 0
    for chunk in _chunked(rows, 500):
        _request("POST", "task_candidates", body=chunk, prefer="return=minimal")
        n += len(chunk)
    return n


def seed_shortlists(task_id: str, names: list[str]) -> None:
    body = [{"task_id": task_id, "name": n} for n in names]
    _request("POST", "shortlists", body=body, prefer="return=minimal")


def save_ranking(meta: dict, top200: list[dict], shortlisted: list[dict],
                 honeypots: list[dict], seed_names: Optional[list[str]] = None) -> dict:
    """Persist a complete ranking run. Best-effort: never raises to the caller."""
    if not enabled():
        return {"ok": False, "reason": "supabase-not-configured"}
    task_id = meta["task_id"]
    try:
        upsert_task(meta)
        rows: list[dict] = []
        for r in top200:
            rows.append({**r, "task_id": task_id, "category": "top200"})
        for r in shortlisted:
            rows.append({**r, "task_id": task_id, "category": "shortlisted"})
        for r in honeypots:
            rows.append({**r, "task_id": task_id, "category": "honeypot"})
        n = insert_candidates(rows)
        seed_shortlists(task_id, seed_names or ["Shortlist 1", "Shortlist 2", "Shortlist 3"])
        _log("success", f"Supabase: stored task {task_id} ({n} candidate rows, 3 shortlists)")
        return {"ok": True, "task_id": task_id, "rows": n}
    except Exception as e:
        _log("error", f"Supabase store failed: {e}")
        return {"ok": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Reads — Pipeline page
# ---------------------------------------------------------------------------
def list_tasks(limit: int = 100) -> list[dict]:
    return _request("GET", "ranking_tasks", params={
        "select": "task_id,name,role,file_name,ranked,honeypots,strong_matches,created_at",
        "order": "created_at.desc",
        "limit": str(limit),
    }) or []


def get_task(task_id: str) -> Optional[dict]:
    rows = _request("GET", "ranking_tasks", params={
        "select": "*", "task_id": f"eq.{task_id}", "limit": "1",
    }) or []
    return rows[0] if rows else None


def task_candidates(task_id: str, category: str = "top200", limit: int = 200) -> list[dict]:
    return _request("GET", "task_candidates", params={
        "select": "*",
        "task_id": f"eq.{task_id}",
        "category": f"eq.{category}",
        "order": "rank.asc",
        "limit": str(limit),
    }) or []


def list_shortlists(task_id: str) -> list[dict]:
    sls = _request("GET", "shortlists", params={
        "select": "*", "task_id": f"eq.{task_id}", "order": "created_at.asc",
    }) or []
    # attach member counts
    for sl in sls:
        members = list_shortlist_members(sl["id"])
        sl["members"] = members
        sl["count"] = len(members)
    return sls


def create_shortlist(task_id: str, name: str) -> dict:
    rows = _request("POST", "shortlists", body={"task_id": task_id, "name": name},
                    prefer="return=representation") or []
    return rows[0] if rows else {}


def delete_shortlist(shortlist_id: str) -> None:
    _request("DELETE", "shortlists", params={"id": f"eq.{shortlist_id}"},
             prefer="return=minimal")


def list_shortlist_members(shortlist_id: str) -> list[dict]:
    return _request("GET", "shortlist_members", params={
        "select": "*", "shortlist_id": f"eq.{shortlist_id}", "order": "added_at.asc",
    }) or []


def add_shortlist_member(shortlist_id: str, member: dict) -> dict:
    body = {**member, "shortlist_id": shortlist_id}
    rows = _request("POST", "shortlist_members", body=body,
                    prefer="resolution=merge-duplicates,return=representation") or []
    return rows[0] if rows else {}


def remove_shortlist_member(member_id: int) -> None:
    _request("DELETE", "shortlist_members", params={"id": f"eq.{member_id}"},
             prefer="return=minimal")
