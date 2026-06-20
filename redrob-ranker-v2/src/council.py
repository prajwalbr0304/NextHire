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

    raw = (0.35 * recency + 0.30 * response + 0.15 * saved
           + 0.10 * otw + 0.10 * interview)
    # map [0,1] -> [AVAIL_MIN, AVAIL_MAX]
    mult = config.AVAIL_MIN + raw * (config.AVAIL_MAX - config.AVAIL_MIN)

    if days > 120:
        msg = f"dormant (~{days}d since active), response rate {response:.2f}"
    elif response < 0.2:
        msg = f"low recruiter responsiveness ({response:.2f})"
    elif recency > 0.5 and response > 0.5:
        msg = f"actively engaged (response {response:.2f})"
    else:
        msg = f"moderate engagement (response {response:.2f})"
    return mult, msg


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

    parts = {
        "semantic_seer": s1, "name_rectifier": s2, "evidence_scout": s3,
        "mask_piercer": s4, "path_reader": s5, "terrain_master": s6,
    }
    w = config.COUNCIL_WEIGHTS
    wsum = sum(w.values())
    core = sum(parts[k] * w[k] for k in parts) / wsum

    return {
        "parts": parts,
        "core": core,
        "neg_mult": neg_mult,
        "avail_mult": avail_mult,
        "rationales": {
            "semantic_seer": r1, "name_rectifier": r2, "evidence_scout": r3,
            "mask_piercer": r4, "path_reader": r5, "terrain_master": r6,
            "neti_neti": r7, "availability": r9,
        },
    }
