# MiroBet Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a swarm intelligence sports betting MVP using MiroFish consensus voting for NBA predictions (Moneyline, Spread, Over/Under), backed by Kaggle data + Polymarket odds, with backtest + paper trade evaluation.

**Architecture:** Lean consensus-voting architecture — NO Zep, NO OASIS. 64 agents call LLM directly for independent analysis, then aggregate votes. Data stored in SQLite + JSON files. Flask backend (extend MiroFish), Vue 3 frontend.

**Tech Stack:** Python 3.11+, Flask, Vue 3 + Vite, SQLite, Pandas, Groq API (llama-3.3-70b), Docker.

---

## Phase 1: Data Layer

### Task 1: Project scaffold + dependencies

**Files:**
- Create: `MiroFish/backend/app/services/mirobet_config.py`
- Create: `MiroFish/requirements_mirobet.txt`
- Modify: `MiroFish/backend/app/__init__.py` (register new blueprint)
- Create: `MiroFish/backend/app/api/mirobet.py`
- Create: `tests/test_mirobet_config.py`

**Step 1: Create requirements file**

```python
# requirements_mirobet.txt
flask>=3.0.0
flask-cors>=6.0.0
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pandas>=2.0.0
requests>=2.31.0
```

**Step 2: Create config service**

```python
"""
MiroBet configuration
"""
import os
from dotenv import load_dotenv

# Load .env from MiroFish root
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')
if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)

class MiroBetConfig:
    """MiroBet configuration"""
    # LLM config (Groq preferred)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.groq.com/openai/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'llama-3.3-70b-versatile')

    # MiroBet specific
    AGENT_COUNT = int(os.environ.get('MIROBET_AGENT_COUNT', '64'))
    AGENTS_PER_PERSONA = 16  # 4 personas x 16 = 64 agents
    MAX_TOKENS_PER_CALL = 500
    KELLY_MIN_THRESHOLD = 0.05  # 5% minimum Kelly fraction to bet
    KELLY_MAX_FRACTION = 0.20   # 20% max bankroll per bet
    BACKTEST_SEASONS = 3  # 2022-23, 2023-24, 2024-25

    # Data paths
    DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data')
    NBA_STATS_DIR = os.path.join(DATA_DIR, 'nba_stats')
    PREDICTIONS_DIR = os.path.join(DATA_DIR, 'predictions')
    POLYMARKET_CACHE_DIR = os.path.join(DATA_DIR, 'polymarket_cache')
```

**Step 3: Run test**

```bash
cd MiroFish && pip install -r requirements_mirobet.txt
pytest tests/test_mirobet_config.py -v
```

**Expected:** PASS — config loads correctly

**Step 4: Commit**

```bash
git add requirements_mirobet.txt backend/app/services/mirobet_config.py tests/test_mirobet_config.py
git commit -m "feat(mirobet): add MiroBet config and dependencies"
```

---

### Task 2: NBA data loader (Kaggle → SQLite)

**Files:**
- Create: `MiroFish/backend/app/services/nba_data_loader.py`
- Create: `tests/test_nba_data_loader.py`
- Create: `MiroFish/data/nba_stats/` (placeholder)

**Step 1: Write test**

```python
# tests/test_nba_data_loader.py
from app.services.nba_data_loader import NBADataLoader

def test_loader_initializes():
    loader = NBADataLoader()
    assert loader.data_dir.endswith('data/nba_stats')
    assert loader.seasons == ['2022-23', '2023-24', '2024-25']

def test_get_player_vector():
    loader = NBADataLoader()
    vector = loader.get_player_vector("LeBron James", "2023-24")
    assert 'pts' in vector
    assert 'reb' in vector
    assert 'ast' in vector
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_nba_data_loader.py -v
```

**Expected:** FAIL — module doesn't exist yet

**Step 3: Write minimal loader**

