"""
run_live.py — Main entry point for the live prediction pipeline.

1. Fetch live odds, standings, and results from APIs
2. Fall back to hardcoded data if any API fails
3. Merge live data into the prediction engine
4. Generate the dashboard
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetchers.odds_fetcher import fetch_all_odds
from fetchers.scores_fetcher import fetch_all_standings, fetch_all_results
from prediction_engine import (
    NBA_STANDINGS, NHL_STANDINGS, EPL_STANDINGS, LALIGA_STANDINGS,
    RECENT_RESULTS, UPCOMING_GAMES,
    predict_game, backtest_on_results, monte_carlo_simulation,
    generate_dashboard,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def load_cached(filename):
    """Load previously fetched data from disk."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def merge_standings(live_standings):
    """
    Merge live standings into the engine's hardcoded dicts.
    Returns updated copies; doesn't mutate the originals.
    """
    nba = dict(NBA_STANDINGS)
    nhl = dict(NHL_STANDINGS)
    epl = dict(EPL_STANDINGS)
    laliga = dict(LALIGA_STANDINGS)

    if "NBA" in live_standings:
        for team, data in live_standings["NBA"].items():
            nba[team] = data
        print(f"  Merged {len(live_standings['NBA'])} NBA teams from live data")

    if "NHL" in live_standings:
        for team, data in live_standings["NHL"].items():
            nhl[team] = data
        print(f"  Merged {len(live_standings['NHL'])} NHL teams from live data")

    if "EPL" in live_standings:
        for team, data in live_standings["EPL"].items():
            epl[team] = data
        print(f"  Merged {len(live_standings['EPL'])} EPL teams from live data")

    return nba, nhl, epl, laliga


def merge_results(live_results):
    """Merge live results with hardcoded results, deduplicating."""
    combined = list(RECENT_RESULTS)
    existing = {(r["home"], r["away"], r["league"]) for r in combined}

    added = 0
    for r in live_results:
        key = (r["home"], r["away"], r["league"])
        if key not in existing:
            combined.append(r)
            existing.add(key)
            added += 1

    print(f"  Merged results: {len(RECENT_RESULTS)} hardcoded + {added} new = {len(combined)} total")
    return combined


def merge_upcoming(live_odds):
    """Use live odds as upcoming games, fall back to hardcoded."""
    if not live_odds:
        print("  Using hardcoded upcoming games")
        return list(UPCOMING_GAMES)

    # Filter to only future games
    upcoming = []
    for game in live_odds:
        upcoming.append({
            "league": game["league"],
            "home": game["home"],
            "away": game["away"],
            "time": game["time"],
            "mkt": game["mkt"],
        })

    print(f"  Using {len(upcoming)} live upcoming games with market odds")
    return upcoming if upcoming else list(UPCOMING_GAMES)


def main():
    print("=" * 70)
    print("LIVE PREDICTION PIPELINE")
    print("=" * 70)

    # ── Step 1: Fetch live data ──────────────────────────────────
    print("\n[1] Fetching live data from APIs...")

    try:
        live_odds = fetch_all_odds()
    except Exception as e:
        print(f"  [FAIL] Odds fetch failed: {e}")
        live_odds = load_cached("odds.json") or []

    try:
        live_standings = fetch_all_standings()
    except Exception as e:
        print(f"  [FAIL] Standings fetch failed: {e}")
        live_standings = load_cached("standings.json") or {}

    try:
        live_results = fetch_all_results()
    except Exception as e:
        print(f"  [FAIL] Results fetch failed: {e}")
        live_results = load_cached("results.json") or []

    # ── Step 2: Merge with hardcoded fallbacks ───────────────────
    print("\n[2] Merging live data with fallbacks...")

    import prediction_engine as pe
    nba, nhl, epl, laliga = merge_standings(live_standings)

    # Monkey-patch the module-level standings so models use live data
    pe.NBA_STANDINGS.update(nba)
    pe.NHL_STANDINGS.update(nhl)
    pe.EPL_STANDINGS.update(epl)
    pe.LALIGA_STANDINGS.update(laliga)

    results = merge_results(live_results)
    upcoming = merge_upcoming(live_odds)

    # ── Step 3: Run the engine ───────────────────────────────────
    print("\n[3] Running prediction engine...")

    print("  Backtest (pure model)...")
    bt_pure = backtest_on_results(results, use_market=False)
    print(f"  → {bt_pure['overall']['correct']}/{bt_pure['overall']['total']} = {bt_pure['overall']['accuracy']*100:.1f}%")

    print("  Backtest (market blend)...")
    bt_mkt = backtest_on_results(results, use_market=True)
    print(f"  → {bt_mkt['overall']['correct']}/{bt_mkt['overall']['total']} = {bt_mkt['overall']['accuracy']*100:.1f}%")

    print("  Monte Carlo (2000 sims)...")
    mc = monte_carlo_simulation(2000)

    print("  Generating predictions...")
    predictions = []
    for g in upcoming:
        pred = predict_game(g, recent_results=results, use_market=True)
        if pred:
            predictions.append(pred)
    predictions.sort(key=lambda p: -p["confidence"])
    print(f"  → {len(predictions)} predictions generated")

    # ── Step 4: Generate dashboard ───────────────────────────────
    print("\n[4] Generating dashboard...")
    html = generate_dashboard(bt_pure, bt_mkt, mc, predictions)

    site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_site")
    os.makedirs(site_dir, exist_ok=True)
    out = os.path.join(site_dir, "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"  Dashboard saved to: {out}")

    # Also save predictions as JSON for future API use
    pred_path = os.path.join(DATA_DIR, "predictions.json")
    with open(pred_path, "w") as f:
        json.dump({
            "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "predictions": predictions,
            "backtest_accuracy": bt_pure["overall"]["accuracy"],
        }, f, indent=2)
    print(f"  Predictions JSON saved to: {pred_path}")

    print("\n" + "=" * 70)
    print("DONE — Dashboard is ready")
    print("=" * 70)


if __name__ == "__main__":
    main()
