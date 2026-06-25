"""
app/dashboard/components.py
Reusable Plotly chart builders for the NUMIP Streamlit dashboard.
Each function returns a go.Figure — pages call st.plotly_chart(fig).
"""
import numipy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

RISK_COLORS = {1:"#2ecc71",2:"#f1c40f",3:"#e67e22",4:"#e74c3c",5:"#8e44ad"}
RISK_LABELS = {1:"Very Low",2:"Low",3:"Moderate",4:"High",5:"Critical"}
TOPIC_COLORS = {
    "breakdown":"#e67e22","accident":"#e74c3c","police_block":"#9b59b6",
    "flooding":"#3498db","positive":"#2ecc71","overloading":"#f39c12","unknown":"#95a5a6",
}
DAY_NAMES = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]


# ── KPI Card helper (returns HTML string) ─────────────────────────────────────
def kpi_card_html(label: str, value: str, delta: str = "", color: str = "#3498db") -> str:
    delta_html = f'<p style="color:#7f8c8d;font-size:0.82rem;margin:2px 0 0">{delta}</p>' if delta else ""
    return f"""
    <div style="background:#1e2530;border-radius:10px;padding:18px 20px;
                border-left:4px solid {color};margin-bottom:4px">
        <p style="color:#a0aab4;font-size:0.78rem;margin:0;text-transform:uppercase;
                  letter-spacing:0.05em">{label}</p>
        <p style="color:#ffffff;font-size:1.9rem;font-weight:700;margin:4px 0 0">{value}</p>
        {delta_html}
    </div>"""


