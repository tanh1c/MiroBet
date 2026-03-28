# MiroBet — Swarm Intelligence Sports Betting Engine

## Design Document v1.0 | Date: 2026-03-28

---

## 1. Overview

**Project name:** MiroBet
**Type:** MVP — Personal Prototype
**Core idea:** Leverage MiroFish swarm intelligence to simulate thousands of AI agents that analyze NBA game data and generate consensus predictions across Moneyline, Spread, and Over/Under bet types. Compare consensus against Polymarket odds to find actionable edges.
**Methodology:** Backtest 2-3 seasons offline → Paper trade live if edge found
**Target user:** Single user (personal experimentation)

---

## 2. Goals & Success Criteria

| Phase | Criteria | Metric |
|-------|----------|--------|
| Backtest | MiroFish consensus beats Polymarket odds | Edge > 5% consistently |
| Backtest | Positive ROI after vig | ROI > 10% |
| Paper Trade | Positive P&L maintained | ROI > 5% over 30 days |

If backtest does not show consistent edge → pivot or stop.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────┐
│               DATA LAYER (Free)                  │
│  Kaggle NBA Stats (CSV) │ Polymarket API (REST)  │
└────────────┬──────────────────┬──────────────────┘
             │                  │
             ▼                  ▼
┌──────────────────────────────────────────────────┐
│           MIROFISH ENGINE (Backend)              │
│  • 64 agents: Stat Analysts, Form Trackers,     │
│    Insider Bettors, Oddsmakers (16 each)        │
│  • LLM: Groq API (llama-3.3-70b) — free tier    │
│  • Input: player stat vectors + team context     │
│  • Output: consensus probability per bet type    │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│           DECISION LAYER                        │
│  MiroFish consensus % vs Polymarket implied %   │
│  Kelly Criterion threshold filter                │
│  → Signal: BET (with Kelly fraction) / NO BET  │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│           EVALUATION LAYER                       │
│  Phase 1: Backtest offline (2-3 seasons)         │
│  Phase 2: Paper trade live (no real money)      │
└──────────────────────────────────────────────────┘
```

---

## 4. Data Pipeline

### 4a. NBA Stats (Kaggle — Free)

- **Source:** Kaggle NBA stats datasets (player stats, team stats, game logs)
- **Scope:** 2-3 most recent seasons (~246 regular season games)
- **Format:** CSV → SQLite for easy querying
- **Data transformed into 3 vector types:**

| Vector Type | Fields | Purpose |
|-------------|--------|---------|
| Player Stat Vector | pts, reb, ast, eFG%, usage_rate | Individual performance (top 10 per team, across 3 seasons) |
| Team Form Tensor | last 10 games W/L, home/away splits, pace, defensive rating, W/L streak | Recent form |
| Matchup History | H2H records, positional mismatches | Historical edge |

### 4b. Polymarket Odds (Public API — Free)

- **Endpoint:** Polymarket CLOB REST API (public, no auth required for reads)
- **Filter:** NBA game markets only
- **Data used:** Outcome prices → converted to implied probability %
- **Timing:** Pulled before tip-off as the "market consensus" baseline

---

## 5. MiroFish Integration

### 5a. Adaptation from MiroFish Core

| MiroFish (Original) | MiroBet (Adapted) |
|--------------------|-------------------|
| Project | 1 NBA game |
| Task | 3 bet types (ML, Spread, O/U) |
| Agent profiles (software roles) | Agent profiles (sports personas) |
| Ontology (software context) | Ontology (sports betting context) |
| OASIS simulation engine | Retained unchanged |
| ReportAgent output | Consensus % per bet type |

### 5b. Agent Personas (64 agents total)

| Persona | Count | Role Description |
|---------|-------|-----------------|
| Stat Analyst | 16 | Analyzes stat vectors, identifies performance trends |
| Form Tracker | 16 | Monitors recent form, home/away splits, streaks |
| Insider Bettor | 16 | Factors in H2H, matchups, situational angles |
| Oddsmaker | 16 | Estimates spread/O/U based on pace and defense |

### 5c. Consensus Output Format

```json
{
  "game_id": "LAL@BOS-2024-03-15",
  "timestamp": "2024-03-15T18:00:00Z",
  "agents": 64,
  "consensus": {
    "moneyline": {
      "home_win_prob": 0.62,
      "away_win_prob": 0.38,
      "polymarket_implied": 0.40,
      "edge": 0.22
    },
    "spread": {
      "home_cover_prob": 0.55,
      "line": -4.5,
      "polymarket_implied": 0.52,
      "edge": 0.03
    },
    "over_under": {
      "over_prob": 0.48,
      "line": 225.5,
      "polymarket_implied": 0.50,
      "edge": -0.02
    }
  },
  "kelly": {
    "home_ml_fraction": 0.553,
    "home_spread_fraction": 0.0,
    "over_fraction": 0.0
  },
  "signal": "HOME_ML"
}
```

---

## 6. Decision Layer

### 6a. Edge Calculation

```
Edge = MiroFish Consensus % - Polymarket Implied %

