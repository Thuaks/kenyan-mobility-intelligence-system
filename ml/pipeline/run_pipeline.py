"""
ml/pipeline/run_pipeline.py
Master ML pipeline orchestrator.
Runs all four engines in sequence and writes results to the SQLite DB
so the FastAPI layer can serve them immediately.

Run manually:  python ml/pipeline/run_pipeline.py
Scheduled via: APScheduler (configured in app/main.py lifespan)
"""
import os, sys, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import joblib
from datetime import datetime, timezone, date, timedelta
from loguru import logger

# ML modules
from ml.risk.classifier  import train  as train_risk,  predict as predict_risk
from ml.demand.forecaster import (
    train_prophet, train_xgboost, forecast_xgb,
    plot_prophet_forecast, plot_xgb_vs_actual, plot_model_comparison,
    plot_demand_heatmap,
)
from ml.blackspot.detector import run_dbscan, build_cluster_profiles
from ml.nlp.sentiment      import score_sentiment, fit_topic_model


MODEL_VERSION = f"v{datetime.now(timezone.utc).strftime('%Y%m%d')}"
MODELS_DIR    = "models/saved"
DATA_PROC     = "data/processed"
FIGURES_DIR   = "figures"


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _section(title: str):
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print(f"{'═'*55}")


def _load_data() -> dict:
    return {
        "accidents": pd.read_csv(f"{DATA_PROC}/accidents_clean.csv"),
        "routes":    pd.read_csv(f"{DATA_PROC}/route_profiles.csv"),
        "demand":    pd.read_csv(f"{DATA_PROC}/demand_dataset.csv", parse_dates=["date"]),
        "social":    pd.read_csv(f"{DATA_PROC}/social_sentiment.csv"),
        "weather":   pd.read_csv(f"{DATA_PROC}/nairobi_weather.csv"),
    }


def _write_risk_scores_to_db(route_df: pd.DataFrame, artifact: dict):
    """Persist risk scores + SHAP drivers to SQLite via SQLAlchemy."""
    try:
        from app.db.base import SessionLocal, create_tables
        from app.models.route import Route, RouteRiskScore
        create_tables()
        db = SessionLocal()

        # Upsert routes catalogue
        for _, row in route_df.iterrows():
            existing = db.query(Route).filter(Route.route_id == row["route_id"]).first()
            if not existing:
                db.add(Route(
                    route_id=row["route_id"],
                    route_name=row["route_name"],
                    sub_county=row.get("sub_county"),
                    distance_km=float(row.get("distance_km", 0)),
                    n_stops=int(row.get("n_stops", 0)),
                    avg_fare_ksh=int(row.get("avg_fare_ksh", 0)),
                    is_active=True,
                ))
        db.commit()

        # Write risk scores
        for _, row in route_df.iterrows():
            result = predict_risk(row["route_id"], route_df, artifact)
            if "error" in result:
                continue
            db.add(RouteRiskScore(
                route_id=row["route_id"],
                risk_score=result["risk_score"],
                risk_label=result["risk_label"],
                confidence=result["confidence"],
                top_drivers=result["top_drivers"],
                accidents_24mo=int(row.get("accidents_24mo", 0)),
                accidents_per_km=float(row.get("accidents_per_km", 0)),
                model_version=MODEL_VERSION,
                scored_at=datetime.now(timezone.utc),
            ))
        db.commit()
        db.close()
        print(f"  ✓ Risk scores written to DB ({len(route_df)} routes)")
    except Exception as e:
        print(f"  ⚠ DB write failed (run generate_data.py first): {e}")


