"""
Multi-Market Prediction Models
==============================
Extends the base prediction engine with:
  1. Spread / handicap predictions (NBA, NHL, EPL, La Liga)
  2. Over/under totals predictions (all leagues)
  3. Both Teams To Score (BTTS) predictions (soccer)
  4. Cross-market signal extraction to improve moneyline picks

Each market model estimates its own probability, then feeds a
"market consensus signal" back into the win probability model.
"""

import math
import statistics
from collections import defaultdict

# ─── Import base standings from the main engine ─────────────────────
from prediction_engine import (
    NBA_STANDINGS, NHL_STANDINGS, EPL_STANDINGS, LALIGA_STANDINGS,
    RECENT_RESULTS,
    NBAModel, NHLModel, SoccerModel,
)


# ════════════════════════════════════════════════════════════════════
# SECTION 1: SCORING AVERAGES FROM RECENT RESULTS
# ════════════════════════════════════════════════════════════════════

def team_scoring_profile(team, league, results=None, n=10):
    """
    Compute a team's average offensive & defensive output
    from their last n games. Returns (avg_scored, avg_conceded).
    """
    results = results or RECENT_RESULTS
    games = [
        r for r in results
        if r.get("league") == league and (r["home"] == team or r["away"] == team)
    ][-n:]

    if not games:
        # League-average fallback
        defaults = {"NBA": (112, 112), "NHL": (3.0, 3.0), "EPL": (1.3, 1.3), "La Liga": (1.25, 1.25)}
        return defaults.get(league, (1.5, 1.5))

    scored, conceded = [], []
    for g in games:
        if g["home"] == team:
            scored.append(g["score_h"])
            conceded.append(g["score_a"])
        else:
            scored.append(g["score_a"])
            conceded.append(g["score_h"])

    return (statistics.mean(scored), statistics.mean(conceded))


def league_avg_total(league, results=None):
    """Average combined score for a league from recent results."""
    results = results or RECENT_RESULTS
    games = [r for r in results if r.get("league") == league]
    if not games:
        return {"NBA": 224, "NHL": 6.0, "EPL": 2.6, "La Liga": 2.5}.get(league, 3.0)
    return statistics.mean(g["score_h"] + g["score_a"] for g in games)


# ════════════════════════════════════════════════════════════════════
# SECTION 2: SPREAD / HANDICAP MODEL
# ════════════════════════════════════════════════════════════════════

class SpreadModel:
    """
    Predict the point spread (margin of victory).

    Method: Convert win probability to expected margin using
    sport-specific scaling, then blend with scoring differential.

    NBA:  1% win prob ≈ 0.30 points (calibrated to ~±12 max spread)
    NHL:  1% win prob ≈ 0.04 goals  (calibrated to ~±2.0 max spread)
    EPL:  1% win prob ≈ 0.035 goals (calibrated to ~±2.5 max spread)
    La Liga: same as EPL
    """
    PROB_TO_POINTS = {
        "NBA": 0.30,
        "NHL": 0.04,
        "EPL": 0.035,
        "La Liga": 0.035,
    }

    @staticmethod
    def predict(home, away, league, win_probs, market=None, results=None):
        """
        Returns: {
            "spread_home": -5.5,     (negative = home favored)
            "spread_away": 5.5,
            "home_cover_prob": 0.55, (prob home covers the market spread)
            "confidence": 0.58,
            "tier": "LEAN"
        }
        """
        results = results or RECENT_RESULTS
        scale = SpreadModel.PROB_TO_POINTS.get(league, 0.05)

        # Win prob → expected margin
        home_wp = win_probs.get("home", 0.5)
        prob_edge = (home_wp - 0.5) * 100  # e.g. 65% → +15
        model_spread = prob_edge * scale    # e.g. +15 * 0.30 = +4.5 points

        # Scoring differential adjustment
        h_off, h_def = team_scoring_profile(home, league, results)
        a_off, a_def = team_scoring_profile(away, league, results)
        scoring_diff = ((h_off - a_def) - (a_off - h_def)) / 2

        # Blend: 60% prob-based, 40% scoring-based
        spread = -(model_spread * 0.6 + scoring_diff * 0.4)

        # Round to nearest 0.5
        spread = round(spread * 2) / 2

        # Market spread comparison
        home_cover_prob = 0.50
        mkt_spread = None
        if market and "spread" in market:
            mkt_spread = market["spread"]  # e.g. -5.5
            # Disagreement between our spread and market = edge
            diff = spread - mkt_spread
            # Each 1 point of disagreement ≈ 3-4% cover probability shift
            shift = {"NBA": 0.03, "NHL": 0.08, "EPL": 0.07, "La Liga": 0.07}
            home_cover_prob = max(0.30, min(0.70, 0.50 + diff * shift.get(league, 0.05)))

        confidence = abs(home_cover_prob - 0.50) + 0.50
        tier = _tier_from_confidence(confidence, league)

        return {
            "spread_home": spread,
            "spread_away": -spread,
            "mkt_spread": mkt_spread,
            "home_cover_prob": round(home_cover_prob, 4),
            "confidence": round(confidence, 4),
            "tier": tier,
        }


