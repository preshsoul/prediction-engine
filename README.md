# Multi-League Prediction Engine

Sports prediction dashboard covering NBA, NHL, EPL, and La Liga.  
Elo + form + market-blend models with backtesting and Monte Carlo simulation.

## Live Dashboard

Once deployed, your dashboard is at:  
`https://<your-username>.github.io/<repo-name>/`

## Setup (5 minutes)

### 1. Create the repo

Go to [github.com/new](https://github.com/new) and create a new repository.  
Name it whatever you want (e.g. `prediction-engine`). Make it **public**.

### 2. Push this code

```bash
cd prediction-engine
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 3. Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. That's it — the workflow handles the rest

### 4. First deploy

The workflow runs automatically on push. It also runs **every 6 hours** via cron.  
You can trigger it manually: **Actions** → **Build & Deploy Predictions** → **Run workflow**

## Updating Predictions

Edit the data in `prediction_engine.py`:
- `UPCOMING_GAMES` — the games you want predictions for
- `RECENT_RESULTS` — results for backtesting
- Standings dicts — current league tables

Push your changes and the dashboard rebuilds automatically.

## How It Works

| Component | What it does |
|-----------|-------------|
| `NBAModel` | 60/25/15 market-Elo-form blend, 3.5% home advantage |
| `NHLModel` | 65/25/10 blend, variance compression (no LOCK tier) |
| `SoccerModel` | 55/25/10/10 blend with three-outcome draw modeling |
| Backtest | Runs every result through the model to measure accuracy |
| Monte Carlo | 2000 random matchups to test calibration |
| Dashboard | Static HTML + Chart.js, dark/light mode |

## Cost

**$0.** GitHub Pages is free for public repos. The Actions workflow uses ~30 seconds of compute per run, well within the 2,000 free minutes/month.
