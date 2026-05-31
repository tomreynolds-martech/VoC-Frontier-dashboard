"""Frontiers 2026 Voice-of-Customer dashboard (single page).

Data source : data/frontiers_responses.csv  (committed in the repo)
Update       : replace that CSV and reload the app.
Run locally  : streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, config, data

st.set_page_config(page_title=config.APP_TITLE, page_icon=config.APP_ICON,
                   layout="wide", initial_sidebar_state="expanded")

# ---- Light styling --------------------------------------------------------
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem;}
      div[data-testid="stMetric"] {
          background: #F5F7FA; border: 1px solid #E5E9F0;
          border-radius: 14px; padding: 14px 16px;}
      div[data-testid="stMetricValue"] {font-size: 1.7rem;}
      h1, h2, h3 {letter-spacing: -0.01em;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data():
    return data.load_data()


df = get_data()

st.markdown(f"# {config.APP_ICON} {config.APP_TITLE}")
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
    for fld in config.TEXT_FIELDS:
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

# ---- Trend visual with global toggle --------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Trend over time")
    tc = st.columns([1, 1])
    mode = tc[0].radio("View", ["Overall", "Attendee Type", "Campaign"],
                       horizontal=True, label_visibility="collapsed")
    metric = tc[1].selectbox("Metric", list(config.SCORE_FIELDS),
                             format_func=lambda k: config.SCORE_FIELDS[k],
                             label_visibility="collapsed")
    st.plotly_chart(charts.trend_chart(f, mode, metric), use_container_width=True)

with right:
    st.subheader("Most helpful next step")
    st.plotly_chart(charts.next_step_breakdown(f), use_container_width=True)

st.divider()

# ---- Comparison panels ----------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    st.subheader("Agency vs Client")
    st.plotly_chart(charts.attendee_comparison(f), use_container_width=True)
with c2:
    st.subheader("Campaign performance")
    rank_metric = st.selectbox("Rank by", list(config.SCORE_FIELDS),
                               format_func=lambda k: config.SCORE_FIELDS[k],
                               key="rank_metric")
    st.plotly_chart(charts.campaign_ranking(f, rank_metric), use_container_width=True)

st.divider()

# ---- Heat map -------------------------------------------------------------
st.subheader("Score distribution heat map")
split = st.radio("Break down by", ["attendee_type", "campaign_name"],
                 format_func=lambda k: "Attendee Type" if k == "attendee_type" else "Campaign",
                 horizontal=True)
st.plotly_chart(charts.score_heatmap(f, split), use_container_width=True)

st.divider()

# ---- Qualitative insights -------------------------------------------------
st.subheader("Qualitative insights")
tabs = st.tabs([config.TEXT_FIELDS[t] for t in config.TEXT_FIELDS])
for tab, fld in zip(tabs, config.TEXT_FIELDS):
    with tab:
        if fld not in f:
            st.write("No data.")
            continue
        themes = charts.extract_themes(f[fld])
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
                 "campaign_name"] + list(config.SCORE_FIELDS) +
                ["next_step", "reason", "improvement"] if c in f]
st.dataframe(f[display_cols], hide_index=True, use_container_width=True, height=380)

st.download_button("Download filtered view (CSV)",
                   data=data.to_csv_bytes(f),
                   file_name="frontiers_voc_filtered.csv", mime="text/csv")
