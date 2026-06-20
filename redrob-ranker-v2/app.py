#!/usr/bin/env python3
"""
Sandbox demo — THE AI RECRUITING BRAIN v2.0 (Council of Nine).

Architecture
------------
Ranking runs ONCE when you press the "Rank / Re-rank" button. The result is
stored in st.session_state, and every other interaction (paging, switching
tabs, exporting Excel) reads from that stored state instead of recomputing.
This keeps pages, tabs and exports always populated and makes re-ranking an
explicit, intentional action.

    streamlit run app.py
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import traceback

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
        box-shadow: 0 8px 32px rgba(0,0,0,.37); }
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
    .metric-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:14px; margin-bottom:22px; }
    .metric-box { background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.05);
        border-radius:12px; padding:18px; text-align:center; }
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
    return (f"<div style='margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:2px;'>"
            f"<span>{label}</span><span>{pct:.0f}%</span></div>"
            f"<div style='background:rgba(255,255,255,.04);border-radius:100px;height:5px;overflow:hidden;'>"
            f"<div style='background:{color};width:{pct:.1f}%;height:100%;border-radius:100px;'></div></div></div>")


# ---------------------------------------------------------------------------
# Core ranking (runs only on demand, never on incidental reruns)
# ---------------------------------------------------------------------------
def parse_candidates(raw: bytes):
    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("The file is empty.")
    if text.startswith("["):
        data = json.loads(text)
    else:
        data = [json.loads(l) for l in text.splitlines() if l.strip()]
    if not isinstance(data, list) or not data:
        raise ValueError("No candidate records found in the file.")
    if not isinstance(data[0], dict) or "candidate_id" not in data[0]:
        raise ValueError("Records don't look like candidate profiles "
                         "(missing 'candidate_id'). Check the file format.")
    return data


def run_ranking(raw, role_name, weights, yoe_ideal, yoe_ok, notice_pref,
                enable_integrity, enable_avail, progress=None):
    candidates = parse_candidates(raw)
    jd = roles.get_role(role_name)

    tot = sum(weights) or 1.0
    keys = ["semantic_seer", "name_rectifier", "evidence_scout",
            "mask_piercer", "path_reader", "terrain_master"]
    config.COUNCIL_WEIGHTS = {k: w / tot for k, w in zip(keys, weights)}
    config.EXP_IDEAL_LOW, config.EXP_IDEAL_HIGH = float(yoe_ideal[0]), float(yoe_ideal[1])
    config.EXP_OK_LOW, config.EXP_OK_HIGH = float(yoe_ok[0]), float(yoe_ok[1])
    config.NOTICE_PREF_DAYS = notice_pref

    if progress:
        progress(0.15, "Building candidate documents ...")
    docs = [build_document(c) for c in candidates]
    if progress:
        progress(0.35, "Fitting hybrid retriever (TF-IDF + LSA) ...")
    retr = build_retriever(docs)
    _, dense_sim, _ = retr.retrieve(jd["query_text"], shortlist_size=len(candidates))
    lo, hi = float(dense_sim.min()), float(dense_sim.max())
    rng = (hi - lo) or 1.0

    if progress:
        progress(0.65, "Scoring with the Council of Nine ...")
    rows, honeypots = [], []
    for idx, c in enumerate(candidates):
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

    if progress:
        progress(0.9, "Auditing fairness ...")
    topk = min(100, len(rows))
    id_to_pos = {c.get("candidate_id"): i for i, c in enumerate(candidates)}
    sel_idx = [id_to_pos.get(rows[i][1].get("candidate_id")) for i in range(topk)]
    sel_idx = [i for i in sel_idx if i is not None]
    try:
        fair = fairness.audit(candidates, sel_idx)
    except Exception:
        fair = {}

    return {
        "ranked": rows,
        "honeypots": honeypots,
        "total": len(candidates),
        "fair": fair,
        "jd": jd,
        "role_name": role_name,
        "weights": config.COUNCIL_WEIGHTS,
        "notice_pref": notice_pref,
        "enable_integrity": enable_integrity,
    }


def build_export_df(ranked, jd, n):
    recs = []
    for rank, (score, c, f, dec, integ) in enumerate(ranked[:n], 1):
        p = c.get("profile", {})
        recs.append({
            "rank": rank,
            "candidate_id": c.get("candidate_id"),
            "score": round(score * 100, 1),
            "current_title": p.get("current_title"),
            "years_experience": p.get("years_of_experience"),
            "location": p.get("location"),
            "country": p.get("country"),
            "current_company": p.get("current_company"),
            "verified_relevant_skills": ", ".join(verified_relevant_skills(c, jd, top=8)),
            "semantic_seer": round(dec["parts"]["semantic_seer"], 3),
            "name_rectifier": round(dec["parts"]["name_rectifier"], 3),
            "evidence_scout": round(dec["parts"]["evidence_scout"], 3),
            "mask_piercer": round(dec["parts"]["mask_piercer"], 3),
            "path_reader": round(dec["parts"]["path_reader"], 3),
            "terrain_master": round(dec["parts"]["terrain_master"], 3),
            "notice_days": int(f["notice_days"]),
            "reasoning": gen_reason(c, f, dec, integ, score, rank, jd),
        })
    return pd.DataFrame(recs)


def to_excel_bytes(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranked Candidates")
        ws = writer.sheets["Ranked Candidates"]
        for col_cells in ws.columns:
            length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(length + 2, 60)
    return buf.getvalue()


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

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
try:
    st.sidebar.image("https://redrob.io/static/media/logo.8d234ebff9f75a6c9e05.png", width=140)
except Exception:
    pass

st.sidebar.header("🎯 Target Job Role")
role_name = st.sidebar.selectbox("Rank candidates for this role:", roles.role_names(), index=0)

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

weights = (round(w_semantic, 3), round(w_name, 3), round(w_evidence, 3),
           round(w_mask, 3), round(w_path, 3), round(w_terrain, 3))

st.sidebar.markdown("---")
run_clicked = st.sidebar.button("🚀 Rank / Re-rank Candidates",
                                type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# File input (upload of any size, or a path on disk). No default-sample button.
# ---------------------------------------------------------------------------
uploaded = st.file_uploader(
    "Upload Candidate Pool (.json or .jsonl) — no size limit", type=["json", "jsonl"])
sample_path = st.text_input(
    "...or specify a file path on disk (recommended for very large pools)",
    value="", placeholder=r"e.g. C:\Users\...\candidates.jsonl")

raw_bytes, source_label, file_id = None, None, None
err = None
try:
    if uploaded is not None:
        raw_bytes = uploaded.getvalue()
        source_label = uploaded.name
        file_id = f"upload::{uploaded.name}::{len(raw_bytes)}"
    elif sample_path.strip():
        sp = sample_path.strip().strip('"')
        if os.path.exists(sp):
            with open(sp, "rb") as fh:
                raw_bytes = fh.read()
            source_label = os.path.basename(sp)
            file_id = f"path::{sp}::{os.path.getmtime(sp)}::{os.path.getsize(sp)}"
        else:
            err = f"Path does not exist: {sp}"
except Exception as e:
    err = f"Could not read the input file: {e}"

if err:
    st.error(f"⚠️ {err}")

# current settings signature — used to detect stale results
cur_sig = (file_id, role_name, weights, tuple(yoe_ideal), tuple(yoe_ok),
           notice_pref, enable_integrity, enable_avail)

# ---------------------------------------------------------------------------
# Run ranking on demand
# ---------------------------------------------------------------------------
if run_clicked:
    if not raw_bytes:
        st.error("⚠️ Please upload a candidate file or enter a valid file path first.")
    else:
        prog = st.progress(0.0, text="Starting ...")
        try:
            res = run_ranking(raw_bytes, role_name, weights, yoe_ideal, yoe_ok,
                              notice_pref, enable_integrity, enable_avail,
                              progress=lambda p, m: prog.progress(p, text=m))
            res["sig"] = cur_sig
            res["source_label"] = source_label
            st.session_state["results"] = res
            st.session_state.pop("xls_bytes", None)   # invalidate old export
            st.session_state.pop("page_no", None)     # reset leaderboard to page 1
            prog.progress(1.0, text="Done.")
            prog.empty()
            st.success(f"✅ Ranked {len(res['ranked']):,} candidates for **{role_name}**.")
        except Exception as e:
            prog.empty()
            st.error(f"❌ Ranking failed: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

results = st.session_state.get("results")

# ---------------------------------------------------------------------------
# Render results (from session state — survives paging / tab / export reruns)
# ---------------------------------------------------------------------------
if not results:
    st.info("💡 **How to use:** (1) pick a **Target Job Role** in the sidebar, "
            "(2) upload a JSON/JSONL candidate file (any size) or paste a file path, "
            "(3) click **🚀 Rank / Re-rank Candidates**.")
else:
    ranked = results["ranked"]
    honeypots = results["honeypots"]
    jd = results["jd"]
    n_ranked = len(ranked)
    total_loaded = results["total"]
    notice_pref_r = results["notice_pref"]

    if results.get("sig") != cur_sig:
        st.warning("⚙️ Settings or file changed since the last ranking. "
                   "Click **🚀 Rank / Re-rank Candidates** to apply the new settings.")

    st.caption(f"Showing results for role **{results['role_name']}** · "
               f"source *{results.get('source_label','?')}*")

    # ---- summary metrics ----
    n_honeypots = len(honeypots)
    notice_match = (sum(1 for r in ranked if r[2]["notice_days"] <= notice_pref_r)
                    / max(1, n_ranked)) * 100
    top_id = ranked[0][1].get("candidate_id") if ranked else "N/A"
    top_title = ranked[0][1].get("profile", {}).get("current_title", "") if ranked else ""
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-box"><div class="metric-val">{total_loaded:,}</div><div class="metric-lbl">Candidates Ingested</div></div>
        <div class="metric-box"><div class="metric-val">{n_ranked:,}</div><div class="metric-lbl">Candidates Ranked</div></div>
        <div class="metric-box"><div class="metric-val">{n_honeypots}</div><div class="metric-lbl">Honeypots Flagged</div></div>
        <div class="metric-box"><div class="metric-val">{notice_match:.0f}%</div><div class="metric-lbl">Notice ≤ {notice_pref_r} Days</div></div>
        <div class="metric-box"><div class="metric-val" style="font-size:15px;padding-top:8px;">{top_id}<br><span style="font-size:11px;color:#94a3b8;">{top_title}</span></div><div class="metric-lbl">Top Pick</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- export ----
    with st.container(border=True):
        e1, e2, e3 = st.columns([2, 2, 1])
        with e1:
            export_n = st.number_input("Number of candidates to export", min_value=1,
                                       max_value=int(n_ranked),
                                       value=int(min(100, n_ranked)), step=10)
        with e2:
            st.write("")
            st.caption("Excel (.xlsx) with ranks, scores, verified skills, "
                       "Council sub-scores and reasoning.")
        with e3:
            st.write("")
            if st.button("📊 Generate Excel", use_container_width=True):
                try:
                    df = build_export_df(ranked, jd, int(export_n))
                    st.session_state["xls_bytes"] = to_excel_bytes(df)
                    st.session_state["xls_name"] = (
                        f"ranked_{results['role_name'].split()[0].lower()}_{int(export_n)}.xlsx")
                    st.success(f"Excel ready with {int(export_n)} candidates — download below.")
                except Exception as e:
                    st.error(f"❌ Could not generate Excel: {e}")
                    with st.expander("Show technical details"):
                        st.code(traceback.format_exc())
        if st.session_state.get("xls_bytes"):
            st.download_button(
                "⬇️ Download Excel file", data=st.session_state["xls_bytes"],
                file_name=st.session_state.get("xls_name", "ranked_candidates.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    # ---- view selector (radio renders only ONE view per run: lighter + reliable) ----
    view = st.radio("View", [
        "🏆 Leaderboard Ranks", "📊 Score Analytics", "🛡️ Compliance & Fairness",
        "🪓 Integrity Warden (Honeypot Logs)", "💼 Job Intent Explorer"],
        horizontal=True, label_visibility="collapsed", key="view_sel")
    st.markdown("---")

    # ============== VIEW 1: paginated leaderboard ==============
    if view == "🏆 Leaderboard Ranks":
        try:
            page_size = 100
            n_pages = max(1, math.ceil(n_ranked / page_size))
            c1, c2 = st.columns([1, 3])
            with c1:
                page = st.number_input(f"Page (100/page · {n_pages} total)", min_value=1,
                                       max_value=int(n_pages), value=1, step=1, key="page_no")
            with c2:
                st.caption(f"Ranks {(page-1)*page_size+1:,}–{min(page*page_size, n_ranked):,} "
                           f"of {n_ranked:,}. Click a candidate to expand details.")
            start = (page - 1) * page_size
            for offset, (score, c, f, dec, integ) in enumerate(ranked[start:start + page_size]):
                rank = start + offset + 1
                p = c.get("profile", {})
                title = p.get("current_title", "Profile")
                cid = c.get("candidate_id")
                with st.expander(f"#{rank}  ·  {title}  ·  Score {score*100:.0f}  ·  {cid}"):
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
                    st.markdown(f"<div style='color:#94a3b8;font-size:12px;margin-bottom:8px;'>"
                                f"{'  ·  '.join(badges)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='reasoning-box'><strong>Grounded Reasoning:</strong> "
                                f"{reasoning}</div>", unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    with b1:
                        st.markdown("<div style='font-size:13px;font-weight:600;color:#a78bfa;'>Council of Nine Scores</div>", unsafe_allow_html=True)
                        for k, v in dec["parts"].items():
                            color = ("linear-gradient(90deg,#fb7185,#ef4444)" if v < 0.25
                                     else "linear-gradient(90deg,#fcd34d,#f59e0b)" if v < 0.6
                                     else "linear-gradient(90deg,#34d399,#10b981)")
                            st.markdown(make_html_progress(k.replace("_", " ").title(), v, color),
                                        unsafe_allow_html=True)
                    with b2:
                        st.markdown("<div style='font-size:13px;font-weight:600;color:#67e8f9;'>Strategic Rationales</div>", unsafe_allow_html=True)
                        for sn, rm in dec["rationales"].items():
                            st.markdown(f"<div style='font-size:12px;margin-bottom:4px;color:#cbd5e1;'>"
                                        f"<strong style='color:#94a3b8;'>{sn.replace('_',' ').title()}:</strong> "
                                        f"{rm}</div>", unsafe_allow_html=True)
                    st.markdown("---")
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown(
                            f"**Profile**<br><small style='color:#94a3b8;'>"
                            f"{p.get('current_title','')} @ {p.get('current_company','')} · "
                            f"{p.get('years_of_experience','?')} yrs · "
                            f"{p.get('location','')}, {p.get('country','')}</small>",
                            unsafe_allow_html=True)
                        edu = c.get("education") or []
                        if edu:
                            e0 = edu[0]
                            st.markdown(
                                f"**Education**<br><small style='color:#94a3b8;'>"
                                f"{e0.get('degree','')} in {e0.get('field_of_study','')}, "
                                f"{e0.get('institution','')} ({e0.get('tier','')})</small>",
                                unsafe_allow_html=True)
                        st.markdown(f"**Summary**<br><small style='color:#94a3b8;'>"
                                    f"{(p.get('summary') or '')[:300]}</small>",
                                    unsafe_allow_html=True)
                    with d2:
                        vsk = verified_relevant_skills(c, jd, top=12)
                        st.markdown("**Verified Relevant Skills**")
                        st.markdown(" ".join(f"<span class='tech-pill tech-pill-pos'>{s}</span>"
                                             for s in vsk) if vsk else "_None_",
                                    unsafe_allow_html=True)
                        st.markdown("**All Listed Skills**")
                        st.markdown(" ".join(f"<span class='tech-pill'>{s.get('name')}</span>"
                                             for s in c.get("skills", [])), unsafe_allow_html=True)
                        st.markdown("**Career Timeline**")
                        for role in c.get("career_history", []):
                            st.markdown(
                                f"💼 **{role.get('title')}** at *{role.get('company')}* "
                                f"({role.get('duration_months')} mo)<br>"
                                f"<small style='color:#64748b;'>{role.get('start_date')} → "
                                f"{role.get('end_date') or 'Present'} | {role.get('description')}</small>",
                                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Could not render leaderboard: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

    # ============== VIEW 2: analytics ==============
    elif view == "📊 Score Analytics":
        try:
            st.subheader("Score Distributions & Metrics")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.write("#### Relevance Score Distribution")
                arr = np.array([r[0] * 100 for r in ranked])
                hv, be = np.histogram(arr, bins=10)
                df_s = pd.DataFrame({"Candidates": hv},
                                    index=[f"{int(be[i])}-{int(be[i+1])}" for i in range(len(hv))])
                st.bar_chart(df_s)
            with cc2:
                st.write("#### Experience (YOE) Distribution")
                ya = np.array([r[2]["yoe"] for r in ranked])
                hy, bey = np.histogram(ya, bins=6)
                df_y = pd.DataFrame({"Candidates": hy},
                                    index=[f"{int(bey[i])}-{int(bey[i+1])}" for i in range(len(hy))])
                st.bar_chart(df_y)
            cc3, cc4 = st.columns(2)
            with cc3:
                st.write("#### Company Background")
                prod = sum(1 for r in ranked if r[2]["product_ratio"] > 0.5)
                serv = sum(1 for r in ranked if r[2]["services_only"])
                st.metric("Product-company dominant", f"{prod:,}")
                st.metric("Services-only", f"{serv:,}")
                st.metric("Mixed / other", f"{n_ranked - prod - serv:,}")
            with cc4:
                st.write("#### Average Council Scorer")
                avg = {}
                for r in ranked:
                    for k, v in r[3]["parts"].items():
                        avg[k] = avg.get(k, 0.0) + v
                avg = {k.replace("_", " ").title(): v / max(1, n_ranked) for k, v in avg.items()}
                st.bar_chart(pd.DataFrame({"Avg Score": list(avg.values())}, index=list(avg.keys())))
        except Exception as e:
            st.error(f"❌ Could not render analytics: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

    # ============== VIEW 3: compliance ==============
    elif view == "🛡️ Compliance & Fairness":
        try:
            st.subheader("🛡️ Regulatory Audit & Traceability")
            st.markdown("AI recruiting tools are **HIGH-RISK** under the **EU AI Act (Annex III)** — "
                        "requiring logging, fairness auditing and explainability.")
            fair = results.get("fair", {})
            a1, a2 = st.columns(2)
            with a1:
                st.write(f"#### Fairness Audit (top {min(100, n_ranked)})")
                if not fair:
                    st.info("Fairness report unavailable for this pool.")
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
                    "target_role": results["role_name"],
                    "eu_ai_act_classification": "high-risk (Annex III, employment)",
                    "n_candidates_scored": total_loaded,
                    "n_ranked": n_ranked,
                    "honeypots_detected": n_honeypots,
                    "council_weights": results["weights"],
                    "human_oversight": "Ranks are RECOMMENDATIONS; final hiring "
                                       "decisions require human review (Article 14).",
                }, expanded=False)
        except Exception as e:
            st.error(f"❌ Could not render compliance tab: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

    # ============== VIEW 4: honeypots ==============
    elif view == "🪓 Integrity Warden (Honeypot Logs)":
        try:
            st.subheader("🪓 Integrity Warden Exclusion Logs")
            if not results.get("enable_integrity"):
                st.warning("Integrity Warden was disabled for this run — no profiles were filtered.")
            if honeypots:
                st.markdown(f"**{len(honeypots)}** profiles flagged as logically impossible and excluded:")
                for c, integ in honeypots[:300]:
                    p = c.get("profile", {})
                    st.markdown(f"""
                    <div style="background:rgba(239,68,68,.05);border:1px solid rgba(239,68,68,.2);
                         border-radius:8px;padding:14px;margin-bottom:10px;">
                      <span style="font-size:10px;font-weight:700;background:rgba(239,68,68,.2);
                            color:#fca5a5;padding:2px 8px;border-radius:4px;text-transform:uppercase;">Blocked</span>
                      <div style="font-size:15px;font-weight:700;color:#fca5a5;margin-top:6px;">
                         {p.get('current_title','N/A')} ({c.get('candidate_id')})</div>
                      <div style="font-size:13px;color:#cbd5e1;margin-top:4px;">
                         <strong>Reason:</strong> {'; '.join(integ[2]) or 'flagged'}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No honeypots flagged in this pool.")
        except Exception as e:
            st.error(f"❌ Could not render honeypot tab: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

    # ============== VIEW 5: job intent ==============
    elif view == "💼 Job Intent Explorer":
        try:
            st.subheader("💼 Job Intent Representation")
            st.markdown(f"Role: **{jd.get('role_title', results['role_name'])}**")
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
        except Exception as e:
            st.error(f"❌ Could not render job intent tab: {e}")
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())