```python
"""
NBA Data Loader - Kaggle CSV → SQLite
Handles 3 seasons: 2022-23, 2023-24, 2024-25
"""
import os
import pandas as pd
import sqlite3
from typing import Dict, Any, List, Optional

class NBADataLoader:
    def __init__(self, data_dir: str = None):
        from .mirobet_config import MiroBetConfig
        self.data_dir = data_dir or MiroBetConfig.NBA_STATS_DIR
        self.seasons = ['2022-23', '2023-24', '2024-25']
        os.makedirs(self.data_dir, exist_ok=True)

    def get_player_vector(self, player_name: str, season: str) -> Dict[str, float]:
        """Return stat vector for a player: pts, reb, ast, eFG%, usage_rate"""
        return {
            'pts': 25.0,
            'reb': 7.5,
            'ast': 7.0,
            'efg_pct': 0.55,
            'usage_rate': 0.30
        }

    def get_team_form_tensor(self, team_id: str, season: str) -> Dict[str, Any]:
        """Return team form: last 10 games, home/away splits, pace, defensive rating"""
        return {
            'last_10_wins': 7,
            'home_record': '15-5',
            'away_record': '10-10',
            'pace': 102.5,
            'defensive_rating': 108.2,
            'streak': 'W3'
        }

    def get_matchup_history(self, team_a: str, team_b: str) -> Dict[str, Any]:
        """Return H2H records, positional mismatches"""
        return {
            'team_a_wins': 2,
            'team_b_wins': 1,
            'avg_margin_a': 4.2,
            'avg_margin_b': -4.2,
            'last_3_meetings': ['A+6', 'B+3', 'A+2']
        }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_nba_data_loader.py -v
```

**Expected:** PASS

**Step 5: Commit**

```bash
git add backend/app/services/nba_data_loader.py tests/test_nba_data_loader.py
git commit -m "feat(mirobet): add NBA data loader skeleton"
```

---

### Task 3: Polymarket odds fetcher

**Files:**
- Create: `MiroFish/backend/app/services/odds_fetcher.py`
- Create: `tests/test_odds_fetcher.py`

**Step 1: Write test**

```python
# tests/test_odds_fetcher.py
from app.services.odds_fetcher import PolymarketFetcher

def test_fetcher_initializes():
    fetcher = PolymarketFetcher()
    assert fetcher.base_url == "https://clob.p Polymarket.com"
```

**Step 2: Run test — verify FAIL**

**Step 3: Write fetcher**

```python
"""
Polymarket Odds Fetcher
Public API - no auth required for reads
"""
import time
import requests
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..services.mirobet_config import MiroBetConfig

class PolymarketFetcher:
    BASE_URL = "https://clob.p Polymarket.com"

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl = cache_ttl_seconds
        self.cache_dir = MiroBetConfig.POLYMARKET_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_nba_markets(self) -> List[Dict[str, Any]]:
        """Fetch current NBA betting markets from Polymarket"""
        # TODO: Replace with actual Polymarket API call
        # Endpoint: GET /markets?cat=nba
        return []

    def get_implied_probability(self, market_id: str) -> Dict[str, float]:
        """Convert Polymarket prices to implied probabilities"""
        # Polymarket is a CLOB - prices are already probabilities
        # Price of $0.40 = 40% implied probability
        return {'home_win': 0.40, 'away_win': 0.60}

    def get_spread_and_total(self, market_id: str) -> Dict[str, Any]:
        """Extract spread and over/under from market data"""
        return {'spread': -4.5, 'over_under': 225.5}
```

**Step 4: Run test — verify PASS**

**Step 5: Commit**

---

## Phase 2: MiroFish Integration (Consensus Engine)

### Task 4: Sports agent prompts

**Files:**
- Create: `MiroFish/backend/app/services/agent_prompts.py`
- Create: `tests/test_agent_prompts.py`

**Step 1: Write prompts module**

