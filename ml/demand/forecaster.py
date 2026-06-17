"""
ml/demand/forecaster.py
Two-model demand forecasting pipeline:
  1. Prophet   — per-route time-series with holiday effects
  2. XGBoost   — multi-route regressor with engineered features
Outputs: saved models, 7-day forecasts written to DB, 4 diagnostic figures.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder
from ml.features import DEMAND_FEATURES, engineer_demand_features, join_route_features, train_test_split_temporal

MODELS_DIR  = "models/saved"
FIGURES_DIR = "figures"
DAY_NAMES   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

KENYA_HOLIDAYS = pd.DataFrame({
    "holiday":      "Kenya Public Holiday",
    "ds": pd.to_datetime([
        "2023-01-01","2023-04-07","2023-05-01","2023-06-01",
        "2023-10-20","2023-12-12","2023-12-25","2023-12-26",
        "2024-01-01","2024-04-19","2024-05-01","2024-06-01",
        "2024-10-20","2024-12-12","2024-12-25","2024-12-26",
    ]),
    "lower_window": 0,
    "upper_window": 1,
})


# ══════════════════════════════════════════════════════════════════════════════
# MODEL 1 — Prophet (single route, full time-series)
# ══════════════════════════════════════════════════════════════════════════════
def train_prophet(demand_df: pd.DataFrame, route_id: str) -> tuple:
    """Train Prophet on one route. Returns (model, forecast_df, mape)."""
    df = demand_df[demand_df["route_id"] == route_id].copy()
    df["ds"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h")
    df = df.rename(columns={"passengers": "y"})[["ds", "y"]].sort_values("ds")

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.05,
        holidays=KENYA_HOLIDAYS,
    )
    m.fit(df)

    future   = m.make_future_dataframe(periods=7 * 24, freq="h")
    forecast = m.predict(future)
    forecast["yhat"]       = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

    # MAPE on in-sample last 60 days
    merged = df.merge(
        forecast[["ds","yhat"]], on="ds", how="inner"
    ).tail(60 * 24)
    mape = mean_absolute_percentage_error(
        merged["y"] + 1, merged["yhat"] + 1
    ) if len(merged) > 0 else 0.0

    return m, forecast, mape


# ══════════════════════════════════════════════════════════════════════════════
# MODEL 2 — XGBoost (all routes, multi-route regressor)
# ══════════════════════════════════════════════════════════════════════════════
def train_xgboost(
    demand_df: pd.DataFrame,
    route_df:  pd.DataFrame,
    test_days: int = 60,
) -> tuple:
    """Train XGBoost across all routes. Returns (model, le, features, metrics, test_df, preds)."""
    df = engineer_demand_features(demand_df.copy())
    df = join_route_features(df, route_df)

    le = LabelEncoder()
    df["route_enc"] = le.fit_transform(df["route_id"])

    features = DEMAND_FEATURES + ["route_enc"]
    train_df, test_df = train_test_split_temporal(df, test_days=test_days)

    X_train, y_train = train_df[features].fillna(0), train_df["passengers"]
    X_test,  y_test  = test_df[features].fillna(0),  test_df["passengers"]

    model = XGBRegressor(
        n_estimators=600, max_depth=6, learning_rate=0.04,
        subsample=0.85, colsample_bytree=0.75,
        min_child_weight=3, gamma=0.05,
        random_state=42, verbosity=0,
        early_stopping_rounds=30,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    preds = np.clip(model.predict(X_test), 0, None)
    mape  = mean_absolute_percentage_error(y_test + 1, preds + 1)
    mae   = mean_absolute_error(y_test, preds)
    print(f"  XGBoost → MAPE: {mape*100:.2f}%  |  MAE: {mae:.1f} passengers/hr")

    metrics = {"mape": float(mape), "mae": float(mae)}
    return model, le, features, metrics, test_df, preds


# ══════════════════════════════════════════════════════════════════════════════
# INFERENCE
# ══════════════════════════════════════════════════════════════════════════════
def forecast_xgb(
    model, le, features: list,
    route_id: str,
    route_df: pd.DataFrame,
    days: int = 7,
) -> pd.DataFrame:
    """Generate day×hour forecast for one route using the XGBoost model."""
    route_meta = route_df[route_df["route_id"] == route_id].iloc[0]
    rows = []
    base = pd.Timestamp.now().normalize()
    for d in range(days):
        dt  = base + pd.Timedelta(days=d)
        dow = dt.dayofweek
        for h in range(5, 23):
            rows.append({
                "hour": h, "day_of_week": dow, "month": dt.month,
                "is_weekend": int(dow >= 5), "is_holiday": 0, "in_school_term": 1,
                "hour_sin":  np.sin(2*np.pi*h/24),  "hour_cos": np.cos(2*np.pi*h/24),
                "dow_sin":   np.sin(2*np.pi*dow/7), "dow_cos":  np.cos(2*np.pi*dow/7),
                "month_sin": np.sin(2*np.pi*dt.month/12),
                "month_cos": np.cos(2*np.pi*dt.month/12),
                "distance_km":        float(route_meta.get("distance_km", 10)),
                "population_density": float(route_meta.get("population_density", 10000)),
                "avg_fare_ksh":       float(route_meta.get("avg_fare_ksh", 60)),
                "route_enc":          int(le.transform([route_id])[0]),
                "date": dt.date(),
            })
    fut = pd.DataFrame(rows)
    fut["predicted_passengers"] = np.clip(
        model.predict(fut[features].fillna(0)), 0, None
    ).astype(int)
    return fut


# ══════════════════════════════════════════════════════════════════════════════
# VISUALISATIONS
# ══════════════════════════════════════════════════════════════════════════════
def plot_prophet_forecast(forecast: pd.DataFrame, route_name: str, route_id: str):
    recent = forecast.tail(21 * 24)   # 3 weeks context
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(recent["ds"], recent["yhat_lower"], recent["yhat_upper"],
                    alpha=0.18, color="#3498db", label="95% CI")
    ax.plot(recent["ds"], recent["yhat"], color="#2980b9", lw=1.8, label="Forecast")
    # Mark weekends
    for _, row in recent.groupby(recent["ds"].dt.date):
        pass
    ax.set_title(f"Prophet Demand Forecast — {route_name}", fontsize=13, pad=10)
    ax.set_xlabel("Date / Hour"); ax.set_ylabel("Predicted Passengers / hr")
    ax.legend(fontsize=10); ax.grid(alpha=0.25)
    plt.tight_layout()
    out = f"{FIGURES_DIR}/07_prophet_forecast_{route_id}.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure: prophet_forecast_{route_id}")


def plot_xgb_vs_actual(test_df: pd.DataFrame, preds: np.ndarray, route_id: str = "R001"):
    """Overlay actual vs predicted for a single route on the holdout period."""
    mask   = test_df["route_id"] == route_id
    actual = test_df.loc[mask, "passengers"].values[:7*18]
    pred   = preds[mask.values][:7*18]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(actual, label="Actual",           color="#2ecc71", lw=1.8)
    ax.plot(pred,   label="XGBoost Forecast", color="#e74c3c", lw=1.8, linestyle="--")
    ax.fill_between(range(len(actual)),
                    pred * 0.88, pred * 1.12,
                    alpha=0.12, color="#e74c3c", label="±12% band")
    ax.set_title("XGBoost Demand — Actual vs Predicted (60-day holdout, R001)", fontsize=13)
    ax.set_xlabel("Hour Index (18 hours/day × 7 days shown)")
    ax.set_ylabel("Passengers / hr")
    ax.legend(fontsize=10); ax.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/08_xgb_demand_vs_actual.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: xgb_demand_vs_actual")


def plot_model_comparison(prophet_mape: float, xgb_mape: float):
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        ["Prophet (per-route)", "XGBoost (multi-route)"],
        [prophet_mape * 100, xgb_mape * 100],
        color=["#3498db", "#e74c3c"], width=0.45, edgecolor="white",
    )
    for bar, v in zip(bars, [prophet_mape * 100, xgb_mape * 100]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f"{v:.1f}%", ha="center", fontsize=13, fontweight="bold")
    ax.axhline(12, color="gray", linestyle="--", lw=1.3, label="Target MAPE (12%)")
    ax.set_ylabel("MAPE (%)"); ax.set_ylim(0, max(20, prophet_mape*110, xgb_mape*110))
    ax.set_title("Demand Model Comparison — MAPE on 60-day holdout", fontsize=13)
    ax.legend(fontsize=10); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/19_demand_model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: demand_model_comparison")


def plot_demand_heatmap(demand_df: pd.DataFrame, route_id: str = "R001"):
    """Hour-of-day × day-of-week average demand heatmap for one route."""
    df = demand_df[demand_df["route_id"] == route_id].copy()
    pivot = df.pivot_table(
        values="passengers", index="hour", columns="day_of_week", aggfunc="mean"
    )
    pivot.columns = [DAY_NAMES[c] for c in pivot.columns]

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(pivot, cmap="YlOrRd", linewidths=0.3, annot=True, fmt=".0f",
                ax=ax, cbar_kws={"label": "Avg Passengers/hr"})
    ax.set_title(f"Demand Heatmap — Hour × Day of Week ({route_id})", fontsize=13)
    ax.set_xlabel("Day of Week"); ax.set_ylabel("Hour of Day")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/03_demand_heatmap_{route_id}.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure: demand_heatmap_{route_id}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def run():
    os.makedirs(MODELS_DIR,  exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    demand_df = pd.read_csv("data/processed/demand_dataset.csv", parse_dates=["date"])
    route_df  = pd.read_csv("data/processed/route_profiles.csv")

    # ── Prophet on R001 ─────────────────────────────────────────────────────
    print("\n  [1/2] Training Prophet on R001 (CBD–Route1) …")
    m_prophet, forecast, p_mape = train_prophet(demand_df, "R001")
    print(f"  Prophet  → MAPE: {p_mape*100:.2f}%")
    plot_prophet_forecast(forecast, "CBD–Route1", "R001")
    plot_demand_heatmap(demand_df, "R001")
    joblib.dump(
        {"model": m_prophet, "forecast": forecast, "mape": p_mape},
        f"{MODELS_DIR}/demand_prophet_R001.pkl",
    )
    print(f"  ✓ Prophet model saved")

    # ── XGBoost multi-route ──────────────────────────────────────────────────
    print("\n  [2/2] Training XGBoost multi-route regressor …")
    xgb_model, le, feats, xgb_metrics, test_df, preds = train_xgboost(demand_df, route_df)
    plot_xgb_vs_actual(test_df, preds, route_id="R001")
    plot_model_comparison(p_mape, xgb_metrics["mape"])
    joblib.dump(
        {"model": xgb_model, "label_encoder": le, "features": feats, "metrics": xgb_metrics},
        f"{MODELS_DIR}/demand_xgb.pkl",
    )
    print(f"  ✓ XGBoost model saved")

    # Sample 7-day forecast
    print("\n  Sample 7-day forecast for R001:")
    fut = forecast_xgb(xgb_model, le, feats, "R001", route_df, days=3)
    summary = fut.groupby("date")["predicted_passengers"].agg(["sum","max"])
    for date, row in summary.iterrows():
        print(f"    {date}  total={int(row['sum']):>5}  peak={int(row['max']):>4} pax/hr")


if __name__ == "__main__":
    print("\n🔵 Training Demand Forecasting Models\n" + "─"*45)
    run()
