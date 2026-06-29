"""
NextHire — The AI Recruiting Brain (Streamlit Cloud sandbox)
============================================================

A self-contained Streamlit front-end for the Redrob Ranker v2.0 "Council of
Nine" engine. It reuses the EXACT scoring pipeline that powers the FastAPI
backend (``api/ranker.py`` + ``src/``) so the ranking, integrity screen,
fairness audit and analytics match the production Next.js dashboard.

Why this file exists
--------------------
Streamlit Community Cloud can only run a Python Streamlit app — it cannot host
the Next.js (``web/``) frontend or the FastAPI (``api/``) server. This module is
that Streamlit app: upload a candidate pool (or use the bundled 50-profile
sample), pick a role, tune the Council weights, and rank — entirely on CPU,
offline, with no external services required.

Deploy on Streamlit Cloud
-------------------------
  Repository    : prajwalbr0304/AI-RECRUITING
  Branch        : main
  Main file path: redrob-ranker-v2/streamlit_app.py
  Python version: 3.13   (Advanced settings — matches requirements.txt pins)
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading

# --- Make the engine deterministic, offline and dependency-light BEFORE import.
# Force the always-available LSA retrieval backend so the app never attempts to
# download a sentence-transformers model (which is not installed on the Cloud).
os.environ.setdefault("REDROB_EMBED_BACKEND", "lsa")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import pandas as pd
import streamlit as st

# Make `src` and `api` importable regardless of the launch working directory.
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from src import config, roles            # noqa: E402
from api import ranker                   # noqa: E402

# ---------------------------------------------------------------------------
# Page config + light styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NextHire — AI Recruiting Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; padding-bottom: 3rem;}
      .nh-title {font-size: 2.0rem; font-weight: 800; letter-spacing:-0.02em; margin-bottom:0;}
      .nh-sub {color: #6b7280; margin-top: 0.1rem;}
      .nh-pill {display:inline-block; padding:2px 10px; border-radius:999px;
                font-size:0.75rem; font-weight:600; margin-right:6px;}
      .nh-good {background:#dcfce7; color:#166534;}
      .nh-warn {background:#fef9c3; color:#854d0e;}
      .nh-bad  {background:#fee2e2; color:#991b1b;}
      .nh-info {background:#e0e7ff; color:#3730a3;}
      div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

COUNCIL_KEYS = ranker.COUNCIL_KEYS
COUNCIL_LABELS = ranker.COUNCIL_LABELS
DEFAULT_WEIGHTS = dict(config.COUNCIL_WEIGHTS)

SEVERITY_PILL = {
    "low": "nh-info", "medium": "nh-warn",
    "high": "nh-bad", "critical": "nh-bad",
}


@st.cache_resource(show_spinner=False)
def _run_lock() -> threading.Lock:
    """Process-wide lock so concurrent Cloud sessions don't clobber the shared
    in-memory ranking STATE during a run + snapshot."""
    return threading.Lock()


def _find_sample() -> str | None:
    """Locate a bundled / committed sample candidate file."""
    candidates = [
        os.path.join(HERE, "sample_candidates.json"),
        os.path.join(HERE, "sample_candidates.jsonl"),
        os.path.join(
            os.path.dirname(HERE),
            "[PUB] India_runs_data_and_ai_challenge",
            "India_runs_data_and_ai_challenge",
            "sample_candidates.json",
        ),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _pill(text: str, kind: str = "nh-info") -> str:
    return f'<span class="nh-pill {kind}">{text}</span>'


# ---------------------------------------------------------------------------
# Ranking run (synchronous) + snapshot into session_state
# ---------------------------------------------------------------------------
def run_ranking(file_path: str, role: str, weights: dict, params: dict) -> dict:
    """Run the full pipeline under a lock and snapshot every view we render,
    so the UI stays consistent even if another session ranks afterwards."""
    with _run_lock():
        ranker._do_rank(file_path, role, weights, params)
        if ranker.STATE.get("status") != "done":
            raise RuntimeError(ranker.STATE.get("message", "Ranking failed."))

        lb = ranker.leaderboard(page=1, size=5000, query="")
        items = lb.get("items", [])
        details: dict[str, dict] = {}
        for it in items[:300]:               # cap heavy detail precompute
            d = ranker.detail(it["candidate_id"])
            if d:
                details[it["candidate_id"]] = d

        snapshot = {
            "summary": ranker.summary(),
            "leaderboard": items,
            "analytics": ranker.analytics(),
            "compliance": ranker.compliance(),
            "honeypots": ranker.honeypots(limit=500),
            "job_intent": ranker.job_intent(),
            "details": details,
            "logs": list(ranker.get_logs()),
            "role": role,
            "xlsx": ranker.export_excel(min(500, len(items))) if items else b"",
        }
    return snapshot


# ---------------------------------------------------------------------------
# Sidebar — controls
# ---------------------------------------------------------------------------
def sidebar_controls() -> dict | None:
    st.sidebar.markdown("### ⚙️ Ranking setup")

    sample_path = _find_sample()
    source = st.sidebar.radio(
        "Candidate data",
        ["Bundled sample (50 profiles)", "Upload JSON / JSONL"],
        index=0,
        help="The sample is a 50-profile demo pool. Upload your own JSON array "
             "or JSONL file (same schema) to rank a real pool.",
    )

    file_path: str | None = None
    if source.startswith("Bundled"):
        if sample_path:
            file_path = sample_path
            st.sidebar.caption(f"Using `{os.path.basename(sample_path)}`")
        else:
            st.sidebar.error("Bundled sample not found in the repository.")
    else:
        up = st.sidebar.file_uploader("Upload candidates", type=["json", "jsonl"])
        if up is not None:
            suffix = ".jsonl" if up.name.lower().endswith(".jsonl") else ".json"
            tmp = os.path.join(tempfile.gettempdir(), "nexthire_upload" + suffix)
            with open(tmp, "wb") as fh:
                fh.write(up.getbuffer())
            file_path = tmp
            st.sidebar.caption(f"Loaded `{up.name}` ({up.size/1e6:.1f} MB)")

    role = st.sidebar.selectbox("Target role", roles.role_names(), index=0)

    with st.sidebar.expander("Council weights (%)", expanded=False):
        st.caption("Six additive sub-scorers. Values are normalised at runtime.")
        weights = {}
        for k in COUNCIL_KEYS:
            weights[k] = st.slider(
                COUNCIL_LABELS[k], 0, 40,
                int(round(DEFAULT_WEIGHTS.get(k, 0) * 100)), 1,
                key=f"w_{k}",
            )

    with st.sidebar.expander("Fit parameters", expanded=False):
        yoe_ideal = st.slider("Ideal years of experience", 0.0, 25.0,
                              (config.EXP_IDEAL_LOW, config.EXP_IDEAL_HIGH), 0.5)
        yoe_ok = st.slider("Acceptable years of experience", 0.0, 30.0,
                           (config.EXP_OK_LOW, config.EXP_OK_HIGH), 0.5)
        notice = st.number_input("Preferred notice period (days)", 0, 180,
                                 int(config.NOTICE_PREF_DAYS), 5)
        integrity = st.toggle("Integrity Warden (exclude honeypots)", value=True)
        availability = st.toggle("Availability Oracle", value=True)

    params = {
        "yoe_ideal": list(yoe_ideal),
        "yoe_ok": list(yoe_ok),
        "notice_pref": int(notice),
        "integrity": integrity,
        "availability": availability,
        "disqualifiers": True,
    }

    run = st.sidebar.button("🚀 Rank candidates", type="primary",
                            width="stretch", disabled=file_path is None)

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "CPU-only · offline · no external API keys required. Powered by the "
        "Council-of-Nine engine (`src/`)."
    )

    if run and file_path:
        return {"file_path": file_path, "role": role,
                "weights": weights, "params": params}
    return None


# ---------------------------------------------------------------------------
# Rendering helpers for each tab
# ---------------------------------------------------------------------------
def render_overview(snap: dict) -> None:
    s = snap["summary"]
    c = st.columns(6)
    c[0].metric("Ingested", f"{s.get('ingested', 0):,}")
    c[1].metric("Ranked", f"{s.get('ranked', 0):,}")
    c[2].metric("Strong (≥85)", f"{s.get('strong_matches', 0):,}")
    c[3].metric("Honeypots excluded", f"{s.get('honeypots', 0):,}")
    c[4].metric("Notice ≤ pref", f"{s.get('notice_pct', 0)}%")
    c[5].metric("Runtime", f"{s.get('runtime', 0)}s")

    st.caption(
        f"Role: **{s.get('role', '—')}**  ·  Dataset: `{s.get('file', '—')}` "
        f"({s.get('file_size_mb', '—')} MB)"
    )

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Score distribution**")
        hist = snap["analytics"].get("score_hist", [])
        if hist:
            df = pd.DataFrame(hist)
            st.bar_chart(df, x="bucket", y="count", height=240)
    with right:
        st.markdown("**Quality tiers**")
        tiers = snap["analytics"].get("tiers", [])
        if tiers:
            df = pd.DataFrame(tiers).set_index("label")
            st.bar_chart(df, height=240)

    st.markdown("**Council weights in effect**")
    wcols = st.columns(len(s.get("weights", [])) or 1)
    for col, w in zip(wcols, s.get("weights", [])):
        col.metric(w["label"], f"{w['pct']}%")


def render_leaderboard(snap: dict) -> None:
    items = snap["leaderboard"]
    if not items:
        st.info("No ranked candidates.")
        return

    q = st.text_input("Search by candidate id, title or company", "")
    if q:
        ql = q.lower()
        items = [it for it in items
                 if ql in (it.get("candidate_id", "").lower())
                 or ql in (it.get("title", "").lower())
                 or ql in (it.get("company", "").lower())]

    rows = []
    for it in items:
        rows.append({
            "Rank": it["rank"],
            "Score": it["score"],
            "Candidate": it["candidate_id"],
            "Title": it.get("title", "—"),
            "Company": it.get("company", ""),
            "YOE": it.get("yoe"),
            "Location": it.get("location", ""),
            "Notice (d)": it.get("notice_days"),
            "Title✓": "✓" if it.get("verified_title") else "",
            "Product": "✓" if it.get("product") else "",
            "Active": "✓" if it.get("active") else "",
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df, width="stretch", hide_index=True, height=520,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.1f"),
            "YOE": st.column_config.NumberColumn("YOE", format="%.1f"),
        },
    )

    dl = st.columns(2)
    if snap.get("xlsx"):
        dl[0].download_button(
            "⬇️ Download Excel (top results)", data=snap["xlsx"],
            file_name="nexthire_ranked.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    dl[1].download_button(
        "⬇️ Download CSV (this view)", data=df.to_csv(index=False).encode("utf-8"),
        file_name="nexthire_ranked.csv", mime="text/csv",
        width="stretch",
    )


def render_candidate(snap: dict) -> None:
    items = snap["leaderboard"]
    details = snap["details"]
    if not items:
        st.info("No ranked candidates.")
        return

    labels = {f"#{it['rank']} · {it['candidate_id']} · {it.get('title','')}":
              it["candidate_id"] for it in items}
    pick = st.selectbox("Candidate", list(labels.keys()))
    cid = labels[pick]
    d = details.get(cid)
    if not d:
        st.warning("Detailed insights were only precomputed for the top 300 "
                   "ranked candidates. This one is outside that window.")
        return

    head = st.columns([3, 1, 1])
    head[0].markdown(f"### {d.get('title','—')}")
    head[0].caption(f"{d.get('company','')} · {d.get('location','')} · "
                    f"{d.get('yoe','?')} yrs · notice ~{d.get('notice_days','?')}d")
    head[1].metric("Score", f"{d.get('score', 0):.1f}")
    head[2].metric("Rank", f"#{d.get('rank', '—')}")

    if d.get("summary"):
        st.markdown(f"> {d['summary']}")

    st.markdown("**Why this score** — weighted Council contributions")
    bd = pd.DataFrame(d.get("score_breakdown", []))
    if not bd.empty:
        bd = bd.rename(columns={"label": "Signal", "score": "Sub-score",
                                "weight": "Weight %", "points": "Points"})
        st.dataframe(bd[["Signal", "Sub-score", "Weight %", "Points"]],
                     width="stretch", hide_index=True)

    cols = st.columns(2)
    with cols[0]:
        st.markdown("**✅ Strengths**")
        for sgth in d.get("strengths", []):
            st.markdown(f"- **{sgth['label']}** — {sgth['detail']}")
        if not d.get("strengths"):
            st.caption("No standout strengths detected.")
    with cols[1]:
        st.markdown("**⚠️ Weaknesses**")
        for wk in d.get("weaknesses", []):
            st.markdown(f"- **{wk['label']}** — {wk['detail']}")
        if not d.get("weaknesses"):
            st.caption("No material weaknesses detected.")

    risk = d.get("risk", {})
    st.markdown("**🛡️ Risk assessment**")
    rc = st.columns([1, 3])
    rc[0].metric("Risk score", f"{risk.get('score', 0)}",
                 risk.get("level", "low").upper())
    rc[0].progress(min(100, int(risk.get("score", 0))) / 100)
    with rc[1]:
        for f in risk.get("factors", []):
            st.markdown(_pill(f"{f['label']} ({f['severity']})",
                              SEVERITY_PILL.get(f["severity"], "nh-info")),
                        unsafe_allow_html=True)

    cov = st.columns([1, 1])
    with cov[0]:
        st.markdown("**Must-have coverage**")
        pct = d.get("must_have_coverage", 0)
        st.progress(pct / 100)
        st.caption(f"{d.get('must_have_covered',0)}/{d.get('must_have_total',0)} "
                   f"required capabilities matched ({pct}%)")
        miss = d.get("missing_qualifications", [])
        if miss:
            st.markdown("**Missing / gaps**")
            for m in miss:
                st.markdown(f"- {m['label']}")
    with cov[1]:
        st.markdown("**Verified relevant skills**")
        skills = d.get("verified_skills", [])
        if skills:
            st.markdown(" ".join(_pill(s, "nh-good") for s in skills),
                        unsafe_allow_html=True)
        else:
            st.caption("None verified.")
        sim = d.get("similar_roles", [])
        if sim:
            st.markdown("**Also a fit for**")
            for r in sim:
                st.markdown(f"- {r['role']} — {r['match']}% match")

    if d.get("career"):
        st.markdown("**Career history**")
        for r in d["career"]:
            with st.expander(f"{r.get('title','—')} · {r.get('company','')} "
                             f"({r.get('start','?')} → {r.get('end','?')})"):
                st.write(r.get("description", ""))

    if d.get("reasoning"):
        st.markdown("**Model reasoning**")
        st.info(d["reasoning"])


def render_analytics(snap: dict) -> None:
    a = snap["analytics"]
    if not a:
        st.info("No analytics available.")
        return

    c = st.columns(2)
    with c[0]:
        st.markdown("**Experience (YOE) distribution**")
        if a.get("yoe_hist"):
            st.bar_chart(pd.DataFrame(a["yoe_hist"]), x="bucket", y="count", height=240)
    with c[1]:
        st.markdown("**Average Council sub-scores**")
        if a.get("council_avg"):
            df = pd.DataFrame(a["council_avg"]).set_index("label")[["avg"]]
            st.bar_chart(df, height=240)

    c2 = st.columns(2)
    with c2[0]:
        st.markdown("**Top skills in pool**")
        if a.get("top_skills"):
            df = pd.DataFrame(a["top_skills"]).set_index("name")[["count", "verified"]]
            st.bar_chart(df, height=260)
    with c2[1]:
        st.markdown("**Company background**")
        comp = a.get("company", {})
        if comp:
            df = pd.DataFrame(
                {"type": ["Product", "Services", "Mixed"],
                 "count": [comp.get("product", 0), comp.get("services", 0),
                           comp.get("mixed", 0)]}
            )
            st.bar_chart(df, x="type", y="count", height=260)

    if a.get("skills_heatmap", {}).get("skills"):
        st.markdown("**Skill proficiency heatmap**")
        hm = a["skills_heatmap"]
        df = pd.DataFrame(hm["matrix"], index=hm["skills"], columns=hm["levels"])
        st.dataframe(df, width="stretch")

    c3 = st.columns(2)
    with c3[0]:
        st.markdown("**Top locations**")
        if a.get("locations"):
            st.bar_chart(pd.DataFrame(a["locations"]).set_index("label"), height=240)
    with c3[1]:
        st.markdown("**Hiring funnel**")
        if a.get("funnel"):
            st.dataframe(pd.DataFrame(a["funnel"]), width="stretch",
                         hide_index=True)


def render_compliance(snap: dict) -> None:
    comp = snap["compliance"]
    if not comp:
        st.info("No compliance report available.")
        return

    overall = comp.get("overall", {})
    if overall.get("passes"):
        st.success(f"✅ {overall.get('summary', 'No bias detected.')}")
    else:
        st.warning(f"⚠️ {overall.get('summary', 'Potential bias flagged.')}")

    flags = comp.get("bias_flags", [])
    if flags:
        st.markdown("**Bias flags**")
        for f in flags:
            st.markdown(
                _pill(f"{f['attribute']} · {f['metric']} = {f['value']}",
                      SEVERITY_PILL.get(f["severity"], "nh-warn")),
                unsafe_allow_html=True,
            )
            st.caption(f["message"])

    metrics = comp.get("metrics", {})
    if metrics:
        st.markdown("**Fairness metrics (4/5ths rule)**")
        rows = []
        for attr, m in metrics.items():
            rows.append({
                "Attribute": attr,
                "Disparate impact": m.get("disparate_impact_ratio"),
                "Passes 4/5ths": "✓" if m.get("passes_four_fifths") else "✗",
                "Parity diff": m.get("statistical_parity_diff"),
                "Score gap": m.get("score_gap"),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    scoring = comp.get("scoring", {})
    if scoring:
        st.markdown("**How the score is computed**")
        st.code(scoring.get("formula", ""), language="text")
        st.caption(scoring.get("explanation", ""))
        if scoring.get("council"):
            st.dataframe(
                pd.DataFrame(scoring["council"])[["label", "description", "weight", "avg"]]
                .rename(columns={"label": "Signal", "description": "What it measures",
                                 "weight": "Weight %", "avg": "Pool avg"}),
                width="stretch", hide_index=True,
            )
        if scoring.get("gates"):
            st.markdown("**Multiplicative gates**")
            for g in scoring["gates"]:
                st.markdown(f"- **{g['name']}** ({g['type']}) — {g['detail']}")

    audit = comp.get("audit", {})
    if audit:
        with st.expander("EU AI Act audit record"):
            st.json(audit)


def render_integrity(snap: dict) -> None:
    hp = snap["honeypots"]
    if not hp or hp.get("total", 0) == 0:
        st.success("No integrity violations (honeypots) detected in this pool.")
        return

    c = st.columns(3)
    c[0].metric("Honeypots flagged", f"{hp.get('total', 0):,}")
    c[1].metric("Inflation rate", f"{hp.get('inflation_rate', 0)}%")
    c[2].metric("Most common", hp.get("most_common_violation", "—"))

    if hp.get("violation_counts"):
        st.markdown("**Violation types**")
        st.bar_chart(pd.DataFrame(hp["violation_counts"]).set_index("type"), height=240)

    st.markdown("**Flagged profiles**")
    rows = []
    for it in hp.get("items", []):
        rows.append({
            "Candidate": it.get("candidate_id"),
            "Title": it.get("title"),
            "Violation": it.get("violation_type"),
            "Flagged": it.get("flagged_skill") or "—",
            it.get("claimed_label", "Claimed"): it.get("claimed_value"),
            it.get("baseline_label", "Baseline"): it.get("baseline_value"),
            "Severity": it.get("severity"),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                 height=420)


def render_logs(snap: dict) -> None:
    logs = snap.get("logs", [])
    if not logs:
        st.info("No activity logged.")
        return
    df = pd.DataFrame(logs)[["ts", "level", "source", "msg"]]
    st.dataframe(df, width="stretch", hide_index=True, height=520)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.markdown('<p class="nh-title">🧠 NextHire — The AI Recruiting Brain</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="nh-sub">Council-of-Nine candidate ranking · explainable, '
        'fairness-audited, CPU-only and fully offline.</p>',
        unsafe_allow_html=True,
    )

    request = sidebar_controls()

    if request:
        try:
            with st.spinner("Ranking the pool through the Council of Nine…"):
                st.session_state["result"] = run_ranking(**request)
            st.toast("Ranking complete.", icon="✅")
        except Exception as e:  # surface engine errors cleanly
            st.error(f"Ranking failed: {type(e).__name__}: {e}")

    snap = st.session_state.get("result")
    if not snap:
        st.info(
            "👈 Pick a data source and target role in the sidebar, then click "
            "**Rank candidates**. Start with the bundled 50-profile sample for an "
            "instant demo, or upload your own JSON/JSONL pool."
        )
        with st.expander("What is this?"):
            st.markdown(
                "- Ranks candidates against a target role using six explainable "
                "sub-scorers (the *Council of Nine*).\n"
                "- Excludes logically-impossible *honeypot* profiles (Integrity Warden).\n"
                "- Runs a disparate-impact **fairness audit** (EU AI Act, 4/5ths rule).\n"
                "- 100% CPU, offline — no API keys or external services."
            )
        return

    tabs = st.tabs([
        "📊 Overview", "🏆 Leaderboard", "👤 Candidate",
        "📈 Analytics", "⚖️ Compliance", "🔍 Integrity", "🧾 Activity log",
    ])
    with tabs[0]:
        render_overview(snap)
    with tabs[1]:
        render_leaderboard(snap)
    with tabs[2]:
        render_candidate(snap)
    with tabs[3]:
        render_analytics(snap)
    with tabs[4]:
        render_compliance(snap)
    with tabs[5]:
        render_integrity(snap)
    with tabs[6]:
        render_logs(snap)


if __name__ == "__main__":
    main()