```python
"""
MiroBet Agent Prompts
Defines persona-specific prompts for 4 agent types
"""
from typing import Dict

AGENT_PERSONAS = {
    "stat_analyst": {
        "name": "Stat Analyst",
        "count": 16,
        "system_prompt": """You are a statistical analyst specializing in NBA basketball.
You analyze player and team statistics to predict game outcomes.
Focus on: points, rebounds, assists, eFG%, usage rate, PER, win shares.
Output ONLY a probability number between 0.0 and 1.0.""",
        "analysis_prompt": """Analyze these stats for {home_team} vs {away_team}:

HOME TEAM PLAYERS ({home_stats})

AWAY TEAM PLAYERS ({away_stats})

Based purely on statistics, what is the probability that {home_team} wins?
Reply with only a number between 0.0 and 1.0 (e.g., 0.62)"""
    },
    "form_tracker": {
        "name": "Form Tracker",
        "count": 16,
        "system_prompt": """You are a form tracker specializing in NBA momentum analysis.
You analyze recent performance trends, home/away splits, and streaks.
Output ONLY a probability number between 0.0 and 1.0.""",
        "analysis_prompt": """Analyze recent form for {home_team} vs {away_team}:

HOME TEAM FORM ({home_form})

AWAY TEAM FORM ({away_form})

Based on recent momentum and form, what is the probability that {home_team} wins?
Reply with only a number between 0.0 and 1.0 (e.g., 0.62)"""
    },
    "insider_bettor": {
        "name": "Insider Bettor",
        "count": 16,
        "system_prompt": """You are an insider bettor with knowledge of NBA matchups.
You analyze head-to-head records, positional mismatches, and situational edges.
Output ONLY a probability number between 0.0 and 1.0.""",
        "analysis_prompt": """Analyze matchup history for {home_team} vs {away_team}:

H2H RECORD ({h2h})

Based on matchup history and situational factors, what is the probability that {home_team} wins?
Reply with only a number between 0.0 and 1.0 (e.g., 0.62)"""
    },
    "oddsmaker": {
        "name": "Oddsmaker",
        "count": 16,
        "system_prompt": """You are an oddsmaker specializing in NBA spreads and totals.
You estimate point spreads and over/under lines based on team strengths.
Output ONLY a number between 0.0 and 1.0 or a decimal line."""
    }
}

def build_agent_prompt(persona: str, game_context: Dict) -> Dict[str, str]:
    """Build system + user prompts for a given agent persona"""
    if persona not in AGENT_PERSONAS:
        raise ValueError(f"Unknown persona: {persona}")

    p = AGENT_PERSONAS[persona]
    return {
        "system": p["system_prompt"],
        "user": p["analysis_prompt"].format(**game_context)
    }
```

**Step 2: Run test, write implementation, commit**

---

### Task 5: Consensus aggregator

**Files:**
- Create: `MiroFish/backend/app/services/consensus_engine.py`
- Create: `tests/test_consensus_engine.py`

**Step 1: Write test**

```python
# tests/test_consensus_engine.py
from app.services.consensus_engine import ConsensusAggregator

def test_simple_average():
    votes = [0.62, 0.58, 0.65, 0.60, 0.63]
    agg = ConsensusAggregator(votes)
    assert abs(agg.get_consensus() - 0.616) < 0.01

def test_outlier_removal():
    votes = [0.62, 0.58, 0.99, 0.60, 0.63]  # 0.99 is outlier
    agg = ConsensusAggregator(votes, remove_outliers=True)
    consensus = agg.get_consensus()
    assert consensus < 0.70  # outlier removed, consensus lower
```

**Step 2: Run test — FAIL**

**Step 3: Write implementation**

```python
"""
Consensus Aggregator
Aggregates agent votes into a single consensus probability
"""
import statistics
from typing import List

class ConsensusAggregator:
    def __init__(self, votes: List[float], remove_outliers: bool = True):
        self.votes = votes
        self.remove_outliers = remove_outliers

    def _remove_outliers(self, votes: List[float]) -> List[float]:
        if len(votes) < 4:
            return votes
        mean = statistics.mean(votes)
        stdev = statistics.stdev(votes) if len(votes) > 1 else 0
        if stdev == 0:
            return votes
        return [v for v in votes if abs(v - mean) < 2 * stdev]

    def get_consensus(self) -> float:
        votes = self.votes
        if self.remove_outliers:
            votes = self._remove_outliers(votes)
        return round(statistics.mean(votes), 4)

    def get_confidence(self) -> float:
        """Return confidence score based on agreement among agents"""
        if len(self.votes) < 2:
            return 0.0
        stdev = statistics.stdev(self.votes)
        confidence = max(0, 1 - (stdev * 2))  # Lower stdev = higher confidence
        return round(confidence, 4)
```

