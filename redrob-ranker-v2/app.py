#!/usr/bin/env python3
"""
Sandbox demo — THE AI RECRUITING BRAIN v2.0 (Council of Nine).

Features
--------
* Pick a TARGET JOB ROLE from a dropdown (or use the contest JD).
* Upload a candidate pool of ANY size (the .streamlit/config.toml lifts the cap).
* Ranks the ENTIRE uploaded pool (not just 100), best -> least.
* Results shown 100 per page, each candidate in an expandable card.
* Download a spec-compliant submission CSV (candidate_id,rank,score,reasoning)
  or export the full ranked list (choose how many) to an Excel (.xlsx) file.

    streamlit run app.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import council, integrity, fairness, roles
import src.config as config
from src.features import build_document, compute_features
from src.reasoning import generate as gen_reason
from src.retrieve import build_retriever
from src.score import _soft_nudge
from src.skills_verify import verified_relevant_skills

st.set_page_config(
    page_title="THE AI RECRUITING BRAIN v2.0",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    code, pre { font-family: 'JetBrains Mono', monospace !important; }
    .header-card {
        background: linear-gradient(135deg, rgba(10,15,30,.7), rgba(20,25,55,.7));
        border: 1px solid rgba(91,61,232,.3); border-radius: 16px; padding: 30px;
        margin-bottom: 20px; backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,.37); position: relative; overflow: hidden;
    }
    .header-title { font-size: 38px; font-weight: 800;
        background: linear-gradient(135deg,#a78bfa,#67e8f9);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 4px; letter-spacing: -1px; }
    .header-subtitle { font-size: 15px; color: #94a3b8; margin-bottom: 16px; }
    .custom-badge { display:inline-flex; align-items:center; gap:6px; padding:6px 14px;
        border-radius:20px; font-size:11px; font-weight:600; text-transform:uppercase;
        letter-spacing:.5px; margin-right:8px; margin-bottom:8px; border:1px solid; }
    .badge-v2 { background:rgba(6,182,212,.08); color:#67e8f9; border-color:rgba(6,182,212,.3); }
    .badge-eu { background:rgba(244,63,94,.08); color:#fb7185; border-color:rgba(244,63,94,.3); }
    .badge-explain { background:rgba(139,92,246,.08); color:#c084fc; border-color:rgba(139,92,246,.3); }
    .badge-cpu { background:rgba(16,185,129,.08); color:#34d399; border-color:rgba(16,185,129,.3); }
    .reasoning-box { background:rgba(91,61,232,.05); border-left:3px solid #8b5cf6;
        border-radius:4px; padding:12px 14px; margin:10px 0; font-size:13.5px;
        line-height:1.6; color:#e2e8f0; }
    .metric-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
        gap:14px; margin-bottom:22px; }
    .metric-box { background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.05);
        border-radius:12px; padding:18px; text-align:center; backdrop-filter:blur(8px); }
    .metric-val { font-size:26px; font-weight:800;
        background:linear-gradient(135deg,#fff 30%,#a78bfa 100%);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .metric-lbl { font-size:11px; color:#64748b; text-transform:uppercase;
        letter-spacing:1px; font-weight:600; margin-top:4px; }
    .tech-pill { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px;
        font-weight:500; margin:2px; background:rgba(255,255,255,.04);
        border:1px solid rgba(255,255,255,.08); color:#cbd5e1; }
    .tech-pill-pos { background:rgba(16,185,129,.08); color:#34d399; border-color:rgba(16,185,129,.2); }
    .tech-pill-neg { background:rgba(239,68,68,.08); color:#fca5a5; border-color:rgba(239,68,68,.2); }
</style>
""", unsafe_allow_html=True)