Example:
  MiroFish: 62% home win
  Polymarket: 40% implied (2.5 decimal odds)
  Edge = 22 percentage points → ACTIONABLE
```

### 6b. Kelly Criterion

```
f* = (bp - q) / b

Where:
  b = decimal_odds - 1
  p = MiroFish probability
  q = 1 - p

Example:
  b = 1.5, p = 0.62, q = 0.38
  f* = (1.5 × 0.62 - 0.38) / 1.5 = 0.553 → BET 55% of bankroll

Safety filters:
  • Min Kelly fraction to bet: 5% (filter out noise)
  • Max bet per game: 20% of bankroll (volatility cap)
  • NO BET if edge < Kelly minimum threshold
```

---

## 7. Evaluation Layer

### Phase 1: Backtest (Offline)

- **Data:** 2-3 NBA seasons (~246 games)
- **Process:** Run MiroFish simulation for each historical game, compare consensus vs actual result
- **Metrics tracked:**
  - Hit rate (% correct direction per bet type)
  - ROI = (wins - losses) / total bets
  - Average edge = avg(MiroFish% - Implied%)
  - Sharpe ratio (risk-adjusted return)
  - Breakdown by bet type (ML / Spread / O/U)
- **Success threshold to proceed to Phase 2:**
  - Edge > 5% consistently across all seasons
  - ROI > 10% after accounting for vig

### Phase 2: Paper Trade (Live)

- **Data source:** Polymarket API real-time
- **Action:** System recommends bet; user tracks P&L in simulation
- **Monitor:** ROI, win streak, drawdown, edge drift
- **Agents retrained** periodically with new game data

---

## 8. Project Structure

```
mirobet/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── sports.py           # NBA game endpoints
│   │   │   ├── odds.py             # Polymarket API proxy
│   │   │   ├── simulation.py       # MiroFish run trigger
│   │   │   └── prediction.py       # Consensus + Kelly output
│   │   ├── services/
│   │   │   ├── data_fetcher.py     # Kaggle data loader
│   │   │   ├── odds_fetcher.py      # Polymarket API client
│   │   │   ├── vector_builder.py    # Stats → agent input vectors
│   │   │   ├── agent_prompts.py    # Sports-specific agent prompts
│   │   │   └── kelly_filter.py     # Kelly criterion calculator
│   │   ├── models/
│   │   │   ├── game.py             # NBA game model
│   │   │   ├── prediction.py        # Prediction result model
│   │   │   └── portfolio.py         # Paper trade portfolio model
│   │   └── services/               # MiroFish core (retained)
│   │       ├── graph_builder.py
│   │       ├── simulation_manager.py
│   │       ├── report_agent.py
│   │       └── ...
│   └── run.py
├── data/
│   ├── nba_stats/                  # Kaggle CSV files
│   │   ├── player_stats.csv
│   │   ├── team_stats.csv
│   │   └── game_logs.csv
│   ├── polymarket_cache/           # Cached odds responses
│   └── predictions/                # Backtest results JSON
│       ├── backtest_2022-23.json
│       ├── backtest_2023-24.json
│       └── backtest_2024-25.json
├── frontend/                      # Vue 3 + Vite (retain MiroFish UI)
│   ├── src/
│   │   ├── components/
│   │   │   ├── GameSelector.vue
│   │   │   ├── SimulationPanel.vue
│   │   │   ├── PredictionCard.vue
│   │   │   └── BacktestDashboard.vue
│   │   └── views/
│   │       ├── BacktestView.vue
│   │       └── LiveTradeView.vue
│   └── vite.config.js
├── tests/
│   ├── test_data_pipeline.py
│   ├── test_kelly_filter.py
│   └── test_consensus.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 9. Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | Python 3.11+, FastAPI | Leverage MiroFish backend |
| Frontend | Vue 3 + Vite | Leverage MiroFish frontend |
| LLM | Groq API (llama-3.3-70b) | Free tier (~14k req/min) |
| Data | SQLite + Pandas | Local storage for MVP |
| Cache | Local filesystem | No complex DB needed |
| Deployment | Docker + Docker Compose | Inherit MiroFish setup |
| Simulation | OASIS (MiroFish core) | Unchanged |

