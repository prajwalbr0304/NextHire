"""
Stage [3 helper] — Skills verification (anti-skillfishing).

Real platforms verify claims against credential issuers and assessment results.
Here we expose the named, *verified* JD-relevant skills for a candidate so the
reasoning layer never hallucinates a skill the candidate doesn't actually hold,
and so the Mask-Piercer can distinguish a claim from a credential.
"""
from __future__ import annotations

from typing import List

from .features import _lower

# Issuers we treat as trustworthy for certification verification.
KNOWN_ISSUERS = {
    "aws", "amazon", "google", "microsoft", "azure", "coursera", "deeplearning.ai",
    "stanford", "nvidia", "databricks", "ibm", "meta", "huggingface", "oracle",
}

PROF = {"beginner": 0.4, "intermediate": 0.65, "advanced": 0.85, "expert": 1.0}


def verified_relevant_skills(c: dict, jd: dict, top: int = 4) -> List[str]:
    """Return the candidate's best *verified* JD-relevant skill names.

    'Verified' == listed AND backed by some endorsements or usage duration, so
    we never surface a 0-endorsement / 0-duration keyword as if it were real.
    """
    must = jd.get("must_have_capabilities", [])
    out = []
    for s in (c.get("skills") or []):
        name = s.get("name") or ""
        lname = _lower(name)
        relevant = any(m in lname or lname in m for m in must)
        if not relevant:
            continue
        endo = float(s.get("endorsements") or 0)
        dur = float(s.get("duration_months") or 0)
        if endo <= 0 and dur <= 0:
            continue  # unverified claim — skip
        prof = PROF.get(_lower(s.get("proficiency")), 0.5)
        rank = prof * (1 + min(endo, 50) / 50.0 + min(dur, 48) / 48.0)
        out.append((rank, name))
    out.sort(key=lambda x: -x[0])
    return [n for _, n in out[:top]]


def certification_credibility(c: dict) -> float:
    certs = c.get("certifications") or []
    if not certs:
        return 0.0
    trusted = sum(1 for ct in certs if any(k in _lower(ct.get("issuer")) for k in KNOWN_ISSUERS))
    return min(trusted / 3.0, 1.0)
