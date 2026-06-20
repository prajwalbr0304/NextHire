"""
Stage [0b] — Feature engineering.

Turns each raw candidate dict into (a) a clean text document for retrieval and
(b) a flat dict of derived numeric features consumed by the Council of Nine,
the integrity layer, and the behavioural modifier.

Pure-Python + datetime only: fast and fully reproducible on CPU.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List

# Reference "today" — fixed for deterministic recency math (dataset is mid-2026).
REFERENCE_DATE = _dt.date(2026, 6, 13)


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def _g(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _parse_date(s):
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _lower(s) -> str:
    return (s or "").lower()


# ----------------------------------------------------------------------------
# candidate document (for SPLADE/TF-IDF + dense embedding)
# ----------------------------------------------------------------------------
def build_document(c: dict) -> str:
    """Concatenate the honest, evidence-bearing text of a profile.

    Career *descriptions* are weighted (repeated) because that is where genuine
    'built/shipped a system' evidence lives — the gold the JD asks us to find.
    """
    p = c.get("profile", {}) or {}
    parts: List[str] = [
        _lower(p.get("headline")),
        _lower(p.get("summary")),
        _lower(p.get("current_title")),
        _lower(p.get("current_industry")),
    ]
    for role in (c.get("career_history") or []):
        parts.append(_lower(role.get("title")))
        parts.append(_lower(role.get("industry")))
        desc = _lower(role.get("description"))
        # weight descriptions 2x — evidence matters more than headers
        parts.append(desc)
        parts.append(desc)
    skills = [_lower(s.get("name")) for s in (c.get("skills") or [])]
    parts.append(" ".join(skills))
    for e in (c.get("education") or []):
        parts.append(_lower(e.get("field_of_study")))
        parts.append(_lower(e.get("degree")))
    return " ".join([x for x in parts if x])


# ----------------------------------------------------------------------------
# numeric / categorical features
# ----------------------------------------------------------------------------
def compute_features(c: dict, jd: dict) -> Dict:
    p = c.get("profile", {}) or {}
    sig = c.get("redrob_signals", {}) or {}
    career = c.get("career_history") or []
    skills = c.get("skills") or []

    yoe = float(p.get("years_of_experience") or 0.0)

    # --- tenure / job-hopping ---
    durations = [float(r.get("duration_months") or 0) for r in career]
    n_roles = max(len(career), 1)
    avg_tenure = (sum(durations) / n_roles) if durations else 0.0
    total_tenure_months = sum(durations)

    # --- product vs services ---
    services = jd.get("services_companies", [])
    product_inds = set(jd.get("product_industries", []))
    companies = [_lower(r.get("company")) for r in career] + [_lower(p.get("current_company"))]
    industries = [_lower(r.get("industry")) for r in career] + [_lower(p.get("current_industry"))]
    services_hits = sum(1 for comp in companies if comp and any(s in comp for s in services))
    services_only = services_hits >= max(1, len([c for c in companies if c])) and services_hits > 0
    product_hits = sum(1 for ind in industries if ind in product_inds)
    product_ratio = product_hits / max(1, len([i for i in industries if i]))

    # --- title identity ---
    pos_titles = jd.get("positive_titles", [])
    neg_titles = jd.get("negative_titles", [])
    cur_title = _lower(p.get("current_title"))
    all_titles = [cur_title] + [_lower(r.get("title")) for r in career]
    title_pos = any(any(t in title for t in pos_titles) for title in all_titles if title)
    cur_title_pos = any(t in cur_title for t in pos_titles)
    cur_title_neg = any(t in cur_title for t in neg_titles)

    # --- evidence in descriptions ---
    ev_phrases = jd.get("evidence_phrases", [])
    desc_text = " ".join(_lower(r.get("description")) for r in career)
    summary_text = _lower(p.get("summary"))
    blob = desc_text + " " + summary_text
    evidence_hits = sum(1 for ph in ev_phrases if ph in blob)

    # --- skill trust (anti keyword-stuffer) ---
    must = jd.get("must_have_capabilities", [])
    assess = sig.get("skill_assessment_scores", {}) or {}
    PROF = {"beginner": 0.4, "intermediate": 0.65, "advanced": 0.85, "expert": 1.0}
    relevant_trust = 0.0
    relevant_skill_count = 0
    raw_relevant_count = 0
    expert_zero_dur = 0
    for s in skills:
        name = _lower(s.get("name"))
        is_relevant = any(m in name or name in m for m in must)
        prof = PROF.get(_lower(s.get("proficiency")), 0.5)
        dur = float(s.get("duration_months") or 0)
        endo = float(s.get("endorsements") or 0)
        if _lower(s.get("proficiency")) == "expert" and dur == 0:
            expert_zero_dur += 1
        if is_relevant:
            raw_relevant_count += 1
            # trust = proficiency tempered by *verification* (duration + endorsements + assessment)
            dur_factor = min(dur / 24.0, 1.0)            # 2y use == full credit
            endo_factor = min(endo / 20.0, 1.0)          # 20 endorsements == full credit
            assess_factor = min((assess.get(s.get("name"), 0) or 0) / 100.0, 1.0)
            verification = max(0.15, 0.5 * dur_factor + 0.3 * endo_factor + 0.2 * assess_factor)
            relevant_trust += prof * verification
            if verification > 0.35:
                relevant_skill_count += 1

    # --- off-domain specialization ---
    offdomain = jd.get("offdomain_skills", [])
    ir_nlp = jd.get("ir_nlp_skills", [])
    skill_names = [_lower(s.get("name")) for s in skills]
    offdomain_hits = sum(1 for sn in skill_names if any(o in sn for o in offdomain))
    irnlp_hits = sum(1 for sn in skill_names if any(o in sn for o in ir_nlp))

    # --- recency / behaviour ---
    last_active = _parse_date(sig.get("last_active_date"))
    days_inactive = (REFERENCE_DATE - last_active).days if last_active else 365

    # --- location / notice ---
    pref_locs = jd.get("preferred_locations", [])
    loc = _lower(p.get("location")) + " " + _lower(p.get("country"))
    location_match = any(pl in loc for pl in pref_locs)
    notice = float(sig.get("notice_period_days") or 90)

    return {
        "yoe": yoe,
        "avg_tenure_months": avg_tenure,
        "total_tenure_months": total_tenure_months,
        "n_roles": len(career),
        "services_only": services_only,
        "services_hits": services_hits,
        "product_ratio": product_ratio,
        "title_pos": title_pos,
        "cur_title_pos": cur_title_pos,
        "cur_title_neg": cur_title_neg,
        "evidence_hits": evidence_hits,
        "relevant_trust": relevant_trust,
        "relevant_skill_count": relevant_skill_count,
        "raw_relevant_count": raw_relevant_count,
        "expert_zero_dur": expert_zero_dur,
        "offdomain_hits": offdomain_hits,
        "irnlp_hits": irnlp_hits,
        "days_inactive": days_inactive,
        "location_match": location_match,
        "notice_days": notice,
        # passthrough behavioural signals
        "open_to_work": bool(sig.get("open_to_work_flag")),
        "response_rate": float(sig.get("recruiter_response_rate") or 0.0),
        "saved_by_recruiters": float(sig.get("saved_by_recruiters_30d") or 0.0),
        "interview_completion": float(sig.get("interview_completion_rate") or 0.0),
        "profile_completeness": float(sig.get("profile_completeness_score") or 0.0),
        "github": float(sig.get("github_activity_score") if sig.get("github_activity_score") is not None else -1),
        "verified_email": bool(sig.get("verified_email")),
        "verified_phone": bool(sig.get("verified_phone")),
    }
