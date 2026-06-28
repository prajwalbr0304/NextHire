"""
Regression tests for the JD's explicit disqualifiers, the hardened availability
(ghost) gate, the list-independent keyword-stuffer guard, and the nice-to-have /
evaluation-rigor additive bonuses.

Each gate is tested in BOTH directions: a profile that SHOULD be penalised, and a
near-identical profile that should NOT be (so the gates stay conservative and
never nuke legitimate candidates — protecting ranking quality).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import council, integrity
from src.features import compute_features
from src.score import load_jd, _soft_nudge

JD = load_jd()

STRONG_DESC = ("Built and shipped a production recommendation system serving "
               "10 million users; designed the retrieval and ranking pipeline "
               "with embeddings and deployed models to production at scale.")


def cand(cid, title, *, company="ShopStream", industry="E-commerce", yoe=7.0,
         desc=STRONG_DESC, skills=None, duration=84, is_current=True, signals=None):
    base_skills = [
        {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 84},
        {"name": "Embeddings", "proficiency": "advanced", "endorsements": 20, "duration_months": 48},
        {"name": "Information Retrieval", "proficiency": "advanced", "endorsements": 18, "duration_months": 40},
    ]
    sig = {
        "recruiter_response_rate": 0.6, "last_active_date": "2026-06-01",
        "open_to_work_flag": True, "saved_by_recruiters_30d": 5,
        "interview_completion_rate": 0.9, "skill_assessment_scores": {},
        "notice_period_days": 30, "github_activity_score": 60,
        "offer_acceptance_rate": 0.8, "avg_response_time_hours": 10,
        "applications_submitted_30d": 3, "search_appearance_30d": 20,
        "profile_views_received_30d": 15,
    }
    if signals:
        sig.update(signals)
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": "T", "headline": title, "summary": desc,
            "location": "Pune", "country": "India", "years_of_experience": yoe,
            "current_title": title, "current_company": company,
            "current_company_size": "1001-5000", "current_industry": industry,
        },
        "career_history": [{
            "company": company, "title": title, "start_date": "2018-06-01",
            "end_date": None, "duration_months": duration, "is_current": is_current,
            "industry": industry, "company_size": "1001-5000", "description": desc,
        }],
        "education": [{"institution": "IIT", "degree": "B.Tech",
                       "field_of_study": "Computer Science", "start_year": 2014,
                       "end_year": 2018, "grade": "8.5", "tier": "tier_1"}],
        "skills": skills if skills is not None else base_skills,
        "redrob_signals": sig,
    }


def _disq(c):
    return council.disqualifier_screen(compute_features(c, JD))


def _neg(c):
    return council.neti_neti(compute_features(c, JD))


def _final(c, sem_sim):
    f = compute_features(c, JD)
    integ = integrity.check(c)
    if integ[1]:
        return 0.0
    dec = council.deliberate(f, sem_sim)
    fit = dec["core"] * integ[0] * dec["neg_mult"] * dec["disqualifier_mult"]
    return max(0.0, fit * dec["avail_mult"] + _soft_nudge(f))


# ---------------------------------------------------------------------------
# Control: a clean, strong candidate must trip NO disqualifier.
# ---------------------------------------------------------------------------
def test_control_has_no_disqualifiers():
    mult, reasons = _disq(cand("CAND_0000001", "Senior Machine Learning Engineer"))
    assert mult == 1.0
    assert reasons == "no JD disqualifiers"


# ---------------------------------------------------------------------------
# 1) Pure research / academia with no production deployment.
# ---------------------------------------------------------------------------
def test_research_only_is_disqualified():
    c = cand("CAND_0000002", "Research Scientist", company="Max Planck Institute",
             industry="Research", yoe=7.0,
             desc="Studied theoretical questions and taught graduate courses.",
             skills=[{"name": "Mathematics", "proficiency": "expert",
                      "endorsements": 10, "duration_months": 60}])
    mult, reasons = _disq(c)
    assert mult < 1.0 and "research" in reasons.lower()


def test_product_applied_scientist_not_penalised():
    # Same "Research Scientist" title, but at a product company WITH production
    # delivery evidence -> the gate must NOT fire.
    c = cand("CAND_0000003", "Research Scientist", company="Google",
             industry="Software", yoe=7.0, desc=STRONG_DESC)
    _, reasons = _disq(c)
    assert "research" not in reasons.lower()


# ---------------------------------------------------------------------------
# 2) Recent LangChain/OpenAI-wrapper tooling only, no pre-LLM ML depth.
# ---------------------------------------------------------------------------
def test_recent_wrapper_only_is_disqualified():
    c = cand("CAND_0000004", "AI Engineer", yoe=2.0,
             desc="Built chatbots with LangChain calling the OpenAI API.",
             skills=[{"name": "LangChain", "proficiency": "expert", "endorsements": 2, "duration_months": 6},
                     {"name": "OpenAI API", "proficiency": "advanced", "endorsements": 1, "duration_months": 8},
                     {"name": "Prompt Engineering", "proficiency": "advanced", "endorsements": 0, "duration_months": 5}])
    mult, reasons = _disq(c)
    assert mult < 1.0 and "wrapper" in reasons.lower()


def test_wrapper_with_prior_ml_not_penalised():
    # Uses LangChain BUT has substantial pre-LLM ML depth -> the "unless" clause.
    c = cand("CAND_0000005", "AI Engineer", yoe=6.0, desc=STRONG_DESC,
             skills=[{"name": "LangChain", "proficiency": "expert", "endorsements": 2, "duration_months": 6},
                     {"name": "Machine Learning", "proficiency": "expert", "endorsements": 30, "duration_months": 48},
                     {"name": "Information Retrieval", "proficiency": "advanced", "endorsements": 20, "duration_months": 40}])
    _, reasons = _disq(c)
    assert "wrapper" not in reasons.lower()


# ---------------------------------------------------------------------------
# 3) Senior who moved into architecture/management and stopped shipping code.
# ---------------------------------------------------------------------------
def test_leadership_no_code_drift_is_penalised():
    c = cand("CAND_0000006", "Engineering Manager", yoe=12.0, duration=30,
             desc="Managed a team of engineers and oversaw quarterly planning.",
             signals={"github_activity_score": 5})
    mult, reasons = _disq(c)
    assert mult < 1.0 and "leadership" in reasons.lower()


def test_principal_engineer_who_codes_not_penalised():
    c = cand("CAND_0000007", "Principal Engineer", yoe=12.0, desc=STRONG_DESC)
    _, reasons = _disq(c)
    assert "leadership" not in reasons.lower()


# ---------------------------------------------------------------------------
# 4) 5y+ closed-source with zero external validation.
# ---------------------------------------------------------------------------
def test_closed_source_unvalidated_is_penalised():
    c = cand("CAND_0000008", "Software Engineer", yoe=8.0,
             desc="Worked on internal proprietary systems for the company.",
             signals={"github_activity_score": -1})
    mult, reasons = _disq(c)
    assert mult < 1.0 and "closed-source" in reasons.lower()


def test_closed_source_with_oss_not_penalised():
    c = cand("CAND_0000009", "Software Engineer", yoe=8.0,
             desc="Worked on internal proprietary systems for the company.",
             signals={"github_activity_score": 70})  # external validation present
    _, reasons = _disq(c)
    assert "closed-source" not in reasons.lower()


# ---------------------------------------------------------------------------
# Ghost candidate (Req 5): perfect on paper but dormant + unresponsive must lose
# to a reachable, slightly-weaker-on-merit candidate.
# ---------------------------------------------------------------------------
def test_ghost_candidate_loses_to_active_candidate():
    ghost = cand("CAND_0000010", "Staff Machine Learning Engineer", yoe=8.0,
                 signals={"last_active_date": "2025-11-25",          # ~200 days dormant
                          "recruiter_response_rate": 0.05, "open_to_work_flag": False})
    active = cand("CAND_0000011", "Senior Machine Learning Engineer", yoe=6.0,
                  signals={"last_active_date": "2026-06-10", "recruiter_response_rate": 0.7})
    # Adversarial: give the ghost the HIGHER semantic similarity.
    assert _final(active, 0.70) > _final(ghost, 0.95)


# ---------------------------------------------------------------------------
# Off-list keyword stuffer (Req 7): a non-engineering title NOT in negative_titles
# with a wall of unverified AI skills must still be screened by neti-neti.
# ---------------------------------------------------------------------------
def test_offlist_stuffer_is_contained():
    stuffer = cand("CAND_0000012", "Growth Marketer", company="AdCo",
                   industry="Marketing", yoe=6.0,
                   desc="Ran marketing campaigns and managed social media channels.",
                   skills=[{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 1}
                           for n in ["RAG", "Embeddings", "LLM", "NLP"]])
    penalty, reasons = _neg(stuffer)
    assert penalty < 1.0 and "no engineering title" in reasons.lower()
    # and it should land well below a genuine engineer
    assert _final(stuffer, 0.6) < _final(cand("CAND_0000013", "Senior AI Engineer"), 0.6)


# ---------------------------------------------------------------------------
# Nice-to-have (Req 4) and evaluation rigor (Req 3) must lift the score.
# ---------------------------------------------------------------------------
def test_nice_to_have_skills_boost_score():
    plain = compute_features(cand("CAND_0000014", "Senior AI Engineer"), JD)
    nice = compute_features(
        cand("CAND_0000015", "Senior AI Engineer", skills=[
            {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 84},
            {"name": "LoRA", "proficiency": "advanced", "endorsements": 20, "duration_months": 30},
            {"name": "XGBoost", "proficiency": "advanced", "endorsements": 25, "duration_months": 36},
        ]), JD)
    assert nice["nice_trust"] > 0
    assert _soft_nudge(nice) > _soft_nudge(plain)


def test_evaluation_rigor_boosts_score():
    plain = compute_features(cand("CAND_0000016", "Senior AI Engineer"), JD)
    rigorous = compute_features(
        cand("CAND_0000017", "Senior AI Engineer",
             desc="Designed offline evaluation with NDCG and MRR and ran A/B testing "
                  "to measure ranking quality."), JD)
    assert rigorous["eval_framework_hits"] >= 2
    assert _soft_nudge(rigorous) > _soft_nudge(plain)