def _write_forecasts_to_db(
    xgb_model, le, feats: list,
    route_df: pd.DataFrame,
    days: int = 7,
):
    """Write 7-day demand forecasts to DemandForecast table."""
    try:
        from app.db.base import SessionLocal, create_tables
        from app.models.forecast import DemandForecast
        from app.models.route import Route
        create_tables()
        db = SessionLocal()

        # Clear old forecasts (keep DB lean — rolling 7-day window)
        db.query(DemandForecast).filter(
            DemandForecast.forecast_date < date.today()
        ).delete()
        db.commit()

        written = 0
        for route_id in route_df["route_id"].tolist():
            try:
                fut = forecast_xgb(xgb_model, le, feats, route_id, route_df, days=days)
                for _, row in fut.iterrows():
                    db.add(DemandForecast(
                        route_id=route_id,
                        forecast_date=row["date"],
                        hour=int(row["hour"]),
                        yhat=float(row["predicted_passengers"]),
                        yhat_lower=float(row["predicted_passengers"] * 0.85),
                        yhat_upper=float(row["predicted_passengers"] * 1.15),
                        xgb_yhat=float(row["predicted_passengers"]),
                        model_version=MODEL_VERSION,
                    ))
                    written += 1
            except Exception:
                continue
        db.commit()
        db.close()
        print(f"  ✓ Demand forecasts written to DB ({written:,} records)")
    except Exception as e:
        print(f"  ⚠ Forecast DB write failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE STAGES
# ══════════════════════════════════════════════════════════════════════════════
def stage_risk(data: dict) -> dict:
    _section("STAGE 1 — Route Risk Classifier")
    t0 = time.time()
    artifact = train_risk(data["routes"])
    _write_risk_scores_to_db(data["routes"], artifact)
    print(f"  ⏱  {time.time()-t0:.1f}s")
    return artifact


def stage_demand(data: dict) -> tuple:
    _section("STAGE 2 — Demand Forecasting")
    t0 = time.time()

    # Prophet on all routes (for portfolio we just do R001 + R005)
    prophet_mapes = []
    for rid in ["R001", "R005"]:
        print(f"\n  Prophet → {rid} …")
        m, fc, mape = train_prophet(data["demand"], rid)
        prophet_mapes.append(mape)
        route_name = data["routes"].loc[
            data["routes"]["route_id"] == rid, "route_name"
        ].values[0]
        plot_prophet_forecast(fc, route_name, rid)
        plot_demand_heatmap(data["demand"], rid)
        joblib.dump({"model": m, "forecast": fc, "mape": mape},
                    f"{MODELS_DIR}/demand_prophet_{rid}.pkl")
        print(f"  Prophet {rid} MAPE: {mape*100:.2f}%")

    # XGBoost multi-route
    print("\n  XGBoost multi-route …")
    xgb_model, le, feats, xgb_metrics, test_df, preds = train_xgboost(
        data["demand"], data["routes"]
    )
    plot_xgb_vs_actual(test_df, preds)
    plot_model_comparison(sum(prophet_mapes)/len(prophet_mapes), xgb_metrics["mape"])
    joblib.dump(
        {"model": xgb_model, "label_encoder": le, "features": feats, "metrics": xgb_metrics},
        f"{MODELS_DIR}/demand_xgb.pkl",
    )
    _write_forecasts_to_db(xgb_model, le, feats, data["routes"], days=7)
    print(f"  ⏱  {time.time()-t0:.1f}s")
    return xgb_model, le, feats


def stage_blackspot(data: dict):
    _section("STAGE 3 — Blackspot Detection (DBSCAN)")
    t0 = time.time()
    from ml.blackspot.detector import (
        run_dbscan, build_cluster_profiles,
        plot_accident_scatter, plot_blackspot_map,
        plot_blackspot_profiles, plot_accident_heatmap_hourday,
    )
    acc_df     = run_dbscan(data["accidents"], radius_m=600, min_pts=5)
    cluster_df = build_cluster_profiles(acc_df)
    cluster_df.to_csv(f"{DATA_PROC}/blackspot_clusters.csv", index=False)

    plot_accident_scatter(acc_df)
    plot_blackspot_map(acc_df, cluster_df)
    plot_blackspot_profiles(cluster_df)
    plot_accident_heatmap_hourday(acc_df)
    print(f"  ✓ {len(cluster_df)} blackspot clusters saved")
    print(f"  ⏱  {time.time()-t0:.1f}s")


def stage_nlp(data: dict):
    _section("STAGE 4 — NLP Sentiment + Topic Modelling")
    t0 = time.time()
    from ml.nlp.sentiment import (
        score_sentiment, fit_topic_model,
        plot_sentiment_distribution, plot_topic_breakdown,
        plot_volume_trend, plot_keyword_bars,
    )
    df = score_sentiment(data["social"])
    df, _, _, _, top_kws = fit_topic_model(df, n_topics=6)
    df.to_csv(f"{DATA_PROC}/social_sentiment_enriched.csv", index=False)

    plot_sentiment_distribution(df)
    plot_topic_breakdown(df)
    plot_volume_trend(df)
    plot_keyword_bars(top_kws)
    print(f"  ✓ {len(df):,} tweets scored and clustered")
    print(f"  ⏱  {time.time()-t0:.1f}s")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════════════════
def _print_summary(t_start: float, data: dict):
    elapsed = time.time() - t_start
    figures = sorted(os.listdir(FIGURES_DIR)) if os.path.isdir(FIGURES_DIR) else []
    models  = sorted(os.listdir(MODELS_DIR))  if os.path.isdir(MODELS_DIR)  else []

    print(f"\n{'═'*55}")
    print("  PIPELINE COMPLETE")
    print(f"{'═'*55}")
    print(f"  Total runtime  : {elapsed:.1f}s")
    print(f"  Model version  : {MODEL_VERSION}")
    print(f"  Accidents      : {len(data['accidents']):,}")
    print(f"  Routes scored  : {len(data['routes'])}")
    print(f"  Demand records : {len(data['demand']):,}")
    print(f"  Tweets scored  : {len(data['social']):,}")
    print(f"  Models saved   : {len(models)}")
    print(f"  Figures saved  : {len(figures)}")
    print(f"\n  Figures:")
    for f in figures:
        print(f"    {f}")
    print(f"\n  Models:")
    for m in models:
        size = os.path.getsize(f"{MODELS_DIR}/{m}") / 1024
        print(f"    {m:<35s} {size:>6.1f} KB")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def run_all():
    t_start = time.time()
    os.makedirs(MODELS_DIR,  exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"\n🚦 NUMP ML Pipeline  —  {MODEL_VERSION}")
    print(f"   Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    data = _load_data()
    print(f"\n  Data loaded:")
    for k, v in data.items():
        print(f"    {k:12s}: {len(v):>8,} rows")

    stage_risk(data)
    stage_demand(data)
    stage_blackspot(data)
    stage_nlp(data)
    _print_summary(t_start, data)


if __name__ == "__main__":
    run_all()
