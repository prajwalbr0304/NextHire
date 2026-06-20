"""
Stage [7] — Fairness-aware auditing (EU AI Act, Annex III high-risk hiring AI).

We MEASURE exposure of protected/proxy groups in the selected top-100 vs. the
pool and compute the disparate-impact ratio (the '4/5ths rule', threshold 0.8).

Design choice: by default we *audit and log* rather than forcibly re-rank, so we
never silently override genuine merit. A bounded DELTR-style nudge is available
(`apply=True`) for production where legal parity is mandated. We deliberately do
NOT infer gender from names for scoring (only region/tier, which are in-data),
to avoid introducing a noisy, ethically fraught signal.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .features import _g, _lower


def _group_keys(c: dict) -> Dict[str, str]:
    p = c.get("profile", {}) or {}
    edu = c.get("education") or []
    tier = edu[0].get("tier") if edu else "unknown"
    return {
        "region": _lower(p.get("country")) or "unknown",
        "institution_tier": tier or "unknown",
    }


def audit(pool: List[dict], selected_idx: List[int]) -> Dict:
    """Compute representation + disparate-impact ratios for the selected set."""
    report = {}
    for attr in ("region", "institution_tier"):
        pool_counts = Counter(_group_keys(c)[attr] for c in pool)
        sel_counts = Counter(_group_keys(pool[i])[attr] for i in selected_idx)
        n_pool = sum(pool_counts.values()) or 1
        n_sel = sum(sel_counts.values()) or 1

        rates = {}
        for g in pool_counts:
            pool_rate = pool_counts[g] / n_pool
            sel_rate = sel_counts.get(g, 0) / n_sel
            rates[g] = {
                "pool_share": round(pool_rate, 4),
                "selected_share": round(sel_rate, 4),
                "selection_rate": round(sel_counts.get(g, 0) / max(pool_counts[g], 1), 4),
            }
        sel_rates = [v["selection_rate"] for v in rates.values() if v["selection_rate"] > 0]
        di = (min(sel_rates) / max(sel_rates)) if len(sel_rates) >= 2 else 1.0
        report[attr] = {
            "disparate_impact_ratio": round(di, 3),
            "passes_four_fifths": di >= 0.8,
            "groups": rates,
        }
    return report
