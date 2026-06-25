"""
app/dashboard/streamlit_app.py
Main Streamlit entry point — bootstraps the NUMIP dashboard.
Streamlit Community Cloud runs THIS file.
All 5 pages live in pages/ and are auto-discovered by Streamlit's MPA system.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from app.dashboard.config import GLOBAL_CSS, APP_TITLE, APP_ICON

# set_page_config MUST be the very first Streamlit command in a script
# run — calling require_data() (which uses st.spinner/st.cache_resource)
# before this raises StreamlitAPIException.
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

from app.dashboard.bootstrap import require_data
require_data()

with st.sidebar:
    st.markdown("## 🚦 NUMIP")
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
    st.page_link("pages/05_social.py",     label="📣 Social Intelligence Feed")
    st.divider()
    st.markdown(
        "<span style='color:#8b9ab0;font-size:0.75rem'>"
        "v1.0 · Built with XGBoost · Prophet<br>"
        "DBSCAN · VADER · FastAPI · Folium<br><br>"
        "Built by <b style='color:#8b9ab0'>Alex Thuku</b>"
        "</span>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div style='text-align:center;padding:60px 20px 30px'>"
    "<div style='font-size:4rem'>🚦</div>"
    "<h1 style='font-size:2.4rem;font-weight:700;margin:10px 0 6px'>NUMIP</h1>"
    "<h2 style='font-size:1.3rem;font-weight:400;color:#8b9ab0;margin:0 0 20px'>"
    "Nairobi Urban Mobility Intelligence Platform</h2>"
    "<p style='color:#6b7a95;max-width:620px;margin:0 auto;font-size:0.95rem'>"
    "Real-time transit demand forecasting · Matatu route risk scoring · "
    "Road safety blackspot detection · Social incident intelligence — "
    "Nairobi, Kenya"
    "</p>"
    "</div>",
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)

feature_cards = [
    (c1, "🏠", "Home & KPIs",          "pages/01_home.py",       "#3498db",
     "8 headline metrics · risk distribution · accident trends · key findings"),
    (c2, "🗺️", "Route Risk Map",        "pages/02_risk_map.py",   "#e74c3c",
     "XGBoost risk scores · SHAP drivers · interactive Folium map · route profiles"),
    (c3, "📈", "Demand Forecast",       "pages/03_demand.py",     "#2ecc71",
     "Prophet + XGBoost · 7-day hourly forecasts · demand heatmap · spike alerts"),
    (c4, "📍", "Blackspot Intelligence","pages/04_blackspots.py", "#e67e22",
     "DBSCAN clustering · blackspot map · cause analysis · accident explorer"),
    (c5, "📣", "Social Feed",           "pages/05_social.py",     "#9b59b6",
     "VADER sentiment · topic clusters · incident cards · keyword analysis"),
]

for col, icon, title, link, color, desc in feature_cards:
    with col:
        st.markdown(
            f"<div class='feature-card' style='--accent:{color}'>"
            f"<div class='feature-icon'>{icon}</div>"
            f"<div class='feature-title'>{title}</div>"
            f"<div class='feature-desc'>{desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.markdown(
    "<p style='text-align:center;color:#4a5568;font-size:0.8rem'>"
    "Stack: &nbsp;"
    "<b style='color:#8b9ab0'>FastAPI</b> · "
    "<b style='color:#8b9ab0'>Streamlit</b> · "
    "<b style='color:#8b9ab0'>XGBoost</b> · "
    "<b style='color:#8b9ab0'>Prophet</b> · "
    "<b style='color:#8b9ab0'>DBSCAN</b> · "
    "<b style='color:#8b9ab0'>SHAP</b> · "
    "<b style='color:#8b9ab0'>VADER</b> · "
    "<b style='color:#8b9ab0'>SQLAlchemy</b> · "
    "<b style='color:#8b9ab0'>DuckDB</b> · "
    "<b style='color:#8b9ab0'>Folium</b> · "
    "<b style='color:#8b9ab0'>Plotly</b>"
    "</p>",
    unsafe_allow_html=True,
)
