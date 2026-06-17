"""
ml/blackspot/detector.py
DBSCAN spatial clustering on NTSA accident GPS coordinates.
Identifies statistically significant accident blackspot zones.
Outputs: enriched cluster CSV + 3 geospatial figures.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

FIGURES_DIR   = "figures"
DATA_PROCESSED = "data/processed"

NAIROBI_CENTER  = (-1.286389, 36.817223)
EARTH_RADIUS_M  = 6_371_000
SEVERITY_WEIGHT = {"Fatal": 3.0, "Serious": 1.5, "Minor": 0.5}
RISK_COLORS     = {1:"#2ecc71", 2:"#f1c40f", 3:"#e67e22", 4:"#e74c3c", 5:"#8e44ad"}


# ══════════════════════════════════════════════════════════════════════════════
# CLUSTERING
# ══════════════════════════════════════════════════════════════════════════════
def run_dbscan(
    acc_df: pd.DataFrame,
    radius_m: int  = 600,
    min_pts:  int  = 5,
) -> pd.DataFrame:
    """
    Run DBSCAN on accident coordinates using haversine distance.
    Returns acc_df with a 'cluster' column added (-1 = noise).
    """
    coords_rad = np.radians(acc_df[["latitude", "longitude"]].values)
    eps_rad    = radius_m / EARTH_RADIUS_M

    db = DBSCAN(eps=eps_rad, min_samples=min_pts, metric="haversine", n_jobs=-1)
    labels = db.fit_predict(coords_rad)

    acc_df = acc_df.copy()
    acc_df["cluster"] = labels

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise    = (labels == -1).sum()
    pct_clustered = (labels != -1).mean() * 100

    print(f"  DBSCAN  radius={radius_m}m  min_pts={min_pts}")
    print(f"  Clusters found   : {n_clusters}")
    print(f"  Points clustered : {(labels != -1).sum():,} ({pct_clustered:.1f}%)")
    print(f"  Noise points     : {n_noise:,}")

    # Silhouette score (only if >1 cluster and enough clustered points)
    clustered = acc_df[acc_df["cluster"] != -1]
    if n_clusters > 1 and len(clustered) > n_clusters:
        try:
            sil = silhouette_score(
                np.radians(clustered[["latitude","longitude"]].values),
                clustered["cluster"].values,
                metric="haversine",
                sample_size=min(1000, len(clustered)),
                random_state=42,
            )
            print(f"  Silhouette score : {sil:.3f}")
        except Exception:
            pass

    return acc_df


def build_cluster_profiles(acc_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-cluster statistics into a summary DataFrame."""
    records = []
    for cid in sorted(set(acc_df["cluster"].unique())):
        if cid == -1:
            continue
        grp = acc_df[acc_df["cluster"] == cid]

        # Centroid
        ctr_lat = grp["latitude"].mean()
        ctr_lon = grp["longitude"].mean()

        # Radius — std dev of coords × earth degrees to metres
        lat_std = grp["latitude"].std()
        lon_std = grp["longitude"].std()
        radius  = max(50, int(((lat_std + lon_std) / 2) * 111_000))

        # Severity score
        sev_score = sum(
            SEVERITY_WEIGHT.get(s, 0.5)
            for s in grp["severity"]
        )

        # Risk tier (1–5) from severity score density
        density = sev_score / max(radius, 1) * 1000
        if   density < 0.5:  tier = 1
        elif density < 1.5:  tier = 2
        elif density < 3.0:  tier = 3
        elif density < 6.0:  tier = 4
        else:                 tier = 5

        # Dominant attributes
        dom_hour  = int(grp["hour"].mode().iloc[0])
        dom_type  = grp["accident_type"].mode().iloc[0]
        dom_cause = grp["cause"].mode().iloc[0]

        records.append({
            "cluster_id":     int(cid),
            "centroid_lat":   round(ctr_lat, 6),
            "centroid_lon":   round(ctr_lon, 6),
            "radius_m":       radius,
            "n_incidents":    len(grp),
            "n_fatal":        int((grp["severity"] == "Fatal").sum()),
            "n_serious":      int((grp["severity"] == "Serious").sum()),
            "n_minor":        int((grp["severity"] == "Minor").sum()),
            "severity_score": round(sev_score, 1),
            "risk_tier":      tier,
            "dominant_hour":  dom_hour,
            "time_of_day":    _hour_label(dom_hour),
            "dominant_type":  dom_type,
            "dominant_cause": dom_cause,
            "pct_peak_hour":  round(grp["is_peak_hour"].mean() * 100, 1),
            "pct_rainy":      round((grp["weather_condition"] == "Raining").mean() * 100, 1),
            "pct_dark":       round((grp["lighting"] == "Darkness").mean() * 100, 1),
        })

    return pd.DataFrame(records).sort_values("severity_score", ascending=False).reset_index(drop=True)


