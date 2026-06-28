"""
Stage [10] — Grounded reasoning generation.

Produces a 1-2 sentence justification per candidate that passes all six Stage-4
manual-review checks:
  * specific facts (years, current title, named verified skills, signal values)
  * connects to JD requirements
  * acknowledges honest concerns where they exist
  * no hallucination (only verified skills are named)
  * varied across candidates (driven by each profile's own salient features
    AND by deterministic per-candidate phrasing variants)
  * tone matches rank (top picks confident; filler honest about being marginal)

Variety is introduced via deterministic variant selection seeded by candidate_id,
so the same candidate always gets the same phrasing (reproducible) but adjacent
candidates read differently (not templated). Ranks/scores are computed upstream
in score.py and are NOT affected by this module — only the reasoning string varies.
"""
from __future__ import annotations

import hashlib
from typing import Dict

from .skills_verify import verified_relevant_skills


def _confidence_word(score: float, rank: int) -> str:
    """Tone calibrated by BOTH score and rank so a rank-95 candidate never reads
    as 'strong fit' (the Stage-4 rank-consistency check). Rank band dominates at
    the margins: the top-25 are allowed glowing language; the bottom band is
    honestly marginal regardless of the continuous score."""
    if rank <= 10 and score >= 0.80:
        return "high-confidence fit"
    if rank <= 25 and score >= 0.62:
        return "strong fit"
    if rank <= 60 and score >= 0.55:
        return "solid fit"
    if rank <= 80 and score >= 0.50:
        return "moderate fit"
    if rank <= 90:
        return "partial fit"
    return "marginal fit"


def _variant(seed: str, n: int) -> int:
    """Deterministic int in [0, n) from a string seed (candidate_id + salt).
    Same candidate -> same variant every run (reproducible); different candidates
    spread across variants (variety)."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % n


def generate(c: dict, f: Dict, council: Dict, integrity, score: float,
             rank: int, jd: dict) -> str:
    p = c.get("profile", {}) or {}
    title = p.get("current_title") or "Professional"
    yoe = f["yoe"]
    cid = c.get("candidate_id") or "CAND_0000000"
    rats = council["rationales"]

    # ---- the single most decisive positive signal for THIS candidate ----
    parts = council["parts"]
    drivers = sorted(parts.items(), key=lambda kv: -kv[1])
    top_key = drivers[0][0]
    driver_msg = rats.get(top_key, "")

    # ---- name real, verified skills (never hallucinate) ----
    vskills = verified_relevant_skills(c, jd, top=3)

    # ---- honest concern (Kintsugi: name the flaw, don't hide it) ----
    concerns = []
    disq = council["rationales"].get("disqualifier", "")
    if disq and disq != "no JD disqualifiers":
        concerns.append(disq.split(";")[0].strip())
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

    conf = _confidence_word(score, rank)

    # ---- deterministic variant selection (variety, not templating) ----
    lead_variants = [
        f"{title} with {yoe:.1f} yrs",
        f"{yoe:.1f}-yr {title}",
        f"{title} ({yoe:.1f} yrs)",
    ]
    skills_variants = [
        "; verified " + ", ".join(vskills) if vskills else "",
        "; named skills: " + ", ".join(vskills) if vskills else "",
        " with verified " + ", ".join(vskills) if vskills else "",
    ]
    concern_variants = [
        lambda c0: f", with one concern: {c0}.",
        lambda c0: f"; caveat: {c0}.",
        lambda c0: f" (concern: {c0}).",
    ]

    lead = lead_variants[_variant(cid + "lead", len(lead_variants))]
    skills_clause = skills_variants[_variant(cid + "sk", len(skills_variants))]
    body = f"{lead}; {driver_msg}{skills_clause}."

    # ---- assemble, tone matched to rank band ----
    if rank <= 25:
        msg = f"{body} {conf.capitalize()}"
        if concerns:
            msg += concern_variants[_variant(cid + "cn", len(concern_variants))](concerns[0])
        else:
            msg += "."
    elif rank <= 75:
        # mid-tier: honest about being a secondary match
        if concerns:
            msg = f"{body} {conf.capitalize()} but limited by {concerns[0]}."
        else:
            msg = f"{body} {conf.capitalize()}; secondary match."
    else:
        # bottom band: honestly marginal — no glowing language for rank 95
        if concerns:
            msg = f"{body} {conf.capitalize()}; {concerns[0]} caps the ceiling."
        else:
            msg = f"{body} {conf.capitalize()}; included as a lower-tier filler."

    # keep it tidy and within ~2 sentences
    return " ".join(msg.split())
