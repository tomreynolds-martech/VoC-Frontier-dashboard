"""Plotly chart builders and small analytics helpers for the dashboard."""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src import config

PALETTE = ["#0B5FFF", "#00B3A4", "#FF8A3D", "#A05BFF", "#FF5C8A", "#2BB673"]


def _empty(msg: str = "No data for the current filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#888"))
    fig.update_layout(height=320, xaxis_visible=False, yaxis_visible=False)
    return fig


def trend_chart(df: pd.DataFrame, mode: str, metric_field: str) -> go.Figure:
    """Trend over time for a chosen metric.

    mode: 'Overall' | 'Attendee Type' | 'Campaign'
    Shows absolute response counts (bars) + average score line.
    """
    if df.empty or "response_date" not in df:
        return _empty()
    d = df.dropna(subset=["response_date"]).copy()
    if d.empty:
        return _empty()
    d["day"] = d["response_date"].dt.date

    fig = go.Figure()
    label = config.SCORE_FIELDS.get(metric_field, metric_field)

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
                    range=[config.SCORE_MIN - 0.2, config.SCORE_MAX + 0.2]),
        xaxis=dict(title=None),
        plot_bgcolor="white",
    )
    return fig


def attendee_comparison(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty()
    rows = []
    for fld, label in config.SCORE_FIELDS.items():
        if fld not in df:
            continue
        for at, grp in df.groupby("attendee_type"):
            rows.append({"Metric": label, "Attendee Type": at,
                         "Avg": grp[fld].mean()})
    if not rows:
        return _empty()
    cmp = pd.DataFrame(rows)
    fig = px.bar(cmp, x="Metric", y="Avg", color="Attendee Type",
                 barmode="group", color_discrete_sequence=PALETTE)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=80),
                      yaxis=dict(range=[0, config.SCORE_MAX]),
                      plot_bgcolor="white",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(tickangle=-25)
    return fig


def campaign_ranking(df: pd.DataFrame, metric_field: str, top_n: int = 12) -> go.Figure:
    if df.empty or metric_field not in df:
        return _empty()
    g = (df.groupby("campaign_name")
           .agg(avg=(metric_field, "mean"), n=("record_id", "count"))
           .reset_index().sort_values("avg"))
    g = g.tail(top_n)
    label = config.SCORE_FIELDS.get(metric_field, metric_field)
    fig = px.bar(g, x="avg", y="campaign_name", orientation="h",
                 text=g["avg"].round(2),
                 color="avg", color_continuous_scale="Blues")
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title=f"Avg {label}", range=[0, config.SCORE_MAX]),
                      yaxis=dict(title=None), coloraxis_showscale=False,
                      plot_bgcolor="white")
    fig.update_yaxes(tickfont=dict(size=10))
    return fig


def score_heatmap(df: pd.DataFrame, split: str = "attendee_type") -> go.Figure:
    if df.empty:
        return _empty()
    fields = [f for f in config.SCORE_FIELDS if f in df]
    groups = sorted(df[split].dropna().unique())
    z, ytext = [], []
    for g in groups:
        sub = df[df[split] == g]
        z.append([round(sub[f].mean(), 2) if sub[f].notna().any() else None
                  for f in fields])
        ytext.append(str(g)[:40])
    if not z:
        return _empty()
    fig = go.Figure(go.Heatmap(
        z=z, x=[config.SCORE_FIELDS[f] for f in fields], y=ytext,
        colorscale="RdYlGn", zmin=config.SCORE_MIN, zmax=config.SCORE_MAX,
        text=z, texttemplate="%{text}", colorbar=dict(title="Avg")))
    fig.update_layout(height=80 + 42 * len(groups),
                      margin=dict(l=10, r=10, t=30, b=80))
    fig.update_xaxes(tickangle=-25, tickfont=dict(size=10))
    return fig


def next_step_breakdown(df: pd.DataFrame) -> go.Figure:
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


def extract_themes(series: pd.Series, top_n: int = 12) -> pd.DataFrame:
    """Very lightweight keyword frequency for open-text fields."""
    words = Counter()
    for txt in series.dropna():
        for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]+", str(txt).lower()):
            if len(w) > 3 and w not in config.STOP_WORDS:
                words[w] += 1
    rows = words.most_common(top_n)
    return pd.DataFrame(rows, columns=["Theme", "Mentions"])