# ════════════════════════════════════════════════════════════════════
# SECTION 3: OVER/UNDER TOTALS MODEL
# ════════════════════════════════════════════════════════════════════

class TotalsModel:
    """
    Predict the total combined score (over/under).

    Method: Poisson-style estimation using team offensive/defensive
    profiles against league averages, with home advantage boost.

    Expected total = (home_off_rate × away_def_rate + away_off_rate × home_def_rate) × league_avg
    """
    HOME_BOOST = {"NBA": 1.02, "NHL": 1.015, "EPL": 1.03, "La Liga": 1.035}

    @staticmethod
    def predict(home, away, league, market=None, results=None):
        """
        Returns: {
            "predicted_total": 221.5,
            "over_prob": 0.54,
            "under_prob": 0.46,
            "confidence": 0.54,
            "tier": "LEAN"
        }
        """
        results = results or RECENT_RESULTS
        lg_avg = league_avg_total(league, results)

        h_off, h_def = team_scoring_profile(home, league, results)
        a_off, a_def = team_scoring_profile(away, league, results)

        # Rates relative to league average half
        lg_half = lg_avg / 2
        if lg_half == 0:
            lg_half = 1

        h_off_rate = h_off / lg_half
        h_def_rate = h_def / lg_half
        a_off_rate = a_off / lg_half
        a_def_rate = a_def / lg_half

        # Expected scores
        boost = TotalsModel.HOME_BOOST.get(league, 1.02)
        exp_home = (h_off_rate * a_def_rate) * lg_half * boost
        exp_away = (a_off_rate * h_def_rate) * lg_half

        predicted_total = exp_home + exp_away

        # Round to nearest 0.5
        predicted_total = round(predicted_total * 2) / 2

        # Variance estimation (higher-scoring sports have higher variance)
        variance_pct = {"NBA": 0.08, "NHL": 0.18, "EPL": 0.22, "La Liga": 0.22}
        sigma = predicted_total * variance_pct.get(league, 0.15)

        # Over/under probability against market line
        mkt_total = None
        if market and "total" in market:
            mkt_total = market["total"]
            # Normal approximation: P(total > line) using z-score
            if sigma > 0:
                z = (predicted_total - mkt_total) / sigma
                over_prob = _normal_cdf(z)
            else:
                over_prob = 0.50
        else:
            # No market line — compare against league average
            if sigma > 0:
                z = (predicted_total - lg_avg) / sigma
                over_prob = _normal_cdf(z)
            else:
                over_prob = 0.50

        over_prob = max(0.20, min(0.80, over_prob))
        under_prob = 1 - over_prob

        confidence = max(over_prob, under_prob)
        tier = _tier_from_confidence(confidence, league)

        return {
            "predicted_total": predicted_total,
            "mkt_total": mkt_total,
            "over_prob": round(over_prob, 4),
            "under_prob": round(under_prob, 4),
            "exp_home_score": round(exp_home, 1),
            "exp_away_score": round(exp_away, 1),
            "confidence": round(confidence, 4),
            "tier": tier,
        }


