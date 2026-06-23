"""
app/dashboard/pages/04_blackspots.py
Page 4 — Blackspot Intelligence
DBSCAN-detected accident blackspot clusters, Folium cluster map,
severity breakdown, cause analysis, and raw accident explorer.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from app.dashboard.config import GLOBAL_CSS, RISK_COLORS, RISK_LABELS
from app.dashboard.data_loader import load_accidents, load_blackspots
from app.dashboard.components.charts import blackspot_severity_bar, accident_by_hour_bar
from app.dashboard.components.maps import blackspot_map, accident_heatmap_map

st.set_page_config(
    page_title="KUMIP — Blackspot Intelligence",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.dashboard.bootstrap import require_data
require_data()
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 KUMIP")
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
    min_incidents = st.slider("Min incidents to show cluster", 1, 50, 3)
    severity_filter = st.multiselect(
        "Filter accidents by severity",
        ["Fatal", "Serious", "Minor"],
        default=["Fatal", "Serious", "Minor"],
    )
    map_type = st.radio("Map type", ["Blackspot Clusters", "Accident Heatmap"], index=0)
    show_raw = st.checkbox("Show raw accident table", value=False)


# ── Load ───────────────────────────────────────────────────────────────────────
with st.spinner("Loading accident data…"):
    acc_df = load_accidents()
    bs_df  = load_blackspots()

if acc_df.empty:
    st.error("Accident data not found. Run `make seed`.")
    st.stop()

acc_filtered = acc_df[acc_df["severity"].isin(severity_filter)].copy()
bs_filtered  = bs_df[bs_df["n_incidents"] >= min_incidents].copy() if not bs_df.empty else pd.DataFrame()


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0'>📍 Blackspot Intelligence</h2>"
    "<p style='color:#8b9ab0;margin-top:4px'>"
    "DBSCAN spatial clustering · 600m radius · min 5 incidents · "
    "Nairobi road network 2021–2024</p>",
    unsafe_allow_html=True,
)
st.divider()


# ── Row 1 — KPI cards ──────────────────────────────────────────────────────────
def kpi_card(val, label, color="#c8d0e0", sub=None):
    sub_html = f"<div class='kpi-label' style='color:#6b7a95'>{sub}</div>" if sub else ""
    return (f"<div class='kpi-card'>"
            f"<div class='kpi-value' style='color:{color};font-size:1.6rem'>{val}</div>"
            f"<div class='kpi-label'>{label}</div>{sub_html}</div>")

total_acc  = len(acc_filtered)
total_fatal = int((acc_filtered["severity"] == "Fatal").sum())
pct_peak   = round(acc_filtered["is_peak_hour"].mean() * 100, 1) if "is_peak_hour" in acc_filtered.columns else 0
top_cause  = acc_filtered["cause"].mode().iloc[0] if not acc_filtered.empty else "N/A"
top_sub    = acc_filtered["sub_county"].value_counts().index[0] if not acc_filtered.empty else "N/A"

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: st.markdown(kpi_card(f"{total_acc:,}",            "Accidents (filtered)",   "#e74c3c"), unsafe_allow_html=True)
with c2: st.markdown(kpi_card(total_fatal,                  "Fatal Accidents",        "#8e44ad"), unsafe_allow_html=True)
with c3: st.markdown(kpi_card(len(bs_filtered),            "Blackspot Clusters",      "#e67e22"), unsafe_allow_html=True)
with c4: st.markdown(kpi_card(f"{pct_peak:.1f}%",          "In Peak Hours",          "#f1c40f"), unsafe_allow_html=True)
with c5: st.markdown(kpi_card(top_sub,                     "Worst Sub-County",       "#e74c3c"), unsafe_allow_html=True)
with c6: st.markdown(kpi_card(top_cause,                   "Top Cause",              "#e67e22"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Row 2 — Map + Cluster table ───────────────────────────────────────────────
col_map, col_table = st.columns([3, 2])

with col_map:
    st.markdown("<div class='section-header'>Nairobi Blackspot Map</div>", unsafe_allow_html=True)
    with st.spinner("Rendering map…"):
        if map_type == "Blackspot Clusters" and not bs_filtered.empty:
            m = blackspot_map(acc_filtered, bs_filtered)
        else:
            m = accident_heatmap_map(acc_filtered)
        components.html(m._repr_html_(), height=460, scrolling=False)

with col_table:
    st.markdown("<div class='section-header'>Cluster Profiles</div>", unsafe_allow_html=True)
    if not bs_filtered.empty:
        for i, row in bs_filtered.iterrows():
            tier  = int(row["risk_tier"])
            color = RISK_COLORS.get(tier, "#999")
            time_label = row.get("time_of_day", f"Hour {int(row['dominant_hour'])}")
            st.markdown(
                f"<div style='background:#1e2130;border-left:4px solid {color};"
                f"border-radius:6px;padding:10px 14px;margin-bottom:8px'>"
                f"<b style='color:#fff'>Blackspot BS{i+1}</b> &nbsp;"
                f"<span class='risk-badge' style='background:{color}'>Tier {tier}</span><br>"
                f"<span style='color:#8b9ab0;font-size:0.8rem'>"
                f"📍 {row['centroid_lat']:.4f}, {row['centroid_lon']:.4f}<br>"
                f"🚨 {int(row['n_incidents'])} incidents · {int(row['n_fatal'])} fatal<br>"
                f"⏰ Peak: {time_label}<br>"
                f"⚠️ Top cause: {row['dominant_cause']}<br>"
                f"💥 Top type: {row['dominant_type']}"
                f"</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info(f"No clusters with ≥{min_incidents} incidents. Lower the filter.")


# ── Row 3 — Severity breakdown + Accident by hour ─────────────────────────────
col_sev, col_hour = st.columns(2)

with col_sev:
    st.markdown("<div class='section-header'>Blackspot Severity Breakdown</div>", unsafe_allow_html=True)
    if not bs_filtered.empty:
        st.plotly_chart(blackspot_severity_bar(bs_filtered), use_container_width=True)
    else:
        st.info("No blackspot data to display.")

with col_hour:
    st.markdown("<div class='section-header'>Accident Frequency by Hour</div>", unsafe_allow_html=True)
    if not acc_filtered.empty:
        st.plotly_chart(accident_by_hour_bar(acc_filtered), use_container_width=True)


# ── Row 4 — Cause + Surface analysis ─────────────────────────────────────────
col_cause, col_surf = st.columns(2)

with col_cause:
    st.markdown("<div class='section-header'>Accidents by Primary Cause</div>", unsafe_allow_html=True)
    if not acc_filtered.empty:
        cause_counts = acc_filtered["cause"].value_counts()
        fig_cause = go.Figure(go.Bar(
            x=cause_counts.values[::-1], y=cause_counts.index[::-1],
            orientation="h",
            marker_color="#e67e22",
            hovertemplate="<b>%{y}</b><br>%{x} accidents<extra></extra>",
        ))
        fig_cause.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            font=dict(color="#c8d0e0"), height=300,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        fig_cause.update_xaxes(gridcolor="#1e2130", title="Accident Count")
        fig_cause.update_yaxes(gridcolor="#1e2130")
        st.plotly_chart(fig_cause, use_container_width=True)

with col_surf:
    st.markdown("<div class='section-header'>Accidents by Road Surface & Lighting</div>", unsafe_allow_html=True)
    if not acc_filtered.empty:
        surf = acc_filtered["road_surface"].value_counts()
        light = acc_filtered["lighting"].value_counts()
        fig_surf = go.Figure()
        fig_surf.add_trace(go.Bar(
            name="Road Surface", x=surf.index, y=surf.values,
            marker_color="#3498db",
        ))
        fig_surf.add_trace(go.Bar(
            name="Lighting", x=light.index, y=light.values,
            marker_color="#9b59b6",
        ))
        fig_surf.update_layout(
            barmode="group",
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            font=dict(color="#c8d0e0"), height=300,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(bgcolor="rgba(30,33,48,0.8)"),
        )
        fig_surf.update_xaxes(gridcolor="#1e2130")
        fig_surf.update_yaxes(gridcolor="#1e2130", title="Count")
        st.plotly_chart(fig_surf, use_container_width=True)


# ── Row 5 — Raw accident table ─────────────────────────────────────────────────
if show_raw:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Raw Accident Records (latest 200)</div>", unsafe_allow_html=True)

    display_cols = ["accident_id","date","hour","sub_county","route_name",
                    "severity","accident_type","cause","road_surface","lighting","weather_condition"]
    available = [c for c in display_cols if c in acc_filtered.columns]
    raw_display = acc_filtered[available].sort_values("date", ascending=False).head(200)

    def _color_sev(val):
        m = {"Fatal":"#8e44ad22", "Serious":"#e74c3c22", "Minor":"#3498db22"}
        return f"background-color:{m.get(val,'transparent')}"

    styled = (
        raw_display.style
        .applymap(_color_sev, subset=["severity"])
        .set_properties(**{"text-align":"left"})
    )
    st.dataframe(styled, use_container_width=True, height=380)
    st.caption(f"Showing {min(200, len(acc_filtered))} of {len(acc_filtered):,} filtered records")


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='color:#4a5568;font-size:0.75rem;text-align:center'>"
    "Blackspot model: DBSCAN · eps=600m (haversine) · min_samples=5 · "
    "Severity scoring: Fatal=3.0 · Serious=1.5 · Minor=0.5</p>",
    unsafe_allow_html=True,
)
