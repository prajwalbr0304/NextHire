"""
Stage [3] — The Council of Nine (Navaratna).

Nine independent, interpretable sub-scorers. Each embodies a tested principle
of human judgement drawn from world strategic traditions AND maps to a concrete,
measurable feature. Each returns a score in [0, 1] (or a bounded multiplier for
the gating scorers) plus a short, honest rationale fragment used by reasoning.py.

  1 Semantic Seer      (Daoism / Wu Wei)            -> semantic JD<->profile fit
  2 Name-Rectifier     (Confucius / Zhengming)      -> title matches reality
  3 Evidence Scout     (Kautilya / Arthashastra)    -> demonstrated 'shipped a system'
  4 Mask-Piercer       (Honne vs Tatemae)           -> verified skill-trust
  5 Path-Reader        (Shu-Ha-Ri / Ship of Theseus)-> experience band + stability
  6 Terrain Master     (Sun Tzu)                    -> product-vs-services + domain
  7 Neti-Neti Gatekeeper (Vedanta)                  -> negative screen (multiplier)
  8 Integrity Warden   (Yaksha Prashna)             -> plausibility (see integrity.py)
  9 Availability Oracle (I Ching / Yin-Yang)        -> behavioural modifier (multiplier)
"""
from __future__ import annotations

from typing import Dict, Tuple

from . import config

Result = Tuple[float, str]


# --------------------------------------------------------------------------
# 1. Semantic Seer — let meaning flow (semantic similarity is precomputed)
# --------------------------------------------------------------------------
def semantic_seer(sem_sim: float) -> Result:
    s = max(0.0, min(1.0, sem_sim))
    if s > 0.66:
        msg = "strong semantic alignment with the JD's retrieval/ranking focus"
    elif s > 0.4:
        msg = "moderate semantic alignment with the role"
    else:
        msg = "weak semantic overlap with the JD"
    return s, msg


# --------------------------------------------------------------------------
# 2. Name-Rectifier — the title must match the reality (Zhengming)
# --------------------------------------------------------------------------
def name_rectifier(f: Dict) -> Result:
    if f["cur_title_neg"]:
        # current role is an explicit non-engineering identity -> the classic
        # keyword-stuffer trap (e.g. "HR Manager" with a wall of AI skills)
        return 0.08, "current title is a non-engineering role (role/skill mismatch)"
    if f["cur_title_pos"]:
        return 1.0, "current title is a genuine engineering/ML role"
    if f["title_pos"]:
        return 0.6, "engineering title appears in career history but not current role"
    return 0.3, "title gives no clear engineering signal"


# --------------------------------------------------------------------------
# 3. Evidence Scout — verify by deeds, not claims (Arthashastra)
# --------------------------------------------------------------------------
def evidence_scout(f: Dict) -> Result:
    hits = f["evidence_hits"]
    s = min(hits / 12.0, 1.0)
    if hits >= 8:
        msg = f"career descriptions show rich build/ship evidence ({hits} signals)"
    elif hits >= 4:
        msg = f"some demonstrated systems-building evidence ({hits} signals)"
    else:
        msg = f"little concrete evidence of shipping systems ({hits} signals)"
    return s, msg


# --------------------------------------------------------------------------
# 4. Mask-Piercer — public face vs true self (Honne / Tatemae)
# --------------------------------------------------------------------------
def mask_piercer(f: Dict) -> Result:
    trust = f["relevant_trust"]
    raw = f["raw_relevant_count"]
    s = min(trust / 4.0, 1.0)
    # a long list of relevant skills with near-zero verified trust == stuffing
    if raw >= 5 and trust < 1.0:
        msg = f"{raw} relevant skills listed but weakly verified (likely keyword-stuffing)"
        s = min(s, 0.35)
    elif trust >= 2.5:
        msg = "relevant skills are well-verified by endorsements and usage"
    elif trust > 0:
        msg = "some verified relevant skills"
    else:
        msg = "no verified JD-relevant skills"
    return s, msg


# --------------------------------------------------------------------------
# 5. Path-Reader — mastery stages + career continuity
# --------------------------------------------------------------------------
def path_reader(f: Dict) -> Result:
    yoe = f["yoe"]
    # experience-band fit (JD: 5-9 required, 6-8 ideal) - soft trapezoid
    if config.EXP_IDEAL_LOW <= yoe <= config.EXP_IDEAL_HIGH:
        band = 1.0
    elif config.EXP_OK_LOW <= yoe <= config.EXP_OK_HIGH:
        band = 0.8
    elif 3 <= yoe < config.EXP_OK_LOW or config.EXP_OK_HIGH < yoe <= 12:
        band = 0.5
    else:
        band = 0.25

    # tenure stability — penalise title-chasing job-hoppers (JD: "hop every 1.5y")
    avg = f["avg_tenure_months"]
    if f["n_roles"] <= 1:
        stability = 0.75            # single role: neutral-ish
    elif avg >= config.JOBHOP_TENURE_MONTHS:
        stability = 1.0
    else:
        stability = max(0.4, avg / config.JOBHOP_TENURE_MONTHS)

    s = band * stability
    bits = []
    bits.append(f"{yoe:.1f} yrs experience")
    if avg < config.JOBHOP_TENURE_MONTHS and f["n_roles"] > 1:
        bits.append(f"short average tenure ({avg:.0f} mo)")
    return s, ", ".join(bits)


