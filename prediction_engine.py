"""
Multi-League Prediction Engine
==============================
Sport-specific predictive models with backtesting framework.
Leagues: NBA, NHL, EPL, La Liga

Architecture:
  1. Sport-specific feature extractors
  2. Blended probability models (market + Elo + form + context)
  3. Backtest harness on real results + Monte Carlo edge-case simulation
  4. Static HTML dashboard output with Chart.js
"""

import math
import random
import json
import statistics
from datetime import datetime
from collections import defaultdict

# =============================================================================
# SECTION 1: STANDINGS DATA (live as of 2026-03-13)
# =============================================================================

NBA_STANDINGS = {
    "Detroit Pistons": {"w": 47, "l": 18, "conf": "East"},
    "Cleveland Cavaliers": {"w": 40, "l": 26, "conf": "East"},
    "Milwaukee Bucks": {"w": 27, "l": 38, "conf": "East"},
    "Chicago Bulls": {"w": 27, "l": 39, "conf": "East"},
    "Indiana Pacers": {"w": 15, "l": 51, "conf": "East"},
    "Orlando Magic": {"w": 37, "l": 28, "conf": "East"},
    "Miami Heat": {"w": 38, "l": 29, "conf": "East"},
    "Atlanta Hawks": {"w": 35, "l": 31, "conf": "East"},
    "Charlotte Hornets": {"w": 34, "l": 33, "conf": "East"},
    "Washington Wizards": {"w": 16, "l": 49, "conf": "East"},
    "Boston Celtics": {"w": 43, "l": 23, "conf": "East"},
    "New York Knicks": {"w": 42, "l": 25, "conf": "East"},
    "Toronto Raptors": {"w": 36, "l": 29, "conf": "East"},
    "Philadelphia 76ers": {"w": 35, "l": 31, "conf": "East"},
    "Brooklyn Nets": {"w": 17, "l": 49, "conf": "East"},
    "Los Angeles Lakers": {"w": 41, "l": 25, "conf": "West"},
    "Phoenix Suns": {"w": 39, "l": 27, "conf": "West"},
    "LA Clippers": {"w": 33, "l": 32, "conf": "West"},
    "Golden State Warriors": {"w": 32, "l": 33, "conf": "West"},
    "Sacramento Kings": {"w": 16, "l": 51, "conf": "West"},
    "Oklahoma City Thunder": {"w": 52, "l": 15, "conf": "West"},
    "Denver Nuggets": {"w": 41, "l": 26, "conf": "West"},
    "Minnesota Timberwolves": {"w": 40, "l": 26, "conf": "West"},
    "Portland Trail Blazers": {"w": 31, "l": 35, "conf": "West"},
    "Utah Jazz": {"w": 20, "l": 46, "conf": "West"},
    "San Antonio Spurs": {"w": 48, "l": 18, "conf": "West"},
    "Houston Rockets": {"w": 40, "l": 25, "conf": "West"},
    "Memphis Grizzlies": {"w": 23, "l": 42, "conf": "West"},
    "Dallas Mavericks": {"w": 22, "l": 44, "conf": "West"},
    "New Orleans Pelicans": {"w": 22, "l": 45, "conf": "West"},
}

NHL_STANDINGS = {
    "Colorado Avalanche": {"w": 44, "l": 11, "conf": "West", "div": "Central"},
    "Dallas Stars": {"w": 41, "l": 14, "conf": "West", "div": "Central"},
    "Minnesota Wild": {"w": 38, "l": 16, "conf": "West", "div": "Central"},
    "Utah Mammoth": {"w": 34, "l": 26, "conf": "West", "div": "Central"},
    "Nashville Predators": {"w": 29, "l": 27, "conf": "West", "div": "Central"},
    "Winnipeg Jets": {"w": 26, "l": 28, "conf": "West", "div": "Central"},
    "St. Louis Blues": {"w": 26, "l": 29, "conf": "West", "div": "Central"},
    "Chicago Blackhawks": {"w": 25, "l": 29, "conf": "West", "div": "Central"},
    "Anaheim Ducks": {"w": 36, "l": 26, "conf": "West", "div": "Pacific"},
    "Vegas Golden Knights": {"w": 30, "l": 22, "conf": "West", "div": "Pacific"},
    "Edmonton Oilers": {"w": 32, "l": 26, "conf": "West", "div": "Pacific"},
    "San Jose Sharks": {"w": 31, "l": 26, "conf": "West", "div": "Pacific"},
    "Seattle Kraken": {"w": 29, "l": 26, "conf": "West", "div": "Pacific"},
    "Los Angeles Kings": {"w": 26, "l": 23, "conf": "West", "div": "Pacific"},
    "Calgary Flames": {"w": 26, "l": 32, "conf": "West", "div": "Pacific"},
    "Vancouver Canucks": {"w": 20, "l": 37, "conf": "West", "div": "Pacific"},
    "Carolina Hurricanes": {"w": 41, "l": 18, "conf": "East", "div": "Metro"},
    "Pittsburgh Penguins": {"w": 32, "l": 18, "conf": "East", "div": "Metro"},
    "New York Islanders": {"w": 37, "l": 23, "conf": "East", "div": "Metro"},
    "Columbus Blue Jackets": {"w": 33, "l": 21, "conf": "East", "div": "Metro"},
    "Philadelphia Flyers": {"w": 31, "l": 23, "conf": "East", "div": "Metro"},
    "Washington Capitals": {"w": 33, "l": 27, "conf": "East", "div": "Metro"},
    "New Jersey Devils": {"w": 32, "l": 31, "conf": "East", "div": "Metro"},
    "New York Rangers": {"w": 27, "l": 30, "conf": "East", "div": "Metro"},
    "Buffalo Sabres": {"w": 40, "l": 20, "conf": "East", "div": "Atlantic"},
    "Tampa Bay Lightning": {"w": 40, "l": 20, "conf": "East", "div": "Atlantic"},
    "Montreal Canadiens": {"w": 36, "l": 18, "conf": "East", "div": "Atlantic"},
    "Detroit Red Wings": {"w": 36, "l": 23, "conf": "East", "div": "Atlantic"},
    "Boston Bruins": {"w": 36, "l": 23, "conf": "East", "div": "Atlantic"},
    "Ottawa Senators": {"w": 32, "l": 23, "conf": "East", "div": "Atlantic"},
    "Florida Panthers": {"w": 33, "l": 29, "conf": "East", "div": "Atlantic"},
    "Toronto Maple Leafs": {"w": 28, "l": 27, "conf": "East", "div": "Atlantic"},
}

