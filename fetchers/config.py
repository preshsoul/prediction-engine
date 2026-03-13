"""
Configuration for live data fetchers.
API keys are read from environment variables (set in GitHub Secrets).
"""

import os

# ── API Keys (set these as GitHub Secrets) ──────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")          # the-odds-api.com (free: 500 req/mo)
BDL_API_KEY = os.environ.get("BDL_API_KEY", "")            # balldontlie.io (free tier)

# ── The Odds API sport keys ─────────────────────────────────────────
ODDS_SPORTS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "EPL": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
}

# ── BallDontLie league IDs ──────────────────────────────────────────
BDL_LEAGUES = {
    "NBA": "nba",
    "NHL": "nhl",
    "EPL": "epl",
}

# ── Data directory ──────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Rate limiting ───────────────────────────────────────────────────
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
BDL_API_BASE = "https://api.balldontlie.io/v2"