# ════════════════════════════════════════════════════════════════════
# SECTION 4: BOTH TEAMS TO SCORE (BTTS) — SOCCER ONLY
# ════════════════════════════════════════════════════════════════════

class BTTSModel:
    """
    Predict whether both teams will score.

    Method: Estimate each team's scoring probability in this specific
    matchup, then P(BTTS) = P(home scores) × P(away scores).
    """

    @staticmethod
    def scoring_prob(team, opponent, league, is_home, results=None):
        """Probability that `team` scores at least 1 goal against `opponent`."""
        results = results or RECENT_RESULTS

        # Base: how often does this team score?
        games = [
            r for r in results
            if r.get("league") == league and (r["home"] == team or r["away"] == team)
        ][-8:]

        if not games:
            return 0.70  # league average fallback

        scored_count = sum(
            1 for g in games
            if (g["home"] == team and g["score_h"] > 0) or
               (g["away"] == team and g["score_a"] > 0)
        )
        base_rate = scored_count / len(games)

        # Adjust for opponent's defensive quality
        opp_games = [
            r for r in results
            if r.get("league") == league and (r["home"] == opponent or r["away"] == opponent)
        ][-8:]

        if opp_games:
            conceded_count = sum(
                1 for g in opp_games
                if (g["home"] == opponent and g["score_a"] > 0) or
                   (g["away"] == opponent and g["score_h"] > 0)
            )
            opp_leak_rate = conceded_count / len(opp_games)
        else:
            opp_leak_rate = 0.70

        # Home boost
        boost = 1.08 if is_home else 0.95

        # Blend: 50% own scoring rate, 30% opponent concession rate, 20% league avg
        prob = (base_rate * 0.50 + opp_leak_rate * 0.30 + 0.70 * 0.20) * boost
        return max(0.15, min(0.95, prob))

    @staticmethod
    def predict(home, away, league, market=None, results=None):
        """
        Returns: {
            "btts_yes_prob": 0.62,
            "btts_no_prob": 0.38,
            "home_scores_prob": 0.82,
            "away_scores_prob": 0.75,
            "pick": "BTTS Yes",
            "confidence": 0.62,
            "tier": "STRONG"
        }
        """
        results = results or RECENT_RESULTS

        h_scores = BTTSModel.scoring_prob(home, away, league, True, results)
        a_scores = BTTSModel.scoring_prob(away, home, league, False, results)

        btts_yes = h_scores * a_scores
        btts_no = 1 - btts_yes

        # Blend with market if available
        if market and "btts_yes" in market:
            mkt_yes = market["btts_yes"] / 100
            btts_yes = 0.45 * mkt_yes + 0.55 * btts_yes
            btts_no = 1 - btts_yes

        pick = "BTTS Yes" if btts_yes >= 0.50 else "BTTS No"
        confidence = max(btts_yes, btts_no)

        # BTTS tiers
        if confidence >= 0.70:
            tier = "LOCK"
        elif confidence >= 0.58:
            tier = "STRONG"
        elif confidence >= 0.52:
            tier = "LEAN"
        else:
            tier = "TOSS-UP"

        return {
            "btts_yes_prob": round(btts_yes, 4),
            "btts_no_prob": round(btts_no, 4),
            "home_scores_prob": round(h_scores, 4),
            "away_scores_prob": round(a_scores, 4),
            "pick": pick,
            "confidence": round(confidence, 4),
            "tier": tier,
        }


# ════════════════════════════════════════════════════════════════════
# SECTION 5: CROSS-MARKET SIGNAL EXTRACTION
# ════════════════════════════════════════════════════════════════════

