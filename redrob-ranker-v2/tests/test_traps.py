"""
The decisive differentiator test (blueprint Section 3.3, the JD's own example).

The JD literally hands us the disqualifying case and the saving case:
  * a keyword-perfect "HR Manager" with every AI skill listed  -> NOT a fit
  * a plain-language engineer who *built* a recsys at a product co -> a fit

A correct ranker MUST score the gem above the stuffer EVEN WHEN the stuffer has
a higher raw semantic similarity (because their skills list is buzzword-dense).
We also assert the integrity layer floors a blatant honeypot.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import council, integrity
from src.features import compute_features
from src.score import load_jd

JD = load_jd()


def _fit(candidate, sem_sim):
    f = compute_features(candidate, JD)
    integ = integrity.check(candidate)
    if integ[1]:
        return 0.0, f, integ
    dec = council.deliberate(f, sem_sim)
    return dec["core"] * integ[0] * dec["neg_mult"], f, integ


# --- the keyword stuffer: perfect skills, wrong identity, no real evidence ---
STUFFER = {
    "candidate_id": "CAND_9000001",
    "profile": {
        "anonymized_name": "K Stuffer", "headline": "HR Manager | AI enthusiast",
        "summary": "Experienced HR Manager handling recruitment and payroll.",
        "location": "Pune", "country": "India", "years_of_experience": 7.0,
        "current_title": "HR Manager", "current_company": "PeopleCorp",
        "current_company_size": "201-500", "current_industry": "HR Services",
    },
    "career_history": [{
        "company": "PeopleCorp", "title": "HR Manager", "start_date": "2019-01-01",
        "end_date": None, "duration_months": 84, "is_current": True,
        "industry": "HR Services", "company_size": "201-500",
        "description": "Managed hiring, onboarding, payroll and employee relations.",
    }],
    "education": [{"institution": "Some University", "degree": "MBA",
                   "field_of_study": "HR", "start_year": 2010, "end_year": 2012,
                   "grade": None, "tier": "tier_3"}],
    # every trendy AI skill, but ZERO endorsements and ZERO usage = unverified
    "skills": [{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 1}
               for n in ["RAG", "Embeddings", "Vector Database", "LLM", "Fine-tuning",
                          "NLP", "Information Retrieval", "Ranking", "FAISS"]],
    "redrob_signals": {"recruiter_response_rate": 0.8, "last_active_date": "2026-06-10",
                       "open_to_work_flag": True, "saved_by_recruiters_30d": 8,
                       "interview_completion_rate": 1.0, "skill_assessment_scores": {},
                       "notice_period_days": 30, "github_activity_score": -1},
}

# --- the hidden gem: plain language, real evidence, genuine engineering ---
GEM = {
    "candidate_id": "CAND_9000002",
    "profile": {
        "anonymized_name": "G Em", "headline": "Software Engineer",
        "summary": "I build large-scale recommendation and search systems for "
                   "millions of users at a product company.",
        "location": "Bangalore", "country": "India", "years_of_experience": 7.0,
        "current_title": "Software Engineer", "current_company": "ShopStream",
        "current_company_size": "1001-5000", "current_industry": "E-commerce",
    },
    "career_history": [{
        "company": "ShopStream", "title": "Software Engineer", "start_date": "2018-06-01",
        "end_date": None, "duration_months": 96, "is_current": True,
        "industry": "E-commerce", "company_size": "1001-5000",
        "description": "Designed and shipped the product recommendation system serving "
                       "10 million users. Built the retrieval and ranking pipeline with "
                       "embeddings; deployed models to production and reduced latency.",
    }],
    "education": [{"institution": "IIT", "degree": "B.Tech",
                   "field_of_study": "Computer Science", "start_year": 2014,
                   "end_year": 2018, "grade": "8.5", "tier": "tier_1"}],
    "skills": [
        {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 84},
        {"name": "Recommendation Systems", "proficiency": "advanced", "endorsements": 25, "duration_months": 60},
        {"name": "Embeddings", "proficiency": "advanced", "endorsements": 18, "duration_months": 48},
    ],
    "redrob_signals": {"recruiter_response_rate": 0.6, "last_active_date": "2026-06-01",
                       "open_to_work_flag": True, "saved_by_recruiters_30d": 5,
                       "interview_completion_rate": 0.9, "skill_assessment_scores": {"Python": 90},
                       "notice_period_days": 30, "github_activity_score": 70},
}

# --- a blatant honeypot: impossible profile ---
HONEYPOT = {
    "candidate_id": "CAND_9000003",
    "profile": {"anonymized_name": "H P", "headline": "AI Engineer", "summary": "AI.",
                "location": "Pune", "country": "India", "years_of_experience": 8.0,
                "current_title": "AI Engineer", "current_company": "NewCo",
                "current_company_size": "11-50", "current_industry": "AI/ML"},
    # one role lasting 200 months (16y) on an 8y career = impossible
    "career_history": [{
        "company": "NewCo", "title": "AI Engineer", "start_date": "2009-01-01",
        "end_date": None, "duration_months": 200, "is_current": True,
        "industry": "AI/ML", "company_size": "11-50",
        "description": "Did AI things.",
    }],
    "education": [],
    "skills": [{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
               for n in ["RAG", "LLM", "NLP", "Embeddings", "Ranking", "FAISS"]],
    "redrob_signals": {"recruiter_response_rate": 0.9, "last_active_date": "2026-06-10",
                       "open_to_work_flag": True, "saved_by_recruiters_30d": 9,
                       "interview_completion_rate": 1.0, "skill_assessment_scores": {},
                       "notice_period_days": 15, "github_activity_score": -1},
}


def test_gem_beats_stuffer_even_with_higher_semantic_sim():
    # adversarial: give the stuffer a HIGHER semantic similarity than the gem
    stuffer_fit, _, _ = _fit(STUFFER, sem_sim=0.95)
    gem_fit, _, _ = _fit(GEM, sem_sim=0.60)
    assert gem_fit > stuffer_fit, (
        f"gem ({gem_fit:.3f}) must outrank keyword-stuffer ({stuffer_fit:.3f})"
    )


def test_stuffer_is_strongly_penalised():
    stuffer_fit, f, _ = _fit(STUFFER, sem_sim=0.95)
    assert f["cur_title_neg"] is True
    assert stuffer_fit < 0.35, "an HR-Manager keyword-stuffer should score low"


def test_honeypot_is_flagged_and_floored():
    fit, _, integ = _fit(HONEYPOT, sem_sim=0.9)
    assert integ[1] is True, "blatant impossible profile must be flagged as honeypot"
    assert fit == 0.0, "honeypot must be floored to zero"
