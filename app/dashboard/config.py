"""
app/dashboard/config.py
Dashboard-wide theme, colour palette, and shared constants.
"""

APP_TITLE       = "NUMIP — Nairobi Urban Mobility"
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

  .stApp {{
      background-color: #0f1117;
      color: #e0e0e0;
      background-image: radial-gradient(circle, rgba(255,255,255,0.035) 1px, transparent 1px);
      background-size: 24px 24px;
  }}

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

  @keyframes fade-up {{
      from {{ opacity: 0; transform: translateY(14px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes risk-pulse {{
      0%, 100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(142, 68, 173, 0.4); }}
      50%      {{ opacity: 0.82; box-shadow: 0 0 0 6px rgba(142, 68, 173, 0); }}
  }}

  .kpi-card {{
      background: rgba(30, 33, 48, 0.55);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 10px;
      padding: 18px 20px;
      text-align: center;
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
      cursor: default;
      animation: fade-up 0.45s ease-out backwards;
  }}
  .kpi-card:hover {{
      transform: translateY(-4px);
      border-color: #4a5578;
      background: rgba(35, 39, 64, 0.65);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255,255,255,0.04);
  }}
  div[data-testid="column"]:nth-of-type(1) .kpi-card {{ animation-delay: 0.02s; }}
  div[data-testid="column"]:nth-of-type(2) .kpi-card {{ animation-delay: 0.07s; }}
  div[data-testid="column"]:nth-of-type(3) .kpi-card {{ animation-delay: 0.12s; }}
  div[data-testid="column"]:nth-of-type(4) .kpi-card {{ animation-delay: 0.17s; }}
  div[data-testid="column"]:nth-of-type(5) .kpi-card {{ animation-delay: 0.22s; }}
  div[data-testid="column"]:nth-of-type(6) .kpi-card {{ animation-delay: 0.27s; }}
  div[data-testid="column"]:nth-of-type(7) .kpi-card {{ animation-delay: 0.32s; }}
  div[data-testid="column"]:nth-of-type(8) .kpi-card {{ animation-delay: 0.37s; }}

  .risk-badge-critical {{
      animation: risk-pulse 2.2s ease-in-out infinite;
  }}

  /* ── Page title — animated accent underline + breathing icon ──────────── */
  @keyframes underline-draw {{
      from {{ width: 0; }}
      to   {{ width: 100%; }}
  }}
  @keyframes icon-breathe {{
      0%, 100% {{ transform: scale(1) rotate(0deg); }}
      50%      {{ transform: scale(1.08) rotate(-3deg); }}
  }}
  .page-title-wrap {{
      margin-bottom: 0;
  }}
  .page-title-icon {{
      display: inline-block;
      animation: icon-breathe 3.4s ease-in-out infinite;
      /* Escape the parent .page-title-gradient's background-clip:text +
         color:transparent — without this, the emoji inherits transparent
         text color and becomes invisible since it's nested inside the
         gradient-clipped <h2>. */
      -webkit-background-clip: initial;
      background-clip: initial;
      color: initial;
      background: none;
  }}
  .page-title-underline {{
      height: 3px;
      width: 0;
      border-radius: 2px;
      margin-top: 6px;
      animation: underline-draw 0.7s ease-out 0.15s forwards;
  }}
  .page-title-gradient {{
      background: linear-gradient(90deg, #ffffff -10%, var(--title-accent, #ffffff) 75%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
  }}
  @keyframes cursor-blink {{
      0%, 50%  {{ opacity: 1; }}
      51%, 100% {{ opacity: 0; }}
  }}
  .subtitle-cursor {{
      display: inline-block;
      margin-left: 2px;
      animation: cursor-blink 1.1s step-end infinite;
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

  /* ── Custom scrollbar — thin, dark-theme native ─────────────────────────── */
  ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
  }}
  ::-webkit-scrollbar-track {{
      background: #0f1117;
  }}
  ::-webkit-scrollbar-thumb {{
      background: #2d3250;
      border-radius: 8px;
      transition: background 0.2s ease;
  }}
  ::-webkit-scrollbar-thumb:hover {{
      background: #4a5578;
  }}
  * {{
      scrollbar-width: thin;
      scrollbar-color: #2d3250 #0f1117;
  }}

  /* ── Custom scrollbar — thin, dark-theme native ─────────────────────────── */
  ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
  }}
  ::-webkit-scrollbar-track {{
      background: #0f1117;
  }}
  ::-webkit-scrollbar-thumb {{
      background: #2d3250;
      border-radius: 8px;
      transition: background 0.2s ease;
  }}
  ::-webkit-scrollbar-thumb:hover {{
      background: #4a5578;
  }}
  * {{
      scrollbar-width: thin;
      scrollbar-color: #2d3250 #0f1117;
  }}
</style>
"""

def render_page_title(icon: str, title: str, subtitle: str, accent: str) -> str:
    """
    Returns HTML for a page title with:
      - a breathing icon animation
      - an animated underline that draws in on load, colored per-page
      - a subtitle line beneath
    Usage: st.markdown(render_page_title("🗺️", "Route Risk Map", "...", "#e74c3c"), unsafe_allow_html=True)
    """
    return (
        f"<div class='page-title-wrap'>"
        f"<h2 class='page-title-gradient' style='margin-bottom:0;--title-accent:{accent}'>"
        f"<span class='page-title-icon'>{icon}</span> {title}"
        f"</h2>"
        f"<div class='page-title-underline' style='background:{accent}'></div>"
        f"<p style='color:#8b9ab0;margin-top:8px'>{subtitle}"
        f"<span class='subtitle-cursor' style='color:{accent}'>▌</span>"
        f"</p>"
        f"</div>"
    )