def _hour_label(h: int) -> str:
    if   6  <= h < 9:  return "AM Peak (6–9am)"
    elif 9  <= h < 12: return "Morning (9am–12pm)"
    elif 12 <= h < 14: return "Midday (12–2pm)"
    elif 14 <= h < 17: return "Afternoon (2–5pm)"
    elif 17 <= h < 20: return "PM Peak (5–8pm)"
    elif 20 <= h < 23: return "Evening (8–11pm)"
    else:               return "Night (11pm–6am)"


# ══════════════════════════════════════════════════════════════════════════════
# VISUALISATIONS
# ══════════════════════════════════════════════════════════════════════════════
def plot_accident_scatter(acc_df: pd.DataFrame):
    """All accidents coloured by severity on a Nairobi bounding box."""
    fig, ax = plt.subplots(figsize=(10, 9))
    colors  = {"Fatal":"#8e44ad","Serious":"#e74c3c","Minor":"#3498db"}
    sizes   = {"Fatal":35,"Serious":15,"Minor":6}
    alphas  = {"Fatal":0.9,"Serious":0.6,"Minor":0.3}

    for sev, grp in acc_df.groupby("severity"):
        ax.scatter(grp["longitude"], grp["latitude"],
                   c=colors[sev], s=sizes[sev], alpha=alphas[sev],
                   label=f"{sev} ({len(grp):,})", zorder=int(sev=="Fatal")+2)

    ax.set_xlim(36.65, 37.10); ax.set_ylim(-1.45, -1.16)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title("Nairobi Accident Locations by Severity (2021–2024)", fontsize=13, pad=10)
    ax.legend(title="Severity", fontsize=10, title_fontsize=10)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/01_accident_scatter_nairobi.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: accident_scatter_nairobi")


def plot_blackspot_map(acc_df: pd.DataFrame, cluster_df: pd.DataFrame):
    """Scatter of accidents with DBSCAN cluster circles overlaid."""
    fig, ax = plt.subplots(figsize=(11, 10))

    # Background accidents (grey)
    noise = acc_df[acc_df["cluster"] == -1]
    ax.scatter(noise["longitude"], noise["latitude"],
               c="#bdc3c7", s=4, alpha=0.25, label="Unclustered", zorder=1)

    # Clustered points coloured by tier
    for _, cl in cluster_df.iterrows():
        grp = acc_df[acc_df["cluster"] == cl["cluster_id"]]
        col = RISK_COLORS[int(cl["risk_tier"])]
        ax.scatter(grp["longitude"], grp["latitude"],
                   c=col, s=12, alpha=0.7, zorder=2)

        # Cluster circle (radius in degrees ≈ metres / 111000)
        radius_deg = cl["radius_m"] / 111_000
        circle = plt.Circle(
            (cl["centroid_lon"], cl["centroid_lat"]),
            radius_deg * 2,
            color=col, fill=False, linewidth=2, alpha=0.8, zorder=3,
        )
        ax.add_patch(circle)
        ax.annotate(
            f"BS{int(cl['cluster_id'])+1}\n({cl['n_incidents']})",
            (cl["centroid_lon"], cl["centroid_lat"]),
            fontsize=7, ha="center", va="center",
            fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.2", fc=col, alpha=0.85),
            zorder=4,
        )

    ax.set_xlim(36.65, 37.10); ax.set_ylim(-1.45, -1.16)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title("Nairobi Accident Blackspot Clusters (DBSCAN 600m radius)", fontsize=13, pad=10)

    legend_patches = [
        mpatches.Patch(color=c, label=f"Risk Tier {t}")
        for t, c in RISK_COLORS.items() if t in cluster_df["risk_tier"].values
    ]
    legend_patches.append(mpatches.Patch(color="#bdc3c7", label="Unclustered"))
    ax.legend(handles=legend_patches, fontsize=9, title="Risk Tier", title_fontsize=9)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/04_blackspot_cluster_map.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: blackspot_cluster_map")


