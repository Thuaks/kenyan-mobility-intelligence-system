"""
app/dashboard/components/charts.py
Reusable Plotly chart builders shared across all 5 dashboard pages.
Dark-theme native — no matplotlib needed in the dashboard layer.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from app.dashboard.config import (
    RISK_COLORS, RISK_LABELS, TOPIC_COLORS, SENTIMENT_COLORS, DAY_NAMES
)

# ── Shared layout defaults ─────────────────────────────────────────────────────
_LAYOUT = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    font=dict(color="#c8d0e0", family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(
        bgcolor="rgba(30,33,48,0.8)",
        bordercolor="#2d3250",
        borderwidth=1,
    ),
)


def _apply(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(**_LAYOUT, title=dict(text=title, font=dict(size=14)), height=height)
    fig.update_xaxes(gridcolor="#1e2130", zerolinecolor="#2d3250")
    fig.update_yaxes(gridcolor="#1e2130", zerolinecolor="#2d3250")
    return fig


# ── KPI / summary charts ───────────────────────────────────────────────────────
def risk_tier_donut(route_df: pd.DataFrame) -> go.Figure:
    counts = route_df["risk_score"].value_counts().sort_index()
    labels = [RISK_LABELS[int(t)] for t in counts.index]
    colors = [RISK_COLORS[int(t)] for t in counts.index]

    fig = go.Figure(go.Pie(
        labels=labels, values=counts.values,
        hole=0.62, marker_colors=colors,
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>Routes: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{len(route_df)}</b><br>Routes",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="#ffffff"),
    )
    return _apply(fig, "Route Risk Distribution", height=320)


def accident_by_hour_bar(acc_df: pd.DataFrame) -> go.Figure:
    hourly = acc_df.groupby("hour").size().reset_index(name="count")
    colors = [
        "#e74c3c" if (6 <= h < 9 or 16 <= h < 20) else "#3498db"
        for h in hourly["hour"]
    ]
    fig = go.Figure(go.Bar(
        x=hourly["hour"], y=hourly["count"],
        marker_color=colors,
        hovertemplate="Hour %{x}:00 — %{y} accidents<extra></extra>",
    ))
    fig.add_vrect(x0=5.5, x1=8.5,  fillcolor="#e74c3c", opacity=0.07, line_width=0)
    fig.add_vrect(x0=15.5, x1=19.5, fillcolor="#e74c3c", opacity=0.07, line_width=0)
    fig.update_xaxes(title="Hour of Day", dtick=1)
    fig.update_yaxes(title="Accident Count")
    return _apply(fig, "Accidents by Hour of Day  (red = peak hours)", height=300)


def accident_by_subcounty_bar(acc_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    counts = acc_df["sub_county"].value_counts().head(top_n)
    fig = go.Figure(go.Bar(
        x=counts.values[::-1], y=counts.index[::-1],
        orientation="h",
        marker_color="#e74c3c",
        hovertemplate="<b>%{y}</b><br>%{x} accidents<extra></extra>",
    ))
    fig.update_xaxes(title="Accident Count")
    return _apply(fig, f"Top {top_n} Sub-Counties by Accident Frequency", height=340)


# ── Demand charts ──────────────────────────────────────────────────────────────
def demand_heatmap(pivot_df: pd.DataFrame, route_name: str = "") -> go.Figure:
    cols = [DAY_NAMES[int(c)] for c in pivot_df.columns]
    fig  = go.Figure(go.Heatmap(
        z=pivot_df.values,
        x=cols,
        y=pivot_df.index.tolist(),
        colorscale="YlOrRd",
        hovertemplate="Hour %{y}:00 | %{x}<br><b>%{z:.0f} passengers</b><extra></extra>",
        colorbar=dict(title="Avg Pax/hr", thickness=12),
    ))
    fig.update_yaxes(title="Hour of Day", autorange="reversed")
    fig.update_xaxes(title="Day of Week")
    return _apply(fig, f"Demand Heatmap — {route_name}  (avg passengers/hr)", height=420)


def demand_forecast_line(forecast_df: pd.DataFrame, route_name: str = "") -> go.Figure:
    if forecast_df.empty:
        return go.Figure()

    # Build datetime axis
    forecast_df = forecast_df.copy()
    forecast_df["dt"] = pd.to_datetime(forecast_df["date"].astype(str)) + \
                        pd.to_timedelta(forecast_df["hour"], unit="h")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=forecast_df["dt"],
        y=forecast_df["predicted_passengers"],
        mode="lines",
        name="XGBoost Forecast",
        line=dict(color="#3498db", width=2),
        fill="tozeroy",
        fillcolor="rgba(52,152,219,0.08)",
        hovertemplate="%{x|%a %b %d %H:%M}<br><b>%{y} passengers</b><extra></extra>",
    ))
    # Shade weekends
    for dt in pd.to_datetime(forecast_df["date"].unique()):
        if dt.dayofweek >= 5:
            fig.add_vrect(
                x0=dt, x1=dt + pd.Timedelta(hours=17),
                fillcolor="#2d3250", opacity=0.3, line_width=0,
            )
    fig.update_xaxes(title="Date / Hour")
    fig.update_yaxes(title="Predicted Passengers / hr")
    return _apply(fig, f"7-Day Demand Forecast — {route_name}", height=360)


def prophet_forecast_line(forecast_df: pd.DataFrame, route_name: str = "") -> go.Figure:
    if forecast_df is None or forecast_df.empty:
        return go.Figure()
    recent = forecast_df.tail(14 * 24)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recent["ds"], y=recent["yhat_upper"],
        mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=recent["ds"], y=recent["yhat_lower"],
        mode="lines", line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(52,152,219,0.15)",
        name="95% CI",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=recent["ds"], y=recent["yhat"],
        mode="lines", name="Prophet Forecast",
        line=dict(color="#3498db", width=2),
        hovertemplate="%{x|%a %d %b %H:%M}<br><b>%{y:.0f} passengers</b><extra></extra>",
    ))
    fig.update_xaxes(title="Date / Hour")
    fig.update_yaxes(title="Passengers / hr")
    return _apply(fig, f"Prophet Demand Forecast — {route_name}", height=360)


def model_comparison_bar(prophet_mape: float, xgb_mape: float) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=["Prophet (per-route)", "XGBoost (multi-route)"],
        y=[prophet_mape * 100, xgb_mape * 100],
        marker_color=["#3498db", "#e74c3c"],
        text=[f"{prophet_mape*100:.1f}%", f"{xgb_mape*100:.1f}%"],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>MAPE: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=12, line_dash="dash", line_color="#f1c40f",
                  annotation_text="Target 12%", annotation_position="bottom right")
    fig.update_yaxes(title="MAPE (%)", range=[0, max(70, prophet_mape*115, xgb_mape*115)])
    return _apply(fig, "Demand Model Comparison — MAPE on 60-day holdout", height=300)


# ── Risk charts ────────────────────────────────────────────────────────────────
def route_risk_bar(route_df: pd.DataFrame) -> go.Figure:
    df = route_df.sort_values("risk_score", ascending=False).copy()
    df["short_name"] = df["route_name"].str.replace("CBD–", "").str.strip()
    colors = [RISK_COLORS[int(s)] for s in df["risk_score"]]

    fig = go.Figure(go.Bar(
        x=df["short_name"], y=df["risk_score"],
        marker_color=colors, marker_line_width=0,
        customdata=df[["route_id", "accidents_24mo", "accidents_per_km", "sub_county"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Risk Score: %{y}/5<br>"
            "Accidents (24mo): %{customdata[1]}<br>"
            "Accidents/km: %{customdata[2]:.3f}<br>"
            "Sub-county: %{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_xaxes(tickangle=-40, title="Route")
    fig.update_yaxes(title="Risk Score (1–5)", range=[0, 5.5], dtick=1)
    return _apply(fig, "Route Risk Scores — All Nairobi Matatu Routes", height=380)


def shap_waterfall_bar(drivers: list, route_name: str = "") -> go.Figure:
    """Horizontal bar of SHAP top drivers for one route."""
    if not drivers:
        return go.Figure()
    features = [d["feature"].replace("_", " ").title() for d in drivers]
    values   = [d["shap_value"] for d in drivers]
    colors   = ["#e74c3c" if v > 0 else "#2ecc71" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=features,
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>SHAP: %{x:.4f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="#8b9ab0", line_width=1)
    fig.update_xaxes(title="SHAP Value  (+ = increases risk)")
    return _apply(fig, f"Risk Drivers — {route_name}", height=300)


# ── Social / NLP charts ────────────────────────────────────────────────────────
def sentiment_pie(social_df: pd.DataFrame) -> go.Figure:
    col = "sentiment_label" if "sentiment_label" in social_df.columns else "sentiment"
    counts = social_df[col].value_counts()
    colors = [SENTIMENT_COLORS.get(l, "#999") for l in counts.index]
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values,
        hole=0.55, marker_colors=colors,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value} tweets<extra></extra>",
    ))
    return _apply(fig, "Tweet Sentiment Distribution", height=300)


def topic_volume_bar(social_df: pd.DataFrame) -> go.Figure:
    col = "topic_label" if "topic_label" in social_df.columns else "topic"
    counts = social_df[col].value_counts()
    colors = [TOPIC_COLORS.get(t, "#999") for t in counts.index]
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>%{y} tweets<extra></extra>",
    ))
    fig.update_xaxes(title="Topic")
    fig.update_yaxes(title="Tweet Count")
    return _apply(fig, "Tweet Volume by Topic", height=300)


def tweet_volume_trend(social_df: pd.DataFrame) -> go.Figure:
    df = social_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    inc_col = "is_incident_nlp" if "is_incident_nlp" in df.columns else "is_incident"
    weekly = df.set_index("date").resample("W").agg(
        total=(inc_col, "count"),
        incidents=(inc_col, "sum"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["date"], y=weekly["total"],
        mode="lines+markers", name="All Tweets",
        line=dict(color="#3498db", width=2),
        fill="tozeroy", fillcolor="rgba(52,152,219,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=weekly["date"], y=weekly["incidents"],
        mode="lines+markers", name="Incident Tweets",
        line=dict(color="#e74c3c", width=2, dash="dot"),
    ))
    fig.update_xaxes(title="Week")
    fig.update_yaxes(title="Tweet Count")
    return _apply(fig, "Social Media Volume Trend — Weekly", height=320)


def blackspot_severity_bar(bs_df: pd.DataFrame) -> go.Figure:
    top = bs_df.head(min(8, len(bs_df))).copy()
    top["label"] = [f"BS{i+1}" for i in range(len(top))]

    n_fatal   = top["n_fatal"]   if "n_fatal"   in top.columns else pd.Series(0, index=top.index)
    n_serious = top["n_serious"] if "n_serious" in top.columns else pd.Series(0, index=top.index)
    n_minor   = top["n_minor"]   if "n_minor"   in top.columns else pd.Series(0, index=top.index)
    has_breakdown = ("n_serious" in top.columns) or ("n_minor" in top.columns)

    fig = go.Figure()
    if has_breakdown:
        fig.add_trace(go.Bar(name="Fatal", x=top["label"], y=n_fatal,
            marker_color="#8e44ad", hovertemplate="<b>%{x}</b><br>Fatal: %{y}<extra></extra>"))
        fig.add_trace(go.Bar(name="Serious", x=top["label"], y=n_serious,
            marker_color="#e74c3c", hovertemplate="<b>%{x}</b><br>Serious: %{y}<extra></extra>"))
        fig.add_trace(go.Bar(name="Minor", x=top["label"], y=n_minor,
            marker_color="#3498db", hovertemplate="<b>%{x}</b><br>Minor: %{y}<extra></extra>"))
        fig.update_layout(barmode="stack")
    else:
        total = top["n_incidents"] if "n_incidents" in top.columns else n_fatal
        fig.add_trace(go.Bar(name="Fatal", x=top["label"], y=n_fatal,
            marker_color="#8e44ad", hovertemplate="<b>%{x}</b><br>Fatal: %{y}<extra></extra>"))
        fig.add_trace(go.Bar(name="Other", x=top["label"], y=(total - n_fatal).clip(lower=0),
            marker_color="#3498db", hovertemplate="<b>%{x}</b><br>Other: %{y}<extra></extra>"))
        fig.update_layout(barmode="stack")

    fig.update_xaxes(title="Blackspot Cluster")
    fig.update_yaxes(title="Accident Count")
    return _apply(fig, "Blackspot Severity Breakdown", height=320)