EPL_STANDINGS = {
    "Arsenal FC": {"w": 20, "l": 3, "d": 7, "pts": 67, "gd": 35},
    "Manchester City": {"w": 18, "l": 5, "d": 6, "pts": 60, "gd": 30},
    "Manchester United": {"w": 14, "l": 6, "d": 9, "pts": 51, "gd": 12},
    "Aston Villa": {"w": 15, "l": 8, "d": 6, "pts": 51, "gd": 14},
    "Chelsea FC": {"w": 13, "l": 7, "d": 9, "pts": 48, "gd": 15},
    "Liverpool FC": {"w": 14, "l": 9, "d": 6, "pts": 48, "gd": 13},
    "Brentford FC": {"w": 13, "l": 11, "d": 5, "pts": 44, "gd": 4},
    "Everton FC": {"w": 12, "l": 10, "d": 7, "pts": 43, "gd": 2},
    "AFC Bournemouth": {"w": 9, "l": 7, "d": 13, "pts": 40, "gd": 1},
    "Fulham FC": {"w": 12, "l": 13, "d": 4, "pts": 40, "gd": -2},
    "Sunderland AFC": {"w": 10, "l": 9, "d": 10, "pts": 40, "gd": 0},
    "Newcastle United": {"w": 11, "l": 12, "d": 6, "pts": 39, "gd": -1},
    "Crystal Palace": {"w": 10, "l": 11, "d": 8, "pts": 38, "gd": -3},
    "Brighton & Hove Albion": {"w": 9, "l": 10, "d": 10, "pts": 37, "gd": -2},
    "Leeds United": {"w": 7, "l": 12, "d": 10, "pts": 31, "gd": -8},
    "Tottenham Hotspur": {"w": 7, "l": 14, "d": 8, "pts": 29, "gd": -14},
    "Nottingham Forest": {"w": 7, "l": 15, "d": 7, "pts": 28, "gd": -16},
    "West Ham United": {"w": 7, "l": 15, "d": 7, "pts": 28, "gd": -18},
    "Burnley FC": {"w": 4, "l": 18, "d": 7, "pts": 19, "gd": -28},
    "Wolverhampton Wanderers": {"w": 3, "l": 20, "d": 7, "pts": 16, "gd": -34},
}

LALIGA_STANDINGS = {
    "Real Madrid": {"w": 18, "l": 4, "d": 6, "pts": 60, "gd": 32},
    "FC Barcelona": {"w": 19, "l": 5, "d": 4, "pts": 61, "gd": 38},
    "Atletico Madrid": {"w": 16, "l": 5, "d": 7, "pts": 55, "gd": 22},
    "Athletic Bilbao": {"w": 13, "l": 6, "d": 9, "pts": 48, "gd": 14},
    "Villarreal CF": {"w": 13, "l": 8, "d": 7, "pts": 46, "gd": 10},
    "Real Sociedad": {"w": 11, "l": 8, "d": 9, "pts": 42, "gd": 5},
    "Real Betis Seville": {"w": 11, "l": 9, "d": 8, "pts": 41, "gd": 4},
    "Sevilla FC": {"w": 10, "l": 10, "d": 8, "pts": 38, "gd": 0},
    "RC Celta de Vigo": {"w": 9, "l": 10, "d": 9, "pts": 36, "gd": -2},
    "CA Osasuna": {"w": 9, "l": 11, "d": 8, "pts": 35, "gd": -4},
    "Girona FC": {"w": 8, "l": 11, "d": 9, "pts": 33, "gd": -5},
    "Rayo Vallecano": {"w": 8, "l": 11, "d": 9, "pts": 33, "gd": -6},
    "RCD Mallorca": {"w": 8, "l": 12, "d": 8, "pts": 32, "gd": -8},
    "Getafe CF": {"w": 8, "l": 13, "d": 7, "pts": 31, "gd": -10},
    "Valencia CF": {"w": 7, "l": 12, "d": 9, "pts": 30, "gd": -9},
    "Levante UD": {"w": 7, "l": 13, "d": 8, "pts": 29, "gd": -12},
    "Deportivo Alaves": {"w": 6, "l": 14, "d": 8, "pts": 26, "gd": -15},
    "Real Oviedo": {"w": 6, "l": 14, "d": 8, "pts": 26, "gd": -14},
    "Espanyol Barcelona": {"w": 5, "l": 15, "d": 8, "pts": 23, "gd": -18},
    "Elche CF": {"w": 4, "l": 17, "d": 7, "pts": 19, "gd": -22},
}

# =============================================================================
# SECTION 2: RECENT RESULTS (for backtesting)
# =============================================================================

