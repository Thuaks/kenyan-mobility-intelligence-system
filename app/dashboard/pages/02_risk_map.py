"""
app/dashboard/pages/02_risk_map.py
Page 2 — Route Risk Map
Interactive route selector with live risk scores, SHAP driver breakdown,
Folium risk map, and a full route comparison table.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from app.dashboard.config import GLOBAL_CSS, RISK_COLORS, RISK_LABELS
from app.dashboard.data_loader import load_routes, load_accidents, load_risk_model
from app.dashboard.components.charts import shap_waterfall_bar, route_risk_bar
from app.dashboard.components.maps import route_risk_map, accident_heatmap_map

st.set_page_config(
    page_title="NUMP — Route Risk Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.dashboard.bootstrap import require_data
require_data()
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 NUMP")
    st.markdown(
        "<span style='color:#8b9ab0;font-size:0.82rem'>"
        "Nairobi Urban Mobility<br>Platform</span>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='ke-flag-stripe'></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### Navigation")
    st.page_link("pages/01_home.py",       label="🏠 Home & KPIs")
    st.page_link("pages/02_risk_map.py",   label="🗺️ Route Risk Map")
    st.page_link("pages/03_demand.py",     label="📈 Demand Forecast")
    st.page_link("pages/04_blackspots.py", label="📍 Blackspot Intelligence")
    st.page_link("pages/05_social.py",     label="📣 Social Feed")
    st.divider()

    st.markdown("### 🎛️ Controls")
    risk_filter = st.multiselect(
        "Filter by risk tier",
        options=[1, 2, 3, 4, 5],
        default=[1, 2, 3, 4, 5],
        format_func=lambda x: f"Tier {x} — {RISK_LABELS[x]}",
    )
    map_layer = st.radio(
        "Map layer",
        ["Route Risk Markers", "Accident Heatmap"],
        index=0,
    )
    show_table = st.checkbox("Show full route table", value=True)


# ── Load ───────────────────────────────────────────────────────────────────────
with st.spinner("Loading route data…"):
    route_df  = load_routes()
    acc_df    = load_accidents()
    risk_art  = load_risk_model()

if route_df.empty:
    st.error("Route data not found. Run `make seed` then `make train`.")
    st.stop()

# Apply tier filter
filtered_df = route_df[route_df["risk_score"].isin(risk_filter)].copy()


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:0'>🗺️ Route Risk Map</h2>"
    "<p style='color:#8b9ab0;margin-top:4px'>"
    "ML-scored risk tiers for all 20 Nairobi matatu routes · "
    "XGBoost classifier + SHAP explainability</p>",
    unsafe_allow_html=True,
)
st.divider()


# ── Row 1 — route selector + risk badge ───────────────────────────────────────
col_sel, col_badge, col_acc, col_dist, col_fare = st.columns([3, 2, 2, 2, 2])

with col_sel:
    route_options = {
        row["route_id"]: f"{row['route_id']} — {row['route_name']}"
        for _, row in route_df.sort_values("risk_score", ascending=False).iterrows()
    }
    selected_id = st.selectbox(
        "Select a route to inspect",
        options=list(route_options.keys()),
        format_func=lambda x: route_options[x],
    )

sel = route_df[route_df["route_id"] == selected_id].iloc[0]
tier  = int(sel["risk_score"])
color = RISK_COLORS[tier]
label = RISK_LABELS[tier]

def metric_card(val, label, color="#c8d0e0"):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:{color};font-size:1.6rem'>{val}</div>"
        f"<div class='kpi-label'>{label}</div>"
        f"</div>"
    )

with col_badge:
    st.markdown(
        f"<div class='kpi-card' style='border-color:{color}'>"
        f"<div class='kpi-value' style='color:{color};font-size:2.4rem'>{tier}/5</div>"
        f"<div class='kpi-label'>Risk Score</div>"
        f"<div style='margin-top:6px'>"
        f"<span class='risk-badge' style='background:{color}'>{label}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
with col_acc:
    st.markdown(
        metric_card(int(sel["accidents_24mo"]), "Accidents (24 mo)", "#e74c3c"),
        unsafe_allow_html=True,
    )
with col_dist:
    st.markdown(
        metric_card(f"{sel['distance_km']:.1f} km", "Route Length", "#3498db"),
        unsafe_allow_html=True,
    )
with col_fare:
    st.markdown(
        metric_card(f"KES {int(sel['avg_fare_ksh'])}", "Avg Fare", "#2ecc71"),
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# ── Row 2 — Map (left) + SHAP drivers (right) ─────────────────────────────────
col_map, col_shap = st.columns([3, 2])

with col_map:
    st.markdown(
        "<div class='section-header'>Interactive Risk Map — Nairobi</div>",
        unsafe_allow_html=True,
    )
    with st.spinner("Rendering map…"):
        if map_layer == "Route Risk Markers":
            m = route_risk_map(filtered_df)
        else:
            m = accident_heatmap_map(acc_df) if not acc_df.empty else route_risk_map(filtered_df)
        components.html(m._repr_html_(), height=480, scrolling=False)

with col_shap:
    st.markdown(
        "<div class='section-header'>SHAP Risk Drivers</div>",
        unsafe_allow_html=True,
    )

    # Build SHAP drivers from model if available, else use feature values
    if risk_art is not None:
        try:
            from ml.risk.classifier import predict as risk_predict
            result = risk_predict(selected_id, route_df, risk_art)
            drivers = result.get("top_drivers", [])
        except Exception:
            drivers = []
    else:
        # Fallback — show top feature values as proxy
        drivers = [
            {"feature": "accidents_per_km",   "shap_value": float(sel["accidents_per_km"]) * 0.3},
            {"feature": "lighting_score",      "shap_value": -(1 - float(sel["lighting_score"])) * 0.2},
            {"feature": "population_density",  "shap_value": float(sel["population_density"]) / 100000 * 0.15},
        ]

    if drivers:
        st.plotly_chart(
            shap_waterfall_bar(drivers, sel["route_name"]),
            use_container_width=True,
        )
    else:
        st.info("Train the risk model to see SHAP explanations.")

    # Driver interpretation
    st.markdown("**Top risk drivers:**")
    direction_icon = {"increases_risk": "🔴", "decreases_risk": "🟢"}
    for d in drivers[:3]:
        icon = direction_icon.get(d.get("direction", ""), "⚪")
        feat = d["feature"].replace("_", " ").title()
        val  = d["shap_value"]
        st.markdown(
            f"{icon} **{feat}** — SHAP: `{val:+.4f}`",
        )


# ── Row 3 — Route detail metrics ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-header'>Route Profile Detail</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
detail_cards = [
    (c1, int(sel["n_stops"]),              "Stops",               "#8b9ab0"),
    (c2, int(sel["n_intersections"]),       "Intersections",       "#8b9ab0"),
    (c3, f"{sel['pct_tarmac']*100:.0f}%",  "Tarmac Coverage",     "#2ecc71"),
    (c4, f"{sel['lighting_score']:.2f}",   "Lighting Score",      "#f1c40f"),
    (c5, int(sel["n_schools_nearby"]),      "Schools Nearby",      "#3498db"),
    (c6, f"{int(sel['accidents_per_km']*1000)/1000:.3f}", "Accidents / km", "#e74c3c"),
]
for col, val, lbl, clr in detail_cards:
    with col:
        st.markdown(metric_card(val, lbl, clr), unsafe_allow_html=True)


# ── Row 4 — Full route comparison table ───────────────────────────────────────
if show_table:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-header'>All Routes — Risk Comparison Table</div>",
        unsafe_allow_html=True,
    )

    display_df = route_df[[
        "route_id", "route_name", "risk_score", "sub_county",
        "distance_km", "accidents_24mo", "accidents_per_km",
        "fatalities_24mo", "avg_fare_ksh", "lighting_score",
    ]].copy().sort_values("risk_score", ascending=False)

    display_df["risk_label"] = display_df["risk_score"].map(RISK_LABELS)
    display_df = display_df.rename(columns={
        "route_id":        "Route ID",
        "route_name":      "Route Name",
        "risk_score":      "Score",
        "risk_label":      "Tier",
        "sub_county":      "Sub-County",
        "distance_km":     "Dist (km)",
        "accidents_24mo":  "Accidents (24mo)",
        "accidents_per_km":"Acc/km",
        "fatalities_24mo": "Fatalities",
        "avg_fare_ksh":    "Fare (KES)",
        "lighting_score":  "Lighting",
    })

    def _color_score(val):
        colors_map = {1:"#2ecc71", 2:"#f1c40f", 3:"#e67e22", 4:"#e74c3c", 5:"#8e44ad"}
        c = colors_map.get(int(val), "#999")
        return f"background-color:{c}22;color:{c};font-weight:bold"

    styled = (
        display_df.style
        .applymap(_color_score, subset=["Score"])
        .format({"Dist (km)": "{:.1f}", "Acc/km": "{:.3f}", "Lighting": "{:.2f}"})
        .set_properties(**{"text-align": "center"})
    )
    st.dataframe(styled, use_container_width=True, height=420)


# ── Row 5 — Risk tier risk bar ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-header'>Risk Score Distribution — Filtered Routes</div>",
    unsafe_allow_html=True,
)
if not filtered_df.empty:
    st.plotly_chart(route_risk_bar(filtered_df), use_container_width=True)
else:
    st.warning("No routes match the selected tier filter.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='color:#4a5568;font-size:0.75rem;text-align:center'>"
    "Risk model: XGBoost 500 estimators · SHAP TreeExplainer · "
    "Features: road geometry + accident history + population density</p>",
    unsafe_allow_html=True,
)
