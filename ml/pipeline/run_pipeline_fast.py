"""
ml/pipeline/run_pipeline_fast.py
Lightweight bootstrap pipeline for Streamlit Cloud's free-tier compute.
Skips per-route Prophet fitting and full NLP topic clustering — the
dashboard already falls back gracefully when those artifacts are absent.
Run the full ml/pipeline/run_pipeline.py manually (or `make train`) for
polished per-route forecasts and topic clusters.
"""
import os, sys, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import joblib
from datetime import datetime, timezone

from ml.risk.classifier import train as train_risk, predict as predict_risk
from ml.blackspot.detector import run_dbscan, build_cluster_profiles
from ml.nlp.sentiment import score_sentiment

MODEL_VERSION = f"v{datetime.now(timezone.utc).strftime('%Y%m%d')}-fast"
MODELS_DIR    = "models/saved"
DATA_PROC     = "data/processed"


def _section(title):
    print(f"\n{'='*50}\n  {title}\n{'='*50}")


def _load_data():
    print("  Loading accidents_clean.csv...", flush=True)
    t0 = time.time()
    accidents = pd.read_csv(f"{DATA_PROC}/accidents_clean.csv")
    print(f"  Loaded accidents: {len(accidents)} rows in {time.time()-t0:.1f}s", flush=True)

    print("  Loading route_profiles.csv...", flush=True)
    t0 = time.time()
    routes = pd.read_csv(f"{DATA_PROC}/route_profiles.csv")
    print(f"  Loaded routes: {len(routes)} rows in {time.time()-t0:.1f}s", flush=True)

    print("  Loading demand_dataset.csv (this is the big one, 262k rows)...", flush=True)
    t0 = time.time()
    demand = pd.read_csv(f"{DATA_PROC}/demand_dataset.csv", parse_dates=["date"], date_format="%Y-%m-%d")
    print(f"  Loaded demand: {len(demand)} rows in {time.time()-t0:.1f}s", flush=True)

    print("  Loading social_sentiment.csv...", flush=True)
    t0 = time.time()
    social = pd.read_csv(f"{DATA_PROC}/social_sentiment.csv")
    print(f"  Loaded social: {len(social)} rows in {time.time()-t0:.1f}s", flush=True)

    return {"accidents": accidents, "routes": routes, "demand": demand, "social": social}


def _write_risk_scores_to_db(route_df, artifact):
    try:
        from app.db.base import SessionLocal, create_tables
        from app.models.route import Route, RouteRiskScore
        create_tables()
        db = SessionLocal()
        for _, row in route_df.iterrows():
            if not db.query(Route).filter(Route.route_id == row["route_id"]).first():
                db.add(Route(
                    route_id=row["route_id"], route_name=row["route_name"],
                    sub_county=row.get("sub_county"),
                    distance_km=float(row.get("distance_km", 0)),
                    n_stops=int(row.get("n_stops", 0)),
                    avg_fare_ksh=int(row.get("avg_fare_ksh", 0)),
                    is_active=True,
                ))
        db.commit()
        for _, row in route_df.iterrows():
            result = predict_risk(row["route_id"], route_df, artifact)
            if "error" in result:
                continue
            db.add(RouteRiskScore(
                route_id=row["route_id"], risk_score=result["risk_score"],
                risk_label=result["risk_label"], confidence=result["confidence"],
                top_drivers=result["top_drivers"],
                accidents_24mo=int(row.get("accidents_24mo", 0)),
                accidents_per_km=float(row.get("accidents_per_km", 0)),
                model_version=MODEL_VERSION, scored_at=datetime.now(timezone.utc),
            ))
        db.commit()
        db.close()
        print(f"  Risk scores written to DB ({len(route_df)} routes)")
    except Exception as e:
        print(f"  WARNING: DB write failed: {e}")


def stage_risk_fast(data):
    _section("STAGE 1 — Route Risk Classifier")
    t0 = time.time()
    artifact = train_risk(data["routes"])
    _write_risk_scores_to_db(data["routes"], artifact)
    print(f"  Elapsed: {time.time()-t0:.1f}s")
    return artifact


def stage_demand_fast(data):
    _section("STAGE 2 — Demand Forecasting (XGBoost only, Prophet skipped)")
    t0 = time.time()
    from ml.features import DEMAND_FEATURES, engineer_demand_features, join_route_features, train_test_split_temporal
    from xgboost import XGBRegressor
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import mean_absolute_percentage_error

    df = engineer_demand_features(data["demand"].copy())
    df = join_route_features(df, data["routes"])
    le = LabelEncoder()
    df["route_enc"] = le.fit_transform(df["route_id"])
    features = DEMAND_FEATURES + ["route_enc"]

    train_df, test_df = train_test_split_temporal(df, test_days=60)
    X_train, y_train = train_df[features].fillna(0), train_df["passengers"]
    X_test,  y_test  = test_df[features].fillna(0),  test_df["passengers"]

    model = XGBRegressor(
        n_estimators=150, max_depth=5, learning_rate=0.08,
        subsample=0.85, colsample_bytree=0.75, random_state=42, verbosity=0,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test).clip(0)
    mape = mean_absolute_percentage_error(y_test + 1, preds + 1)
    print(f"  XGBoost MAPE: {mape*100:.2f}%")

    joblib.dump(
        {"model": model, "label_encoder": le, "features": features, "metrics": {"mape": float(mape)}},
        f"{MODELS_DIR}/demand_xgb.pkl",
    )
    print(f"  Elapsed: {time.time()-t0:.1f}s")


def stage_blackspot_fast(data):
    _section("STAGE 3 — Blackspot Detection (DBSCAN)")
    t0 = time.time()
    acc_df = run_dbscan(data["accidents"], radius_m=600, min_pts=5)
    cluster_df = build_cluster_profiles(acc_df)
    cluster_df.to_csv(f"{DATA_PROC}/blackspot_clusters.csv", index=False)
    print(f"  {len(cluster_df)} clusters saved")
    print(f"  Elapsed: {time.time()-t0:.1f}s")


def stage_nlp_fast(data):
    _section("STAGE 4 — NLP Sentiment (VADER only, topic clustering skipped)")
    t0 = time.time()
    df = score_sentiment(data["social"])
    if "topic" in df.columns and "topic_label" not in df.columns:
        df["topic_label"] = df["topic"]
    df.to_csv(f"{DATA_PROC}/social_sentiment_enriched.csv", index=False)
    print(f"  {len(df):,} tweets scored")
    print(f"  Elapsed: {time.time()-t0:.1f}s")


def run_all_fast():
    t_start = time.time()
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"\nKUMIP Fast Bootstrap Pipeline — {MODEL_VERSION}")
    data = _load_data()
    stage_risk_fast(data)
    stage_demand_fast(data)
    stage_blackspot_fast(data)
    stage_nlp_fast(data)
    print(f"\n{'='*50}\n  FAST PIPELINE COMPLETE — {time.time()-t_start:.1f}s total\n{'='*50}")


if __name__ == "__main__":
    run_all_fast()
