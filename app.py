"""Frontiers 2026 Voice-of-Customer dashboard - single-file Streamlit app.

This is fully self-contained: no local package imports. The only files the repo
needs are this app.py, requirements.txt, and the CSV at data/frontiers_responses.csv.

Update the dashboard by replacing data/frontiers_responses.csv (same headers).
Run locally:  streamlit run app.py
"""
from __future__ import annotations

import os
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ===========================================================================
# Configuration
# ===========================================================================
APP_TITLE = "Frontiers 2026 - Voice of Customer"
APP_ICON = "📊"

HERE = os.path.dirname(os.path.abspath(__file__))
# Try a few sensible locations so it works whether the CSV is in data/ or root.
CSV_CANDIDATES = [
    os.path.join(HERE, "data", "frontiers_responses.csv"),
    os.path.join(HERE, "frontiers_responses.csv"),
    "data/frontiers_responses.csv",
    "frontiers_responses.csv",
]

# Maps exact CSV header text -> short field name (whitespace/newline tolerant).
COLUMN_MAP = {
    "Responsedate": "response_date",
    "Name": "name",
    "Account Name": "account_name",
    "Email": "email",
    "Attendee Type": "attendee_type",
    "Campaign Name": "campaign_name",
    "Adhoc SFDC Account - ID": "sfdc_account_id",
    "Adhoc SFDC Contact - ID": "sfdc_contact_id",
    "Program Name": "program_name",
    "Survey ID": "survey_id",
    "How satisfied are you with the relevance and value of the content presented at Frontiers 2026?": "satisfaction",
    "Fuel for Brand Fandom Keynote": "keynote",
    "Q+A Panel with Editors": "panel",
    "Workshop": "workshop",
    "How likely are you to apply the strategies or insights shared during Frontiers with your business?": "apply",
    "Based on your experience with us, how likely are you to collaborate with News\nAustralia in the future?": "collaborate",
    "What would be the most helpful next step for your business?": "next_step",
    "What is the reason for providing the score? (Optional)": "reason",
    "What is one thing we could change or add that would have made this event more impactful for you? (optional)": "improvement",
}

SCORE_FIELDS = {
    "satisfaction": "Overall Satisfaction",
    "keynote": "Fuel for Brand Fandom Keynote",
    "panel": "Q+A Panel with Editors",
    "workshop": "Workshop",
    "apply": "Likelihood to Apply",
    "collaborate": "Likelihood to Collaborate",
}

TEXT_FIELDS = {
    "next_step": "Most Helpful Next Step",
    "reason": "Reason for Score",
    "improvement": "Suggested Improvement",
}

SCORE_MIN, SCORE_MAX = 1, 5
PALETTE = ["#0B5FFF", "#00B3A4", "#FF8A3D", "#A05BFF", "#FF5C8A", "#2BB673"]

STOP_WORDS = set(
    """a an the and or but if then else for to of in on at by with without from as is are was were
    be been being it its this that these those i you he she we they them us our your their my me
    very really great good nice well had has have do did so just too much more most some any
    all no not nor about into over under out up down off than thank thanks event events day
    workshop session sessions news australia frontiers year felt feel like would could really""".split()
)

