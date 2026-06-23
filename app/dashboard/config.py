"""
app/dashboard/config.py
Dashboard-wide theme, colour palette, and shared constants.
Single source of truth for all visual styling decisions.
"""

APP_TITLE       = "NUMP — Kenya Urban Mobility Intelligence"
APP_ICON        = "🚦"
APP_LAYOUT      = "wide"
SIDEBAR_STATE   = "expanded"

# ── Colour palette ─────────────────────────────────────────────────────────────
RISK_COLORS = {
    1: "#2ecc71",   # Very Low  — green
    2: "#f1c40f",   # Low       — yellow
    3: "#e67e22",   # Moderate  — orange
    4: "#e74c3c",   # High      — red
    5: "#8e44ad",   # Critical  — purple
}
RISK_LABELS = {
    1: "Very Low", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"
}

SENTIMENT_COLORS = {
    "Positive": "#2ecc71",
    "Neutral":  "#f1c40f",
    "Negative": "#e74c3c",
}

TOPIC_COLORS = {
    "breakdown":    "#e67e22",
    "accident":     "#e74c3c",
    "police_block": "#9b59b6",
    "flooding":     "#3498db",
    "positive":     "#2ecc71",
    "overloading":  "#f39c12",
    "unknown":      "#95a5a6",
}

NAIROBI_CENTER  = [-1.286389, 36.817223]
MAP_ZOOM_START  = 11

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS     = list(range(5, 23))

# ── CSS injected into every page ───────────────────────────────────────────────
GLOBAL_CSS = """
<style>
  /* Main background */
  .stApp { background-color: #0f1117; color: #e0e0e0; }

  /* Sidebar */
  [data-testid="stSidebar"] {
      background-color: #1a1d27;
      border-right: 1px solid #2d2d3f;
  }

  /* KPI metric cards */
  .kpi-card {
      background: #1e2130;
      border: 1px solid #2d3250;
      border-radius: 10px;
      padding: 18px 20px;
      text-align: center;
  }
  .kpi-value {
      font-size: 2.2rem;
      font-weight: 700;
      color: #ffffff;
      line-height: 1.1;
  }
  .kpi-label {
      font-size: 0.8rem;
      color: #8b9ab0;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-top: 4px;
  }
  .kpi-delta-pos { color: #2ecc71; font-size: 0.85rem; }
  .kpi-delta-neg { color: #e74c3c; font-size: 0.85rem; }

  /* Section headers */
  .section-header {
      font-size: 1.1rem;
      font-weight: 600;
      color: #c8d0e0;
      border-bottom: 2px solid #2d3250;
      padding-bottom: 6px;
      margin-bottom: 14px;
  }

  /* Risk badge */
  .risk-badge {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 0.78rem;
      font-weight: 600;
      color: #ffffff;
  }

  /* Divider */
  hr { border-color: #2d2d3f; }

  /* Tables */
  .dataframe { background-color: #1e2130 !important; }
</style>
"""
