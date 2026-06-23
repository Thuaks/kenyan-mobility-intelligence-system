"""
ml/risk/classifier.py
XGBoost route risk classifier with full SHAP explainability.

Target:   risk_score (1–5 ordinal tier)
Features: road geometry + accident history + population density
Output:   trained model + SHAP explainer + per-route top-3 drivers
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import joblib
import numpy as np
import pandas as pd
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix,
    ConfusionMatrixDisplay, f1_score,
)
from ml.features import RISK_FEATURES, engineer_risk_features

MODELS_DIR  = "models/saved"
FIGURES_DIR = "figures"
RISK_COLORS = {1:"#2ecc71", 2:"#f1c40f", 3:"#e67e22", 4:"#e74c3c", 5:"#8e44ad"}
RISK_LABELS = {1:"Very Low", 2:"Low", 3:"Moderate", 4:"High", 5:"Critical"}


# ── Training ─────────────────────────────────────────────────────────────────
def train(route_df: pd.DataFrame) -> dict:
    os.makedirs(MODELS_DIR,  exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    df = engineer_risk_features(route_df)
    X  = df[RISK_FEATURES].fillna(0).astype(float)
    y  = df["risk_score"].astype(int) - 1          # 0-indexed for XGBoost

    print("  [debug] Initializing XGBClassifier...", flush=True)
    model = XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.04,
        subsample=0.85, colsample_bytree=0.75,
        min_child_weight=2, gamma=0.1,
        use_label_encoder=False, eval_metric="mlogloss",
        random_state=42, verbosity=0,
    )
    print("  [debug] Fitting XGBClassifier...", flush=True)
    model.fit(X, y)
    print("  [debug] XGBClassifier fit complete", flush=True)

    # ── Cross-validation (4-fold — 4 samples per class minimum) ─────────────
    n_classes = len(set(y.tolist()))
    n_splits  = min(4, len(X) // n_classes)
    cv        = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_f1     = cross_val_score(model, X, y, cv=cv, scoring="f1_weighted")
    cv_acc    = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"  CV F1  (weighted) : {cv_f1.mean():.3f}  ± {cv_f1.std():.3f}")
    print(f"  CV Acc            : {cv_acc.mean():.3f} ± {cv_acc.std():.3f}")

    y_pred  = model.predict(X)
    labels  = [RISK_LABELS[i+1] for i in sorted(set(y))]
    f1_weighted = f1_score(y, y_pred, average="weighted")
    print(f"\n{classification_report(y, y_pred, target_names=labels)}")

    # ── SHAP ─────────────────────────────────────────────────────────────────
    # shap_values shape: (n_samples, n_features, n_classes)
    print("  [debug] Creating SHAP TreeExplainer...", flush=True)
    explainer  = shap.TreeExplainer(model)
    print("  [debug] Computing SHAP values...", flush=True)
    shap_vals  = explainer.shap_values(X)   # ndarray (20, 23, 5)
    print("  [debug] SHAP values computed", flush=True)

    _plot_shap_summary(shap_vals, X, df)
    _plot_shap_waterfall(shap_vals, X, df)
    _plot_confusion_matrix(y, y_pred, labels)
    _plot_risk_distribution(df)
    _plot_feature_importance(model, X.columns.tolist())

    # ── Save ─────────────────────────────────────────────────────────────────
    artifact = {
        "model":         model,
        "explainer":     explainer,
        "shap_values":   shap_vals,
        "features":      RISK_FEATURES,
        "metrics":       {"cv_f1": float(cv_f1.mean()), "f1_weighted": float(f1_weighted)},
        "model_version": "v1.0",
    }
    path = f"{MODELS_DIR}/risk_classifier.pkl"
    joblib.dump(artifact, path)
    print(f"\n  ✓ Risk classifier saved → {path}")
    return artifact


# ── Inference ─────────────────────────────────────────────────────────────────
def predict(route_id: str, route_df: pd.DataFrame, artifact: dict) -> dict:
    """Return risk score + SHAP top-3 drivers for a single route."""
    model     = artifact["model"]
    explainer = artifact["explainer"]
    features  = artifact["features"]
    shap_vals = artifact["shap_values"]

    df  = engineer_risk_features(route_df)
    row = df[df["route_id"] == route_id]
    if row.empty:
        return {"error": f"Route {route_id} not found"}

    X_row      = row[features].fillna(0).astype(float)
    pred_tier  = int(model.predict(X_row)[0]) + 1
    proba      = model.predict_proba(X_row)[0]
    row_idx    = int(df[df["route_id"] == route_id].index[0])

    # shap_vals: (n_samples, n_features, n_classes) — pick row + predicted class
    sv_3d      = np.array(shap_vals)
    sv_row     = sv_3d[row_idx, :, pred_tier - 1]      # (n_features,)
    top_drivers = sorted(
        zip(features, sv_row.tolist()), key=lambda x: abs(x[1]), reverse=True
    )[:3]

    return {
        "route_id":    route_id,
        "route_name":  row["route_name"].values[0],
        "risk_score":  pred_tier,
        "risk_label":  RISK_LABELS[pred_tier],
        "risk_color":  RISK_COLORS[pred_tier],
        "confidence":  round(float(proba[pred_tier - 1]), 3),
        "top_drivers": [
            {
                "feature":    f,
                "shap_value": round(float(v), 4),
                "direction":  "increases_risk" if v > 0 else "decreases_risk",
            }
            for f, v in top_drivers
        ],
        "model_version": artifact.get("model_version", "v1.0"),
    }


# ── Plots ─────────────────────────────────────────────────────────────────────
def _plot_shap_summary(shap_vals, X, df):
    # shap_vals: (n_samples, n_features, n_classes) → mean |shap| per feature
    sv_arr   = np.array(shap_vals)                        # (20, 23, 5)
    mean_abs = np.abs(sv_arr).mean(axis=0).mean(axis=1)  # (23,) mean over samples & classes
    sorted_idx = np.argsort(mean_abs)[::-1][:12]
    feat_names = [RISK_FEATURES[i].replace("_", " ").title() for i in sorted_idx]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].barh(feat_names[::-1], mean_abs[sorted_idx][::-1], color="#3498db", edgecolor="white")
    axes[0].set_xlabel("Mean |SHAP Value|")
    axes[0].set_title("Feature Importance (SHAP)\nAll Risk Classes", fontsize=12)
    axes[0].grid(axis="x", alpha=0.3)

    tier_counts = df["risk_score"].value_counts().sort_index()
    colors = [RISK_COLORS[t] for t in tier_counts.index]
    bars = axes[1].bar(
        [RISK_LABELS[t] for t in tier_counts.index],
        tier_counts.values, color=colors, edgecolor="white", linewidth=1.5
    )
    for bar, v in zip(bars, tier_counts.values):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                     str(v), ha="center", fontsize=12, fontweight="bold")
    axes[1].set_title("Route Risk Tier Distribution", fontsize=12)
    axes[1].set_ylabel("Number of Routes")
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/09_shap_summary_risk.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: shap_summary_risk")


def _plot_shap_waterfall(shap_vals, X, df):
    """Waterfall for highest-risk and lowest-risk route.
    shap_vals shape: (n_samples, n_features, n_classes)
    """
    sv_3d       = np.array(shap_vals)               # (20, 23, 5)
    highest_idx = int(df["risk_score"].idxmax())
    lowest_idx  = int(df["risk_score"].idxmin())

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, row_idx, label in [
        (axes[0], highest_idx, "Highest Risk"),
        (axes[1], lowest_idx,  "Lowest Risk"),
    ]:
        tier    = int(df.loc[row_idx, "risk_score"]) - 1
        sv_row  = sv_3d[row_idx, :, tier]           # (n_features,) for this class
        top_n   = min(10, len(sv_row))
        order   = np.argsort(np.abs(sv_row))[::-1][:top_n].tolist()
        feat_nm = [RISK_FEATURES[i].replace("_", " ").title() for i in order]
        vals    = [float(sv_row[i]) for i in order]
        colors  = ["#e74c3c" if v > 0 else "#2ecc71" for v in vals]

        ax.barh(feat_nm[::-1], vals[::-1], color=colors[::-1], edgecolor="white")
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(
            f"SHAP Waterfall — {label}\n{df.loc[row_idx, 'route_name']}",
            fontsize=11
        )
        ax.set_xlabel("SHAP Value (impact on risk prediction)")
        ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/10_shap_waterfall_routes.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: shap_waterfall_routes")


def _plot_confusion_matrix(y, y_pred, labels):
    cm  = confusion_matrix(y, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd",
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, ax=ax)
    ax.set_title("Route Risk Classifier — Confusion Matrix", fontsize=13)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/20_risk_confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: risk_confusion_matrix")


def _plot_risk_distribution(df):
    fig, ax = plt.subplots(figsize=(12, 5))
    sorted_df = df.sort_values("risk_score", ascending=False)
    colors    = [RISK_COLORS[int(s)] for s in sorted_df["risk_score"]]
    bars = ax.bar(
        range(len(sorted_df)),
        sorted_df["risk_score"],
        color=colors, edgecolor="white", linewidth=0.8
    )
    ax.set_xticks(range(len(sorted_df)))
    ax.set_xticklabels(
        [r.split("–")[1].strip() if "–" in r else r
         for r in sorted_df["route_name"]],
        rotation=45, ha="right", fontsize=9
    )
    ax.set_ylabel("Risk Score (1–5)")
    ax.set_title("Route Risk Scores — All Nairobi Matatu Routes", fontsize=13)
    legend_patches = [
        mpatches.Patch(color=c, label=f"Tier {t}: {RISK_LABELS[t]}")
        for t, c in RISK_COLORS.items()
    ]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/06_route_risk_scores.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: route_risk_scores")


def _plot_feature_importance(model, feature_names):
    importance = model.feature_importances_
    sorted_idx = np.argsort(importance)[::-1][:15]
    names  = [feature_names[i].replace("_"," ").title() for i in sorted_idx]
    values = importance[sorted_idx]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(names[::-1], values[::-1], color="#9b59b6", edgecolor="white")
    ax.set_title("XGBoost Feature Importance — Route Risk Model", fontsize=13)
    ax.set_xlabel("Gain Importance")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/11_xgb_feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: xgb_feature_importance")


if __name__ == "__main__":
    print("\n🔵 Training Route Risk Classifier\n" + "─"*45)
    route_df = pd.read_csv("data/processed/route_profiles.csv")
    artifact = train(route_df)
    print("\n  Sample predictions:")
    for rid in ["R001", "R005", "R010", "R015", "R020"]:
        result = predict(rid, route_df, artifact)
        print(f"  {rid}: score={result['risk_score']} "
              f"({result['risk_label']})  conf={result['confidence']:.2f}  "
              f"top_driver={result['top_drivers'][0]['feature']}")
