"""
Specialist agents (Section 8 of the blueprint).

Each is a thin, single-responsibility wrapper around a `src/` module. Kept in
one file for clarity; in production each would be its own microservice with the
same interface.
"""
from __future__ import annotations

from typing import Dict, List

from src import council as _council
from src import integrity as _integrity
from src.features import build_document, compute_features
from src.reasoning import generate as _generate
from src.retrieve import build_retriever
from src.skills_verify import verified_relevant_skills


class JDParserAgent:
    """Decompose the JD into a structured intent profile (loaded from jd_intent.json)."""

    def parse(self, jd: dict) -> dict:
        # Already-structured intent; in production this would call an LLM to
        # decompose a raw JD into this schema + multi-query expansions.
        return jd


class SourceAgent:
    """Multi-vector retrieval -> shortlist (Mottainai: never drop a hidden gem)."""

    def __init__(self, docs: List[str], verbose=False):
        self.retriever = build_retriever(docs, verbose=verbose)

    def shortlist(self, jd: dict):
        return self.retriever.retrieve(jd["query_text"])


class EvaluateAgent:
    """Council of Nine scoring (Evaluate)."""

    def score(self, features: Dict, sem_sim: float) -> Dict:
        return _council.deliberate(features, sem_sim)


class VerifyAgent:
    """Integrity / honeypot / credential verification (Verify)."""

    def verify(self, candidate: dict):
        return _integrity.check(candidate)

    def verified_skills(self, candidate: dict, jd: dict):
        return verified_relevant_skills(candidate, jd)


class ExplainAgent:
    """Grounded, calibrated reasoning (Explain)."""

    def explain(self, candidate, features, council, integrity, score, rank, jd) -> str:
        return _generate(candidate, features, council, integrity, score, rank, jd)