RECENT_RESULTS = [
    {"league":"NBA","home":"San Antonio Spurs","away":"Boston Celtics","score_h":125,"score_a":116},
    {"league":"NBA","home":"Portland Trail Blazers","away":"Charlotte Hornets","score_h":101,"score_a":103},
    {"league":"NBA","home":"Sacramento Kings","away":"Indiana Pacers","score_h":114,"score_a":109},
    {"league":"NBA","home":"Golden State Warriors","away":"Chicago Bulls","score_h":124,"score_a":130},
    {"league":"NBA","home":"Los Angeles Lakers","away":"Minnesota Timberwolves","score_h":120,"score_a":106},
    {"league":"NBA","home":"Orlando Magic","away":"Cleveland Cavaliers","score_h":128,"score_a":122},
    {"league":"NBA","home":"New Orleans Pelicans","away":"Toronto Raptors","score_h":122,"score_a":111},
    {"league":"NBA","home":"Utah Jazz","away":"New York Knicks","score_h":117,"score_a":134},
    {"league":"NBA","home":"Denver Nuggets","away":"Houston Rockets","score_h":129,"score_a":93},
    {"league":"NBA","home":"Sacramento Kings","away":"Charlotte Hornets","score_h":109,"score_a":117},
    {"league":"NBA","home":"LA Clippers","away":"Minnesota Timberwolves","score_h":153,"score_a":128},
    {"league":"NBA","home":"Detroit Pistons","away":"Philadelphia 76ers","score_h":131,"score_a":109},
    {"league":"NBA","home":"Orlando Magic","away":"Washington Wizards","score_h":136,"score_a":131},
    {"league":"NBA","home":"Indiana Pacers","away":"Phoenix Suns","score_h":108,"score_a":123},
    {"league":"NBA","home":"Atlanta Hawks","away":"Brooklyn Nets","score_h":108,"score_a":97},
    {"league":"NBA","home":"Miami Heat","away":"Milwaukee Bucks","score_h":112,"score_a":105},
    {"league":"NBA","home":"Memphis Grizzlies","away":"Dallas Mavericks","score_h":112,"score_a":120},
    {"league":"NBA","home":"San Antonio Spurs","away":"Denver Nuggets","score_h":131,"score_a":136},
    {"league":"NBA","home":"Oklahoma City Thunder","away":"Boston Celtics","score_h":104,"score_a":102},
    {"league":"NBA","home":"Los Angeles Lakers","away":"Chicago Bulls","score_h":142,"score_a":130},
    {"league":"NHL","home":"Minnesota Wild","away":"Utah Mammoth","score_h":5,"score_a":0},
    {"league":"NHL","home":"Winnipeg Jets","away":"Anaheim Ducks","score_h":1,"score_a":4},
    {"league":"NHL","home":"Colorado Avalanche","away":"Edmonton Oilers","score_h":3,"score_a":4},
    {"league":"NHL","home":"Seattle Kraken","away":"Nashville Predators","score_h":2,"score_a":4},
    {"league":"NHL","home":"Ottawa Senators","away":"Montreal Canadiens","score_h":2,"score_a":3},
    {"league":"NHL","home":"Philadelphia Flyers","away":"Washington Capitals","score_h":4,"score_a":1},
    {"league":"NHL","home":"Toronto Maple Leafs","away":"Anaheim Ducks","score_h":6,"score_a":4},
    {"league":"NHL","home":"New Jersey Devils","away":"Calgary Flames","score_h":4,"score_a":5},
    {"league":"NHL","home":"Carolina Hurricanes","away":"St. Louis Blues","score_h":1,"score_a":3},
    {"league":"NHL","home":"Tampa Bay Lightning","away":"Detroit Red Wings","score_h":4,"score_a":1},
    {"league":"NHL","home":"Buffalo Sabres","away":"Washington Capitals","score_h":1,"score_a":2},
    {"league":"NHL","home":"Florida Panthers","away":"Columbus Blue Jackets","score_h":2,"score_a":1},
    {"league":"NHL","home":"Boston Bruins","away":"San Jose Sharks","score_h":2,"score_a":4},
    {"league":"NHL","home":"Winnipeg Jets","away":"New York Rangers","score_h":3,"score_a":6},
    {"league":"NHL","home":"Minnesota Wild","away":"Philadelphia Flyers","score_h":2,"score_a":3},
    {"league":"NHL","home":"Dallas Stars","away":"Edmonton Oilers","score_h":7,"score_a":2},
    {"league":"NHL","home":"Utah Mammoth","away":"Chicago Blackhawks","score_h":2,"score_a":3},
    {"league":"NHL","home":"Vegas Golden Knights","away":"Pittsburgh Penguins","score_h":6,"score_a":2},
    {"league":"NHL","home":"Seattle Kraken","away":"Colorado Avalanche","score_h":1,"score_a":5},
    {"league":"NHL","home":"Vancouver Canucks","away":"Nashville Predators","score_h":4,"score_a":3},
    {"league":"EPL","home":"AFC Bournemouth","away":"Brentford FC","score_h":0,"score_a":0},
    {"league":"EPL","home":"Everton FC","away":"Burnley FC","score_h":2,"score_a":0},
    {"league":"EPL","home":"Leeds United","away":"Sunderland AFC","score_h":0,"score_a":1},
    {"league":"EPL","home":"Wolverhampton Wanderers","away":"Liverpool FC","score_h":2,"score_a":1},
    {"league":"EPL","home":"Brighton & Hove Albion","away":"Arsenal FC","score_h":0,"score_a":1},
    {"league":"EPL","home":"Fulham FC","away":"West Ham United","score_h":0,"score_a":1},
    {"league":"EPL","home":"Aston Villa","away":"Chelsea FC","score_h":1,"score_a":4},
    {"league":"EPL","home":"Manchester City","away":"Nottingham Forest","score_h":2,"score_a":2},
    {"league":"EPL","home":"Newcastle United","away":"Manchester United","score_h":2,"score_a":1},
    {"league":"EPL","home":"Tottenham Hotspur","away":"Crystal Palace","score_h":1,"score_a":3},
    {"league":"La Liga","home":"RC Celta de Vigo","away":"Real Madrid","score_h":1,"score_a":2},
    {"league":"La Liga","home":"CA Osasuna","away":"RCD Mallorca","score_h":2,"score_a":2},
    {"league":"La Liga","home":"Levante UD","away":"Girona FC","score_h":1,"score_a":1},
    {"league":"La Liga","home":"Atletico Madrid","away":"Real Sociedad","score_h":3,"score_a":2},
    {"league":"La Liga","home":"Athletic Bilbao","away":"FC Barcelona","score_h":0,"score_a":1},
    {"league":"La Liga","home":"Villarreal CF","away":"Elche CF","score_h":2,"score_a":1},
    {"league":"La Liga","home":"Getafe CF","away":"Real Betis Seville","score_h":2,"score_a":0},
    {"league":"La Liga","home":"Sevilla FC","away":"Rayo Vallecano","score_h":1,"score_a":1},
    {"league":"La Liga","home":"Valencia CF","away":"Deportivo Alaves","score_h":3,"score_a":2},
    {"league":"La Liga","home":"Espanyol Barcelona","away":"Real Oviedo","score_h":1,"score_a":1},
]

# =============================================================================
# SECTION 3: UPCOMING GAMES
# =============================================================================

