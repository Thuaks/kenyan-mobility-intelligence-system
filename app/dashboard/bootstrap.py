"""
app/dashboard/bootstrap.py
Shared first-run bootstrap, callable from EVERY page independently.
Uses an atomic file lock so concurrent page-containers never race to
generate/train simultaneously and corrupt each other's CSV reads.
"""
import os
import sys
import time
import subprocess
import streamlit as st

_DATA_MARKER  = "data/processed/route_profiles.csv"
_MODEL_MARKER = "models/saved/risk_classifier.pkl"
_LOCK_FILE    = "data/.bootstrap.lock"

_POLL_INTERVAL = 2
_MAX_WAIT      = 280


def _acquire_lock(lock_path=_LOCK_FILE) -> bool:
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock(lock_path=_LOCK_FILE):
    try:
        os.remove(lock_path)
    except FileNotFoundError:
        pass


def _lock_is_stale(lock_path=_LOCK_FILE, max_age_seconds: int = 600) -> bool:
    try:
        age = time.time() - os.path.getmtime(lock_path)
        return age > max_age_seconds
    except FileNotFoundError:
        return False


def _run_subprocess(args, timeout):
    return subprocess.run(
        [sys.executable, "-u"] + args,
        check=True, capture_output=True, text=True, timeout=timeout,
    )


def _wait_for_marker(marker_path, lock_path, max_wait) -> bool:
    waited = 0
    while waited < max_wait:
        if os.path.exists(marker_path):
            return True
        if not os.path.exists(lock_path):
            return os.path.exists(marker_path)
        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL
    return os.path.exists(marker_path)


@st.cache_resource(show_spinner=False)
def ensure_data_ready() -> dict:
    status = {"data_ok": False, "models_ok": False, "error": None}

    if os.path.exists(_LOCK_FILE) and _lock_is_stale():
        _release_lock()

    if not os.path.exists(_DATA_MARKER):
        if _acquire_lock():
            try:
                with st.spinner("First-time setup: generating datasets (about 30s)..."):
                    try:
                        _run_subprocess(["scripts/generate_data.py"], timeout=180)
                    except subprocess.CalledProcessError as e:
                        status["error"] = f"Data generation failed:\n{(e.stderr or '')[-2000:]}"
                        return status
                    except subprocess.TimeoutExpired as e:
                        status["error"] = f"Data generation timed out after 180s.\n\n{(e.stdout or '')[-2000:]}"
                        return status
            finally:
                _release_lock()
        else:
            with st.spinner("Waiting for setup already in progress..."):
                if not _wait_for_marker(_DATA_MARKER, _LOCK_FILE, _MAX_WAIT):
                    status["error"] = "Timed out waiting for another process's data generation."
                    return status

    status["data_ok"] = os.path.exists(_DATA_MARKER)

    if not os.path.exists(_MODEL_MARKER):
        model_lock = _LOCK_FILE + ".model"
        got_lock = _acquire_lock(model_lock)

        if got_lock:
            try:
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
                        status["error"] = f"ML pipeline timed out after 240s.\n\n{(e.stdout or '')[-2000:]}"
            finally:
                _release_lock(model_lock)
        else:
            with st.spinner("Waiting for model training already in progress..."):
                _wait_for_marker(_MODEL_MARKER, model_lock, _MAX_WAIT)

    status["models_ok"] = os.path.exists(_MODEL_MARKER)
    return status


def require_data(show_warning_if_partial: bool = True) -> dict:
    status = ensure_data_ready()
    if status.get("error") and show_warning_if_partial:
        with st.expander("⚠️ Setup warning (click for details)", expanded=False):
            st.warning("Some ML models may not have finished training. Data and partial results are still usable.")
            st.code(status["error"])
    return status
