"""
Stage [6] — Integrity & honeypot guard (the Integrity Warden, Yaksha Prashna).

The dataset seeds ~80 honeypots (out of 100K): 'subtly impossible' profiles. The
organisers (submission_spec Section 7) name two patterns explicitly:
  (a) "8 years of experience at a company founded 3 years ago"  (tenure that
      cannot fit the role's actual calendar window), and
  (b) "expert proficiency in 10 skills with 0 years used"       (expert + 0 months).

This layer flags ONLY the genuinely impossible, using high-precision rules:
  HARD 1  >= EXPERT_ZERO_MIN skills marked 'expert' with 0 months of use      (pattern b)
  HARD 2  a role whose claimed duration exceeds its real start->end window     (pattern a)
  HARD 3  a self-contradictory timeline (role starts after it ends / in future)
  HARD 4  a skill used for more years than the technology has existed          (impossible)

It deliberately does NOT compare a skill's total usage against the candidate's
*professional* years of experience: per candidate_schema.json a skill's
``duration_months`` is "Months the candidate has used this skill" (total —
academic, personal, and professional), a field distinct from
``profile.years_of_experience``. Conflating the two wrongly excludes legitimate
strong candidates (e.g. an engineer with 7y of total Elasticsearch use but 4y of
professional tenure), so that proxy is intentionally absent.

Returns (integrity_score in [0,1], is_honeypot, reasons[list]).
"""
from __future__ import annotations

from typing import List, Tuple

from . import config
from .features import REFERENCE_DATE, _parse_date, _lower

# ----------------------------------------------------------------------------
# Earliest year each (recent) technology could realistically have been used.
# Used by HARD 4: a skill whose stated duration implies first use more than
# config.HONEYPOT_TECH_AGE_MARGIN_YEARS before this year is impossible.
# Only well-known *recent* tools are listed; mature/undated skills (Python,
# Elasticsearch, Deep Learning, Information Retrieval, ...) are intentionally
# absent so they are never age-flagged. Conservative years (public availability).
# ----------------------------------------------------------------------------
TECH_FIRST_YEAR = {
    "rag": 2020,
    "peft": 2022,
    "lora": 2021,
    "qlora": 2023,
    "llamaindex": 2022,
    "langchain": 2022,
    "langgraph": 2023,
    "qdrant": 2021,
    "pinecone": 2021,
    "pgvector": 2021,
    "chromadb": 2022,
    "vllm": 2023,
    "haystack": 2020,
    "dspy": 2023,
    "autogen": 2023,
    "whisper": 2022,
    "segment anything": 2023,
    "stable diffusion": 2022,
}


def _span_months(start, end) -> int | None:
    """Calendar months between a role's start and end (end defaults to the
    reference 'today' for current roles). None when start is unparseable."""
    if start is None:
        return None
    end = end or REFERENCE_DATE
    return (end.year - start.year) * 12 + (end.month - start.month)


def check(c: dict) -> Tuple[float, bool, List[str]]:
    p = c.get("profile", {}) or {}
    career = c.get("career_history") or []
    skills = c.get("skills") or []
    edu = c.get("education") or []

    score = 1.0
    reasons: List[str] = []

    # ---- HARD 1: 'expert' proficiency with 0 months of use (pattern b) -------
    # No legitimate profile in the pool has even one such skill; a cluster of
    # >= EXPERT_ZERO_MIN is a planting signature.
    expert_zero = [
        s.get("name")
        for s in skills
        if "duration_months" in s
        and float(s.get("duration_months") or 0) == 0
        and _lower(s.get("proficiency")) == "expert"
    ]
    if len(expert_zero) >= config.HONEYPOT_EXPERT_ZERO_MIN:
        named = ", ".join(str(n) for n in expert_zero[:6])
        return 0.0, True, [
            f"{len(expert_zero)} 'expert' skills with 0 months of use ({named}) — impossible"
        ]

    # ---- HARD 2: claimed role tenure exceeds its real calendar window --------
    # "8 years at a company founded 3 years ago" (pattern a): duration_months
    # cannot exceed the actual start->end span by a wide margin.
    for r in career:
        dur = float(r.get("duration_months") or 0)
        span = _span_months(_parse_date(r.get("start_date")),
                             _parse_date(r.get("end_date")))
        if (span is not None
                and dur - span > config.HONEYPOT_TENURE_OVER_SPAN_MONTHS
                and dur > config.HONEYPOT_TENURE_MIN_MONTHS):
            return 0.0, True, [
                f"role '{r.get('title')}' claims {int(dur)}mo but its dates span "
                f"only {span}mo — impossible tenure"
            ]

    # ---- HARD 3: role timeline self-contradiction ----------------------------
    for r in career:
        sd = _parse_date(r.get("start_date"))
        ed = _parse_date(r.get("end_date"))
        if sd and ed and sd > ed:
            return 0.0, True, ["a role starts after it ends"]
        if sd and (sd - REFERENCE_DATE).days > 60:
            return 0.0, True, ["a role starts in the future"]

    # ---- HARD 4: a skill used longer than the technology has existed ---------
    margin = config.HONEYPOT_TECH_AGE_MARGIN_YEARS
    for s in skills:
        dur = float(s.get("duration_months") or 0)
        first = TECH_FIRST_YEAR.get(_lower(s.get("name")))
        if first and dur > 0:
            implied_start = REFERENCE_DATE.year - dur / 12.0
            if implied_start < first - margin:
                return 0.0, True, [
                    f"skill '{s.get('name')}' used {int(dur)}mo (since ~{implied_start:.0f}) "
                    f"but the technology only existed since ~{first} — impossible"
                ]

    # ---- SOFT penalties (do not exclude; just lower the integrity multiplier) ----
    # role duration mildly inconsistent with its own dates (within the HARD-2 band)
    for r in career:
        sd = _parse_date(r.get("start_date"))
        ed = _parse_date(r.get("end_date")) or REFERENCE_DATE
        dur = float(r.get("duration_months") or 0)
        if sd and ed:
            real = (ed.year - sd.year) * 12 + (ed.month - sd.month)
            if abs(real - dur) > 18:
                score *= 0.9
                reasons.append("a role's duration is inconsistent with its dates")
                break

    # 1-2 expert skills with zero usage: suspicious but not impossible
    if 1 <= len(expert_zero) < config.HONEYPOT_EXPERT_ZERO_MIN:
        score *= 0.85
        reasons.append(f"{len(expert_zero)} 'expert' skill(s) with 0 months of use")

    # education ends before it starts
    for e in edu:
        sy, ey = e.get("start_year"), e.get("end_year")
        if isinstance(sy, int) and isinstance(ey, int) and ey < sy:
            score *= 0.9
            reasons.append("education ends before it starts")
            break

    return max(0.0, min(1.0, score)), False, reasons