UPCOMING_GAMES = [
    {"league":"NBA","home":"Dallas Mavericks","away":"Cleveland Cavaliers","time":"2026-03-13T23:30Z","mkt":{"h":13,"a":87}},
    {"league":"NBA","home":"Detroit Pistons","away":"Memphis Grizzlies","time":"2026-03-13T23:30Z","mkt":{"h":90.4,"a":9.6}},
    {"league":"NBA","home":"Indiana Pacers","away":"New York Knicks","time":"2026-03-13T23:30Z","mkt":{"h":12.5,"a":87.5}},
    {"league":"NBA","home":"Toronto Raptors","away":"Phoenix Suns","time":"2026-03-13T23:30Z","mkt":{"h":63.2,"a":36.8}},
    {"league":"NBA","home":"Houston Rockets","away":"New Orleans Pelicans","time":"2026-03-14T00:00Z","mkt":{"h":71.4,"a":28.6}},
    {"league":"NBA","home":"Portland Trail Blazers","away":"Utah Jazz","time":"2026-03-14T02:00Z","mkt":{"h":89,"a":11}},
    {"league":"NBA","home":"Golden State Warriors","away":"Minnesota Timberwolves","time":"2026-03-14T02:00Z","mkt":{"h":32.5,"a":67.5}},
    {"league":"NBA","home":"LA Clippers","away":"Chicago Bulls","time":"2026-03-14T02:30Z","mkt":{"h":86.2,"a":13.8}},
    {"league":"NHL","home":"New York Islanders","away":"Los Angeles Kings","time":"2026-03-13T23:00Z","mkt":{"h":55.8,"a":44.2}},
    {"league":"NHL","home":"St. Louis Blues","away":"Edmonton Oilers","time":"2026-03-14T00:00Z","mkt":{"h":42,"a":58}},
    {"league":"EPL","home":"Burnley FC","away":"AFC Bournemouth","time":"2026-03-14T15:00Z","mkt":{"h":23.2,"a":52.1,"d":24.7}},
    {"league":"EPL","home":"Sunderland AFC","away":"Brighton & Hove Albion","time":"2026-03-14T15:00Z","mkt":{"h":28.9,"a":42.3,"d":28.8}},
    {"league":"EPL","home":"Arsenal FC","away":"Everton FC","time":"2026-03-14T17:30Z","mkt":{"h":69.8,"a":10.9,"d":19.3}},
    {"league":"EPL","home":"Chelsea FC","away":"Newcastle United","time":"2026-03-14T17:30Z","mkt":{"h":53.1,"a":24.2,"d":22.7}},
    {"league":"EPL","home":"West Ham United","away":"Manchester City","time":"2026-03-14T20:00Z","mkt":{"h":21.2,"a":56.6,"d":22.2}},
    {"league":"EPL","home":"Liverpool FC","away":"Tottenham Hotspur","time":"2026-03-15T16:30Z","mkt":{"h":74.1,"a":10.6,"d":15.3}},
    {"league":"La Liga","home":"Deportivo Alaves","away":"Villarreal CF","time":"2026-03-13T20:00Z","mkt":{"h":29,"a":42.8,"d":28.2}},
    {"league":"La Liga","home":"Girona FC","away":"Athletic Bilbao","time":"2026-03-14T13:00Z","mkt":{"h":34.8,"a":36.7,"d":28.5}},
    {"league":"La Liga","home":"Atletico Madrid","away":"Getafe CF","time":"2026-03-14T15:15Z","mkt":{"h":61.4,"a":13.9,"d":24.7}},
    {"league":"La Liga","home":"Real Oviedo","away":"Valencia CF","time":"2026-03-14T17:30Z","mkt":{"h":32.7,"a":37.1,"d":30.2}},
    {"league":"La Liga","home":"Real Madrid","away":"Elche CF","time":"2026-03-14T20:00Z","mkt":{"h":72.5,"a":11.6,"d":15.9}},
    {"league":"La Liga","home":"FC Barcelona","away":"Sevilla FC","time":"2026-03-15T15:15Z","mkt":{"h":75.9,"a":10.1,"d":14}},
]


# =============================================================================
# SECTION 4: SPORT-SPECIFIC PREDICTION MODELS
# =============================================================================

class NBAModel:
    """
    NBA: 60% market / 25% Elo / 15% form
    Home advantage: 3.5% (post-COVID compression)
    """
    HOME_ADV = 0.035
    MARKET_W, ELO_W, FORM_W = 0.60, 0.25, 0.15

    @staticmethod
    def win_rate(team):
        s = NBA_STANDINGS.get(team)
        return s["w"] / (s["w"] + s["l"]) if s else 0.5

    @staticmethod
    def strength(team):
        wr = max(0.01, min(0.99, NBAModel.win_rate(team)))
        return math.log(wr / (1 - wr))

    @staticmethod
    def form(team, recent):
        games = [r for r in recent if r.get("league") == "NBA" and (r["home"] == team or r["away"] == team)][-5:]
        if not games: return 0.0
        wins = sum(1 for g in games if (g["home"]==team and g["score_h"]>g["score_a"]) or (g["away"]==team and g["score_a"]>g["score_h"]))
        return max(-0.08, min(0.08, (wins/len(games) - NBAModel.win_rate(team)) * 0.4))

    @staticmethod
    def predict(home, away, market=None, recent=None, **kw):
        recent = recent or []
        diff = NBAModel.strength(home) - NBAModel.strength(away) + NBAModel.HOME_ADV * 4
        elo_h = 1 / (1 + math.exp(-diff))
        form_adj = (NBAModel.form(home, recent) - NBAModel.form(away, recent)) * 0.5
        elo_adj = max(0.02, min(0.98, elo_h + form_adj))
        if market:
            bl = NBAModel.MARKET_W * market["h"]/100 + NBAModel.ELO_W * elo_h + NBAModel.FORM_W * elo_adj
        else:
            bl = elo_adj
        bl = max(0.02, min(0.98, bl))
        return {"home": bl, "away": 1-bl}


class NHLModel:
    """
    NHL: 65% market / 25% Elo / 10% form
    Home advantage: 2.5%
    Variance compression: 0.7x then 0.85x (no game above 72%)
    No LOCK tier — hockey is too chaotic
    """
    HOME_ADV = 0.025
    MARKET_W, ELO_W, FORM_W = 0.65, 0.25, 0.10
    COMPRESS_1, COMPRESS_2 = 0.7, 0.85

    @staticmethod
    def win_rate(team):
        s = NHL_STANDINGS.get(team)
        return s["w"]/(s["w"]+s["l"]) if s and (s["w"]+s["l"])>0 else 0.5

    @staticmethod
    def strength(team):
        wr = max(0.05, min(0.95, NHLModel.win_rate(team)))
        return math.log(wr / (1 - wr))

    @staticmethod
    def form(team, recent):
        games = [r for r in recent if r.get("league")=="NHL" and (r["home"]==team or r["away"]==team)][-5:]
        if not games: return 0.0
        wins = sum(1 for g in games if (g["home"]==team and g["score_h"]>g["score_a"]) or (g["away"]==team and g["score_a"]>g["score_h"]))
        return (wins/len(games) - NHLModel.win_rate(team)) * 0.3

    @staticmethod
    def predict(home, away, market=None, recent=None, **kw):
        recent = recent or []
        diff = NHLModel.strength(home) - NHLModel.strength(away) + NHLModel.HOME_ADV * 3
        elo_h = 1/(1+math.exp(-diff))
        elo_h = 0.5 + (elo_h - 0.5) * NHLModel.COMPRESS_1
        form_adj = (NHLModel.form(home, recent) - NHLModel.form(away, recent)) * 0.4
        elo_adj = max(0.15, min(0.85, elo_h + form_adj))
        if market:
            bl = NHLModel.MARKET_W * market["h"]/100 + NHLModel.ELO_W * elo_h + NHLModel.FORM_W * elo_adj
        else:
            bl = elo_adj
        bl = 0.5 + (bl - 0.5) * NHLModel.COMPRESS_2
        bl = max(0.15, min(0.85, bl))
        return {"home": bl, "away": 1-bl}