# ===========================================================================
# Data loading
# ===========================================================================
def _norm_key(s: str) -> str:
    return " ".join(str(s).split()).lower()

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    path = next((p for p in CSV_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(
            "Could not find frontiers_responses.csv. Expected it at "
            "data/frontiers_responses.csv in the repo."
        )
    df = pd.read_csv(path)

    lookup = {_norm_key(raw): short for raw, short in COLUMN_MAP.items()}
    rename = {c: lookup[_norm_key(c)] for c in df.columns if _norm_key(c) in lookup}
    df = df.rename(columns=rename)
    df = df[[c for c in COLUMN_MAP.values() if c in df.columns]].copy()

    if "response_date" in df:
        df["response_date"] = pd.to_datetime(df["response_date"], errors="coerce")
    for fld in SCORE_FIELDS:
        if fld in df:
            df[fld] = pd.to_numeric(df[fld], errors="coerce")
    for fld in TEXT_FIELDS:
        if fld in df:
            df[fld] = df[fld].astype("string")

    df = df.reset_index(drop=True)
    df.insert(0, "record_id", range(1, len(df) + 1))
    return df

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    inverse = {v: k for k, v in COLUMN_MAP.items()}
    out = df.drop(columns=[c for c in ["record_id"] if c in df.columns]).copy()
    out = out.rename(columns={c: inverse.get(c, c) for c in out.columns})
    return out.to_csv(index=False).encode("utf-8")

# ===========================================================================
# Charts
# ===========================================================================
def _empty(msg="No data for the current filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#888"))
    fig.update_layout(height=320, xaxis_visible=False, yaxis_visible=False)
    return fig

def trend_chart(df, mode, metric_field) -> go.Figure:
    if df.empty or "response_date" not in df:
        return _empty()
    d = df.dropna(subset=["response_date"]).copy()
    if d.empty:
        return _empty()
    d["day"] = d["response_date"].dt.date
    fig = go.Figure()
    label = SCORE_FIELDS.get(metric_field, metric_field)
    if mode == "Overall":
        g = d.groupby("day").agg(n=("record_id", "count"),
                                 score=(metric_field, "mean")).reset_index()
        fig.add_bar(x=g["day"], y=g["n"], name="Responses",
                    marker_color="#D6E2FF", yaxis="y1")
        fig.add_scatter(x=g["day"], y=g["score"], name=f"Avg {label}",
                        mode="lines+markers", line=dict(color=PALETTE[0], width=3),
                        yaxis="y2")
    else:
        split = "attendee_type" if mode == "Attendee Type" else "campaign_name"
        for i, (key, grp) in enumerate(d.groupby(split)):
            g = grp.groupby("day").agg(score=(metric_field, "mean")).reset_index()
            fig.add_scatter(x=g["day"], y=g["score"], name=str(key)[:38],
                            mode="lines+markers",
                            line=dict(color=PALETTE[i % len(PALETTE)], width=2.5),
                            yaxis="y2")
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(title="Responses", showgrid=False),
        yaxis2=dict(title=f"Avg {label}", overlaying="y", side="right",
                    range=[SCORE_MIN - 0.2, SCORE_MAX + 0.2]),
        xaxis=dict(title=None), plot_bgcolor="white")
    return fig

def attendee_comparison(df) -> go.Figure:
    if df.empty:
        return _empty()
    rows = []
    for fld, label in SCORE_FIELDS.items():
        if fld not in df:
            continue
        for at, grp in df.groupby("attendee_type"):
            rows.append({"Metric": label, "Attendee Type": at, "Avg": grp[fld].mean()})
    if not rows:
        return _empty()
    cmp = pd.DataFrame(rows)
    fig = px.bar(cmp, x="Metric", y="Avg", color="Attendee Type",
                 barmode="group", color_discrete_sequence=PALETTE)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=80),
                      yaxis=dict(range=[0, SCORE_MAX]), plot_bgcolor="white",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(tickangle=-25)
    return fig

def campaign_ranking(df, metric_field, top_n=12) -> go.Figure:
    if df.empty or metric_field not in df:
        return _empty()
    g = (df.groupby("campaign_name")
           .agg(avg=(metric_field, "mean"), n=("record_id", "count"))
           .reset_index().sort_values("avg").tail(top_n))
    label = SCORE_FIELDS.get(metric_field, metric_field)
    fig = px.bar(g, x="avg", y="campaign_name", orientation="h",
                 text=g["avg"].round(2), color="avg", color_continuous_scale="Blues")
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title=f"Avg {label}", range=[0, SCORE_MAX]),
                      yaxis=dict(title=None), coloraxis_showscale=False,
                      plot_bgcolor="white")
    fig.update_yaxes(tickfont=dict(size=10))
    return fig

