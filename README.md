# Sports Odds Repricing Signal App
### MVP Prototype - Technical Assessment Submission

---

## What This Does

A web app that pulls today's NBA games from ESPN's public API, layers on a
mock odds dataset, and flags any game where the market appears to be
mispricing the better team.

**The Signal - "Favorite Undervalued":**
A game is flagged when the higher-ranked team (by 2024-25 win percentage)
has odds that imply a *lower* win probability than their lower-ranked opponent.
In plain terms: the market is pricing the better team as an underdog, which
represents a potential mispricing worth investigating.

---

## Data Sources

| Data | Source | Key Required |
|------|--------|-------------|
| Today's NBA games | ESPN public scoreboard API | No |
| Team rankings | ESPN NBA 2024-25 standings (win%) | No |
| Odds | Mock data (randomly generated) | N/A |

> **Odds Disclaimer:** All odds displayed are mock data generated for
> demonstration purposes only. They do not reflect real betting lines from
> any bookmaker or odds provider.

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, httpx
- **Frontend:** Plain HTML + CSS + Vanilla JS (no build step, no npm)
- **Data:** ESPN public REST API

---

## How to Run

### 1. Clone / download the project

```
cd "04 - Project"
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the server

```bash
uvicorn main:app --reload
```

### 5. Open the app

Open your browser and go to:

```
http://localhost:8000
```

That's it. No API keys, no environment variables, no database.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves the frontend dashboard |
| `GET /api/games` | Returns today's games with odds and flags (JSON) |
| `GET /api/health` | Health check |

---

## Project Structure

```
04 - Project/
├── main.py            # FastAPI backend - data fetching, signal logic
├── requirements.txt   # Python dependencies
├── README.md          # This file
└── static/
    └── index.html     # Frontend dashboard (single file, no build needed)
```

---

## Signal Logic Explained

```
1. Fetch today's NBA games from ESPN scoreboard API
2. Fetch 2024-25 season win% for all 30 NBA teams from ESPN standings
3. For each game:
   a. Identify the higher-ranked team by win%
   b. Assign mock American odds to each team
   c. Convert American odds to implied win probability:
        Favorite (negative): prob = |odds| / (|odds| + 100)
        Underdog (positive): prob = 100 / (odds + 100)
   d. FLAG the game if:
        higher_ranked_team.implied_prob < lower_ranked_team.implied_prob
```

---

## What I Would Build Next (2-Week Sprint)

1. **Real odds integration** - Connect to The Odds API (free tier available)
   to replace mock data with live lines from multiple bookmakers
2. **Line movement tracking** - Store odds snapshots over time to detect
   when lines move against the better team (sharper signal)
3. **Multiple sports** - Extend to NFL and EPL with the same signal logic
4. **Historical backtesting** - Run the Favorite Undervalued flag against
   past seasons to measure how often it actually predicted an upset
5. **Alert system** - Email or Slack notification when a flagged game appears

---

## Assumptions Made

- Team quality is proxied by 2024-25 regular season win percentage. In
  production this would be replaced with a more granular power rating
  (e.g. adjusted net rating, Elo score).
- Odds are mock data. The signal logic is real and correct; only the input
  data is synthetic.
- In a tie on win%, the home team is treated as the higher-ranked team
  (marginal assumption, clearly noted in code).

---

*Submitted for technical assessment. Built with ESPN public API + FastAPI + plain HTML/JS.*