class SoccerModel:
    """
    Soccer (EPL/La Liga): 55% market / 25% Elo / 10% form / 10% GD
    Home adv: EPL 4.5%, La Liga 5.5%
    Three-outcome with explicit draw modeling
    """
    HOME_ADV = {"EPL": 0.045, "La Liga": 0.055}
    MARKET_W = 0.55

    @staticmethod
    def standings(league):
        return EPL_STANDINGS if league == "EPL" else LALIGA_STANDINGS

    @staticmethod
    def ppg(team, league):
        s = SoccerModel.standings(league).get(team)
        if not s: return 1.0
        t = s["w"]+s["l"]+s["d"]
        return s["pts"]/t if t else 1.0

    @staticmethod
    def gdpg(team, league):
        s = SoccerModel.standings(league).get(team)
        if not s: return 0.0
        t = s["w"]+s["l"]+s["d"]
        return s.get("gd",0)/t if t else 0.0

    @staticmethod
    def draw_rate(team, league):
        s = SoccerModel.standings(league).get(team)
        if not s: return 0.28
        t = s["w"]+s["l"]+s["d"]
        return s["d"]/t if t else 0.28

    @staticmethod
    def strength(team, league):
        ppg = SoccerModel.ppg(team, league)
        gd = SoccerModel.gdpg(team, league)
        return (ppg/3.0)*0.7 + (gd/2.0+0.5)*0.3

    @staticmethod
    def form(team, league, recent):
        games = [r for r in recent if r.get("league")==league and (r["home"]==team or r["away"]==team)][-4:]
        if not games: return 0.0
        pts = sum(3 if (g["home"]==team and g["score_h"]>g["score_a"]) or (g["away"]==team and g["score_a"]>g["score_h"]) else (1 if g["score_h"]==g["score_a"] else 0) for g in games)
        return max(-0.06, min(0.06, (pts/len(games) - SoccerModel.ppg(team,league))/3.0*0.3))

    @staticmethod
    def predict(home, away, league, market=None, recent=None, **kw):
        recent = recent or []
        ha = SoccerModel.HOME_ADV.get(league, 0.05)
        sr_h, sr_a = SoccerModel.strength(home,league), SoccerModel.strength(away,league)
        gd_h, gd_a = SoccerModel.gdpg(home,league), SoccerModel.gdpg(away,league)
        diff = (sr_h - sr_a) + ha
        elo_h = 1/(1+math.exp(-diff*5))
        dp_h, dp_a = SoccerModel.draw_rate(home,league), SoccerModel.draw_rate(away,league)
        closeness = max(0, min(1, 1-abs(sr_h-sr_a)*2))
        draw_p = max(0.08, min(0.38, (dp_h+dp_a)/2*0.5 + closeness*0.25 + 0.08))
        gd_adj = (gd_h-gd_a)*0.10
        form_adj = SoccerModel.form(home,league,recent) - SoccerModel.form(away,league,recent)
        adj_h = max(0.05, min(0.90, elo_h + gd_adj + form_adj))
        rem = 1 - draw_p
        total_ha = adj_h + (1-adj_h)
        hp = adj_h/total_ha*rem
        ap = (1-adj_h)/total_ha*rem
        if market:
            mh,ma,md = market["h"]/100, market["a"]/100, market.get("d",25)/100
            mw = SoccerModel.MARKET_W
            hp = mw*mh + (1-mw)*hp
            ap = mw*ma + (1-mw)*ap
            draw_p = mw*md + (1-mw)*draw_p
            t = hp+ap+draw_p
            hp/=t; ap/=t; draw_p/=t
        return {"home": hp, "away": ap, "draw": draw_p}


# =============================================================================
# SECTION 5: UNIFIED PREDICTION INTERFACE
# =============================================================================

def predict_game(game, recent_results=None, use_market=True):
    league = game["league"]
    mkt = game.get("mkt") if use_market else None
    recent = recent_results or RECENT_RESULTS

    if league == "NBA":
        probs = NBAModel.predict(game["home"], game["away"], mkt, recent)
    elif league == "NHL":
        probs = NHLModel.predict(game["home"], game["away"], mkt, recent)
    elif league in ("EPL", "La Liga"):
        probs = SoccerModel.predict(game["home"], game["away"], league, mkt, recent)
    else:
        return None

    is_soccer = league in ("EPL", "La Liga")
    if is_soccer:
        opts = {"home": probs["home"], "away": probs["away"], "draw": probs["draw"]}
        best = max(opts, key=opts.get)
        confidence = opts[best]
        pick = game["home"] if best=="home" else (game["away"] if best=="away" else "DRAW")
    else:
        if probs["home"] >= probs["away"]:
            pick, confidence = game["home"], probs["home"]
        else:
            pick, confidence = game["away"], probs["away"]

    if league == "NHL":
        tier = "STRONG" if confidence >= 0.62 else ("LEAN" if confidence >= 0.52 else "TOSS-UP")
    elif is_soccer:
        tier = "LOCK" if confidence>=0.60 else ("STRONG" if confidence>=0.45 else ("LEAN" if confidence>=0.32 else "TOSS-UP"))
    else:
        tier = "LOCK" if confidence>=0.75 else ("STRONG" if confidence>=0.60 else ("LEAN" if confidence>=0.45 else "TOSS-UP"))

    edge = 0
    if mkt:
        if pick == game["home"]: edge = probs["home"] - mkt["h"]/100
        elif pick == game["away"]: edge = probs["away"] - mkt["a"]/100
        elif pick == "DRAW" and "d" in mkt: edge = probs.get("draw",0) - mkt["d"]/100

    return {"pick":pick,"confidence":round(confidence,4),"tier":tier,"edge":round(edge,4),
            "probs":{k:round(v,4) for k,v in probs.items()},"league":league,"home":game["home"],"away":game["away"]}


# =============================================================================
# SECTION 6: BACKTESTING
# =============================================================================

