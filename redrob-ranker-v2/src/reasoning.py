"""
Stage [10] — Grounded reasoning generation.

Produces a 1-2 sentence justification per candidate that passes all six Stage-4
manual-review checks:
  * specific facts (years, current title, named verified skills, signal values)
  * connects to JD requirements
  * acknowledges honest concerns where they exist
  * no hallucination (only verified skills are named)
  * varied across candidates (driven by each profile's own salient features)
  * tone matches rank (top picks confident; filler honest about being marginal)
"""
from __future__ import annotations

from typing import Dict

from .skills_verify import verified_relevant_skills


def _confidence_word(score: float) -> str:
    if score >= 0.80:
        return "high-confidence fit"
    if score >= 0.62:
        return "strong fit"
    if score >= 0.45:
        return "moderate fit"
    return "marginal fit"


def generate(c: dict, f: Dict, council: Dict, integrity, score: float,
             rank: int, jd: dict) -> str:
    p = c.get("profile", {}) or {}
    title = p.get("current_title") or "Professional"
    yoe = f["yoe"]
    rats = council["rationales"]

    # ---- lead clause: identity + experience ----
    lead = f"{title} with {yoe:.1f} yrs"

    # ---- the single most decisive positive signal for THIS candidate ----
    parts = council["parts"]
    drivers = sorted(parts.items(), key=lambda kv: -kv[1])
    top_key = drivers[0][0]
    driver_msg = rats.get(top_key, "")

    # ---- name real, verified skills (never hallucinate) ----
    vskills = verified_relevant_skills(c, jd, top=3)
    skills_clause = ""
    if vskills:
        skills_clause = "; verified " + ", ".join(vskills)

    # ---- honest concern (Kintsugi: name the flaw, don't hide it) ----
    concerns = []
    if integrity[2]:
        concerns.append(integrity[2][0])
    if f["cur_title_neg"]:
        concerns.append("non-engineering current role")
    if f["services_only"]:
        concerns.append("services-only background")
    if f["days_inactive"] > 120:
        concerns.append(f"inactive ~{f['days_inactive']}d")
    elif f["response_rate"] < 0.2:
        concerns.append(f"low recruiter response ({f['response_rate']:.2f})")
    if f["avg_tenure_months"] and f["avg_tenure_months"] < 18 and f["n_roles"] > 1:
        concerns.append("frequent job changes")
    if f["notice_days"] > 60:
        concerns.append(f"{int(f['notice_days'])}d notice")

    conf = _confidence_word(score)

    # ---- assemble, tone matched to rank ----
    body = f"{lead}; {driver_msg}{skills_clause}."
    if rank <= 25:
        msg = f"{body} {conf.capitalize()}"
        if concerns:
            msg += f", with one concern: {concerns[0]}."
        else:
            msg += "."
    else:
        if concerns:
            msg = f"{body} {conf.capitalize()} but limited by {concerns[0]}."
        else:
            msg = f"{body} {conf.capitalize()}; included as lower-tier match."

    # keep it tidy and within ~2 sentences
    return " ".join(msg.split())
