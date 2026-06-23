"""
app/dashboard/bootstrap.py
Shared first-run bootstrap, callable from EVERY page independently.
Streamlit Cloud can serve different pages from separate container
instances that don't share state — each page must check/trigger its
own data readiness rather than relying solely on streamlit_app.py.
"""
import os
import sys
import subprocess
import streamlit as st

_DATA_MARKER  = "data/processed/route_profiles.csv"
_MODEL_MARKER = "models/saved/risk_classifier.pkl"


@st.cache_resource(show_spinner=False)
def ensure_data_ready() -> dict:
    status = {"data_ok": False, "models_ok": False, "error": None}

    if not os.path.exists(_DATA_MARKER):
        with st.spinner("First-time setup: generating datasets (about 30s)..."):
            try:
                subprocess.run(
                    [sys.executable, "scripts/generate_data.py"],
                    check=True, capture_output=True, text=True, timeout=180,
                )
            except subprocess.CalledProcessError as e:
                status["error"] = f"Data generation failed:\n{e.stderr[-2000:]}"
                return status
            except subprocess.TimeoutExpired:
                status["error"] = "Data generation timed out after 180s."
                return status

    status["data_ok"] = os.path.exists(_DATA_MARKER)

    if not os.path.exists(_MODEL_MARKER):
        with st.spinner("First-time setup: training ML models (1-2 min)..."):
            try:
                subprocess.run(
                    [sys.executable, "ml/pipeline/run_pipeline.py"],
                    check=True, capture_output=True, text=True, timeout=600,
                )
            except subprocess.CalledProcessError as e:
                status["error"] = f"Pipeline stage failed (partial results may exist):\n{e.stderr[-2000:]}"
            except subprocess.TimeoutExpired:
                status["error"] = "ML pipeline timed out after 600s."

    status["models_ok"] = os.path.exists(_MODEL_MARKER)
    return status


def require_data(show_warning_if_partial: bool = True) -> dict:
    status = ensure_data_ready()
    if status.get("error") and show_warning_if_partial:
        with st.expander("⚠️ Setup warning (click for details)", expanded=False):
            st.warning("Some ML models may not have finished training. Data and partial results are still usable.")
            st.code(status["error"])
    return status
