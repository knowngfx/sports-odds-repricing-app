"""
Sports Odds Repricing Signal App - MVP
=======================================
Backend: FastAPI
Data:    ESPN public API (no key required)
Odds:    Mock dataset [CLEARLY LABELLED AS MOCK DATA]
Signal:  "Favorite Undervalued" flag

Favorite Undervalued Rule:
  A game is flagged when the higher-ranked team (by win%) has odds that
  imply a LOWER win probability than their lower-ranked opponent.
  i.e. the market is pricing the better team as an underdog -- a potential
  mispricing signal worth investigating.
"""

import random
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

app = FastAPI(title="Sports Odds Repricing Signal App", version="1.0.0")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_STANDINGS  = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?season=2025"

# Mock odds pool: American odds format
# Negative = favorite, Positive = underdog
# [MOCK DATA - clearly labelled, not from a live odds provider]
MOCK_ODDS_FAVORITES  = [-130, -145, -160, -175, -120, -200, -115, -140, -110, -165]
MOCK_ODDS_UNDERDOGS  = [+110, +125, +140, +155, +100, +170, +105, +120, +100, +145]


# ---------------------------------------------------------------------------
# Helper: American odds -> implied win probability
# ---------------------------------------------------------------------------
def american_to_implied_prob(odds: int) -> float:
    """
    Convert American odds to raw implied probability (no vig removal).
    Negative odds (favorite): prob = abs(odds) / (abs(odds) + 100)
    Positive odds (underdog):  prob = 100 / (odds + 100)
    """
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


# ---------------------------------------------------------------------------
# Helper: Fetch standings - returns dict {team_id: win_pct}
# ---------------------------------------------------------------------------
async def fetch_standings() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(ESPN_STANDINGS)
        resp.raise_for_status()
        data = resp.json()

    standings = {}
    for group in data.get("children", []):
        for entry in group.get("standings", {}).get("entries", []):
            team_id = entry["team"]["id"]
            stats   = {s["name"]: s.get("value", 0.0) for s in entry.get("stats", [])}
            win_pct = stats.get("winPercent", 0.0)
            wins    = int(stats.get("wins", 0))
            losses  = int(stats.get("losses", 0))
            standings[team_id] = {
                "win_pct": round(win_pct, 4),
                "wins":    wins,
                "losses":  losses,
                "record":  f"{wins}-{losses}",
            }
    return standings


# ---------------------------------------------------------------------------
# Helper: Fetch today's NBA games from ESPN scoreboard
# ---------------------------------------------------------------------------
async def fetch_games(standings: dict) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(ESPN_SCOREBOARD)
        resp.raise_for_status()
        data = resp.json()

    games = []
    random.seed(42)  # reproducible mock odds for the same game slate

    for event in data.get("events", []):
        comp        = event["competitions"][0]
        competitors = comp["competitors"]

        if len(competitors) < 2:
            continue

        # Identify home and away
        home = next((c for c in competitors if c["homeAway"] == "home"), competitors[0])
        away = next((c for c in competitors if c["homeAway"] == "away"), competitors[1])

        home_id   = home["team"]["id"]
        away_id   = away["team"]["id"]
        home_info = standings.get(home_id, {"win_pct": 0.0, "record": "N/A", "wins": 0, "losses": 0})
        away_info = standings.get(away_id, {"win_pct": 0.0, "record": "N/A", "wins": 0, "losses": 0})

        # Determine higher/lower ranked by win%
        # (in case of tie, home team treated as higher-ranked)
        home_is_better = home_info["win_pct"] >= away_info["win_pct"]
        better_team    = home if home_is_better else away
        worse_team     = away if home_is_better else home
        better_info    = home_info if home_is_better else away_info
        worse_info     = away_info if home_is_better else home_info

        # ---------------------------------------------------------------
        # [MOCK DATA] Assign American odds
        # We intentionally create some mispriced games for demonstration.
        # In ~30% of games the "better" team is given underdog odds.
        # ---------------------------------------------------------------
        idx = random.randint(0, len(MOCK_ODDS_FAVORITES) - 1)

        if random.random() < 0.35:
            # Mispriced: better team gets underdog odds
            better_odds = MOCK_ODDS_UNDERDOGS[idx]
            worse_odds  = MOCK_ODDS_FAVORITES[idx]
        else:
            # Normal: better team gets favorite odds
            better_odds = MOCK_ODDS_FAVORITES[idx]
            worse_odds  = MOCK_ODDS_UNDERDOGS[idx]

        # Assign back to home/away
        home_odds = better_odds if home_is_better else worse_odds
        away_odds = worse_odds  if home_is_better else better_odds

        home_implied = round(american_to_implied_prob(home_odds), 4)
        away_implied = round(american_to_implied_prob(away_odds), 4)

        # ---------------------------------------------------------------
        # Favorite Undervalued Flag
        # Flag if the higher-ranked team's implied prob < lower-ranked
        # ---------------------------------------------------------------
        better_implied = home_implied if home_is_better else away_implied
        worse_implied  = away_implied if home_is_better else home_implied
        is_flagged     = better_implied < worse_implied

        games.append({
            "game_id":       event["id"],
            "game_time_utc": event["date"],
            "status":        event.get("status", {}).get("type", {}).get("description", "Scheduled"),
            "home": {
                "team_id":        home_id,
                "name":           home["team"]["displayName"],
                "abbreviation":   home["team"]["abbreviation"],
                "logo":           home["team"].get("logo", ""),
                "record":         home_info["record"],
                "win_pct":        home_info["win_pct"],
                "odds_american":  home_odds,
                "implied_prob":   home_implied,
            },
            "away": {
                "team_id":        away_id,
                "name":           away["team"]["displayName"],
                "abbreviation":   away["team"]["abbreviation"],
                "logo":           away["team"].get("logo", ""),
                "record":         away_info["record"],
                "win_pct":        away_info["win_pct"],
                "odds_american":  away_odds,
                "implied_prob":   away_implied,
            },
            "higher_ranked_team": better_team["team"]["displayName"],
            "higher_ranked_win_pct": better_info["win_pct"],
            "higher_ranked_implied_prob": better_implied,
            "lower_ranked_implied_prob":  worse_implied,
            "favorite_undervalued": is_flagged,
            "odds_source": "MOCK DATA - not from a live odds provider",
        })

    return games


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/games")
async def get_games():
    """
    Returns today's NBA games with mock odds and Favorite Undervalued flags.
    Odds are clearly labelled as mock data.
    """
    try:
        standings = await fetch_standings()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch standings: {str(e)}")

    try:
        games = await fetch_games(standings)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch games: {str(e)}")

    flagged_count = sum(1 for g in games if g["favorite_undervalued"])

    return {
        "date":            "Today",
        "league":          "NBA",
        "total_games":     len(games),
        "flagged_games":   flagged_count,
        "odds_disclaimer": "All odds are MOCK DATA generated for demonstration purposes only. Not from a live odds provider.",
        "ranking_source":  "ESPN NBA Standings 2024-25 season (win percentage)",
        "games":           games,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Sports Odds Repricing Signal App", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")