**Step 4: Run test — PASS**

**Step 5: Commit**

---

### Task 6: Kelly criterion filter

**Files:**
- Create: `MiroFish/backend/app/services/kelly_filter.py`
- Create: `tests/test_kelly_filter.py`

**Step 1: Write test**

```python
# tests/test_kelly_filter.py
from app.services.kelly_filter import KellyFilter

def test_kelly_basic():
    """MiroFish 62%, odds 2.5x"""
    kf = KellyFilter()
    fraction = kf.calculate_kelly(consensus=0.62, decimal_odds=2.5)
    assert 0.5 < fraction < 0.6  # ~55%

def test_kelly_below_threshold():
    """MiroFish 52%, odds 2.0x — should return 0 (no bet)"""
    kf = KellyFilter()
    fraction = kf.calculate_kelly(consensus=0.52, decimal_odds=2.0)
    assert fraction < kf.min_threshold  # No bet

def test_should_bet():
    kf = KellyFilter()
    assert kf.should_bet(0.55, 2.5) == True
    assert kf.should_bet(0.51, 2.0) == False
```

**Step 2: Run test — FAIL**

**Step 3: Write implementation**

```python
"""
Kelly Criterion Filter
Determines bet sizing based on edge between MiroFish consensus and Polymarket odds
"""
from ..services.mirobet_config import MiroBetConfig

class KellyFilter:
    def __init__(self, min_threshold: float = None, max_fraction: float = None):
        self.min_threshold = min_threshold or MiroBetConfig.KELLY_MIN_THRESHOLD
        self.max_fraction = max_fraction or MiroBetConfig.KELLY_MAX_FRACTION

    def calculate_kelly(self, consensus: float, decimal_odds: float) -> float:
        """
        Calculate Kelly fraction: f* = (bp - q) / b
        b = decimal_odds - 1
        p = MiroFish probability
        q = 1 - p
        """
        b = decimal_odds - 1
        p = consensus
        q = 1 - p

        if b <= 0:
            return 0.0

        kelly = (b * p - q) / b

        # Apply constraints
        kelly = max(0.0, min(kelly, self.max_fraction))
        return round(kelly, 4)

    def should_bet(self, consensus: float, decimal_odds: float) -> bool:
        """Return True if Kelly fraction exceeds minimum threshold"""
        fraction = self.calculate_kelly(consensus, decimal_odds)
        return fraction >= self.min_threshold

    def get_bet_decision(self, consensus: float, decimal_odds: float) -> dict:
        """Return full bet decision"""
        kelly_fraction = self.calculate_kelly(consensus, decimal_odds)
        return {
            'consensus': consensus,
            'decimal_odds': decimal_odds,
            'implied_probability': round(1 / decimal_odds, 4),
            'edge': round(consensus - (1 / decimal_odds), 4),
            'kelly_fraction': kelly_fraction,
            'should_bet': kelly_fraction >= self.min_threshold,
            'reason': self._get_reason(kelly_fraction)
        }

    def _get_reason(self, kelly_fraction: float) -> str:
        if kelly_fraction >= self.min_threshold:
            return f"Edge found (Kelly={kelly_fraction:.1%})"
        return f"No edge (Kelly={kelly_fraction:.1%} < {self.min_threshold:.1%})"
```

**Step 4: Run test — PASS**

**Step 5: Commit**

---

### Task 7: MiroBet API endpoints

**Files:**
- Create: `MiroFish/backend/app/api/mirobet.py`
- Modify: `MiroFish/backend/app/__init__.py`

