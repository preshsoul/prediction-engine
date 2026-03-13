"""
Fetch live moneyline odds from The Odds API.
Free tier: 500 requests/month. Each call here costs 1 request.
We fetch h2h (moneyline) for 4 sports = 4 requests per run.
At 12 runs/day = 48/day = ~1,440/month (need paid $30 tier for daily).
At 4 runs/day (every 6h) = 16/day = ~480/month (fits free tier).
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from fetchers.config import ODDS_API_KEY, ODDS_SPORTS, ODDS_API_BASE, DATA_DIR
import os


def fetch_odds(sport_key, regions="us,uk", markets="h2h"):
    """Fetch upcoming game odds for a single sport."""
    if not ODDS_API_KEY:
        print(f"  [SKIP] No ODDS_API_KEY set, skipping {sport_key}")
        return []

    url = (
        f"{ODDS_API_BASE}/sports/{sport_key}/odds/"
        f"?apiKey={ODDS_API_KEY}"
        f"&regions={regions}"
        f"&markets={markets}"
        f"&oddsFormat=decimal"
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            remaining = resp.headers.get("x-requests-remaining", "?")
            print(f"  [OK] {sport_key}: {len(data)} events (requests remaining: {remaining})")
            return data
    except urllib.error.HTTPError as e:
        print(f"  [ERR] {sport_key}: HTTP {e.code} — {e.reason}")
        return []
    except Exception as e:
        print(f"  [ERR] {sport_key}: {e}")
        return []


def odds_to_market(event):
    """
    Convert The Odds API event into our engine's market format.
    Averages moneyline across all bookmakers for consensus odds.
    """
    home = event["home_team"]
    away = event["away_team"]

    home_prices, away_prices, draw_prices = [], [], []

    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                if outcome["name"] == home:
                    home_prices.append(outcome["price"])
                elif outcome["name"] == away:
                    away_prices.append(outcome["price"])
                elif outcome["name"] == "Draw":
                    draw_prices.append(outcome["price"])

    if not home_prices or not away_prices:
        return None

    # Convert decimal odds to implied probabilities
    h_prob = sum(1 / p for p in home_prices) / len(home_prices)
    a_prob = sum(1 / p for p in away_prices) / len(away_prices)
    d_prob = sum(1 / p for p in draw_prices) / len(draw_prices) if draw_prices else 0

    # Normalize to 100%
    total = h_prob + a_prob + d_prob
    h_pct = round(h_prob / total * 100, 1)
    a_pct = round(a_prob / total * 100, 1)
    d_pct = round(d_prob / total * 100, 1) if d_prob else 0

    result = {"h": h_pct, "a": a_pct}
    if d_pct:
        result["d"] = d_pct

    return result


def fetch_all_odds():
    """Fetch odds for all configured leagues and save to data/odds.json."""
    print("\n=== Fetching live odds ===")
    all_games = []

    for league, sport_key in ODDS_SPORTS.items():
        events = fetch_odds(sport_key)
        for ev in events:
            mkt = odds_to_market(ev)
            if not mkt:
                continue
            all_games.append({
                "league": league,
                "home": ev["home_team"],
                "away": ev["away_team"],
                "time": ev["commence_time"],
                "mkt": mkt,
                "bookmaker_count": len(ev.get("bookmakers", [])),
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            })

    out_path = os.path.join(DATA_DIR, "odds.json")
    with open(out_path, "w") as f:
        json.dump(all_games, f, indent=2)
    print(f"  Saved {len(all_games)} games with odds to {out_path}")
    return all_games


if __name__ == "__main__":
    fetch_all_odds()
