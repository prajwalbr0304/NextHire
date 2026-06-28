"""
Scoring-metric guarantees (NDCG@10/@50, MAP, P@10).

These lock in the properties the weighted composite rewards:
  * scores are strictly non-increasing and fine-grained (NDCG position sensitivity)
  * higher relevance band ALWAYS outranks lower (MAP: Tier-3+ above Tier-1/2)
  * band score sub-ranges are disjoint (no cross-tier ties)
  * no clearly-unqualified (band-0) candidate enters the top-10 when qualified
    candidates exist (P@10 floor)
  * ordering is deterministic across runs
  * domain-anchored evidence no longer rewards generic management verbs
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config, council, integrity
config.RERANK_BACKEND = "feature"   # deterministic; no torch/network in tests

from src.features import compute_features
from src.score import load_jd, relevance_band, finalize_ranking, _soft_nudge

JD = load_jd()

STRONG_DESC = ("Built and shipped a production recommendation system serving 10 million "
               "users; designed the retrieval and ranking pipeline with embeddings and "
               "deployed models to production at scale.")
STD_DESC = "Built REST APIs and microservices with some exposure to machine learning."
WEAK_DESC = "Ran marketing campaigns, managed stakeholders and owned delivery of plans."

STRONG_SKILLS = [
    {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 84},
    {"name": "Embeddings", "proficiency": "advanced", "endorsements": 22, "duration_months": 48},
    {"name": "Information Retrieval", "proficiency": "advanced", "endorsements": 20, "duration_months": 40},
    {"name": "Recommendation Systems", "proficiency": "advanced", "endorsements": 18, "duration_months": 36},
]
STD_SKILLS = [
    {"name": "Python", "proficiency": "intermediate", "endorsements": 8, "duration_months": 18},
    {"name": "NLP", "proficiency": "intermediate", "endorsements": 4, "duration_months": 10},
]
STUFFER_SKILLS = [{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 1}
                  for n in ["RAG", "Embeddings", "LLM", "NLP"]]


def cand(cid, title, *, company="ShopStream", industry="E-commerce", yoe=7.0,
         desc=STRONG_DESC, skills=None):
    return {
        "candidate_id": cid,
        "profile": {"anonymized_name": "T", "headline": title, "summary": desc,
                    "location": "Pune", "country": "India", "years_of_experience": yoe,
                    "current_title": title, "current_company": company,
                    "current_company_size": "1001-5000", "current_industry": industry},
        "career_history": [{"company": company, "title": title, "start_date": "2018-06-01",
                            "end_date": None, "duration_months": 84, "is_current": True,
                            "industry": industry, "company_size": "1001-5000", "description": desc}],
        "education": [{"institution": "IIT", "degree": "B.Tech", "field_of_study": "CS",
                       "start_year": 2014, "end_year": 2018, "grade": "8.5", "tier": "tier_1"}],
        "skills": skills if skills is not None else STRONG_SKILLS,
        "redrob_signals": {"recruiter_response_rate": 0.6, "last_active_date": "2026-06-01",
                           "open_to_work_flag": True, "saved_by_recruiters_30d": 5,
                           "interview_completion_rate": 0.9, "skill_assessment_scores": {},
                           "notice_period_days": 30, "github_activity_score": 60,
                           "offer_acceptance_rate": 0.8, "avg_response_time_hours": 10,
                           "applications_submitted_30d": 3, "search_appearance_30d": 20,
                           "profile_views_received_30d": 15},
    }


def _rec(c, sem=0.5):
    f = compute_features(c, JD)
    integ = integrity.check(c)
    dec = council.deliberate(f, sem)
    raw = max(0.0, dec["core"] * integ[0] * dec["neg_mult"] * dec["disqualifier_mult"]
              * dec["avail_mult"] + _soft_nudge(f))
    return {"candidate_id": c["candidate_id"], "raw": raw, "f": f, "dec": dec,
            "integ": integ, "candidate": c}


def _pool():
    pool = []
    titles = ["Machine Learning Engineer", "AI Engineer", "Search Engineer",
              "NLP Engineer", "Applied ML Engineer"]
    for i, t in enumerate(titles):                       # 5 strong ML engineers
        pool.append(cand(f"CAND_000{i:04d}", t))
    for i, t in enumerate(["Software Engineer", "Backend Engineer", "Frontend Engineer",
                           "Data Engineer", "Full Stack Developer"]):   # 5 standard
        pool.append(cand(f"CAND_001{i:04d}", t, desc=STD_DESC, skills=STD_SKILLS))
    for i, t in enumerate(["Marketing Manager", "HR Manager", "Accountant",
                           "Operations Manager"]):       # 4 weak non-engineers
        pool.append(cand(f"CAND_002{i:04d}", t, company="AdCo", industry="Marketing",
                         desc=WEAK_DESC, skills=STUFFER_SKILLS))
    return pool


def _rank():
    return finalize_ranking([_rec(c) for c in _pool()], JD, top_n=config.TOP_N)


def test_scores_strictly_non_increasing():
    scores = [r["score"] for r in _rank()]
    assert scores == sorted(scores, reverse=True)


def test_bands_monotonic_with_rank():
    bands = [r["band"] for r in _rank()]
    assert bands == sorted(bands, reverse=True), "a lower band must never outrank a higher one"


def test_band_score_subranges_disjoint():
    ranked = _rank()
    by_band = {}
    for r in ranked:
        by_band.setdefault(r["band"], []).append(r["score"])
    if 2 in by_band and 1 in by_band:
        assert min(by_band[2]) > max(by_band[1])
    if 1 in by_band and 0 in by_band:
        assert min(by_band[1]) > max(by_band[0])


def test_p_at_10_floor_no_unqualified_in_top10():
    # the pool has 10 qualified engineers, so the top-10 must contain NO band-0
    top10 = _rank()[:10]
    assert all(r["band"] >= 1 for r in top10)
    assert all(r["score"] >= config.BAND_RANGES[1][0] for r in top10)


def test_ordering_is_deterministic():
    a = [r["candidate_id"] for r in _rank()]
    b = [r["candidate_id"] for r in _rank()]
    assert a == b


def test_relevance_band_classification():
    strong = _rec(cand("CAND_9000001", "Machine Learning Engineer"))
    assert relevance_band(strong["f"], strong["dec"], strong["integ"]) == 2
    weak = _rec(cand("CAND_9000002", "Marketing Manager", company="AdCo",
                     industry="Marketing", desc=WEAK_DESC, skills=STUFFER_SKILLS))
    assert relevance_band(weak["f"], weak["dec"], weak["integ"]) == 0


def test_domain_anchored_evidence_ignores_generic_verbs():
    pm = compute_features(cand("CAND_9000003", "Project Manager", company="Wipro",
                               industry="IT Services",
                               desc="Led teams, owned delivery and managed stakeholders."), JD)
    eng = compute_features(cand("CAND_9000004", "ML Engineer"), JD)
    assert pm["evidence_hits"] < 3 < eng["evidence_hits"]