def score_heatmap(df, split="attendee_type") -> go.Figure:
    if df.empty:
        return _empty()
    fields = [f for f in SCORE_FIELDS if f in df]
    groups = sorted(df[split].dropna().unique())
    z, ytext = [], []
    for g in groups:
        sub = df[df[split] == g]
        z.append([round(sub[f].mean(), 2) if sub[f].notna().any() else None for f in fields])
        ytext.append(str(g)[:40])
    if not z:
        return _empty()
    fig = go.Figure(go.Heatmap(
        z=z, x=[SCORE_FIELDS[f] for f in fields], y=ytext,
        colorscale="RdYlGn", zmin=SCORE_MIN, zmax=SCORE_MAX,
        text=z, texttemplate="%{text}", colorbar=dict(title="Avg")))
    fig.update_layout(height=80 + 42 * len(groups), margin=dict(l=10, r=10, t=30, b=80))
    fig.update_xaxes(tickangle=-25, tickfont=dict(size=10))
    return fig

def next_step_breakdown(df) -> go.Figure:
    if df.empty or "next_step" not in df:
        return _empty()
    s = df["next_step"].dropna()
    s = s[s.astype(str).str.strip() != ""]
    if s.empty:
        return _empty("No next-step selections in current filters")
    g = s.value_counts().reset_index()
    g.columns = ["Next step", "Count"]
    fig = px.bar(g, x="Count", y="Next step", orientation="h",
                 text="Count", color_discrete_sequence=[PALETTE[1]])
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis=dict(title=None), plot_bgcolor="white")
    fig.update_yaxes(tickfont=dict(size=10))
    return fig

def extract_themes(series, top_n=12) -> pd.DataFrame:
    words = Counter()
    for txt in series.dropna():
        for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]+", str(txt).lower()):
            if len(w) > 3 and w not in STOP_WORDS:
                words[w] += 1
    return pd.DataFrame(words.most_common(top_n), columns=["Theme", "Mentions"])

# ===========================================================================
# App
# ===========================================================================
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON,
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem;}
      div[data-testid="stMetric"] {background:#F5F7FA; border:1px solid #E5E9F0;
          border-radius:14px; padding:14px 16px;}
      div[data-testid="stMetricValue"] {font-size:1.7rem;}
      h1, h2, h3 {letter-spacing:-0.01em;}
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    df = load_data()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.markdown(f"# {APP_ICON} {APP_TITLE}")
st.caption("Voice-of-Customer analytics for Frontiers 2026 - survey results, "
           "session ratings, attendee segmentation, and qualitative feedback.")

# ---- Sidebar filters ------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    sel_campaigns = st.multiselect("Campaign Name",
                                   sorted(df["campaign_name"].dropna().unique()))
    sel_att = st.multiselect("Attendee Type",
                             sorted(df["attendee_type"].dropna().unique()))
    sel_accounts = st.multiselect("Account Name",
                                  sorted(df["account_name"].dropna().unique()))
    if df["response_date"].notna().any():
        dmin = df["response_date"].min().date()
        dmax = df["response_date"].max().date()
        date_range = st.date_input("Response Date", (dmin, dmax),
                                   min_value=dmin, max_value=dmax)
    else:
        date_range = None
    search = st.text_input("Search open-text feedback")
    st.divider()
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()
    st.caption("To update the dashboard, replace "
               "`data/frontiers_responses.csv` in the repo and reload.")

# ---- Apply filters --------------------------------------------------------
f = df.copy()
if sel_campaigns:
    f = f[f["campaign_name"].isin(sel_campaigns)]
if sel_att:
    f = f[f["attendee_type"].isin(sel_att)]
if sel_accounts:
    f = f[f["account_name"].isin(sel_accounts)]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
    f = f[(f["response_date"].dt.date >= start) & (f["response_date"].dt.date <= end)]
if search:
    mask = pd.Series(False, index=f.index)
    for fld in TEXT_FIELDS:
        if fld in f:
            mask |= f[fld].fillna("").str.contains(search, case=False)
    f = f[mask]

st.caption(f"Showing **{len(f)}** of **{len(df)}** responses")

