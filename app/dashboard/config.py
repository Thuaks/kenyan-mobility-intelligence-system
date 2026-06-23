"""
app/dashboard/config.py
Dashboard-wide theme, colour palette, and shared constants.
"""

APP_TITLE       = "NUMP — Nairobi Urban Mobility"
APP_ICON        = "🚦"
APP_LAYOUT      = "wide"
SIDEBAR_STATE   = "expanded"

RISK_COLORS = {
    1: "#2ecc71", 2: "#f1c40f", 3: "#e67e22", 4: "#e74c3c", 5: "#8e44ad",
}
RISK_LABELS = {1: "Very Low", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}

SENTIMENT_COLORS = {"Positive": "#2ecc71", "Neutral": "#f1c40f", "Negative": "#e74c3c"}

TOPIC_COLORS = {
    "breakdown": "#e67e22", "accident": "#e74c3c", "police_block": "#9b59b6",
    "flooding": "#3498db", "positive": "#2ecc71", "overloading": "#f39c12",
    "unknown": "#95a5a6",
}

NAIROBI_CENTER  = [-1.286389, 36.817223]
MAP_ZOOM_START  = 11
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS     = list(range(5, 23))

KE_BLACK = "#000000"
KE_RED   = "#bb0000"
KE_GREEN = "#006600"
KE_WHITE = "#ffffff"

GLOBAL_CSS = f"""
<style>
  [data-testid="stSidebarNav"] {{ display: none; }}

  .stApp {{ background-color: #0f1117; color: #e0e0e0; }}

  [data-testid="stSidebar"] {{
      background-color: #1a1d27;
      border-right: 1px solid #2d2d3f;
  }}

  .ke-flag-stripe {{
      height: 4px;
      width: 100%;
      border-radius: 3px;
      margin: 10px 0 16px 0;
      background: linear-gradient(
          to right,
          {KE_BLACK} 0%, {KE_BLACK} 23%,
          {KE_WHITE} 23%, {KE_WHITE} 27%,
          {KE_RED} 27%, {KE_RED} 73%,
          {KE_WHITE} 73%, {KE_WHITE} 77%,
          {KE_GREEN} 77%, {KE_GREEN} 100%
      );
  }}

  .kpi-card {{
      background: #1e2130;
      border: 1px solid #2d3250;
      border-radius: 10px;
      padding: 18px 20px;
      text-align: center;
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
      cursor: default;
  }}
  .kpi-card:hover {{
      transform: translateY(-4px);
      border-color: #4a5578;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255,255,255,0.04);
  }}
  .kpi-value {{
      font-size: 2.2rem; font-weight: 700; color: #ffffff; line-height: 1.1;
  }}
  .kpi-label {{
      font-size: 0.8rem; color: #8b9ab0; text-transform: uppercase;
      letter-spacing: 0.08em; margin-top: 4px;
  }}
  .kpi-delta-pos {{ color: #2ecc71; font-size: 0.85rem; }}
  .kpi-delta-neg {{ color: #e74c3c; font-size: 0.85rem; }}

  .section-header {{
      font-size: 1.1rem; font-weight: 600; color: #c8d0e0;
      border-bottom: 2px solid #2d3250; padding-bottom: 6px; margin-bottom: 14px;
      transition: border-color 0.2s ease;
  }}

  .risk-badge {{
      display: inline-block; padding: 3px 10px; border-radius: 12px;
      font-size: 0.78rem; font-weight: 600; color: #ffffff;
  }}

  hr {{ border-color: #2d2d3f; }}
  .dataframe {{ background-color: #1e2130 !important; }}

  .feature-card {{
      background: #1e2130;
      border: 1px solid #2d3250;
      border-top: 3px solid var(--accent, #3498db);
      border-radius: 10px;
      padding: 20px 16px;
      text-align: center;
      min-height: 160px;
      transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
      cursor: default;
  }}
  .feature-card:hover {{
      transform: translateY(-6px) scale(1.015);
      box-shadow: 0 12px 28px rgba(0,0,0,0.5), 0 0 18px -4px var(--accent, #3498db);
      background: #232740;
  }}
  .feature-card:hover .feature-icon {{
      transform: translateY(-2px) scale(1.08);
  }}
  .feature-icon {{
      font-size: 2rem;
      transition: transform 0.2s ease;
  }}
  .feature-title {{ color: #fff; font-weight: 600; margin: 8px 0 6px; }}
  .feature-desc  {{ color: #8b9ab0; font-size: 0.78rem; line-height: 1.5; }}

  [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {{
      border-radius: 6px;
      transition: background 0.15s ease, padding-left 0.15s ease;
  }}
  [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {{
      background: #232740;
      padding-left: 4px;
  }}

  .cluster-card {{
      transition: transform 0.18s ease, box-shadow 0.18s ease;
  }}
  .cluster-card:hover {{
      transform: translateX(3px);
      box-shadow: -3px 0 0 0 currentColor, 0 6px 18px rgba(0,0,0,0.4);
  }}

  .incident-card {{
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  }}
  .incident-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 18px rgba(0,0,0,0.4);
  }}
</style>
"""
