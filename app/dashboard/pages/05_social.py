"""
app/dashboard/pages/05_social.py
Page 5 — Social Intelligence Feed
Real-time matatu incident monitoring from Twitter/X.
VADER sentiment scoring, topic clustering, volume trends, and live incident cards.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from app.dashboard.config import GLOBAL_CSS, TOPIC_COLORS, SENTIMENT_COLORS
from app.dashboard.data_loader import load_social
from app.dashboard.components.charts import (
    sentiment_pie, topic_volume_bar, tweet_volume_trend,
)

st.set_page_config(
    page_title="NUMP — Social Intelligence",
    page_icon="📣",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.dashboard.bootstrap import require_data
require_data()
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 NUMP")
    st.markdown("<span style='color:#8b9ab0;font-size:0.82rem'>Kenya Urban Mobility<br>Intelligence Platform</span>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### Navigation")
    st.page_link("pages/01_home.py",       label="🏠 Home & KPIs")
    st.page_link("pages/02_risk_map.py",   label="🗺️ Route Risk Map")
    st.page_link("pages/03_demand.py",     label="📈 Demand Forecast")
    st.page_link("pages/04_blackspots.py", label="📍 Blackspot Intelligence")
    st.page_link("pages/05_social.py",     label="📣 Social Feed")
    st.divider()

    st.markdown("### 🎛️ Controls")
    VALID_TOPICS = ["All","breakdown","accident","police_block","flooding","positive","overloading"]
    topic_filter = st.selectbox("Filter by topic", VALID_TOPICS, index=0)
    sent_filter  = st.multiselect(
        "Filter by sentiment",
        ["Positive", "Neutral", "Negative"],
        default=["Negative", "Neutral"],
    )
    incident_only = st.checkbox("Incident tweets only", value=True)
    n_cards = st.slider("Number of tweet cards", 5, 50, 20)
    show_keywords = st.checkbox("Show keyword analysis", value=True)


# ── Load ───────────────────────────────────────────────────────────────────────
with st.spinner("Loading social data…"):
    social_df = load_social()

if social_df.empty:
    st.error("Social data not found. Run `make seed`.")
    st.stop()

# Normalise column names
topic_col = "topic_label" if "topic_label" in social_df.columns else "topic"
sent_col  = "sentiment_label" if "sentiment_label" in social_df.columns else "sentiment"
inc_col   = "is_incident_nlp" if "is_incident_nlp" in social_df.columns else "is_incident"
comp_col  = "boosted_compound" if "boosted_compound" in social_df.columns else "compound"

# Apply filters
filtered = social_df.copy()
if topic_filter != "All":
    filtered = filtered[filtered[topic_col] == topic_filter]
if sent_filter:
    filtered = filtered[filtered[sent_col].isin(sent_filter)]
if incident_only:
    filtered = filtered[filtered[inc_col] == 1]
filtered = filtered.sort_values("timestamp", ascending=False)


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0'>📣 Social Intelligence Feed</h2>"
    "<p style='color:#8b9ab0;margin-top:4px'>"
    "Matatu incident monitoring · VADER + Sheng sentiment scoring · "
    "TF-IDF / LSA / K-Means topic clustering · X (Twitter)</p>",
    unsafe_allow_html=True,
)
st.divider()


# ── Row 1 — KPI cards ──────────────────────────────────────────────────────────
def kpi_card(val, label, color="#c8d0e0"):
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-value' style='color:{color};font-size:1.5rem'>{val}</div>"
            f"<div class='kpi-label'>{label}</div></div>")

total    = len(social_df)
inc_total= int(social_df[inc_col].sum())
neg_pct  = round((social_df[sent_col] == "Negative").mean() * 100, 1)
avg_sent = round(social_df[comp_col].mean(), 3)
top_topic= social_df[topic_col].value_counts().index[0]
filt_n   = len(filtered)

c1,c2,c3,c4,c5,c6 = st.columns(6)
with c1: st.markdown(kpi_card(f"{total:,}",     "Total Tweets",       "#3498db"), unsafe_allow_html=True)
with c2: st.markdown(kpi_card(f"{inc_total:,}", "Incident Tweets",    "#e74c3c"), unsafe_allow_html=True)
with c3: st.markdown(kpi_card(f"{neg_pct}%",    "Negative Sentiment", "#e74c3c"), unsafe_allow_html=True)
with c4: st.markdown(kpi_card(f"{avg_sent:+.3f}","Avg Compound Score","#f1c40f"), unsafe_allow_html=True)
with c5: st.markdown(kpi_card(top_topic,          "Top Topic",         "#e67e22"), unsafe_allow_html=True)
with c6: st.markdown(kpi_card(f"{filt_n:,}",    "Filtered Results",  "#2ecc71"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Row 2 — Sentiment pie + Topic volume + Trend ───────────────────────────────
col_pie, col_topic, col_trend = st.columns([1, 1, 2])

with col_pie:
    st.markdown("<div class='section-header'>Sentiment Split</div>", unsafe_allow_html=True)
    st.plotly_chart(sentiment_pie(social_df), use_container_width=True)

with col_topic:
    st.markdown("<div class='section-header'>Volume by Topic</div>", unsafe_allow_html=True)
    st.plotly_chart(topic_volume_bar(social_df), use_container_width=True)

with col_trend:
    st.markdown("<div class='section-header'>Weekly Tweet Volume Trend</div>", unsafe_allow_html=True)
    st.plotly_chart(tweet_volume_trend(social_df), use_container_width=True)


# ── Row 3 — Sentiment by topic heatmap ───────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_heat, col_route_sent = st.columns(2)

with col_heat:
    st.markdown("<div class='section-header'>Avg Sentiment Score by Topic</div>", unsafe_allow_html=True)
    topic_sent = social_df.groupby(topic_col)[comp_col].mean().sort_values()
    bar_colors = [TOPIC_COLORS.get(t, "#999") for t in topic_sent.index]
    fig_ts = go.Figure(go.Bar(
        x=topic_sent.values,
        y=topic_sent.index,
        orientation="h",
        marker_color=bar_colors,
        hovertemplate="<b>%{y}</b><br>Avg sentiment: %{x:.3f}<extra></extra>",
    ))
    fig_ts.add_vline(x=0, line_color="#8b9ab0", line_width=1)
    fig_ts.update_layout(
        paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
        font=dict(color="#c8d0e0"), height=300,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig_ts.update_xaxes(gridcolor="#1e2130", title="Mean VADER Compound Score")
    fig_ts.update_yaxes(gridcolor="#1e2130")
    st.plotly_chart(fig_ts, use_container_width=True)

with col_route_sent:
    st.markdown("<div class='section-header'>Incident Tweets by Route</div>", unsafe_allow_html=True)
    if "route_ref" in social_df.columns:
        route_inc = (
            social_df[social_df[inc_col] == 1]["route_ref"]
            .value_counts().head(12)
        )
        fig_ri = go.Figure(go.Bar(
            x=route_inc.values[::-1],
            y=route_inc.index[::-1],
            orientation="h",
            marker_color="#e74c3c",
            hovertemplate="<b>%{y}</b><br>%{x} incidents<extra></extra>",
        ))
        fig_ri.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            font=dict(color="#c8d0e0"), height=300,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        fig_ri.update_xaxes(gridcolor="#1e2130", title="Incident Tweet Count")
        fig_ri.update_yaxes(gridcolor="#1e2130")
        st.plotly_chart(fig_ri, use_container_width=True)


# ── Row 4 — Keyword analysis ──────────────────────────────────────────────────
if show_keywords:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Top Keywords by Topic (TF-IDF)</div>", unsafe_allow_html=True)

    # Pre-computed top keywords per topic from the NLP pipeline
    TOP_KEYWORDS = {
        "accident":     ["accident","police","scene","gari","zimegongana","serious","injury","crash","lorry","road"],
        "breakdown":    ["matatu","imesimama","foleni","breakdown","vehicle","stuck","abiria","wanangoja","route","avoid"],
        "flooding":     ["maji","mvua","flooded","barabara","impassable","heavy","rains","road","mafuriko","water"],
        "police_block": ["roadblock","polisi","checkpoint","delays","wanachunguza","magari","wamezuiwa","expect","cops"],
        "positive":     ["clear","smooth","roads","flowing","good","morning","traffic","ride","time","fine"],
        "overloading":  ["imejaa","overcrowded","dangerous","driver","full","abiria","won","move","loading","matatu"],
    }

    topic_cols = st.columns(3)
    for idx, (topic, kws) in enumerate(TOP_KEYWORDS.items()):
        col = topic_cols[idx % 3]
        with col:
            color = TOPIC_COLORS.get(topic, "#999")
            kw_html = " &nbsp; ".join(
                f"<span style='background:{color}22;color:{color};padding:2px 7px;"
                f"border-radius:10px;font-size:0.78rem;border:1px solid {color}44'>{w}</span>"
                for w in kws[:7]
            )
            st.markdown(
                f"<div style='background:#1e2130;border-left:3px solid {color};"
                f"border-radius:6px;padding:10px 14px;margin-bottom:10px'>"
                f"<b style='color:{color}'>{topic.replace('_',' ').title()}</b><br>"
                f"<div style='margin-top:6px'>{kw_html}</div></div>",
                unsafe_allow_html=True,
            )


# ── Row 5 — Live incident feed cards ──────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<div class='section-header'>📡 Incident Feed "
    f"<span style='color:#8b9ab0;font-size:0.8rem;font-weight:400'>"
    f"({min(n_cards, len(filtered))} of {len(filtered):,} filtered)</span></div>",
    unsafe_allow_html=True,
)

if filtered.empty:
    st.info("No tweets match the current filters. Adjust the sidebar controls.")
else:
    feed_data = filtered.head(n_cards)

    for _, row in feed_data.iterrows():
        topic   = str(row.get(topic_col, "unknown"))
        sent    = str(row.get(sent_col, "Neutral"))
        compound= float(row.get(comp_col, 0))
        t_color = TOPIC_COLORS.get(topic, "#95a5a6")
        s_color = SENTIMENT_COLORS.get(sent, "#999")
        ts      = str(row.get("timestamp",""))[:16]
        text    = str(row.get("text", ""))
        route_ref = str(row.get("route_ref",""))
        retweets  = int(row.get("retweets",0))
        likes     = int(row.get("likes",0))

        # Sentiment bar fill
        bar_pct  = int(abs(compound) * 100)
        bar_color= "#e74c3c" if compound < -0.05 else "#2ecc71" if compound > 0.05 else "#f1c40f"

        st.markdown(
            f"<div style='background:#1e2130;border:1px solid #2d3250;"
            f"border-left:4px solid {t_color};border-radius:8px;"
            f"padding:12px 16px;margin-bottom:8px'>"

            # Header row
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:6px'>"
            f"<span class='risk-badge' style='background:{t_color}'>"
            f"  {topic.replace('_',' ').title()}</span>"
            f"<span style='color:#8b9ab0;font-size:0.75rem'>{ts}</span>"
            f"</div>"

            # Tweet text
            f"<p style='color:#e0e0e0;margin:4px 0 8px 0;font-size:0.9rem'>{text}</p>"

            # Footer row
            f"<div style='display:flex;gap:16px;align-items:center'>"
            f"<span style='color:#8b9ab0;font-size:0.75rem'>📍 {route_ref}</span>"
            f"<span style='color:{s_color};font-size:0.75rem'>● {sent} ({compound:+.2f})</span>"
            f"<div style='flex:1;background:#2d3250;border-radius:4px;height:4px'>"
            f"  <div style='width:{bar_pct}%;background:{bar_color};height:4px;border-radius:4px'></div>"
            f"</div>"
            f"<span style='color:#8b9ab0;font-size:0.72rem'>🔁 {retweets} &nbsp; ❤️ {likes}</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='color:#4a5568;font-size:0.75rem;text-align:center'>"
    "NLP pipeline: VADER sentiment + Sheng keyword boost · TF-IDF vectoriser · "
    "LSA (50 components) · K-Means (6 clusters) · "
    "Sources: X/Twitter · @Ma3Route · #NairobiTraffic</p>",
    unsafe_allow_html=True,
)