**Step 1: Write API blueprint**

```python
"""
MiroBet API Routes
"""
from flask import Blueprint, request, jsonify
import traceback
from ..services.mirobet_config import MiroBetConfig
from ..services.nba_data_loader import NBADataLoader
from ..services.odds_fetcher import PolymarketFetcher
from ..services.agent_prompts import build_agent_prompt
from ..services.consensus_engine import ConsensusAggregator
from ..services.kelly_filter import KellyFilter
from ..services.llm_client import LLMClient

mirobet_bp = Blueprint('mirobet', __name__)


@mirobet_bp.route('/predict', methods=['POST'])
def predict_game():
    """
    Run MiroFish consensus for a single NBA game

    Body:
        {
            "home_team": "LAL",
            "away_team": "BOS",
            "season": "2024-25",
            "game_date": "2025-03-15"
        }

    Returns:
        {
            "success": true,
            "data": {
                "game_id": "LAL@BOS-2025-03-15",
                "consensus": {
                    "moneyline": { "home_win": 0.62, "polymarket_implied": 0.40, "edge": 0.22 },
                    "spread": { "home_cover": 0.55, "line": -4.5, "edge": 0.03 },
                    "over_under": { "over": 0.48, "line": 225.5, "edge": -0.02 }
                },
                "kelly": {
                    "home_ml": { "fraction": 0.553, "should_bet": true, "reason": "Edge found" }
                },
                "confidence": 0.78
            }
        }
    """
    try:
        data = request.get_json() or {}
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        season = data.get('season', '2024-25')

        if not home_team or not away_team:
            return jsonify({"success": False, "error": "home_team and away_team required"}), 400

        # Step 1: Gather data
        loader = NBADataLoader()
        odds_fetcher = PolymarketFetcher()

        home_stats = loader.get_team_stats(home_team, season)
        away_stats = loader.get_team_stats(away_team, season)
        home_form = loader.get_team_form(home_team, season)
        away_form = loader.get_team_form(away_team, season)
        h2h = loader.get_matchup_history(home_team, away_team)
        odds = odds_fetcher.get_implied_probability(f"{home_team}@ {away_team}")

        # Step 2: Run agents (simplified — real implementation in Task 8)
        consensus_ml = run_agents_vote("stat_analyst", home_stats, away_stats, home_form, away_form, h2h)
        consensus_spread = run_agents_vote("form_tracker", home_stats, away_stats, home_form, away_form, h2h)
        consensus_ou = run_agents_vote("oddsmaker", home_stats, away_stats, home_form, away_form, h2h)

        # Step 3: Kelly filter
        kelly = KellyFilter()
        decision_ml = kelly.get_bet_decision(consensus_ml, 1 / odds.get('home_win', 0.5))

        return jsonify({
            "success": True,
            "data": {
                "game_id": f"{home_team}@{away_team}",
                "consensus": {
                    "moneyline": {
                        "home_win": consensus_ml,
                        "polymarket_implied": odds.get('home_win', 0.5),
                        "edge": round(consensus_ml - odds.get('home_win', 0.5), 4)
                    }
                },
                "kelly": {
                    "home_ml": decision_ml
                }
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


def run_agents_vote(persona: str, home_stats, away_stats, home_form, away_form, h2h) -> float:
    """Run agents for a persona type and return consensus"""
    # TODO: Implement actual LLM calls with async parallelization
    import statistics
    # Placeholder: return random consensus between 0.45-0.65
    votes = [0.50 + (hash(f"{persona}{i}") % 20) / 100 for i in range(16)]
    return round(statistics.mean(votes), 4)
```

**Step 2: Register blueprint in `__init__.py`**

```python
# In MiroFish/backend/app/__init__.py, add:
from .api import mirobet_bp
app.register_blueprint(mirobet_bp, url_prefix='/api/mirobet')
```

**Step 3: Test endpoint**

```bash
curl -X POST http://localhost:5001/api/mirobet/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team": "LAL", "away_team": "BOS", "season": "2024-25"}'
```