def cross_market_adjustment(home, away, league, base_win_probs, market=None, results=None):
    """
    Use spread and totals predictions to refine the moneyline win probability.

    Signals:
      - Large predicted spread → strengthens favorite's win prob
      - High predicted total + one-sided → the dominant team benefits
      - Spread/totals disagreement with moneyline → dampens confidence

    Returns adjusted win probs dict.
    """
    results = results or RECENT_RESULTS

    spread_pred = SpreadModel.predict(home, away, league, base_win_probs, market, results)
    totals_pred = TotalsModel.predict(home, away, league, market, results)

    home_wp = base_win_probs.get("home", 0.5)
    away_wp = base_win_probs.get("away", 0.5)
    draw_wp = base_win_probs.get("draw", 0)

    # Signal 1: Spread direction confirmation
    # If our spread says home -6, that confirms a strong home win prob
    predicted_spread = spread_pred["spread_home"]
    spread_signal = 0
    if league == "NBA":
        spread_signal = -predicted_spread * 0.003  # each point of spread = 0.3% win prob shift
    elif league == "NHL":
        spread_signal = -predicted_spread * 0.02
    else:
        spread_signal = -predicted_spread * 0.025

    # Signal 2: Totals asymmetry
    # If we expect home to score much more, that boosts home win prob
    exp_h = totals_pred.get("exp_home_score", 0)
    exp_a = totals_pred.get("exp_away_score", 0)
    total_diff = exp_h - exp_a
    lg_total = league_avg_total(league, results)
    if lg_total > 0:
        totals_signal = (total_diff / lg_total) * 0.05
    else:
        totals_signal = 0

    # Combined adjustment (capped to prevent wild swings)
    adj = max(-0.06, min(0.06, (spread_signal + totals_signal) / 2))

    # Apply to win probs
    if draw_wp > 0:
        # Soccer: redistribute from/to draw
        home_wp = max(0.03, min(0.90, home_wp + adj))
        away_wp = max(0.03, min(0.90, away_wp - adj * 0.6))
        draw_wp = max(0.05, 1 - home_wp - away_wp)
        # Renormalize
        t = home_wp + away_wp + draw_wp
        home_wp /= t
        away_wp /= t
        draw_wp /= t
        return {"home": round(home_wp, 4), "away": round(away_wp, 4), "draw": round(draw_wp, 4)}
    else:
        home_wp = max(0.02, min(0.98, home_wp + adj))
        away_wp = 1 - home_wp
        return {"home": round(home_wp, 4), "away": round(away_wp, 4)}


# ════════════════════════════════════════════════════════════════════
# SECTION 6: UNIFIED MULTI-MARKET PREDICTION
# ════════════════════════════════════════════════════════════════════

