"""
Stage [9 helper] — EU AI Act audit trail.

Every ranking run writes an immutable, timestamped record: input hash, config
weights, timing, honeypot count, and the fairness report. This is the
'logging & traceability' + 'technical documentation' requirement for high-risk
hiring AI (Regulation 2024/1689).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Dict

from . import config


def _input_hash(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            # hash first 8 MB — enough to fingerprint the pool cheaply
            h.update(f.read(8 * 1024 * 1024))
    except Exception:
        h.update(b"unavailable")
    return h.hexdigest()[:16]


def write_audit(candidates_path: str, n_candidates: int, n_honeypots: int,
                runtime_s: float, fairness_report: Dict,
                backend: str) -> str:
    os.makedirs(config.COMPLIANCE_DIR, exist_ok=True)
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    record = {
        "run_timestamp_utc": ts,
        "system": "Redrob Ranker v2.0 (Council of Nine)",
        "eu_ai_act_classification": "high-risk (Annex III, employment)",
        "input_file": os.path.basename(candidates_path),
        "input_fingerprint_sha256_16": _input_hash(candidates_path),
        "n_candidates_scored": n_candidates,
        "honeypots_detected": n_honeypots,
        "runtime_seconds": round(runtime_s, 2),
        "embedding_backend": backend,
        "council_weights": config.COUNCIL_WEIGHTS,
        "availability_bounds": [config.AVAIL_MIN, config.AVAIL_MAX],
        "human_oversight": "Output is a ranked RECOMMENDATION; final hiring "
                           "decisions require human review (Art. 14).",
        "fairness_audit": fairness_report,
    }
    out = os.path.join(config.COMPLIANCE_DIR, f"audit_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return out