# --------------------------------------------------------------------------
# 6. Terrain Master — know the ground (Sun Tzu): product vs services + domain
# --------------------------------------------------------------------------
def terrain_master(f: Dict) -> Result:
    product = f["product_ratio"]
    domain = 0.0
    if f["irnlp_hits"] + f["offdomain_hits"] > 0:
        domain = f["irnlp_hits"] / (f["irnlp_hits"] + f["offdomain_hits"])
    s = 0.55 * product + 0.45 * domain
    if f["services_only"]:
        s *= 0.5
        msg = "career is services-firm dominated (JD disprefers services-only)"
    elif product > 0.5 and domain > 0.5:
        msg = "product-company background with NLP/IR-aligned domain"
    else:
        msg = "mixed company-type / domain alignment"
    return min(s, 1.0), msg


# --------------------------------------------------------------------------
# 7. Neti-Neti Gatekeeper — define excellence by what to reject (multiplier)
# --------------------------------------------------------------------------
def neti_neti(f: Dict) -> Result:
    penalty = 1.0
    reasons = []
    if f["services_only"]:
        penalty *= 0.7
        reasons.append("services-only career")
    # off-domain dominant (CV/speech/robotics) WITHOUT NLP/IR exposure
    if f["offdomain_hits"] >= 3 and f["irnlp_hits"] == 0:
        penalty *= 0.6
        reasons.append("off-domain specialization without NLP/IR")
    if f["cur_title_neg"] and f["relevant_skill_count"] < 2:
        # definitive keyword-stuffer signature: wrong-role title + a wall of
        # AI skills none of which are backed by endorsements or real usage.
        penalty *= 0.45
        reasons.append("non-engineering role with unverified AI skills (keyword-stuffer)")
    # list-INDEPENDENT keyword-stuffer guard: catches off-list fake titles
    # (e.g. "Marketing Technologist", "Growth Lead") that escape negative_titles
    # — no engineering title anywhere, a wall of relevant-looking skills, but no
    # verified trust and no build/ship evidence.
    if (not f["title_pos"] and f["raw_relevant_count"] >= 4
            and f["relevant_trust"] < 1.0 and f["evidence_hits"] < 3):
        penalty *= 0.5
        reasons.append("no engineering title + buzzword-dense unverified skills")
    penalty = max(penalty, config.NEGSCREEN_MIN)
    return penalty, ("; ".join(reasons) if reasons else "no disqualifiers")


# --------------------------------------------------------------------------
# 9. Availability Oracle — balance ability with readiness (bounded multiplier)
# --------------------------------------------------------------------------
def availability_oracle(f: Dict) -> Result:
    import math

    # exponential recency decay (v2.0): active-7-days >> active-90-days
    days = f["days_inactive"]
    recency = math.exp(-days / 45.0)                 # ~0.86 at 7d, ~0.14 at 90d
    response = f["response_rate"]
    saved = min(f["saved_by_recruiters"] / 10.0, 1.0)
    otw = 1.0 if f["open_to_work"] else 0.0
    interview = f["interview_completion"]
    # offer-acceptance history (-1 == unknown -> neutral)
    oa = f.get("offer_acceptance", -1)
    offer = 0.5 if (oa is None or oa < 0) else oa
    # responsiveness speed: same-day replies >> week-long (48h -> ~0.37)
    rt = f.get("avg_response_hours", 0.0)
    speed = math.exp(-rt / 48.0) if rt > 0 else 0.5
    # platform engagement: actively applying / appearing in searches
    engagement = min((f.get("applications_30d", 0.0) / 10.0)
                     + (f.get("search_appearance_30d", 0.0) / 50.0), 1.0)

    raw = (0.30 * recency + 0.25 * response + 0.12 * saved + 0.08 * otw
           + 0.10 * interview + 0.08 * offer + 0.04 * speed + 0.03 * engagement)
    # map [0,1] -> [AVAIL_MIN, AVAIL_MAX]
    mult = config.AVAIL_MIN + raw * (config.AVAIL_MAX - config.AVAIL_MIN)

    # HARD ghost gate (the JD's example): hasn't logged in for months AND barely
    # answers recruiters == "not actually available". Extra multiplier on top of
    # the bounded modifier so a perfect-on-paper ghost drops out of the top
    # (bounded, not zeroed -> a genuinely elite profile is demoted, not erased).
    ghost = (days > config.AVAIL_HARD_DAYS and response < config.AVAIL_HARD_RESP)
    if ghost:
        mult *= config.AVAIL_HARD_MULT
        msg = f"unreachable: dormant ~{days}d + only {response:.0%} recruiter response"
    elif days > 120:
        msg = f"dormant (~{days}d since active), response rate {response:.2f}"
    elif response < 0.2:
        msg = f"low recruiter responsiveness ({response:.2f})"
    elif recency > 0.5 and response > 0.5:
        msg = f"actively engaged (response {response:.2f})"
    else:
        msg = f"moderate engagement (response {response:.2f})"
    return mult, msg