def plot_blackspot_profiles(cluster_df: pd.DataFrame):
    """Bar charts: top blackspots by incident count and by severity score."""
    top = cluster_df.head(min(10, len(cluster_df))).copy()
    top["label"] = [f"BS{i+1}" for i in range(len(top))]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Incident count
    colors0 = [RISK_COLORS[int(t)] for t in top["risk_tier"]]
    axes[0].barh(top["label"][::-1], top["n_incidents"][::-1],
                 color=colors0[::-1], edgecolor="white")
    axes[0].set_title("Top Blackspots by Incident Count", fontsize=12)
    axes[0].set_xlabel("Number of Accidents")
    axes[0].grid(axis="x", alpha=0.3)

    # Fatal breakdown stacked
    axes[1].barh(top["label"][::-1], top["n_fatal"][::-1],
                 color="#8e44ad", label="Fatal", edgecolor="white")
    axes[1].barh(top["label"][::-1], top["n_serious"][::-1],
                 left=top["n_fatal"][::-1].values,
                 color="#e74c3c", label="Serious", edgecolor="white")
    axes[1].barh(top["label"][::-1], top["n_minor"][::-1],
                 left=(top["n_fatal"] + top["n_serious"])[::-1].values,
                 color="#3498db", label="Minor", edgecolor="white")
    axes[1].set_title("Blackspot Severity Breakdown", fontsize=12)
    axes[1].set_xlabel("Number of Accidents")
    axes[1].legend(fontsize=9)
    axes[1].grid(axis="x", alpha=0.3)

    plt.suptitle("Nairobi Road Accident Blackspot Analysis", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/05_blackspot_profiles.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: blackspot_profiles")


def plot_accident_heatmap_hourday(acc_df: pd.DataFrame):
    """Accident frequency heatmap: hour × day-of-week."""
    pivot = acc_df.pivot_table(
        values="accident_id", index="hour", columns="day_of_week",
        aggfunc="count", fill_value=0,
    )
    pivot.columns = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    fig, ax = plt.subplots(figsize=(10, 7))
    import seaborn as sns
    sns.heatmap(pivot, cmap="Reds", linewidths=0.3, annot=True, fmt="d",
                ax=ax, cbar_kws={"label": "Accident Count"})
    ax.set_title("Accident Frequency — Hour of Day × Day of Week", fontsize=13)
    ax.set_xlabel("Day of Week"); ax.set_ylabel("Hour of Day")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/02_accident_heatmap_hour_day.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: accident_heatmap_hour_day")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def run():
    os.makedirs(FIGURES_DIR,   exist_ok=True)
    os.makedirs(DATA_PROCESSED, exist_ok=True)

    acc_df = pd.read_csv(f"{DATA_PROCESSED}/accidents_clean.csv")
    print(f"  Loaded {len(acc_df):,} accident records")

    # Run clustering
    acc_df     = run_dbscan(acc_df, radius_m=600, min_pts=5)
    cluster_df = build_cluster_profiles(acc_df)

    # Save enriched blackspot CSV
    out_path = f"{DATA_PROCESSED}/blackspot_clusters.csv"
    cluster_df.to_csv(out_path, index=False)
    print(f"\n  ✓ {len(cluster_df)} blackspot clusters → {out_path}")

    print("\n  Top 5 blackspots:")
    for _, row in cluster_df.head(5).iterrows():
        print(f"    BS{int(row['cluster_id'])+1}  tier={row['risk_tier']}  "
              f"n={row['n_incidents']}  fatal={row['n_fatal']}  "
              f"cause='{row['dominant_cause']}'  time='{row['time_of_day']}'")

    # Figures
    print()
    plot_accident_scatter(acc_df)
    plot_blackspot_map(acc_df, cluster_df)
    plot_blackspot_profiles(cluster_df)
    plot_accident_heatmap_hourday(acc_df)

    return cluster_df


if __name__ == "__main__":
    print("\n🔵 Blackspot Detection — DBSCAN Spatial Clustering\n" + "─"*50)
    run()
