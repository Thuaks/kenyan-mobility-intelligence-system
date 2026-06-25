"""
app/dashboard/data_loader.py
Cached data loaders for the Streamlit dashboard.
All heavy reads are wrapped in @st.cache_data so they run once per session.
Falls back gracefully if DB or CSV is missing.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import numpy as np
import joblib
import streamlit as st

DATA_PROC  = "data/processed"
MODELS_DIR = "models/saved"


@st.cache_data(ttl=3600, show_spinner=False)
def load_accidents() -> pd.DataFrame:
    path = f"{DATA_PROC}/accidents_clean.csv"
    return pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_routes() -> pd.DataFrame:
    path = f"{DATA_PROC}/route_profiles.csv"
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_demand() -> pd.DataFrame:
    path = f"{DATA_PROC}/demand_dataset.csv"
    return pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_social() -> pd.DataFrame:
    enriched = f"{DATA_PROC}/social_sentiment_enriched.csv"
    fallback = f"{DATA_PROC}/social_sentiment.csv"
    path = enriched if os.path.exists(enriched) else fallback
    return pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_blackspots() -> pd.DataFrame:
    path = f"{DATA_PROC}/blackspot_clusters.csv"
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_weather() -> pd.DataFrame:
    path = f"{DATA_PROC}/nairobi_weather.csv"
    return pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame()

@st.cache_resource(show_spinner=False)
def load_risk_model():
    path = f"{MODELS_DIR}/risk_classifier.pkl"
    return joblib.load(path) if os.path.exists(path) else None

@st.cache_resource(show_spinner=False)
def load_demand_xgb():
    path = f"{MODELS_DIR}/demand_xgb.pkl"
    return joblib.load(path) if os.path.exists(path) else None

@st.cache_resource(show_spinner=False)
def load_prophet(route_id: str = "R001"):
    path = f"{MODELS_DIR}/demand_prophet_{route_id}.pkl"
    return joblib.load(path) if os.path.exists(path) else None

@st.cache_data(ttl=3600, show_spinner=False)
def get_kpi_summary() -> dict:
    acc_df    = load_accidents()
    route_df  = load_routes()
    social_df = load_social()
    bs_df     = load_blackspots()
    return {
        "total_routes":     len(route_df),
        "total_accidents":  len(acc_df),
        "fatal_accidents":  int((acc_df["severity"] == "Fatal").sum()) if not acc_df.empty else 0,
        "total_tweets":     len(social_df),
        "incident_tweets":  int(social_df["is_incident"].sum()) if not social_df.empty and "is_incident" in social_df.columns else 0,
        "total_blackspots": int(len(bs_df)),
        "critical_routes":  int((route_df["risk_score"] >= 4).sum()) if not route_df.empty else 0,
        "avg_risk_score":   round(route_df["risk_score"].mean(), 2) if not route_df.empty else 0,
        "date_range": {
            "from": str(acc_df["date"].min().date()) if not acc_df.empty else "N/A",
            "to":   str(acc_df["date"].max().date()) if not acc_df.empty else "N/A",
        },
    }

@st.cache_data(ttl=3600, show_spinner=False)
def get_demand_heatmap_data(route_id: str) -> pd.DataFrame:
    df = load_demand()
    if df.empty:
        return pd.DataFrame()
    return df[df["route_id"] == route_id].pivot_table(
        values="passengers", index="hour",
        columns="day_of_week", aggfunc="mean", fill_value=0,
    )

@st.cache_data(ttl=600, show_spinner=False)
def get_forecast_for_route(route_id: str, days: int = 7) -> pd.DataFrame:
    from ml.demand.forecaster import forecast_xgb
    xgb_art  = load_demand_xgb()
    route_df = load_routes()
    if xgb_art is None or route_df.empty:
        return pd.DataFrame()
    try:
        return forecast_xgb(
            xgb_art["model"], xgb_art["label_encoder"],
            xgb_art["features"], route_id, route_df, days=days,
        )
    except Exception:
        return pd.DataFrame()

# ── Alert helpers (SMS alert pipeline, mock mode) ───────────────────────────
def _get_alert_db_session():
    """Opens a short-lived SQLAlchemy session for alert operations."""
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from app.db.base import SessionLocal, create_tables
    create_tables()
    return SessionLocal()


@st.cache_data(ttl=30, show_spinner=False)
def get_critical_routes() -> list:
    """Routes currently qualifying for a Critical risk alert."""
    from app.services.alert_service import AlertService
    db = _get_alert_db_session()
    try:
        return AlertService.scan_for_critical_routes(db)
    except Exception:
        return []
    finally:
        db.close()


def trigger_dashboard_alert(route_id: str, recipient_phone: str, custom_message: str = None) -> dict:
    """
    Sends a (mock) SMS alert from the dashboard. Never cached — this is
    a write action. Returns a dict with success/error info for the UI
    to display, rather than raising, so Streamlit pages can show a
    clean message instead of a stack trace.
    """
    from app.services.alert_service import AlertService
    db = _get_alert_db_session()
    try:
        alert = AlertService.trigger_alert(
            db=db, route_id=route_id, recipient_phone=recipient_phone,
            custom_message=custom_message, triggered_by="dashboard",
        )
        return {
            "success": alert.sent,
            "message": alert.message,
            "message_id": alert.at_message_id,
            "error": alert.error_message,
        }
    except ValueError as e:
        return {"success": False, "message": None, "message_id": None, "error": str(e)}
    finally:
        db.close()


def get_alert_history(limit: int = 10) -> list:
    """Recent alert history — never cached, always fresh after a trigger."""
    from app.services.alert_service import AlertService
    db = _get_alert_db_session()
    try:
        alerts = AlertService.get_alert_history(db, limit=limit)
        return [
            {
                "route_id": a.route_id,
                "recipient_phone": a.recipient_phone,
                "message": a.message,
                "sent": a.sent,
                "at_message_id": a.at_message_id,
                "created_at": a.created_at,
            }
            for a in alerts
        ]
    except Exception:
        return []
    finally:
        db.close()
