"""
ml/nlp/sentiment.py
Social media incident intelligence pipeline.
  1. VADER sentiment scoring (Sheng/English code-switched tweets)
  2. TF-IDF topic clustering (BERTopic substitute — no GPU needed for portfolio)
  3. Keyword extraction per topic
  4. 4 diagnostic figures
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from collections import Counter

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline

FIGURES_DIR    = "figures"
DATA_PROCESSED = "data/processed"

TOPIC_COLORS = {
    "breakdown":    "#e67e22",
    "accident":     "#e74c3c",
    "police_block": "#9b59b6",
    "flooding":     "#3498db",
    "positive":     "#2ecc71",
    "overloading":  "#f39c12",
    "unknown":      "#95a5a6",
}

# Sheng/informal Kenyan transport keywords → sentiment hints
SHENG_SENTIMENT = {
    "mbaya": -0.6, "sawa": 0.5, "gari": 0.0, "imevunjika": -0.7,
    "polisi": -0.3, "maji": -0.4, "imejaa": -0.5, "foleni": -0.4,
    "haraka": 0.3, "mazuri": 0.6, "ngori": -0.5, "wizi": -0.7,
    "msiba": -0.8, "salama": 0.6, "kazi": 0.1, "shida": -0.5,
}


# ══════════════════════════════════════════════════════════════════════════════
# PREPROCESSING
# ══════════════════════════════════════════════════════════════════════════════
def clean_text(text: str) -> str:
    """Normalise tweet text: lowercase, strip URLs/mentions/hashtags."""
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#(\w+)", r" \1", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def apply_sheng_boost(vader_score: float, text: str) -> float:
    """Add Sheng keyword sentiment signals to VADER compound score."""
    boost = 0.0
    words = text.lower().split()
    for w in words:
        if w in SHENG_SENTIMENT:
            boost += SHENG_SENTIMENT[w]
    # Clip combined score to [-1, 1]
    return float(np.clip(vader_score + boost * 0.15, -1.0, 1.0))


# ══════════════════════════════════════════════════════════════════════════════
# VADER SCORING
# ══════════════════════════════════════════════════════════════════════════════
def score_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """Apply VADER + Sheng boost to tweet text. Returns df with new columns."""
    analyser = SentimentIntensityAnalyzer()
    df = df.copy()
    df["clean_text"] = df["text"].apply(clean_text)

    vader_scores = df["clean_text"].apply(
        lambda t: analyser.polarity_scores(t)
    )
    df["vader_neg"]      = vader_scores.apply(lambda s: s["neg"])
    df["vader_neu"]      = vader_scores.apply(lambda s: s["neu"])
    df["vader_pos"]      = vader_scores.apply(lambda s: s["pos"])
    df["vader_compound"] = vader_scores.apply(lambda s: s["compound"])
    df["boosted_compound"] = df.apply(
        lambda r: apply_sheng_boost(r["vader_compound"], r["clean_text"]), axis=1
    )
    df["sentiment_label"] = df["boosted_compound"].apply(
        lambda c: "Positive" if c > 0.05 else "Negative" if c < -0.05 else "Neutral"
    )
    df["is_incident_nlp"] = df["vader_neg"].apply(lambda n: int(n > 0.25))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# TOPIC MODELLING (TF-IDF + K-Means + LSA — runs without GPU)
# ══════════════════════════════════════════════════════════════════════════════
TOPIC_LABELS = {
    0: "accident",
    1: "breakdown",
    2: "flooding",
    3: "police_block",
    4: "positive",
    5: "overloading",
}

def fit_topic_model(df: pd.DataFrame, n_topics: int = 6) -> tuple:
    """
    TF-IDF → LSA → K-Means topic clustering.
    Returns (df_with_topics, vectorizer, svd, kmeans, top_keywords_per_topic).
    """
    corpus = df["clean_text"].fillna("").tolist()

    vectorizer = TfidfVectorizer(
        max_features=1500,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.85,
        sublinear_tf=True,
        stop_words="english",
    )
    tfidf = vectorizer.fit_transform(corpus)

    # Dimensionality reduction via LSA
    svd  = TruncatedSVD(n_components=50, random_state=42)
    norm = Normalizer(copy=False)
    lsa  = make_pipeline(svd, norm)
    X    = lsa.fit_transform(tfidf)

    # K-Means clustering
    km = KMeans(n_clusters=n_topics, random_state=42, n_init=15, max_iter=300)
    km.fit(X)
    df = df.copy()
    df["topic_id"]    = km.labels_
    df["topic_label"] = df["topic_id"].map(TOPIC_LABELS).fillna("unknown")

    # Top keywords per topic (from TF-IDF centroids projected back)
    orig_space   = km.cluster_centers_ @ svd.components_
    feat_names   = vectorizer.get_feature_names_out()
    top_keywords = {}
    for t_id in range(n_topics):
        top_idx = orig_space[t_id].argsort()[::-1][:10]
        top_keywords[TOPIC_LABELS.get(t_id, f"topic_{t_id}")] = [
            feat_names[i] for i in top_idx
        ]

    return df, vectorizer, svd, km, top_keywords


# ══════════════════════════════════════════════════════════════════════════════
# FIGURES
# ══════════════════════════════════════════════════════════════════════════════
def plot_sentiment_distribution(df: pd.DataFrame):
    """Sentiment distribution overall + by topic."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Overall pie
    counts = df["sentiment_label"].value_counts()
    colors_pie = {"Positive":"#2ecc71","Neutral":"#f1c40f","Negative":"#e74c3c"}
    axes[0].pie(
        counts.values,
        labels=counts.index,
        colors=[colors_pie.get(l,"#999") for l in counts.index],
        autopct="%1.1f%%", startangle=140,
        textprops={"fontsize": 11},
    )
    axes[0].set_title("Overall Tweet Sentiment Distribution", fontsize=12)

    # By topic bar
    topic_sent = df.groupby("topic_label")["boosted_compound"].mean().sort_values()
    bar_colors = [TOPIC_COLORS.get(t,"#999") for t in topic_sent.index]
    axes[1].barh(topic_sent.index, topic_sent.values, color=bar_colors, edgecolor="white")
    axes[1].axvline(0, color="black", linewidth=0.8)
    axes[1].set_title("Average Sentiment Score by Topic", fontsize=12)
    axes[1].set_xlabel("Mean VADER Compound Score (boosted)")
    axes[1].grid(axis="x", alpha=0.3)

    plt.suptitle("Matatu Social Media Sentiment Analysis — Nairobi", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/14_sentiment_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: sentiment_distribution")


def plot_topic_breakdown(df: pd.DataFrame):
    """Tweet volume by topic + incident vs non-incident split."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    topic_counts = df["topic_label"].value_counts()
    colors0 = [TOPIC_COLORS.get(t,"#999") for t in topic_counts.index]
    bars = axes[0].bar(topic_counts.index, topic_counts.values,
                       color=colors0, edgecolor="white")
    for bar, v in zip(bars, topic_counts.values):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                     str(v), ha="center", fontsize=10, fontweight="bold")
    axes[0].set_title("Tweet Volume by Topic", fontsize=12)
    axes[0].set_xlabel("Topic"); axes[0].set_ylabel("Tweet Count")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].grid(axis="y", alpha=0.3)

    # Incident vs non-incident per topic
    pivot = df.groupby("topic_label")["is_incident"].value_counts().unstack(fill_value=0)
    pivot.columns = ["Non-Incident", "Incident"] if 0 in pivot.columns else pivot.columns
    pivot.plot(kind="bar", ax=axes[1],
               color=["#95a5a6","#e74c3c"], edgecolor="white", width=0.7)
    axes[1].set_title("Incident vs Non-Incident Tweets by Topic", fontsize=12)
    axes[1].set_xlabel("Topic"); axes[1].set_ylabel("Tweet Count")
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].legend(fontsize=9)
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/13_topic_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: topic_breakdown")


def plot_volume_trend(df: pd.DataFrame):
    """Tweet volume over time with incident spike annotations."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    weekly = df.set_index("date").resample("W").agg(
        total=("tweet_id","count"),
        incidents=("is_incident","sum"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(weekly["date"], weekly["total"],
                    alpha=0.15, color="#3498db")
    ax.plot(weekly["date"], weekly["total"],
            color="#3498db", lw=1.8, label="All tweets")
    ax.plot(weekly["date"], weekly["incidents"],
            color="#e74c3c", lw=1.8, linestyle="--", label="Incident tweets")

    # Annotate top 3 incident spikes
    top3 = weekly.nlargest(3, "incidents")
    for _, row in top3.iterrows():
        ax.annotate(
            f"↑ {int(row['incidents'])} incidents",
            (row["date"], row["incidents"]),
            xytext=(0, 14), textcoords="offset points",
            fontsize=8, color="#e74c3c", ha="center",
            arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=0.8),
        )

    ax.set_title("Social Media Tweet Volume — Weekly (2024)", fontsize=13)
    ax.set_xlabel("Week"); ax.set_ylabel("Tweet Count")
    ax.legend(fontsize=10); ax.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/15_tweet_volume_trend.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: tweet_volume_trend")


def plot_keyword_bars(top_keywords: dict):
    """Top keywords per topic as horizontal bar charts."""
    topics   = list(top_keywords.keys())
    n        = len(topics)
    cols     = 3
    rows     = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3.5))
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for i, (topic, keywords) in enumerate(top_keywords.items()):
        ax   = axes_flat[i]
        kws  = keywords[:8]
        vals = list(range(len(kws), 0, -1))
        col  = TOPIC_COLORS.get(topic, "#999")
        ax.barh(kws[::-1], vals[::-1], color=col, alpha=0.85, edgecolor="white")
        ax.set_title(f"Topic: {topic.replace('_',' ').title()}", fontsize=10, fontweight="bold")
        ax.set_xlabel("TF-IDF Rank")
        ax.grid(axis="x", alpha=0.2)

    # Hide unused subplots
    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.suptitle("Top Keywords per Topic Cluster (TF-IDF × LSA × K-Means)", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_DIR}/12_topic_keywords.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ Figure: topic_keywords")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def run():
    os.makedirs(FIGURES_DIR,    exist_ok=True)
    os.makedirs(DATA_PROCESSED, exist_ok=True)

    df = pd.read_csv(f"{DATA_PROCESSED}/social_sentiment.csv")
    print(f"  Loaded {len(df):,} social media records")

    # ── VADER + Sheng scoring ───────────────────────────────────────────────
    print("\n  [1/2] Applying VADER + Sheng sentiment scoring …")
    df = score_sentiment(df)
    neg_pct = (df["sentiment_label"] == "Negative").mean() * 100
    inc_pct = df["is_incident_nlp"].mean() * 100
    print(f"  Negative sentiment : {neg_pct:.1f}%")
    print(f"  Incident tweets    : {inc_pct:.1f}%")
    print(f"  Mean compound score: {df['boosted_compound'].mean():.3f}")

    # ── Topic modelling ──────────────────────────────────────────────────────
    print("\n  [2/2] Fitting topic model (TF-IDF + LSA + K-Means) …")
    df, vec, svd, km, top_keywords = fit_topic_model(df, n_topics=6)
    print("  Topics discovered:")
    for topic, kws in top_keywords.items():
        print(f"    {topic:15s}: {', '.join(kws[:5])}")

    # ── Save enriched CSV ────────────────────────────────────────────────────
    out_path = f"{DATA_PROCESSED}/social_sentiment_enriched.csv"
    df.to_csv(out_path, index=False)
    print(f"\n  ✓ Enriched social CSV → {out_path}")

    # ── Figures ──────────────────────────────────────────────────────────────
    print()
    plot_sentiment_distribution(df)
    plot_topic_breakdown(df)
    plot_volume_trend(df)
    plot_keyword_bars(top_keywords)

    return df, top_keywords


if __name__ == "__main__":
    print("\n🔵 NLP Sentiment + Topic Modelling Pipeline\n" + "─"*48)
    run()