def predict_all_markets(game, recent_results=None, use_market=True):
    """
    Generate predictions for ALL markets for a single game.

    Returns: {
        "moneyline": { ... base win prediction ... },
        "spread": { ... spread prediction ... },
        "totals": { ... over/under prediction ... },
        "btts": { ... BTTS prediction (soccer only) ... },
        "enhanced_moneyline": { ... cross-market-enhanced win prediction ... },
    }
    """
    results = recent_results or RECENT_RESULTS
    league = game["league"]
    home, away = game["home"], game["away"]
    mkt = game.get("mkt") if use_market else None

    # Step 1: Base moneyline prediction (existing engine)
    if league == "NBA":
        base_probs = NBAModel.predict(home, away, mkt, results)
    elif league == "NHL":
        base_probs = NHLModel.predict(home, away, mkt, results)
    elif league in ("EPL", "La Liga"):
        base_probs = SoccerModel.predict(home, away, league, mkt, results)
    else:
        return None

    # Step 2: Spread prediction
    spread = SpreadModel.predict(home, away, league, base_probs, mkt, results)

    # Step 3: Totals prediction
    totals = TotalsModel.predict(home, away, league, mkt, results)

    # Step 4: BTTS (soccer only)
    btts = None
    if league in ("EPL", "La Liga"):
        btts = BTTSModel.predict(home, away, league, mkt, results)

    # Step 5: Cross-market enhanced moneyline
    enhanced_probs = cross_market_adjustment(home, away, league, base_probs, mkt, results)

    # Build enhanced moneyline result
    is_soccer = league in ("EPL", "La Liga")
    if is_soccer:
        opts = {"home": enhanced_probs["home"], "away": enhanced_probs["away"], "draw": enhanced_probs.get("draw", 0)}
        best = max(opts, key=opts.get)
        confidence = opts[best]
        pick = home if best == "home" else (away if best == "away" else "DRAW")
    else:
        if enhanced_probs["home"] >= enhanced_probs["away"]:
            pick, confidence = home, enhanced_probs["home"]
        else:
            pick, confidence = away, enhanced_probs["away"]

    if league == "NHL":
        tier = "STRONG" if confidence >= 0.62 else ("LEAN" if confidence >= 0.52 else "TOSS-UP")
    elif is_soccer:
        tier = "LOCK" if confidence >= 0.60 else ("STRONG" if confidence >= 0.45 else ("LEAN" if confidence >= 0.32 else "TOSS-UP"))
    else:
        tier = "LOCK" if confidence >= 0.75 else ("STRONG" if confidence >= 0.60 else ("LEAN" if confidence >= 0.45 else "TOSS-UP"))

    edge = 0
    if mkt:
        if pick == home:
            edge = enhanced_probs["home"] - mkt["h"] / 100
        elif pick == away:
            edge = enhanced_probs["away"] - mkt["a"] / 100
        elif pick == "DRAW" and "d" in mkt:
            edge = enhanced_probs.get("draw", 0) - mkt["d"] / 100

    enhanced_ml = {
        "pick": pick,
        "confidence": round(confidence, 4),
        "tier": tier,
        "edge": round(edge, 4),
        "probs": enhanced_probs,
        "league": league,
        "home": home,
        "away": away,
    }

    return {
        "moneyline": enhanced_ml,
        "spread": spread,
        "totals": totals,
        "btts": btts,
        "base_probs": {k: round(v, 4) for k, v in base_probs.items()},
    }


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _normal_cdf(z):
    """Approximation of the standard normal CDF."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _tier_from_confidence(confidence, league):
    """Generic tier assignment."""
    if league == "NHL":
        return "STRONG" if confidence >= 0.62 else ("LEAN" if confidence >= 0.52 else "TOSS-UP")
    elif league in ("EPL", "La Liga"):
        return "LOCK" if confidence >= 0.65 else ("STRONG" if confidence >= 0.55 else ("LEAN" if confidence >= 0.48 else "TOSS-UP"))
    else:
        return "LOCK" if confidence >= 0.70 else ("STRONG" if confidence >= 0.58 else ("LEAN" if confidence >= 0.50 else "TOSS-UP"))


# ════════════════════════════════════════════════════════════════════
# CLI TEST
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from prediction_engine import UPCOMING_GAMES

    print("=" * 80)
    print("MULTI-MARKET PREDICTIONS")
    print("=" * 80)

    for game in UPCOMING_GAMES[:6]:
        result = predict_all_markets(game)
        if not result:
            continue

        ml = result["moneyline"]
        sp = result["spread"]
        to = result["totals"]
        bt = result["btts"]

        print(f"\n{'─' * 70}")
        print(f"  {ml['league']:>7}  {ml['home']} vs {ml['away']}")
        print(f"  {'─' * 60}")

        # Moneyline
        print(f"  WIN:     {ml['pick']:<25} {ml['confidence']*100:.0f}% [{ml['tier']}]  edge: {ml['edge']*100:+.1f}%")

        # Spread
        sp_pick = f"{ml['home']} {sp['spread_home']:+.1f}" if sp['spread_home'] < 0 else f"{ml['away']} {sp['spread_away']:+.1f}"
        print(f"  SPREAD:  {sp_pick:<25} {sp['confidence']*100:.0f}% [{sp['tier']}]")

        # Totals
        ou_pick = "OVER" if to['over_prob'] > 0.50 else "UNDER"
        ou_conf = max(to['over_prob'], to['under_prob'])
        line = f"{to.get('mkt_total') or to['predicted_total']}"
        print(f"  TOTAL:   {ou_pick} {line:<21} {ou_conf*100:.0f}% [{to['tier']}]  (pred: {to['predicted_total']})")

        # BTTS
        if bt:
            print(f"  BTTS:    {bt['pick']:<25} {bt['confidence']*100:.0f}% [{bt['tier']}]")

    print(f"\n{'=' * 80}")