---

## 10. Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| LLM cost explodes | Token budget per agent (max 500 tokens/input), cache repeated prompts |
| Polymarket rate limit | Exponential backoff, batch requests, cache responses 5 min TTL |
| Overfitting to historical data | 2-3 seasons only (not full history), hold-out validation |
| MiroFish simulation too slow | 64 agents max for MVP, parallelize LLM calls via Groq async |
| Edge disappears over time | Retrain agent prompts periodically, monitor ROI drift |
| LLM API downtime | Retry with backoff, queue requests |

---

## 11. MVP Scope (V1) — In Scope

- ✅ NBA only (no other sports)
- ✅ Pre-game bets only (no live/in-play betting)
- ✅ Backtest + Paper trade (no real money)
- ✅ 64 agents (scale to 256-512 after validation)
- ✅ Kaggle + Polymarket API (free data sources)
- ✅ Local JSON file storage for results
- ✅ Groq LLM API (free tier)

## MVP Scope (V1) — Out of Scope

- ❌ Multi-sport support
- ❌ Real-money betting integration
- ❌ Live/in-play betting
- ❌ Real-time Polymarket order execution
- ❌ User authentication / multi-user
- ❌ Cloud deployment beyond local Docker
- ❌ Production-grade DB (PostgreSQL etc.)

---

## 12. Implementation Phases

### Phase 1: Data Layer (Week 1)
- Download Kaggle NBA datasets (3 seasons)
- Build data loader + SQLite schema
- Integrate Polymarket API client
- Build vector builder (player stats → agent inputs)

### Phase 2: MiroFish Integration (Week 2)
- Fork/extend MiroFish backend
- Create sports-specific agent prompts
- Adapt graph builder for NBA games
- Adapt ReportAgent to output consensus format

### Phase 3: Decision Layer (Week 2-3)
- Implement Kelly criterion calculator
- Build edge comparison logic
- Add bet sizing filter

### Phase 4: Backtest Engine (Week 3)
- Build backtest runner (iterate all historical games)
- Track and visualize: hit rate, ROI, edge per bet type
- Generate backtest report

### Phase 5: Frontend + Paper Trade (Week 4)
- Build BacktestDashboard view
- Build GameSelector + PredictionCard components
- Build LiveTradeView for paper trading
- Connect frontend to backend APIs

---

*Design approved: 2026-03-28*
