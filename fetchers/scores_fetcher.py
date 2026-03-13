"""
Fetch live standings, recent results, and upcoming schedules.

Sources:
  - BallDontLie API (NBA, NHL, EPL) — standings + recent games
  - The Odds API /scores endpoint — recent results for all leagues
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from fetchers.config import (
    BDL_API_KEY, BDL_API_BASE, BDL_LEAGUES,
    ODDS_API_KEY, ODDS_API_BASE, ODDS_SPORTS,
    DATA_DIR,
)
import os


# ════════════════════════════════════════════════════════════════════
# BallDontLie: Standings
# ════════════════════════════════════════════════════════════════════

def bdl_request(endpoint, params=None):
    """Make a request to BallDontLie API."""
    if not BDL_API_KEY:
        print(f"  [SKIP] No BDL_API_KEY set")
        return None

    url = f"{BDL_API_BASE}/{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"

    req = urllib.request.Request(url, headers={"Authorization": BDL_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [ERR] BDL {endpoint}: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  [ERR] BDL {endpoint}: {e}")
        return None


def fetch_nba_standings():
    """Fetch NBA standings from BallDontLie."""
    data = bdl_request("standings", {"season": "2025"})
    if not data or "data" not in data:
        print("  [WARN] No NBA standings data")
        return {}

    standings = {}
    for team in data["data"]:
        name = team.get("team", {}).get("full_name", "")
        if not name:
            continue
        standings[name] = {
            "w": team.get("wins", 0),
            "l": team.get("losses", 0),
            "conf": team.get("team", {}).get("conference", ""),
        }

    print(f"  [OK] NBA standings: {len(standings)} teams")
    return standings


def fetch_nhl_standings():
    """Fetch NHL standings from BallDontLie."""
    data = bdl_request("nhl/standings", {"season": "2025"})
    if not data or "data" not in data:
        print("  [WARN] No NHL standings data")
        return {}

    standings = {}
    for team in data["data"]:
        name = team.get("team", {}).get("full_name", "")
        if not name:
            continue
        standings[name] = {
            "w": team.get("wins", 0),
            "l": team.get("losses", 0),
            "conf": team.get("team", {}).get("conference", ""),
            "div": team.get("team", {}).get("division", ""),
        }

    print(f"  [OK] NHL standings: {len(standings)} teams")
    return standings


def fetch_epl_standings():
    """Fetch EPL standings from BallDontLie."""
    data = bdl_request("epl/standings", {"season": "2025"})
    if not data or "data" not in data:
        print("  [WARN] No EPL standings data")
        return {}

    standings = {}
    for team in data["data"]:
        name = team.get("team", {}).get("full_name", "")
        if not name:
            continue
        standings[name] = {
            "w": team.get("wins", 0),
            "l": team.get("losses", 0),
            "d": team.get("draws", 0),
            "pts": team.get("points", 0),
            "gd": team.get("goal_difference", 0),
        }

    print(f"  [OK] EPL standings: {len(standings)} teams")
    return standings


# ════════════════════════════════════════════════════════════════════
# The Odds API: Recent scores/results
# ════════════════════════════════════════════════════════════════════

def fetch_scores(sport_key, days_from=3):
    """Fetch completed game scores from The Odds API."""
    if not ODDS_API_KEY:
        print(f"  [SKIP] No ODDS_API_KEY for scores")
        return []

    url = (
        f"{ODDS_API_BASE}/sports/{sport_key}/scores/"
        f"?apiKey={ODDS_API_KEY}"
        f"&daysFrom={days_from}"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            completed = [g for g in data if g.get("completed")]
            print(f"  [OK] {sport_key} scores: {len(completed)} completed games")
            return completed
    except urllib.error.HTTPError as e:
        print(f"  [ERR] {sport_key} scores: HTTP {e.code}")
        return []
    except Exception as e:
        print(f"  [ERR] {sport_key} scores: {e}")
        return []


def scores_to_results(events, league):
    """Convert The Odds API score events into our engine's result format."""
    results = []
    for ev in events:
        if not ev.get("completed"):
            continue
        scores = ev.get("scores", [])
        if not scores or len(scores) < 2:
            continue

        home = ev["home_team"]
        away = ev["away_team"]

        score_h, score_a = 0, 0
        for s in scores:
            if s["name"] == home:
                score_h = int(s.get("score", 0))
            elif s["name"] == away:
                score_a = int(s.get("score", 0))

        results.append({
            "league": league,
            "home": home,
            "away": away,
            "score_h": score_h,
            "score_a": score_a,
            "date": ev.get("commence_time", ""),
        })

    return results


# ════════════════════════════════════════════════════════════════════
# Main orchestrator
# ════════════════════════════════════════════════════════════════════

def fetch_all_standings():
    """Fetch standings for all leagues and save to data/standings.json."""
    print("\n=== Fetching standings ===")
    standings = {}

    nba = fetch_nba_standings()
    if nba:
        standings["NBA"] = nba

    nhl = fetch_nhl_standings()
    if nhl:
        standings["NHL"] = nhl

    epl = fetch_epl_standings()
    if epl:
        standings["EPL"] = epl

    # La Liga: BDL doesn't cover it natively, so we keep manual for now
    # or use football-data.org (free 10 req/min) as a future addition
    print("  [INFO] La Liga standings: using fallback (manual or cached)")

    out_path = os.path.join(DATA_DIR, "standings.json")
    with open(out_path, "w") as f:
        json.dump(standings, f, indent=2)
    print(f"  Saved standings to {out_path}")
    return standings


def fetch_all_results():
    """Fetch recent results for all leagues and save to data/results.json."""
    print("\n=== Fetching recent results ===")
    all_results = []

    for league, sport_key in ODDS_SPORTS.items():
        events = fetch_scores(sport_key, days_from=5)
        results = scores_to_results(events, league)
        all_results.extend(results)

    out_path = os.path.join(DATA_DIR, "results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  Saved {len(all_results)} recent results to {out_path}")
    return all_results


if __name__ == "__main__":
    fetch_all_standings()
    fetch_all_results()