**Step 4: Commit**

---

## Phase 3: Backtest Engine

### Task 8: Full agent voting with Groq LLM

**Files:**
- Modify: `MiroFish/backend/app/api/mirobet.py`
- Create: `MiroFish/backend/app/services/agent_voter.py`
- Create: `tests/test_agent_voter.py`

**Step 1: Write agent voter**

```python
"""
Agent Voter - Runs 64 agents in parallel via Groq API
"""
import asyncio
import os
from typing import List, Dict, Any
from ..services.llm_client import LLMClient
from ..services.agent_prompts import AGENT_PERSONAS, build_agent_prompt
from ..services.mirobet_config import MiroBetConfig

class AgentVoter:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.llm = LLMClient()
        self.agent_count = MiroBetConfig.AGENT_COUNT
        self.personas = list(AGENT_PERSONAS.keys())

    async def run_vote(self, persona: str, game_context: Dict) -> List[float]:
        """Run all agents of a persona type and collect votes"""
        persona_config = AGENT_PERSONAS[persona]
        count = persona_config['count']
        prompts = build_agent_prompt(persona, game_context)

        tasks = []
        for i in range(count):
            task = self._call_agent(prompts['system'], prompts['user'], i)
            tasks.append(task)

        votes = await asyncio.gather(*tasks, return_exceptions=True)
        valid_votes = [v for v in votes if isinstance(v, float) and 0.0 <= v <= 1.0]
        return valid_votes

    async def _call_agent(self, system_prompt: str, user_prompt: str, agent_id: int) -> float:
        """Call LLM for a single agent"""
        response = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=MiroBetConfig.MAX_TOKENS_PER_CALL
        )

        # Parse response to float
        try:
            # Try to extract number from response
            import re
            numbers = re.findall(r'0\.\d+', response)
            if numbers:
                return float(numbers[0])
            return 0.5  # Default if parsing fails
        except:
            return 0.5

    async def run_all_personas(self, game_context: Dict) -> Dict[str, float]:
        """Run all 4 personas and aggregate results"""
        tasks = [self.run_vote(p, game_context) for p in self.personas]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        consensus = {}
        for persona, result in zip(self.personas, results):
            if isinstance(result, list) and len(result) > 0:
                consensus[persona] = sum(result) / len(result)
            else:
                consensus[persona] = 0.5

        return consensus
```

**Step 2: Update API to use AgentVoter**

**Step 3: Run test, commit**

---

### Task 9: Backtest runner

**Files:**
- Create: `MiroFish/backend/app/services/backtest_runner.py`
- Create: `tests/test_backtest_runner.py`

**Step 1: Write backtest runner**

```python
"""
Backtest Runner
Runs MiroFish consensus across 2-3 seasons of historical games
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from .nba_data_loader import NBADataLoader
from .odds_fetcher import PolymarketFetcher
from .agent_voter import AgentVoter
from .consensus_engine import ConsensusAggregator
from .kelly_filter import KellyFilter
from .mirobet_config import MiroBetConfig

class BacktestRunner:
    def __init__(self):
        self.loader = NBADataLoader()
        self.odds_fetcher = PolymarketFetcher()
        self.agent_voter = AgentVoter()
        self.kelly = KellyFilter()

    def run_season(self, season: str) -> Dict[str, Any]:
        """
        Run backtest for all games in a season
        Returns summary metrics
        """
        results = []
        games = self.loader.get_season_games(season)  # TODO: implement

        for game in games:
            result = self.run_single_game(game, season)
            results.append(result)

        return self._summarize(results)

    def run_single_game(self, game: Dict, season: str) -> Dict[str, Any]:
        """Run consensus + Kelly for a single game"""
        game_context = self.loader.build_game_context(game, season)
        consensus = asyncio.run(self.agent_voter.run_all_personas(game_context))

        # Aggregate consensus
        all_votes = list(consensus.values())
        agg = ConsensusAggregator(all_votes)
        final_consensus = agg.get_consensus()

        # Get Polymarket odds (from cache for historical)
        odds = self.odds_fetcher.get_historical_odds(game['market_id'])

        # Kelly decision
        kelly_decision = self.kelly.get_bet_decision(final_consensus, odds['decimal'])

        return {
            'game_id': game['game_id'],
            'actual_result': game['home_win'],  # 1 or 0
            'consensus': final_consensus,
            'kelly_decision': kelly_decision,
            'bet_made': kelly_decision['should_bet'],
            'bet_correct': kelly_decision['should_bet'] and kelly_decision['consensus'] > 0.5 == game['home_win']
        }

    def _summarize(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate backtest metrics"""
        total = len(results)
        bets = [r for r in results if r['bet_made']]
        correct = [r for r in results if r['bet_correct']]

        return {
            'total_games': total,
            'total_bets': len(bets),
            'correct_bets': len(correct),
            'win_rate': len(correct) / len(bets) if bets else 0,
            'roi': self._calculate_roi(bets, results),
            'avg_edge': sum(r['kelly_decision']['edge'] for r in bets) / len(bets) if bets else 0
        }

    def _calculate_roi(self, bets, results) -> float:
        """Calculate ROI"""
        # TODO: implement properly with Kelly fractions
        return 0.0
```

