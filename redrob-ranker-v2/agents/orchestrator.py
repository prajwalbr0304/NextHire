"""
Orchestrator Agent — task decomposition & coordination.

Sequences the specialist agents:
    JD Parser -> Source -> Evaluate -> Verify -> Explain -> Compliance

This mirrors the multi-agent diagram in Section 8 of the blueprint while staying
fully deterministic and offline for the contest. It is a thin coordination layer
over the same `src/` modules used by `rank.py`.
"""
from __future__ import annotations

import time
from typing import List

from src import fairness, compliance
from src.score import load_jd, score_pool


class Orchestrator:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [orchestrator] {msg}", flush=True)

    def run(self, candidates: List[dict], candidates_path: str = "in-memory"):
        t0 = time.time()

        # JD Parser Agent — load the structured intent profile
        jd = load_jd()
        self._log(f"JD Parser: intent for '{jd['role_title']}' ready")

        # Source + Evaluate + Verify + Explain agents run inside score_pool,
        # which performs retrieval (Source), Council scoring + integrity
        # (Evaluate + Verify) and grounded reasoning (Explain).
        self._log("Source+Evaluate+Verify+Explain: scoring pool ...")
        records, stats = score_pool(candidates, jd, retriever=None, verbose=self.verbose)

        # Compliance Agent — fairness audit + EU AI Act trail
        fair = fairness.audit(candidates, stats["selected_idx"])
        audit_path = compliance.write_audit(
            candidates_path, len(candidates), stats["n_honeypots"],
            time.time() - t0, fair, "lsa (sklearn TF-IDF + TruncatedSVD)",
            honeypot_rules=stats.get("honeypot_rules"),
        )
        self._log(f"Compliance: audit written -> {audit_path}")

        return records, stats, fair, audit_path
