"""
ml/features.py
Centralised feature engineering for all KUMIP models.
Single source of truth — imported by risk, demand, and NLP modules.
"""
import numpy as np
import pandas as pd
from typing import List, Tuple

# ── Risk model features ───────────────────────────────────────────────────────
RISK_FEATURES: List[str] = [
    "distance_km", "n_stops", "n_intersections",
    "pct_tarmac", "pct_gravel", "avg_lane_count",
    "has_bus_lane", "n_schools_nearby", "n_markets_nearby",
    "n_hospitals_nearby", "speed_limit_kph", "lighting_score",
    "accidents_24mo", "fatalities_24mo", "accidents_per_km",
    "peak_am_volume", "peak_pm_volume", "avg_daily_trips",
    "avg_fare_ksh", "population_density",
    # Engineered interactions
    "accident_x_darkness",       # accidents_per_km × (1 - lighting_score)
    "density_x_intersections",   # population_density × n_intersections
    "school_proximity_risk",     # n_schools_nearby × accidents_per_km
]

# ── Demand model features ─────────────────────────────────────────────────────
DEMAND_FEATURES: List[str] = [
    "hour", "day_of_week", "month",
    "is_weekend", "is_holiday", "in_school_term",
    # Cyclic encodings — prevent ordinal assumption
    "hour_sin", "hour_cos",
    "dow_sin",  "dow_cos",
    "month_sin", "month_cos",
    # Route characteristics (joined)
    "distance_km", "population_density", "avg_fare_ksh",
]


def engineer_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interaction features to route profile DataFrame."""
    df = df.copy()
    df["accident_x_darkness"]     = df["accidents_per_km"] * (1 - df["lighting_score"])
    df["density_x_intersections"] = (df["population_density"] / 10_000) * df["n_intersections"]
    df["school_proximity_risk"]   = df["n_schools_nearby"] * df["accidents_per_km"]
    return df


def engineer_demand_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclic time encodings and normalise demand DataFrame."""
    df = df.copy()
    df["hour_sin"]   = np.sin(2 * np.pi * df["hour"]        / 24)
    df["hour_cos"]   = np.cos(2 * np.pi * df["hour"]        / 24)
    df["dow_sin"]    = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"]    = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"]  = np.sin(2 * np.pi * df["month"]       / 12)
    df["month_cos"]  = np.cos(2 * np.pi * df["month"]       / 12)
    return df


def join_route_features(
    demand_df: pd.DataFrame,
    route_df: pd.DataFrame,
    cols: List[str] = ("distance_km", "population_density", "avg_fare_ksh"),
) -> pd.DataFrame:
    """Left-join selected route profile columns onto demand DataFrame."""
    route_subset = route_df[["route_id"] + list(cols)]
    return demand_df.merge(route_subset, on="route_id", how="left")


def train_test_split_temporal(
    df: pd.DataFrame,
    date_col: str = "date",
    test_days: int = 60,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Time-aware split — never shuffle temporal data.
    Returns (train, test) where test is the last `test_days` days.
    """
    df[date_col] = pd.to_datetime(df[date_col])
    cutoff = df[date_col].max() - pd.Timedelta(days=test_days)
    return df[df[date_col] <= cutoff].copy(), df[df[date_col] > cutoff].copy()
