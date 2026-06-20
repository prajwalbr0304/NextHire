"""
Stage [6] — Integrity & honeypot guard (the Integrity Warden, Yaksha Prashna).

The dataset seeds ~80 honeypots (out of 100K, i.e. ~0.08%): 'subtly impossible'
profiles. The organisers note a good ranker *naturally* avoids them, and the
disqualification threshold is >10% of the top 100. So this layer is deliberately
CONSERVATIVE: it HARD-flags only the blatantly impossible (forcing those to the
floor), and applies soft penalties for milder inconsistencies. Over-flagging
would wrongly discard legitimate strong candidates, so we err toward caution and
let the Council's evidence-based scoring push genuinely weak/odd profiles down.

Returns (integrity_score in [0,1], is_honeypot, reasons[list]).
"""
from __future__ import annotations

from typing import List, Tuple

from .features import REFERENCE_DATE, _parse_date, _lower


def check(c: dict) -> Tuple[float, bool, List[str]]:
    p = c.get("profile", {}) or {}
    career = c.get("career_history") or []
    skills = c.get("skills") or []
    edu = c.get("education") or []
    yoe = float(p.get("years_of_experience") or 0.0)

    score = 1.0
    hard = False
    reasons: List[str] = []

    # ---- HARD 1: blatant 'expert with 0 months used' pattern (>=5 skills) ----
    expert_zero = sum(
        1 for s in skills
        if "duration_months" in s
        and float(s.get("duration_months") or 0) == 0
        and _lower(s.get("proficiency")) == "expert"
    )
    if expert_zero >= 5:
        hard = True
        reasons.append(f"{expert_zero} 'expert' skills with 0 months of use (impossible)")

    # ---- HARD 2: a single role longer than the entire stated career + 3y ----
    cap = yoe * 12 + 36
    for r in career:
        dur = float(r.get("duration_months") or 0)
        if dur > cap and dur > 24:
            hard = True
            reasons.append(
                f"a single role lasts {int(dur)}mo, exceeding the whole "
                f"{yoe:.0f}y career (impossible)"
            )
            break

    # ---- HARD 3: role timeline self-contradiction ----
    for r in career:
        sd = _parse_date(r.get("start_date"))
        ed = _parse_date(r.get("end_date"))
        if sd and ed and sd > ed:
            hard = True
            reasons.append("a role starts after it ends")
            break
        if sd and (sd - REFERENCE_DATE).days > 60:
            hard = True
            reasons.append("a role starts in the future")
            break

    # ---- HARD 4: skill used far longer than the whole career ----
    for s in skills:
        if float(s.get("duration_months") or 0) > cap and float(s.get("duration_months") or 0) > 24:
            hard = True
            reasons.append(
                f"skill '{s.get('name')}' used {s.get('duration_months')}mo, "
                f"longer than the whole career (impossible)"
            )
            break

    if hard:
        return 0.0, True, reasons

    # ---- SOFT penalties (do not exclude; just lower the integrity multiplier) ----
    # role duration inconsistent with its own dates
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

    # 3-4 expert skills with zero usage: suspicious but not impossible
    if 3 <= expert_zero < 5:
        score *= 0.8
        reasons.append(f"{expert_zero} 'expert' skills with 0 months of use")

    # education ends before it starts
    for e in edu:
        sy, ey = e.get("start_year"), e.get("end_year")
        if isinstance(sy, int) and isinstance(ey, int) and ey < sy:
            score *= 0.9
            reasons.append("education ends before it starts")
            break

    return max(0.0, min(1.0, score)), False, reasons