def backtest_on_results(results, use_market=False):
    by_league = defaultdict(lambda: {"correct":0,"total":0,"details":[]})
    all_c, all_t = 0, 0
    for r in results:
        league = r["league"]
        if use_market:
            if league == "NBA":
                wr_h, wr_a = NBAModel.win_rate(r["home"]), NBAModel.win_rate(r["away"])
            elif league == "NHL":
                wr_h, wr_a = NHLModel.win_rate(r["home"]), NHLModel.win_rate(r["away"])
            else:
                wr_h = SoccerModel.ppg(r["home"],league)/3.0
                wr_a = SoccerModel.ppg(r["away"],league)/3.0
            total = wr_h+wr_a or 1
            sh = wr_h/total*100
            mkt = {"h":sh*0.8,"a":(100-sh)*0.8,"d":20} if league in ("EPL","La Liga") else {"h":sh,"a":100-sh}
        else:
            mkt = None
        game = {"league":league,"home":r["home"],"away":r["away"],"mkt":mkt}
        earlier = [x for x in results if x is not r]
        pred = predict_game(game, recent_results=earlier, use_market=use_market)
        if not pred: continue
        actual = r["home"] if r["score_h"]>r["score_a"] else (r["away"] if r["score_a"]>r["score_h"] else "DRAW")
        correct = pred["pick"]==actual
        by_league[league]["correct"] += int(correct)
        by_league[league]["total"] += 1
        by_league[league]["details"].append({"home":r["home"],"away":r["away"],"score":f"{r['score_h']}-{r['score_a']}",
            "pick":pred["pick"],"actual":actual,"confidence":pred["confidence"],"tier":pred["tier"],"correct":correct})
        all_c += int(correct); all_t += 1
    return {"overall":{"correct":all_c,"total":all_t,"accuracy":round(all_c/max(all_t,1),4)},
            "by_league":{k:{"correct":v["correct"],"total":v["total"],"accuracy":round(v["correct"]/max(v["total"],1),4),"details":v["details"]} for k,v in by_league.items()}}

def monte_carlo_simulation(n_sims=2000):
    random.seed(42)
    cal = defaultdict(lambda: {"pred":0,"wins":0,"n":0})
    lr = defaultdict(lambda: {"c":0,"t":0})
    teams = {"NBA":list(NBA_STANDINGS),"NHL":list(NHL_STANDINGS),"EPL":list(EPL_STANDINGS),"La Liga":list(LALIGA_STANDINGS)}
    for _ in range(n_sims):
        league = random.choice(["NBA","NHL","EPL","La Liga"])
        home, away = random.sample(teams[league], 2)
        pred = predict_game({"league":league,"home":home,"away":away}, use_market=False)
        if not pred: continue
        if league == "NBA":
            tp = NBAModel.win_rate(home)/(NBAModel.win_rate(home)+NBAModel.win_rate(away)) + 0.035 + random.gauss(0,0.12)
            actual = home if random.random() < tp else away
        elif league == "NHL":
            tp = NHLModel.win_rate(home)/(NHLModel.win_rate(home)+NHLModel.win_rate(away)) + 0.025 + random.gauss(0,0.18)
            actual = home if random.random() < tp else away
        else:
            sr_h, sr_a = SoccerModel.strength(home,league), SoccerModel.strength(away,league)
            ha = 0.045 if league=="EPL" else 0.055
            ph = 1/(1+math.exp(-(sr_h-sr_a+ha)*4))*0.75
            pd = max(0.10, min(0.35, 0.25+random.gauss(0,0.05)))
            pa = max(0.05, 1-ph-pd)
            roll = random.random()
            actual = home if roll<ph else ("DRAW" if roll<ph+pd else away)
        correct = pred["pick"]==actual
        lr[league]["c"] += int(correct); lr[league]["t"] += 1
        bk = f"{max(0.20,min(0.95,round(pred['confidence']*20)/20)):.2f}"
        cal[bk]["pred"] += pred["confidence"]; cal[bk]["wins"] += int(correct); cal[bk]["n"] += 1
    cal_data = [{"bucket":float(k),"predicted":round(v["pred"]/v["n"],4),"actual":round(v["wins"]/v["n"],4),"count":v["n"]}
                for k,v in sorted(cal.items()) if v["n"]>=5]
    return {"n_sims":n_sims,
            "league_accuracy":{k:{"correct":v["c"],"total":v["t"],"accuracy":round(v["c"]/max(v["t"],1),4)} for k,v in lr.items()},
            "calibration":cal_data}


# =============================================================================
# SECTION 7: DASHBOARD GENERATION
# =============================================================================