# ── 1. Route Risk Bar Chart ───────────────────────────────────────────────────
def route_risk_bar(rt_df: pd.DataFrame) -> go.Figure:
    df = rt_df.sort_values("risk_score", ascending=True)
    short_names = [
        n.split("–")[1].strip() if "–" in n else n
        for n in df["route_name"]
    ]
    colors = [RISK_COLORS.get(int(s), "#999") for s in df["risk_score"]]

    fig = go.Figure(go.Bar(
        x=df["risk_score"], y=short_names,
        orientation="h",
        marker_color=colors,
        text=[f"{RISK_LABELS.get(int(s),'?')} ({int(s)})" for s in df["risk_score"]],
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate="<b>%{y}</b><br>Risk Score: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Route Risk Scores — All Nairobi Matatu Routes",
        xaxis_title="Risk Score (1–5)",
        xaxis=dict(range=[0, 5.5], tickvals=[1,2,3,4,5]),
        height=540, margin=dict(l=10, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 2. Accident Heatmap (hour × day) ─────────────────────────────────────────
def accident_heatmap(pivot: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Reds",
        hovertemplate="Hour: %{y}:00<br>Day: %{x}<br>Accidents: %{z}<extra></extra>",
        colorbar=dict(title="Accidents"),
    ))
    fig.update_layout(
        title="Accident Frequency — Hour of Day × Day of Week",
        xaxis_title="Day of Week", yaxis_title="Hour of Day",
        height=420, margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 3. Demand Forecast Line Chart ─────────────────────────────────────────────
def demand_forecast_chart(forecast_df: pd.DataFrame, route_name: str) -> go.Figure:
    if forecast_df.empty:
        return go.Figure()

    fig = go.Figure()
    for d, grp in forecast_df.groupby("date"):
        grp = grp.sort_values("hour")
        label = pd.Timestamp(str(d)).strftime("%a %d %b")
        fig.add_trace(go.Scatter(
            x=grp["hour"],
            y=grp["predicted_passengers"],
            mode="lines+markers",
            name=label,
            line=dict(width=2),
            marker=dict(size=5),
            hovertemplate=f"<b>{label}</b><br>Hour: %{{x}}:00<br>Passengers: %{{y}}<extra></extra>",
        ))

    fig.add_vrect(x0=6, x1=9,  fillcolor="#f39c12", opacity=0.08, line_width=0, annotation_text="AM Peak")
    fig.add_vrect(x0=17, x1=20, fillcolor="#e74c3c", opacity=0.08, line_width=0, annotation_text="PM Peak")

    fig.update_layout(
        title=f"7-Day Hourly Demand Forecast — {route_name}",
        xaxis_title="Hour of Day",
        yaxis_title="Predicted Passengers / hr",
        xaxis=dict(tickvals=list(range(5,23))),
        height=420, margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 4. Demand Heatmap ─────────────────────────────────────────────────────────
def demand_heatmap_chart(pivot: pd.DataFrame, route_id: str) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Blues",
        hovertemplate="Hour: %{y}:00<br>Day: %{x}<br>Avg Passengers: %{z:.0f}<extra></extra>",
        colorbar=dict(title="Avg Pax/hr"),
    ))
    fig.update_layout(
        title=f"Average Demand — Hour × Day ({route_id})",
        xaxis_title="Day of Week", yaxis_title="Hour of Day",
        height=380, margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 5. Blackspot Map (Plotly Scattergeo / Scatter) ────────────────────────────
def blackspot_scatter_map(acc_df: pd.DataFrame, bs_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Background accident points by severity
    sev_cfg = {
        "Minor":   dict(color="#3498db", size=3,  opacity=0.25),
        "Serious": dict(color="#e67e22", size=6,  opacity=0.50),
        "Fatal":   dict(color="#8e44ad", size=10, opacity=0.85),
    }
    for sev, cfg in sev_cfg.items():
        grp = acc_df[acc_df["severity"] == sev] if not acc_df.empty else pd.DataFrame()
        if grp.empty:
            continue
        fig.add_trace(go.Scatter(
            x=grp["longitude"], y=grp["latitude"],
            mode="markers",
            name=f"{sev} ({len(grp):,})",
            marker=dict(color=cfg["color"], size=cfg["size"],
                        opacity=cfg["opacity"]),
            hovertemplate=f"<b>{sev}</b><br>%{{y:.4f}}, %{{x:.4f}}<extra></extra>",
        ))

    # Blackspot cluster circles
    if not bs_df.empty:
        for _, row in bs_df.iterrows():
            col  = RISK_COLORS.get(int(row["risk_tier"]), "#999")
            fig.add_trace(go.Scatter(
                x=[row["centroid_lon"]],
                y=[row["centroid_lat"]],
                mode="markers+text",
                name=f"Blackspot {int(row['cluster_id'])+1}",
                marker=dict(color=col, size=22, opacity=0.7,
                            symbol="circle", line=dict(color="white", width=2)),
                text=[f"BS{int(row['cluster_id'])+1}"],
                textfont=dict(color="white", size=9),
                hovertemplate=(
                    f"<b>Blackspot {int(row['cluster_id'])+1}</b><br>"
                    f"Incidents: {row['n_incidents']}<br>"
                    f"Fatal: {row['n_fatal']}<br>"
                    f"Cause: {row['dominant_cause']}<br>"
                    f"Risk Tier: {row['risk_tier']}<extra></extra>"
                ),
                showlegend=False,
            ))

    fig.update_layout(
        title="Nairobi Accident Map — Severity & Blackspot Clusters",
        xaxis=dict(range=[36.65, 37.10], title="Longitude", showgrid=True, gridcolor="#2c3e50"),
        yaxis=dict(range=[-1.45, -1.16], title="Latitude", showgrid=True, gridcolor="#2c3e50"),
        height=560, margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(orientation="v", x=1.01),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        font_color="#e0e0e0",
    )
    return fig


# ── 6. Blackspot Profile Bars ─────────────────────────────────────────────────
def blackspot_profile_chart(bs_df: pd.DataFrame) -> go.Figure:
    if bs_df.empty:
        return go.Figure()

    top = bs_df.head(min(10, len(bs_df))).copy()
    top["label"] = [f"BS{i+1}" for i in range(len(top))]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=["Incident Count", "Severity Breakdown"])

    colors = [RISK_COLORS.get(int(t), "#999") for t in top["risk_tier"]]
    fig.add_trace(go.Bar(
        x=top["n_incidents"], y=top["label"], orientation="h",
        marker_color=colors, name="Incidents",
        hovertemplate="<b>%{y}</b><br>Incidents: %{x}<extra></extra>",
    ), row=1, col=1)

    for col_name, color, label in [
        ("n_fatal",   "#8e44ad", "Fatal"),
        ("n_serious", "#e74c3c", "Serious"),
        ("n_minor",   "#3498db", "Minor"),
    ]:
        fig.add_trace(go.Bar(
            x=top[col_name], y=top["label"], orientation="h",
            marker_color=color, name=label,
        ), row=1, col=2)

    fig.update_layout(
        barmode="stack", height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    return fig


# ── 7. Social Sentiment Trend ─────────────────────────────────────────────────
def social_trend_chart(weekly_df: pd.DataFrame) -> go.Figure:
    if weekly_df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly_df["date"], y=weekly_df["total"],
        name="All Tweets", mode="lines",
        fill="tozeroy", fillcolor="rgba(52,152,219,0.12)",
        line=dict(color="#3498db", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=weekly_df["date"], y=weekly_df["incidents"],
        name="Incident Tweets", mode="lines",
        line=dict(color="#e74c3c", width=2, dash="dash"),
    ))
    fig.update_layout(
        title="Weekly Tweet Volume — All vs Incident Tweets",
        xaxis_title="Week", yaxis_title="Tweet Count",
        height=340, margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 8. Topic Sentiment Bar ────────────────────────────────────────────────────
def topic_sentiment_chart(soc_df: pd.DataFrame) -> go.Figure:
    if soc_df.empty or "topic_label" not in soc_df.columns:
        return go.Figure()

    col = "boosted_compound" if "boosted_compound" in soc_df.columns else "compound"
    agg = soc_df.groupby("topic_label")[col].mean().sort_values()

    colors = [TOPIC_COLORS.get(t, "#999") for t in agg.index]
    fig = go.Figure(go.Bar(
        x=agg.values, y=agg.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}" for v in agg.values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Avg Sentiment: %{x:.3f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="white", line_width=1, opacity=0.5)
    fig.update_layout(
        title="Average Sentiment Score by Topic",
        xaxis_title="Mean VADER Compound (−1 to +1)",
        height=340, margin=dict(l=10, r=60, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig


# ── 9. Severity Donut ────────────────────────────────────────────────────────
def severity_donut(acc_df: pd.DataFrame) -> go.Figure:
    if acc_df.empty:
        return go.Figure()
    counts = acc_df["severity"].value_counts()
    colors = {"Fatal":"#8e44ad","Serious":"#e74c3c","Minor":"#3498db"}
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values,
        hole=0.55,
        marker_colors=[colors.get(l,"#999") for l in counts.index],
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        title="Accidents by Severity",
        height=320, margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        legend=dict(orientation="h", y=-0.1),
    )
    return fig


# ── 10. Sub-county accident bar ───────────────────────────────────────────────
def subcounty_bar(acc_df: pd.DataFrame) -> go.Figure:
    if acc_df.empty:
        return go.Figure()
    top10 = acc_df["sub_county"].value_counts().head(10)
    fig = go.Figure(go.Bar(
        x=top10.values, y=top10.index,
        orientation="h",
        marker_color="#e74c3c",
        hovertemplate="<b>%{y}</b><br>Accidents: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Top 10 Sub-Counties by Accident Count",
        xaxis_title="Accidents",
        height=360, margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
    )
    return fig