**Step 2: Write test, run, commit**

---

## Phase 4: Frontend (Vue 3)

### Task 10: MiroBet frontend pages

**Files:**
- Create: `MiroFish/frontend/src/views/MiroBetView.vue`
- Create: `MiroFish/frontend/src/components/PredictionCard.vue`
- Create: `MiroFish/frontend/src/components/BacktestDashboard.vue`
- Create: `MiroFish/frontend/src/api/mirobet.js`

**Step 1: Create API client**

```javascript
// src/api/mirobet.js
import api from './index'

export const mirobetApi = {
  predictGame(data) {
    return api.post('/api/mirobet/predict', data)
  },

  runBacktest(season) {
    return api.post('/api/mirobet/backtest', { season })
  },

  getBacktestResults(season) {
    return api.get(`/api/mirobet/backtest/${season}`)
  }
}
```

**Step 2: Create PredictionCard component**

```vue
<template>
  <div class="prediction-card">
    <h3>{{ homeTeam }} vs {{ awayTeam }}</h3>
    <div class="consensus-section">
      <div class="bet-type">
        <span class="label">Moneyline</span>
        <span class="value">{{ consensus.moneyline?.home_win || 0 }}%</span>
        <span class="edge" :class="edgeClass">
          Edge: {{ consensus.moneyline?.edge > 0 ? '+' : '' }}{{ consensus.moneyline?.edge || 0 }}
        </span>
      </div>
      <div v-if="kelly.should_bet" class="bet-signal">
        BET {{ (kelly.kelly_fraction * 100).toFixed(0) }}% of bankroll
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  homeTeam: String,
  awayTeam: String,
  consensus: Object,
  kelly: Object
})

const edgeClass = computed(() => {
  const edge = props.consensus?.moneyline?.edge || 0
  return edge > 0.05 ? 'positive' : edge < -0.05 ? 'negative' : 'neutral'
})
</script>
```

**Step 3: Run dev server, test, commit**

---

## Summary of Tasks

| # | Task | Files | Status |
|---|------|-------|--------|
| 1 | Project scaffold + config | 4 | ⬜ |
| 2 | NBA data loader | 3 | ⬜ |
| 3 | Polymarket odds fetcher | 2 | ⬜ |
| 4 | Agent prompts | 2 | ⬜ |
| 5 | Consensus aggregator | 2 | ⬜ |
| 6 | Kelly criterion filter | 2 | ⬜ |
| 7 | MiroBet API endpoints | 2 | ⬜ |
| 8 | Full agent voting (Groq) | 3 | ⬜ |
| 9 | Backtest runner | 2 | ⬜ |
| 10 | Frontend pages | 4 | ⬜ |

**Total: 10 tasks — estimated 2-3 sessions of work**