# ---- KPI header -----------------------------------------------------------
def avg(field):
    return f"{f[field].mean():.2f}" if field in f and f[field].notna().any() else "-"

most_next = "-"
if "next_step" in f and f["next_step"].notna().any():
    vc = f["next_step"].dropna()
    vc = vc[vc.astype(str).str.strip() != ""]
    if not vc.empty:
        most_next = vc.value_counts().idxmax()

r1 = st.columns(4)
r1[0].metric("Total Responses", len(f))
r1[1].metric("Overall Satisfaction", avg("satisfaction"))
r1[2].metric("Likelihood to Apply", avg("apply"))
r1[3].metric("Likelihood to Collaborate", avg("collaborate"))

r2 = st.columns(4)
r2[0].metric("Keynote", avg("keynote"))
r2[1].metric("Q+A Panel", avg("panel"))
r2[2].metric("Workshop", avg("workshop"))
r2[3].metric("Response Rate (filtered)",
             f"{(len(f) / len(df) * 100):.0f}%" if len(df) else "-")

st.info(f"**Most requested next step:** {most_next}")
st.divider()

# ---- Trend visual ---------------------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Trend over time")
    tc = st.columns([1, 1])
    mode = tc[0].radio("View", ["Overall", "Attendee Type", "Campaign"],
                       horizontal=True, label_visibility="collapsed")
    metric = tc[1].selectbox("Metric", list(SCORE_FIELDS),
                             format_func=lambda k: SCORE_FIELDS[k],
                             label_visibility="collapsed")
    st.plotly_chart(trend_chart(f, mode, metric), use_container_width=True)
with right:
    st.subheader("Most helpful next step")
    st.plotly_chart(next_step_breakdown(f), use_container_width=True)

st.divider()

# ---- Comparison panels ----------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    st.subheader("Agency vs Client")
    st.plotly_chart(attendee_comparison(f), use_container_width=True)
with c2:
    st.subheader("Campaign performance")
    rank_metric = st.selectbox("Rank by", list(SCORE_FIELDS),
                               format_func=lambda k: SCORE_FIELDS[k], key="rank_metric")
    st.plotly_chart(campaign_ranking(f, rank_metric), use_container_width=True)

st.divider()

# ---- Heat map -------------------------------------------------------------
st.subheader("Score distribution heat map")
split = st.radio("Break down by", ["attendee_type", "campaign_name"],
                 format_func=lambda k: "Attendee Type" if k == "attendee_type" else "Campaign",
                 horizontal=True)
st.plotly_chart(score_heatmap(f, split), use_container_width=True)

st.divider()

# ---- Qualitative insights -------------------------------------------------
st.subheader("Qualitative insights")
tabs = st.tabs([TEXT_FIELDS[t] for t in TEXT_FIELDS])
for tab, fld in zip(tabs, TEXT_FIELDS):
    with tab:
        if fld not in f:
            st.write("No data.")
            continue
        themes = extract_themes(f[fld])
        tc1, tc2 = st.columns([1, 2])
        with tc1:
            st.markdown("**Top themes**")
            st.dataframe(themes, hide_index=True, use_container_width=True)
        with tc2:
            st.markdown("**Verbatim comments**")
            comments = f[["name", "account_name", "attendee_type", fld]].dropna(subset=[fld])
            comments = comments[comments[fld].astype(str).str.strip() != ""]
            st.dataframe(comments, hide_index=True, use_container_width=True, height=300)

st.divider()

# ---- Response explorer ----------------------------------------------------
st.subheader("Response explorer")
display_cols = [c for c in
                ["response_date", "name", "account_name", "attendee_type",
                 "campaign_name"] + list(SCORE_FIELDS) +
                ["next_step", "reason", "improvement"] if c in f]
st.dataframe(f[display_cols], hide_index=True, use_container_width=True, height=380)

st.download_button("Download filtered view (CSV)", data=to_csv_bytes(f),
                   file_name="frontiers_voc_filtered.csv", mime="text/csv")