def generate_dashboard(bt_pure, bt_mkt, mc, predictions):
    cal_labels = json.dumps([f"{c['bucket']*100:.0f}%" for c in mc["calibration"]])
    cal_predicted = json.dumps([round(c["predicted"]*100,1) for c in mc["calibration"]])
    cal_actual = json.dumps([round(c["actual"]*100,1) for c in mc["calibration"]])
    league_names = json.dumps(list(bt_pure["by_league"].keys()))
    league_pure = json.dumps([bt_pure["by_league"][k]["accuracy"]*100 for k in bt_pure["by_league"]])
    league_mkt = json.dumps([bt_mkt["by_league"][k]["accuracy"]*100 for k in bt_mkt["by_league"]])
    pred_json = json.dumps(predictions)
    bt_details = []
    for league, data in bt_pure["by_league"].items():
        for d in data["details"]:
            bt_details.append({**d, "league": league})
    bt_details_json = json.dumps(bt_details)
    tier_counts = defaultdict(int)
    for p in predictions: tier_counts[p["tier"]] += 1
    tier_labels = json.dumps(list(tier_counts.keys()))
    tier_values = json.dumps(list(tier_counts.values()))
    mc_acc = json.dumps({k:v["accuracy"]*100 for k,v in mc["league_accuracy"].items()})
    now = datetime.now().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Prediction Engine — Backtest Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{{--bg:#fafaf8;--sf:#fff;--bd:#e5e4df;--tx:#1a1a18;--mt:#6b6a65;--ht:#9c9b96;
--red:#E24B4A;--blue:#378ADD;--green:#1D9E75;--coral:#D85A30;--amber:#EF9F27;
--lk-bg:#E1F5EE;--lk-tx:#085041;--lk-bd:#5DCAA5;--st-bg:#E6F1FB;--st-tx:#0C447C;--st-bd:#85B7EB;
--ln-bg:#FAEEDA;--ln-tx:#633806;--ln-bd:#FAC775;--tu-bg:#F1EFE8;--tu-tx:#444441;--tu-bd:#B4B2A9}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a18;--sf:#242421;--bd:#3a3a36;--tx:#e8e7e3;--mt:#9c9b96;--ht:#6b6a65;
--lk-bg:#04342C;--lk-tx:#9FE1CB;--lk-bd:#0F6E56;--st-bg:#042C53;--st-tx:#85B7EB;--st-bd:#185FA5;
--ln-bg:#412402;--ln-tx:#FAC775;--ln-bd:#854F0B;--tu-bg:#2C2C2A;--tu-tx:#B4B2A9;--tu-bd:#5F5E5A}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--tx);line-height:1.6;padding:2rem;max-width:1200px;margin:0 auto}}
h1{{font-size:22px;font-weight:500;margin-bottom:4px}}h2{{font-size:18px;font-weight:500;margin:2rem 0 1rem}}
h3{{font-size:16px;font-weight:500;margin:0 0 12px}}.sub{{font-size:14px;color:var(--mt);margin-bottom:2rem}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:2rem}}
.m{{background:var(--sf);border:.5px solid var(--bd);border-radius:12px;padding:16px;text-align:center}}
.m-l{{font-size:12px;color:var(--mt);margin-bottom:4px}}.m-v{{font-size:24px;font-weight:500}}.m-s{{font-size:11px;color:var(--ht);margin-top:2px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:2rem}}
@media(max-width:768px){{.row{{grid-template-columns:1fr}}}}
.box{{background:var(--sf);border:.5px solid var(--bd);border-radius:12px;padding:20px}}
.cw{{position:relative;height:280px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:8px 10px;border-bottom:1.5px solid var(--bd);color:var(--mt);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
td{{padding:7px 10px;border-bottom:.5px solid var(--bd)}}tr:hover{{background:var(--sf)}}
.p{{display:inline-block;padding:2px 10px;border-radius:8px;font-size:11px;font-weight:500;letter-spacing:.03em}}
.p-LOCK{{background:var(--lk-bg);color:var(--lk-tx);border:.5px solid var(--lk-bd)}}
.p-STRONG{{background:var(--st-bg);color:var(--st-tx);border:.5px solid var(--st-bd)}}
.p-LEAN{{background:var(--ln-bg);color:var(--ln-tx);border:.5px solid var(--ln-bd)}}
.p-TOSS-UP{{background:var(--tu-bg);color:var(--tu-tx);border:.5px solid var(--tu-bd)}}
.ok{{color:var(--green)}}.no{{color:var(--red)}}.ep{{color:var(--green)}}.en{{color:var(--red)}}
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
.d-NBA{{background:var(--red)}}.d-NHL{{background:var(--blue)}}.d-EPL{{background:var(--green)}}.d-LL{{background:var(--coral)}}
.fb{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}}
.fb button{{padding:6px 14px;border-radius:8px;border:.5px solid var(--bd);background:transparent;cursor:pointer;font-size:13px;color:var(--tx);transition:all .15s}}
.fb button.a{{background:var(--sf);border-color:var(--tx);font-weight:500}}.fb button:hover{{background:var(--sf)}}
.disc{{font-size:11px;color:var(--ht);margin-top:2rem;padding:12px 16px;background:var(--sf);border-radius:8px;border:.5px solid var(--bd)}}
</style></head><body>
<h1>Multi-league prediction engine</h1>
<p class="sub">Backtest report &amp; live predictions &mdash; {now}</p>
<div class="metrics">
<div class="m"><div class="m-l">Backtest accuracy (pure)</div><div class="m-v">{bt_pure['overall']['accuracy']*100:.1f}%</div><div class="m-s">{bt_pure['overall']['correct']}/{bt_pure['overall']['total']} games</div></div>
<div class="m"><div class="m-l">With market blend</div><div class="m-v">{bt_mkt['overall']['accuracy']*100:.1f}%</div><div class="m-s">{bt_mkt['overall']['correct']}/{bt_mkt['overall']['total']} games</div></div>
<div class="m"><div class="m-l">Monte Carlo sims</div><div class="m-v">{mc['n_sims']:,}</div><div class="m-s">random matchups</div></div>
<div class="m"><div class="m-l">Live predictions</div><div class="m-v">{len(predictions)}</div><div class="m-s">upcoming games</div></div>
<div class="m"><div class="m-l">Leagues</div><div class="m-v">4</div><div class="m-s">NBA / NHL / EPL / La Liga</div></div>
</div>
<div class="row">
<div class="box"><h3>Calibration curve (Monte Carlo)</h3><div class="cw"><canvas id="c1"></canvas></div></div>
<div class="box"><h3>Accuracy by league</h3><div class="cw"><canvas id="c2"></canvas></div></div>
</div>
<div class="row">
<div class="box"><h3>Tier distribution (live picks)</h3><div class="cw"><canvas id="c3"></canvas></div></div>
<div class="box"><h3>Monte Carlo accuracy by league</h3><div class="cw"><canvas id="c4"></canvas></div></div>
</div>
<h2>Live predictions</h2>
<div class="fb" id="fb"></div>
<table id="pt"><thead><tr><th>League</th><th>Matchup</th><th>Pick</th><th>Conf</th><th>Tier</th><th>Edge</th><th>H%</th><th>A%</th><th>D%</th></tr></thead><tbody></tbody></table>
<h2>Backtest detail (pure model)</h2>
<table id="bt"><thead><tr><th></th><th>League</th><th>Matchup</th><th>Score</th><th>Pick</th><th>Actual</th><th>Conf</th><th>Tier</th></tr></thead><tbody></tbody></table>
<div class="disc">
Model architecture: Sport-specific Elo + form + goal-difference signals, blended with market probabilities where available.
NBA: 60/25/15 market-Elo-form, 3.5% home adv. NHL: 65/25/10, 2.5% home adv, 0.7x+0.85x variance compression, no LOCK tier.
EPL: 55/25/10/10 market-Elo-form-GD, 4.5% home adv. La Liga: same weights, 5.5% home adv.
For entertainment and educational purposes only.
</div>
<script>
const P={pred_json};
const B={bt_details_json};
const gc=getComputedStyle(document.documentElement).getPropertyValue('--bd').trim()||'#e5e4df';
const tc=getComputedStyle(document.documentElement).getPropertyValue('--mt').trim()||'#6b6a65';
Chart.defaults.color=tc;
new Chart(document.getElementById('c1'),{{type:'line',data:{{labels:{cal_labels},datasets:[
{{label:'Perfect',data:{cal_labels}.map(l=>parseFloat(l)),borderColor:'#B4B2A9',borderDash:[5,5],pointRadius:0,borderWidth:1.5}},
{{label:'Predicted',data:{cal_predicted},borderColor:'#378ADD',fill:false,pointRadius:3,borderWidth:2}},
{{label:'Actual',data:{cal_actual},borderColor:'#1D9E75',fill:false,pointRadius:3,borderWidth:2}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}},scales:{{y:{{min:20,max:100,grid:{{color:gc}}}},x:{{grid:{{display:false}}}}}}}}}});
new Chart(document.getElementById('c2'),{{type:'bar',data:{{labels:{league_names},datasets:[
{{label:'Pure model',data:{league_pure},backgroundColor:'#378ADD',borderRadius:4}},
{{label:'Market blend',data:{league_mkt},backgroundColor:'#1D9E75',borderRadius:4}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}},scales:{{y:{{min:0,max:100,grid:{{color:gc}},ticks:{{callback:v=>v+'%'}}}},x:{{grid:{{display:false}}}}}}}}}});
const tC={{'LOCK':'#1D9E75','STRONG':'#378ADD','LEAN':'#EF9F27','TOSS-UP':'#B4B2A9'}};
new Chart(document.getElementById('c3'),{{type:'doughnut',data:{{labels:{tier_labels},datasets:[{{data:{tier_values},backgroundColor:{tier_labels}.map(t=>tC[t]||'#B4B2A9'),borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}}}}}});
const md={mc_acc};
new Chart(document.getElementById('c4'),{{type:'bar',data:{{labels:Object.keys(md),datasets:[{{data:Object.values(md),backgroundColor:Object.keys(md).map(l=>({{NBA:'#E24B4A',NHL:'#378ADD',EPL:'#1D9E75','La Liga':'#D85A30'}})[l]),borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{min:0,max:100,grid:{{color:gc}},ticks:{{callback:v=>v+'%'}}}},x:{{grid:{{display:false}}}}}}}}}});
const dc=l=>l==='La Liga'?'d-LL':'d-'+l;
let af='ALL';
function rp(){{const tb=document.querySelector('#pt tbody');const f=af==='ALL'?P:P.filter(p=>p.league===af);
tb.innerHTML=f.map(p=>{{const ec=p.edge>0?'ep':(p.edge<-.02?'en':'');const es=(p.edge>0?'+':'')+(p.edge*100).toFixed(1)+'%';
const dp=p.probs.draw!=null?(p.probs.draw*100).toFixed(0)+'%':'—';
return`<tr><td><span class="dot ${{dc(p.league)}}"></span>${{p.league}}</td><td>${{p.home}} vs ${{p.away}}</td>
<td style="font-weight:500">${{p.pick==='DRAW'?'DRAW':p.pick}}</td><td>${{(p.confidence*100).toFixed(0)}}%</td>
<td><span class="p p-${{p.tier}}">${{p.tier}}</span></td><td class="${{ec}}">${{es}}</td>
<td>${{(p.probs.home*100).toFixed(0)}}%</td><td>${{(p.probs.away*100).toFixed(0)}}%</td><td>${{dp}}</td></tr>`}}).join('')}}
const ls=['ALL',...new Set(P.map(p=>p.league))];const fb=document.getElementById('fb');
ls.forEach(l=>{{const b=document.createElement('button');b.className=l==='ALL'?'a':'';b.textContent=l;
b.onclick=()=>{{af=l;fb.querySelectorAll('button').forEach(x=>x.classList.remove('a'));b.classList.add('a');rp()}};fb.appendChild(b)}});rp();
const bb=document.querySelector('#bt tbody');
bb.innerHTML=B.map(d=>{{const m=d.correct?'<span class="ok">&#10003;</span>':'<span class="no">&#10007;</span>';
return`<tr><td>${{m}}</td><td><span class="dot ${{dc(d.league)}}"></span>${{d.league}}</td>
<td>${{d.home}} vs ${{d.away}}</td><td>${{d.score}}</td><td style="font-weight:500">${{d.pick}}</td>
<td>${{d.actual}}</td><td>${{(d.confidence*100).toFixed(0)}}%</td><td><span class="p p-${{d.tier}}">${{d.tier}}</span></td></tr>`}}).join('');
</script></body></html>"""
    return html

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    bt_pure, bt_mkt, mc, predictions = None, None, None, None

    print("="*70)
    print("MULTI-LEAGUE PREDICTION ENGINE — BACKTEST REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    print("\n[1] BACKTEST ON REAL RESULTS (pure model, no market)")
    print("-"*50)
    bt_pure = backtest_on_results(RECENT_RESULTS, use_market=False)
    print(f"Overall: {bt_pure['overall']['correct']}/{bt_pure['overall']['total']} = {bt_pure['overall']['accuracy']*100:.1f}%")
    for lg, d in bt_pure["by_league"].items():
        print(f"\n  {lg}: {d['correct']}/{d['total']} = {d['accuracy']*100:.1f}%")
        for x in d["details"]:
            mark = "OK" if x["correct"] else "XX"
            print(f"    [{mark}] {x['home'][:18]:>18} vs {x['away'][:18]:<18} | {x['score']} | Pick: {x['pick'][:18]:<18} | {x['confidence']*100:.0f}% {x['tier']}")

    print("\n\n[2] BACKTEST WITH SYNTHETIC MARKET BLEND")
    print("-"*50)
    bt_mkt = backtest_on_results(RECENT_RESULTS, use_market=True)
    print(f"Overall: {bt_mkt['overall']['correct']}/{bt_mkt['overall']['total']} = {bt_mkt['overall']['accuracy']*100:.1f}%")
    for lg, d in bt_mkt["by_league"].items():
        print(f"  {lg}: {d['correct']}/{d['total']} = {d['accuracy']*100:.1f}%")

    print("\n\n[3] MONTE CARLO SIMULATION (2000 matchups)")
    print("-"*50)
    mc = monte_carlo_simulation(2000)
    print(f"Simulated {mc['n_sims']} matchups")
    for lg, d in mc["league_accuracy"].items():
        print(f"  {lg}: {d['correct']}/{d['total']} = {d['accuracy']*100:.1f}%")
    print("\n  Calibration:")
    for c in mc["calibration"]:
        print(f"    {c['bucket']*100:5.0f}%  pred={c['predicted']*100:5.1f}%  actual={c['actual']*100:5.1f}%  n={c['count']}")

    print("\n\n[4] LIVE PREDICTIONS")
    print("-"*50)
    predictions = []
    for g in UPCOMING_GAMES:
        predictions.append(predict_game(g, use_market=True))
    predictions.sort(key=lambda p: -p["confidence"])
    for p in predictions:
        es = f"+{p['edge']*100:.1f}%" if p['edge']>0 else f"{p['edge']*100:.1f}%"
        print(f"  [{p['league']:>7}] {p['home'][:20]:>20} vs {p['away'][:20]:<20} -> {p['pick'][:20]:<20} | {p['confidence']*100:.0f}% {p['tier']:<8} | Edge: {es}")

    print("\n\nGenerating HTML dashboard...")
    html = generate_dashboard(bt_pure, bt_mkt, mc, predictions)

    import os
    # Write to _site/ for GitHub Pages, fallback to local
    site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_site")
    os.makedirs(site_dir, exist_ok=True)
    out = os.path.join(site_dir, "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"Dashboard saved to: {out}")