def make_html_progress(label, value, color="linear-gradient(90deg,#8b5cf6,#06b6d4)"):
    pct = max(0.0, min(value, 1.0)) * 100
    return f"""
    <div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:2px;">
        <span>{label}</span><span>{pct:.0f}%</span>
      </div>
      <div style="background:rgba(255,255,255,.04);border-radius:100px;height:5px;overflow:hidden;">
        <div style="background:{color};width:{pct:.1f}%;height:100%;border-radius:100px;"></div>
      </div>
    </div>"""


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="header-card">
    <div class="header-title">THE AI RECRUITING BRAIN</div>
    <div class="header-subtitle">Next-Generation Candidate Evaluation Engine &amp; Sandbox (Council of Nine v2.0)</div>
    <div>
        <span class="custom-badge badge-v2">⚡ Version 2.0</span>
        <span class="custom-badge badge-eu">🛡️ EU AI Act Compliant</span>
        <span class="custom-badge badge-explain">🧠 Explainable AI</span>
        <span class="custom-badge badge-cpu">💻 Offline CPU Optimized</span>
    </div>
</div>
""", unsafe_allow_html=True)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
default_sample_path = os.path.abspath(os.path.join(
    REPO_ROOT, "..", "[PUB] India_runs_data_and_ai_challenge",
    "India_runs_data_and_ai_challenge", "sample_candidates.json"))

# ---------------------------------------------------------------------------
# Sidebar — role, weights, parameters
# ---------------------------------------------------------------------------
try:
    st.sidebar.image("https://redrob.io/static/media/logo.8d234ebff9f75a6c9e05.png", width=140)
except Exception:
    pass

st.sidebar.header("🎯 Target Job Role")
role_name = st.sidebar.selectbox(
    "Rank candidates for this role:",
    roles.role_names(),
    index=0,
    help="Pick the job profile to rank the uploaded candidates against.",
)
jd = roles.get_role(role_name)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Scoring Weights")
st.sidebar.caption("Adjust the 'Council of Nine' priorities. Normalised to 100%.")
w_semantic = st.sidebar.slider("👁️ Semantic Seer (Semantic Fit)", 0.0, 1.0, 0.16)
w_name = st.sidebar.slider("孔 Confucius: Name-Rectifier", 0.0, 1.0, 0.20)
w_evidence = st.sidebar.slider("🗡️ Kautilya: Evidence Scout", 0.0, 1.0, 0.22)
w_mask = st.sidebar.slider("🎭 Japan: Mask-Piercer (Skill Trust)", 0.0, 1.0, 0.14)
w_path = st.sidebar.slider("🥋 Shu-Ha-Ri: Path-Reader (YOE/Tenure)", 0.0, 1.0, 0.12)
w_terrain = st.sidebar.slider("⚔️ Sun Tzu: Terrain Master (Domain/Prod)", 0.0, 1.0, 0.16)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Parameters")
yoe_ideal = st.sidebar.slider("Ideal YOE Range", 1, 20, (6, 8))
yoe_ok = st.sidebar.slider("Acceptable YOE Range", 1, 20, (5, 9))
notice_pref = st.sidebar.slider("Notice Period Threshold (Days)", 15, 120, 30)
enable_integrity = st.sidebar.checkbox("Integrity Warden (Honeypot Filter)", value=True)
enable_avail = st.sidebar.checkbox("Availability Oracle (Recency modifier)", value=True)

weights_tuple = (round(w_semantic, 3), round(w_name, 3), round(w_evidence, 3),
                 round(w_mask, 3), round(w_path, 3), round(w_terrain, 3))


# ---------------------------------------------------------------------------
# Cached parsing + ranking (so pagination / export do NOT recompute)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False, max_entries=2)
def parse_candidates(raw: bytes):
    text = raw.decode("utf-8", errors="ignore").strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(l) for l in text.splitlines() if l.strip()]


@st.cache_resource(show_spinner="Ranking the full candidate pool ...", max_entries=2)
def rank_all(raw: bytes, role_name, weights_tuple, yoe_ideal, yoe_ok,
             notice_pref, enable_integrity, enable_avail):
    candidates = parse_candidates(raw)
    jd = roles.get_role(role_name)

    # apply UI-controlled config (cache key includes all of these)
    tot = sum(weights_tuple) or 1.0
    keys = ["semantic_seer", "name_rectifier", "evidence_scout",
            "mask_piercer", "path_reader", "terrain_master"]
    config.COUNCIL_WEIGHTS = {k: w / tot for k, w in zip(keys, weights_tuple)}
    config.EXP_IDEAL_LOW, config.EXP_IDEAL_HIGH = float(yoe_ideal[0]), float(yoe_ideal[1])
    config.EXP_OK_LOW, config.EXP_OK_HIGH = float(yoe_ok[0]), float(yoe_ok[1])
    config.NOTICE_PREF_DAYS = notice_pref

    docs = [build_document(c) for c in candidates]
    retr = build_retriever(docs)
    _, dense_sim, _ = retr.retrieve(jd["query_text"], shortlist_size=len(candidates))
    lo, hi = float(dense_sim.min()), float(dense_sim.max())
    rng = (hi - lo) or 1.0

    rows, honeypots = [], []
    for idx in range(len(candidates)):
        c = candidates[idx]
        f = compute_features(c, jd)
        sem = (dense_sim[idx] - lo) / rng
        integ = integrity.check(c)
        if enable_integrity and integ[1]:
            honeypots.append((c, integ))
            continue
        dec = council.deliberate(f, sem)
        integ_mult = integ[0] if enable_integrity else 1.0
        avail_mult = dec["avail_mult"] if enable_avail else 1.0
        fit = dec["core"] * integ_mult * dec["neg_mult"] * avail_mult + _soft_nudge(f)
        rows.append([max(0.0, fit), c, f, dec, integ])

    rows.sort(key=lambda r: (-r[0], r[1].get("candidate_id") or ""))
    raws = np.array([r[0] for r in rows], dtype=float)
    if len(raws) > 1 and raws.max() > raws.min():
        cal = 0.35 + 0.64 * (raws - raws.min()) / (raws.max() - raws.min())
    else:
        cal = np.full(len(raws), 0.8)
    for r, s in zip(rows, cal):
        r[0] = float(s)
    rows.sort(key=lambda r: (-r[0], r[1].get("candidate_id") or ""))
    return rows, honeypots, len(candidates)


def build_export_df(ranked, jd, n):
    recs = []
    for rank, (score, c, f, dec, integ) in enumerate(ranked[:n], 1):
        p = c.get("profile", {})
        reasoning = gen_reason(c, f, dec, integ, score, rank, jd)
        vsk = verified_relevant_skills(c, jd, top=8)
        recs.append({
            "rank": rank,
            "candidate_id": c.get("candidate_id"),
            "score": round(score * 100, 1),
            "current_title": p.get("current_title"),
            "years_experience": p.get("years_of_experience"),
            "location": p.get("location"),
            "country": p.get("country"),
            "current_company": p.get("current_company"),
            "verified_relevant_skills": ", ".join(vsk),
            "semantic_seer": round(dec["parts"]["semantic_seer"], 3),
            "name_rectifier": round(dec["parts"]["name_rectifier"], 3),
            "evidence_scout": round(dec["parts"]["evidence_scout"], 3),
            "mask_piercer": round(dec["parts"]["mask_piercer"], 3),
            "path_reader": round(dec["parts"]["path_reader"], 3),
            "terrain_master": round(dec["parts"]["terrain_master"], 3),
            "notice_days": int(f["notice_days"]),
            "reasoning": reasoning,
        })
    return pd.DataFrame(recs)


def to_excel_bytes(df, role_name):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranked Candidates")
        ws = writer.sheets["Ranked Candidates"]
        for col_cells in ws.columns:
            length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(length + 2, 60)
    return buf.getvalue()


def to_submission_csv_bytes(ranked, jd, n):
    """Spec CSV (candidate_id,rank,score,reasoning) for the top-`n`.

    Guarantees the official validator passes: scores are rounded to 4 dp and the
    rows are then ordered by (-score, candidate_id), so score is non-increasing by
    rank and any equal scores are broken by candidate_id ascending.
    """
    items = [(round(float(score), 4), c, f, dec, integ)
             for (score, c, f, dec, integ) in ranked[:n]]
    items.sort(key=lambda r: (-r[0], (r[1].get("candidate_id") or "")))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["candidate_id", "rank", "score", "reasoning"])
    for rank, (rscore, c, f, dec, integ) in enumerate(items, 1):
        reasoning = gen_reason(c, f, dec, integ, rscore, rank, jd)
        w.writerow([c.get("candidate_id"), rank, f"{rscore:.4f}", reasoning])
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------
col_up1, col_up2 = st.columns([2, 1])
with col_up1:
    uploaded = st.file_uploader(
        "Upload Candidate Pool (.json or .jsonl) — no size limit",
        type=["json", "jsonl"],
    )
with col_up2:
    st.write("")
    st.write("")
    has_sample = os.path.exists(default_sample_path)
    btn_load = st.button("⚡ Load Default Challenge Sample",
                         use_container_width=True, disabled=not has_sample)

sample_path = st.text_input(
    "...or specify a file path on disk (best for very large pools)",
    value="",
    placeholder=r"e.g. C:\Users\...\candidates.jsonl",
)

raw_bytes = None
source_label = None
if uploaded is not None:
    raw_bytes = uploaded.getvalue()
    source_label = uploaded.name
    st.session_state["use_default"] = False
elif sample_path:
    # an explicitly typed path always wins over the sticky default sample
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as fh:
            raw_bytes = fh.read()
        source_label = os.path.basename(sample_path)
        st.session_state["use_default"] = False
    else:
        st.error(f"Path does not exist: {sample_path}")
elif btn_load and has_sample:
    with open(default_sample_path, "rb") as fh:
        raw_bytes = fh.read()
    source_label = "sample_candidates.json"
    st.session_state["use_default"] = True
elif st.session_state.get("use_default") and has_sample:
    with open(default_sample_path, "rb") as fh:
        raw_bytes = fh.read()
    source_label = "sample_candidates.json"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if raw_bytes:
    try:
        ranked, honeypots, total_loaded = rank_all(
            raw_bytes, role_name, weights_tuple, yoe_ideal, yoe_ok,
            notice_pref, enable_integrity, enable_avail)
    except Exception as e:
        st.error(f"Could not rank candidates: {e}")
        st.stop()

    n_ranked = len(ranked)
    st.success(f"Ranked **{n_ranked:,}** candidates from *{source_label}* "
               f"for the role: **{role_name}**.")

    # ---- summary metrics ----
    n_honeypots = len(honeypots)
    notice_match = (sum(1 for r in ranked if r[2]["notice_days"] <= notice_pref)
                    / max(1, n_ranked)) * 100
    top_id = ranked[0][1].get("candidate_id") if ranked else "N/A"
    top_title = ranked[0][1].get("profile", {}).get("current_title", "") if ranked else ""
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-box"><div class="metric-val">{total_loaded:,}</div><div class="metric-lbl">Candidates Ingested</div></div>
        <div class="metric-box"><div class="metric-val">{n_ranked:,}</div><div class="metric-lbl">Candidates Ranked</div></div>
        <div class="metric-box"><div class="metric-val">{n_honeypots}</div><div class="metric-lbl">Honeypots Flagged</div></div>
        <div class="metric-box"><div class="metric-val">{notice_match:.0f}%</div><div class="metric-lbl">Notice ≤ {notice_pref} Days</div></div>
        <div class="metric-box"><div class="metric-val" style="font-size:15px;padding-top:8px;">{top_id}<br><span style="font-size:11px;color:#94a3b8;">{top_title}</span></div><div class="metric-lbl">Top Pick</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- export bar ----
    with st.container(border=True):
        csv_n = int(min(100, n_ranked))
        st.download_button(
            f"⬇️ Download submission CSV (top {csv_n})",
            data=to_submission_csv_bytes(ranked, jd, csv_n),
            file_name="submission.csv", mime="text/csv",
            use_container_width=True,
            help="Spec format candidate_id,rank,score,reasoning — passes validate_submission.py")
        ex1, ex3 = st.columns([3, 1])
        with ex1:
            export_n = st.number_input(
                "Rows for the detailed Excel export (scores, verified skills, "
                "Council sub-scores, reasoning)", min_value=1,
                max_value=int(n_ranked), value=int(min(100, n_ranked)), step=10)
        with ex3:
            st.write("")
            st.write("")
            if st.button("📊 Generate Excel", use_container_width=True):
                df = build_export_df(ranked, jd, int(export_n))
                xls = to_excel_bytes(df, role_name)
                st.session_state["xls_bytes"] = xls
                st.session_state["xls_name"] = f"ranked_{role_name.split()[0].lower()}_{int(export_n)}.xlsx"
        if st.session_state.get("xls_bytes"):
            st.download_button(
                "⬇️ Download Excel file", data=st.session_state["xls_bytes"],
                file_name=st.session_state.get("xls_name", "ranked_candidates.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    # ---- tabs ----
    tab_rank, tab_charts, tab_audit, tab_honeypot, tab_jd = st.tabs([
        "🏆 Leaderboard Ranks", "📊 Score Analytics", "🛡️ Compliance & Fairness",
        "🪓 Integrity Warden (Honeypot Logs)", "💼 Job Intent Explorer"])

    # ===================== TAB 1: paginated leaderboard =====================
    with tab_rank:
        page_size = 100
        n_pages = max(1, math.ceil(n_ranked / page_size))
        c1, c2 = st.columns([1, 3])
        with c1:
            page = st.number_input(f"Page (100 per page · {n_pages} pages)",
                                   min_value=1, max_value=n_pages, value=1, step=1)
        with c2:
            st.caption(f"Showing ranks {(page-1)*page_size+1:,}–"
                       f"{min(page*page_size, n_ranked):,} of {n_ranked:,}. "
                       "Click any candidate to expand full details.")

        start = (page - 1) * page_size
        # Lightweight rendering: each card body is ONE HTML block (not ~20 widgets),
        # so 100 expanders per page stay fast and never starve the other tabs.
        for offset, (score, c, f, dec, integ) in enumerate(ranked[start:start + page_size]):
            rank = start + offset + 1
            p = c.get("profile", {})
            title = p.get("current_title", "Profile")
            cid = c.get("candidate_id")
            reasoning = gen_reason(c, f, dec, integ, score, rank, jd)

            badges = []
            if f["cur_title_pos"]:
                badges.append("✅ Verified Title")
            if f["product_ratio"] > 0.5:
                badges.append("🏢 Product Co.")
            if f["location_match"]:
                badges.append("📍 Location Match")
            badges.append("🕒 Active" if f["days_inactive"] <= 30
                          else f"💤 Inactive ~{f['days_inactive']}d")
            badges.append(f"⏱ Notice {int(f['notice_days'])}d")
            badge_str = "  ·  ".join(badges)

            bars = "".join(
                make_html_progress(
                    k.replace("_", " ").title(), v,
                    ("linear-gradient(90deg,#fb7185,#ef4444)" if v < 0.25
                     else "linear-gradient(90deg,#fcd34d,#f59e0b)" if v < 0.6
                     else "linear-gradient(90deg,#34d399,#10b981)"))
                for k, v in dec["parts"].items())
            rats = "".join(
                f"<div style='font-size:12px;margin-bottom:3px;color:#cbd5e1;'>"
                f"<strong style='color:#94a3b8;'>{sn.replace('_',' ').title()}:</strong> {rm}</div>"
                for sn, rm in dec["rationales"].items())
            vsk = verified_relevant_skills(c, jd, top=12)
            vsk_html = (" ".join(f"<span class='tech-pill tech-pill-pos'>{s}</span>" for s in vsk)
                        if vsk else "<em>none verified</em>")
            all_sk = " ".join(f"<span class='tech-pill'>{s.get('name')}</span>"
                              for s in c.get("skills", []))
            timeline = "".join(
                f"<div style='margin-bottom:6px;'>💼 <strong>{r.get('title')}</strong> at "
                f"<em>{r.get('company')}</em> ({r.get('duration_months')} mo)<br>"
                f"<small style='color:#64748b;'>{r.get('start_date')} → "
                f"{r.get('end_date') or 'Present'} | {r.get('description')}</small></div>"
                for r in c.get("career_history", []))
            edu = "; ".join(
                f"{e.get('degree')} {e.get('field_of_study')} — {e.get('institution')} "
                f"(tier: {e.get('tier','?')})" for e in c.get("education", [])) or "—"

            body = f"""
            <div style='color:#94a3b8;font-size:12px;margin-bottom:8px;'>{badge_str}</div>
            <div class='reasoning-box'><strong>Grounded Reasoning:</strong> {reasoning}</div>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:18px;'>
              <div><div style='font-size:13px;font-weight:600;color:#a78bfa;margin-bottom:6px;'>Council of Nine Scores</div>{bars}</div>
              <div><div style='font-size:13px;font-weight:600;color:#67e8f9;margin-bottom:6px;'>Strategic Rationales</div>{rats}</div>
            </div>
            <hr style='border-color:rgba(148,163,184,.1);margin:12px 0;'>
            <div style='font-size:13px;'><strong>Summary:</strong> {p.get('summary','')}</div>
            <div style='margin-top:8px;'><strong style='font-size:13px;'>Verified Relevant Skills:</strong><br>{vsk_html}</div>
            <div style='margin-top:8px;'><strong style='font-size:13px;'>All Listed Skills:</strong><br>{all_sk}</div>
            <div style='margin-top:8px;'><strong style='font-size:13px;'>Education:</strong> {edu}</div>
            <div style='margin-top:8px;'><strong style='font-size:13px;'>Career Timeline:</strong><br>{timeline}</div>
            """
            with st.expander(f"#{rank}  ·  {title}  ·  Score {score*100:.0f}  ·  {cid}"):
                st.markdown(body, unsafe_allow_html=True)

    # ===================== TAB 2: analytics =====================
    with tab_charts:
        st.subheader("Score Distributions & Metrics")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.write("#### Relevance Score Distribution")
            arr = np.array([r[0] * 100 for r in ranked])
            hv, be = np.histogram(arr, bins=10)
            st.bar_chart({"Score Range": [f"{int(be[i])}-{int(be[i+1])}" for i in range(len(hv))],
                          "Candidates": hv}, x="Score Range", y="Candidates")
        with cc2:
            st.write("#### Experience (YOE) Distribution")
            ya = np.array([r[2]["yoe"] for r in ranked])
            hy, bey = np.histogram(ya, bins=6)
            st.bar_chart({"YOE Range": [f"{int(bey[i])}-{int(bey[i+1])}" for i in range(len(hy))],
                          "Count": hy}, x="YOE Range", y="Count")
        cc3, cc4 = st.columns(2)
        with cc3:
            st.write("#### Company Background")
            prod = sum(1 for r in ranked if r[2]["product_ratio"] > 0.5)
            serv = sum(1 for r in ranked if r[2]["services_only"])
            st.write(f"Product-company dominant: **{prod:,}**")
            st.write(f"Services-only: **{serv:,}**")
            st.write(f"Mixed / other: **{n_ranked - prod - serv:,}**")
        with cc4:
            st.write("#### Average Council Scorer (all ranked)")
            avg = {}
            for r in ranked:
                for k, v in r[3]["parts"].items():
                    avg[k] = avg.get(k, 0.0) + v
            avg = {k: v / max(1, n_ranked) for k, v in avg.items()}
            st.bar_chart({"Scorer": [k.replace("_", " ").title() for k in avg],
                          "Avg": list(avg.values())}, x="Scorer", y="Avg")

    # ===================== TAB 3: compliance =====================
    with tab_audit:
        st.subheader("🛡️ Regulatory Audit & Traceability")
        st.markdown("AI recruiting tools are **HIGH-RISK** under the **EU AI Act (Annex III)**. "
                    "They require logging, fairness auditing and explainability.")
        topk = min(100, n_ranked)
        all_ids = parse_candidates(raw_bytes)
        id_to_pos = {c.get("candidate_id"): i for i, c in enumerate(all_ids)}
        sel_idx = [id_to_pos.get(ranked[i][1].get("candidate_id")) for i in range(topk)]
        sel_idx = [i for i in sel_idx if i is not None]
        fair = fairness.audit(all_ids, sel_idx)
        a1, a2 = st.columns(2)
        with a1:
            st.write(f"#### Fairness Audit (top {topk})")
            for attr, data in fair.items():
                di = data["disparate_impact_ratio"]
                ok = data["passes_four_fifths"]
                col = "#34d399" if ok else "#fb7185"
                st.markdown(f"**{attr.replace('_',' ').title()}** — Disparate Impact: "
                            f"<strong style='color:{col};'>{di:.3f}</strong> "
                            f"({'✓ pass' if ok else '⚠ review'})", unsafe_allow_html=True)
        with a2:
            st.write("#### Immutable Run Log (EU AI Act Art. 12)")
            st.json({
                "system": "Redrob Ranker v2.0 (Council of Nine)",
                "target_role": role_name,
                "eu_ai_act_classification": "high-risk (Annex III, employment)",
                "n_candidates_scored": total_loaded,
                "n_ranked": n_ranked,
                "honeypots_detected": n_honeypots,
                "council_weights": config.COUNCIL_WEIGHTS,
                "human_oversight": "Ranks are RECOMMENDATIONS; final hiring "
                                   "decisions require human review (Article 14).",
            }, expanded=False)

    # ===================== TAB 4: honeypots =====================
    with tab_honeypot:
        st.subheader("🪓 Integrity Warden Exclusion Logs")
        if not enable_integrity:
            st.warning("Integrity Warden is disabled in the sidebar — no profiles are being filtered.")
        if honeypots:
            show = honeypots[:60]
            st.markdown(f"**{len(honeypots)}** profiles flagged as logically impossible "
                        f"and excluded (showing first {len(show)}):")
            cards = "".join(f"""
                <div style="background:rgba(239,68,68,.05);border:1px solid rgba(239,68,68,.2);
                     border-radius:8px;padding:12px;margin-bottom:8px;">
                  <span style="font-size:10px;font-weight:700;background:rgba(239,68,68,.2);
                        color:#fca5a5;padding:2px 8px;border-radius:4px;text-transform:uppercase;">Blocked</span>
                  <div style="font-size:14px;font-weight:700;color:#fca5a5;margin-top:6px;">
                     {(c.get('profile') or dict()).get('current_title','N/A')} ({c.get('candidate_id')})</div>
                  <div style="font-size:13px;color:#cbd5e1;margin-top:4px;">
                     <strong>Reason:</strong> {'; '.join(integ[2])}</div>
                </div>""" for c, integ in show)
            st.markdown(cards, unsafe_allow_html=True)
        else:
            st.info("No honeypots flagged in this pool.")

    # ===================== TAB 5: job intent =====================
    with tab_jd:
        st.subheader("💼 Job Intent Representation")
        st.markdown(f"Role: **{jd.get('role_title', role_name)}**")
        st.write("#### Must-Have Capabilities")
        st.markdown(" ".join(f"<span class='tech-pill tech-pill-pos'>{s}</span>"
                             for s in jd["must_have_capabilities"]), unsafe_allow_html=True)
        j1, j2 = st.columns(2)
        with j1:
            st.write("#### Positive Title Signals")
            st.markdown(" ".join(f"<span class='tech-pill tech-pill-pos'>{s}</span>"
                                 for s in jd["positive_titles"]), unsafe_allow_html=True)
        with j2:
            st.write("#### Negative Title Signals (Anti-Stuffer)")
            st.markdown(" ".join(f"<span class='tech-pill tech-pill-neg'>{s}</span>"
                                 for s in jd["negative_titles"]), unsafe_allow_html=True)
        st.write("#### Query Text passed to Retrieval")
        st.code(jd["query_text"])
else:
    st.info("💡 Pick a **Target Job Role** in the sidebar, then upload a JSON/JSONL "
            "candidate file (any size) or click **Load Default Challenge Sample**.")
