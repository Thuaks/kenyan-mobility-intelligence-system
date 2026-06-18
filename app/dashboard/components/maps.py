"""
app/dashboard/components/maps.py
Folium map builders — rendered as HTML in Streamlit via st.components.v1.html()
All maps use dark CartoDB tiles to match the dashboard theme.
"""
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
from app.dashboard.config import RISK_COLORS, NAIROBI_CENTER, MAP_ZOOM_START


_TILE = "CartoDB dark_matter"


def _base_map(center=None, zoom=None) -> folium.Map:
    return folium.Map(
        location=center or NAIROBI_CENTER,
        zoom_start=zoom or MAP_ZOOM_START,
        tiles=_TILE,
        prefer_canvas=True,
    )


def accident_heatmap_map(acc_df: pd.DataFrame) -> folium.Map:
    """Folium heatmap of all accident coordinates weighted by severity."""
    m = _base_map()
    weight_map = {"Fatal": 1.0, "Serious": 0.5, "Minor": 0.2}
    heat_data  = [
        [row["latitude"], row["longitude"],
         weight_map.get(row["severity"], 0.2)]
        for _, row in acc_df[["latitude","longitude","severity"]].iterrows()
        if pd.notna(row["latitude"])
    ]
    HeatMap(
        heat_data,
        radius=14, blur=18, max_zoom=13,
        gradient={0.2: "#3498db", 0.5: "#e67e22", 1.0: "#e74c3c"},
    ).add_to(m)
    return m


def blackspot_map(acc_df: pd.DataFrame, bs_df: pd.DataFrame) -> folium.Map:
    """
    Nairobi map with:
      - Grey dots for all accident points
      - Coloured circles for DBSCAN clusters
      - Popup with cluster stats on click
    """
    m = _base_map()

    # Background accident points
    noise = acc_df[acc_df["cluster"] == -1] if "cluster" in acc_df.columns else acc_df
    sample = noise.sample(min(300, len(noise)), random_state=42)
    for _, row in sample.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=2, color="#7f8c8d", weight=0.5,
            fill=True, fill_color="#7f8c8d", fill_opacity=0.3,
        ).add_to(m)

    # Cluster circles
    for i, row in bs_df.iterrows():
        color   = RISK_COLORS.get(int(row["risk_tier"]), "#999999")
        radius  = max(200, int(row["radius_m"]) * 2)
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:200px'>
          <b style='font-size:14px'>Blackspot BS{i+1}</b><br>
          <hr style='margin:4px 0'>
          <b>Incidents:</b> {int(row['n_incidents'])} &nbsp;
          <b>Fatal:</b> {int(row['n_fatal'])}<br>
          <b>Risk Tier:</b> {int(row['risk_tier'])}/5<br>
          <b>Top Cause:</b> {row['dominant_cause']}<br>
          <b>Peak Time:</b> {row.get('time_of_day', '')}
        </div>
        """
        folium.Circle(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=radius,
            color=color, fill=True, fill_color=color,
            fill_opacity=0.25, weight=2,
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=f"BS{i+1} — {int(row['n_incidents'])} incidents",
        ).add_to(m)
        folium.Marker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px;font-weight:bold;'
                     f'color:white;background:{color};border-radius:50%;'
                     f'width:22px;height:22px;line-height:22px;text-align:center;'
                     f'border:1px solid white">BS{i+1}</div>',
                icon_size=(22, 22), icon_anchor=(11, 11),
            ),
        ).add_to(m)

    _add_legend(m, title="Blackspot Risk Tiers")
    return m


def route_risk_map(route_df: pd.DataFrame) -> folium.Map:
    """
    Simulated route map — markers at sub-county centroids coloured by risk score.
    In production: replace with actual route polylines from Digital Matatus GeoJSON.
    """
    # Approximate sub-county centroids
    CENTROIDS = {
        "Westlands":    [-1.2676, 36.8043],
        "Langata":      [-1.3322, 36.7484],
        "Kasarani":     [-1.2214, 36.8978],
        "Embakasi":     [-1.3167, 36.8925],
        "Dagoretti":    [-1.2997, 36.7429],
        "Mathare":      [-1.2567, 36.8539],
        "Kibra":        [-1.3136, 36.7822],
        "Ruaraka":      [-1.2361, 36.8661],
        "Kamukunji":    [-1.2796, 36.8519],
        "Starehe":      [-1.2800, 36.8275],
        "Roysambu":     [-1.2147, 36.8739],
        "Makadara":     [-1.3003, 36.8558],
        "Kiambu":       [-1.1717, 36.8350],
    }
    m = _base_map()
    for _, row in route_df.iterrows():
        tier    = int(row.get("risk_score", 3))
        color   = RISK_COLORS.get(tier, "#999")
        sub     = str(row.get("sub_county", ""))
        coords  = CENTROIDS.get(sub)
        if not coords:
            coords = [
                NAIROBI_CENTER[0] + np.random.uniform(-0.06, 0.06),
                NAIROBI_CENTER[1] + np.random.uniform(-0.06, 0.06),
            ]
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:180px'>
          <b>{row['route_name']}</b><br>
          <hr style='margin:4px 0'>
          <b>Risk Score:</b> {tier}/5<br>
          <b>Sub-county:</b> {sub}<br>
          <b>Accidents (24mo):</b> {int(row.get('accidents_24mo',0))}<br>
          <b>Acc/km:</b> {float(row.get('accidents_per_km',0)):.3f}
        </div>
        """
        folium.CircleMarker(
            location=coords,
            radius=10 + tier * 2,
            color=color, fill=True, fill_color=color,
            fill_opacity=0.75, weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{row['route_name']}  |  Risk {tier}/5",
        ).add_to(m)

    _add_legend(m, title="Route Risk Score")
    return m


def _add_legend(m: folium.Map, title: str = "Legend"):
    legend_html = f"""
    <div style="position:fixed;bottom:20px;left:20px;z-index:1000;
                background:rgba(15,17,23,0.92);border:1px solid #2d3250;
                border-radius:8px;padding:10px 14px;font-family:sans-serif">
      <b style="color:#c8d0e0;font-size:12px">{title}</b><br>
      {''.join(
        f'<span style="display:inline-block;width:12px;height:12px;'
        f'background:{c};border-radius:50%;margin-right:6px"></span>'
        f'<span style="color:#c8d0e0;font-size:11px">Tier {t}</span><br>'
        for t, c in RISK_COLORS.items()
      )}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
