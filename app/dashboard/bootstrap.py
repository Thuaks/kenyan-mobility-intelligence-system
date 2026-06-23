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


def _run_subprocess(args, timeout):
    """
    Run a subprocess with unbuffered stdout (-u flag) so print()
    output is captured in real time rather than sitting in Python's
    internal buffer until the process exits or the buffer fills —
    critical for diagnosing where a slow/hanging script actually is.
    """
    return subprocess.run(
        [sys.executable, "-u"] + args,
        check=True, capture_output=True, text=True, timeout=timeout,
    )


@st.cache_resource(show_spinner=False)
def ensure_data_ready() -> dict:
    status = {"data_ok": False, "models_ok": False, "error": None}

    if not os.path.exists(_DATA_MARKER):
        with st.spinner("First-time setup: generating datasets (about 30s)..."):
            try:
                _run_subprocess(["scripts/generate_data.py"], timeout=180)
            except subprocess.CalledProcessError as e:
                status["error"] = f"Data generation failed:\n{e.stderr[-2000:]}"
                return status
            except subprocess.TimeoutExpired as e:
                out = e.stdout or ""
                status["error"] = f"Data generation timed out after 180s.\n\n--- Output ---\n{out[-2000:]}"
                return status

    status["data_ok"] = os.path.exists(_DATA_MARKER)

    if not os.path.exists(_MODEL_MARKER):
        with st.spinner("First-time setup: training ML models (1-2 min)..."):
            try:
                _run_subprocess(["ml/pipeline/run_pipeline_fast.py"], timeout=240)
            except subprocess.CalledProcessError as e:
                status["error"] = (
                    f"Pipeline failed (exit code {e.returncode}).\n\n"
                    f"--- STDOUT ---\n{(e.stdout or '')[-1500:]}\n\n"
                    f"--- STDERR ---\n{(e.stderr or '')[-1500:]}"
                )
            except subprocess.TimeoutExpired as e:
                out = e.stdout or ""
                status["error"] = f"ML pipeline timed out after 240s.\n\n--- Output before timeout ---\n{out[-2000:]}"

    status["models_ok"] = os.path.exists(_MODEL_MARKER)
    return status


def require_data(show_warning_if_partial: bool = True) -> dict:
    status = ensure_data_ready()
    if status.get("error") and show_warning_if_partial:
        with st.expander("⚠️ Setup warning (click for details)", expanded=False):
            st.warning("Some ML models may not have finished training. Data and partial results are still usable.")
            st.code(status["error"])
    return status