# --------------------------------------------------------------------------
# Disqualifier Screen (Stage [6b]) — the JD's explicit "we will not move
# forward" gates. Multiplicative, floored, each requiring MULTIPLE corroborating
# signals so no single keyword can sink a candidate (protects ranking quality).
# --------------------------------------------------------------------------
def disqualifier_screen(f: Dict) -> Result:
    mult = 1.0
    reasons = []

    # 1) Pure research / academia with no production deployment.
    if (f["research_ratio"] >= config.RESEARCH_RATIO_MIN
            and f["evidence_hits"] < config.EVIDENCE_MIN_FOR_PROD
            and f["product_ratio"] < 0.34):
        mult *= config.RESEARCH_ONLY_MULT
        reasons.append("pure research/academic career with no production-deployment evidence")

    # 2) Recent LangChain/OpenAI-wrapper tooling only, no pre-LLM ML depth.
    if (f["wrapper_skill_count"] >= 1
            and f["core_ml_max_tenure"] < config.CORE_ML_TENURE_MONTHS
            and f["evidence_hits"] < config.EVIDENCE_MIN_FOR_PROD
            and f["relevant_skill_count"] < 3):
        mult *= config.WRAPPER_ONLY_MULT
        reasons.append("AI experience is recent LLM-wrapper tooling without pre-LLM ML production")

    # 3) Senior who moved into architecture/management and stopped shipping code.
    if (f["leadership_current"]
            and f["leadership_current_months"] >= config.LEADERSHIP_MIN_MONTHS
            and f["github"] <= config.LEADERSHIP_GITHUB_MAX
            and f["evidence_hits"] < config.EVIDENCE_MIN_FOR_PROD):
        mult *= config.LEADERSHIP_DRIFT_MULT
        reasons.append("non-IC leadership role with no recent hands-on coding signal")

    # 4) 5y+ closed-source with zero external validation (papers/talks/OSS/certs)
    #    AND no demonstrated delivery — i.e. no way to evaluate how they think.
    if (f["yoe"] >= config.CLOSED_SOURCE_MIN_YOE
            and not f["has_external_validation"]
            and f["github"] <= 0
            and f["evidence_hits"] < config.EVIDENCE_MIN_FOR_PROD):
        mult *= config.CLOSED_SOURCE_MULT
        reasons.append("5y+ closed-source work with no external validation or demonstrated delivery")

    mult = max(mult, config.DISQUAL_MULT_FLOOR)
    return mult, ("; ".join(reasons) if reasons else "no JD disqualifiers")


# --------------------------------------------------------------------------
# Fusion of additive scorers (1-6). Gates (7,8,9) applied in score.py.
# --------------------------------------------------------------------------
def deliberate(f: Dict, sem_sim: float) -> Dict:
    """Run the full council and return scores + rationale fragments."""
    s1, r1 = semantic_seer(sem_sim)
    s2, r2 = name_rectifier(f)
    s3, r3 = evidence_scout(f)
    s4, r4 = mask_piercer(f)
    s5, r5 = path_reader(f)
    s6, r6 = terrain_master(f)
    neg_mult, r7 = neti_neti(f)
    avail_mult, r9 = availability_oracle(f)
    disq_mult, r_disq = disqualifier_screen(f)

    parts = {
        "semantic_seer": s1, "name_rectifier": s2, "evidence_scout": s3,
        "mask_piercer": s4, "path_reader": s5, "terrain_master": s6,
    }
    w = config.COUNCIL_WEIGHTS
    wsum = sum(w.values()) or 1.0
    core = sum(parts[k] * w[k] for k in parts) / wsum

    return {
        "parts": parts,
        "core": core,
        "neg_mult": neg_mult,
        "avail_mult": avail_mult,
        "disqualifier_mult": disq_mult,
        "rationales": {
            "semantic_seer": r1, "name_rectifier": r2, "evidence_scout": r3,
            "mask_piercer": r4, "path_reader": r5, "terrain_master": r6,
            "neti_neti": r7, "availability": r9, "disqualifier": r_disq,
        },
    }
