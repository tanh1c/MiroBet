"""
Polymarket Odds Fetcher
Public API - no auth required for reads
"""
import os
import json
import time
import requests
from typing import Dict, Any, List, Optional

from .mirobet_config import MiroBetConfig


class PolymarketFetcher:
    """Fetches NBA odds from Polymarket CLOB public API"""

    BASE_URL = "https://clob.p Polymarket.com"
    CACHE_TTL = 300  # 5 minutes

    def __init__(self, cache_dir: str = None, cache_ttl: int = None):
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            try:
                self.cache_dir = MiroBetConfig.POLYMARKET_CACHE_DIR
            except Exception:
                self.cache_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'data', 'polymarket_cache'
                )
        self.cache_ttl = cache_ttl or self.CACHE_TTL
        os.makedirs(self.cache_dir, exist_ok=True)

    # ─────────────────────────────────────────────
    # NBA Markets
    # ─────────────────────────────────────────────

    def get_nba_markets(self) -> List[Dict[str, Any]]:
        """Fetch current NBA betting markets from Polymarket"""
        cache_key = "nba_markets"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # Polymarket CLOB markets API
            response = requests.get(
                f"{self.BASE_URL}/markets",
                params={
                    "category": "sports",
                    "active": "true",
                    "limit": 100
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            markets = data.get('markets', [])
            self._set_cache(cache_key, markets)
            return markets
        except Exception:
            return []

    def get_game_markets(self, home_team: str, away_team: str) -> Optional[Dict[str, Any]]:
        """Get Polymarket market for a specific game"""
        markets = self.get_nba_markets()
        search_terms = [home_team.lower(), away_team.lower()]
        for market in markets:
            question = market.get('question', '').lower()
            if all(term in question for term in search_terms):
                return market
        return None

    # ─────────────────────────────────────────────
    # Implied Probabilities (Moneyline)
    # ─────────────────────────────────────────────

    def get_implied_probability(self, home_team: str, away_team: str = None) -> Dict[str, float]:
        """
        Convert Polymarket prices to implied probabilities.
        Polymarket prices are already probabilities (0-1 scale).
        Price $0.40 = 40% implied probability.
        """
        if away_team:
            market = self.get_game_markets(home_team, away_team)
        else:
            market = self.get_game_markets(home_team, "vs")

        if market:
            outcomes = market.get('outcomes', [])
            prices = market.get('outcomePrices', [])
            if len(outcomes) >= 2 and len(prices) >= 2:
                return {
                    'home_win': float(prices[0]),
                    'away_win': float(prices[1]),
                    'market_id': market.get('id', '')
                }

        return self._mock_odds(home_team)

    def _mock_odds(self, home_team: str) -> Dict[str, float]:
        """Return mock odds when API unavailable"""
        import hashlib
        seed = int(hashlib.md5(home_team.encode()).hexdigest()[:8], 16)
        home_prob = 0.45 + (seed % 30) / 100
        return {
            'home_win': round(home_prob, 4),
            'away_win': round(1 - home_prob, 4),
            'market_id': 'mock'
        }

    # ─────────────────────────────────────────────
    # Spread & Over/Under
    # ─────────────────────────────────────────────

    def get_spread_and_total(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Get spread and over/under from market data.
        Note: Polymarket is binary markets; for spread/O/U use a sportsbook API.
        """
        return {
            'spread': -4.5,
            'over_under': 225.5,
            'home_spread_price': 1.91,
            'away_spread_price': 1.91,
            'over_price': 1.91,
            'under_price': 1.91,
            'note': 'Defaults - replace with real sportsbook API for spread/O/U'
        }

    def decimal_from_american(self, american: float) -> float:
        """Convert American odds to decimal"""
        if american > 0:
            return 1 + (american / 100)
        return 1 + (100 / abs(american))

    def american_from_decimal(self, decimal: float) -> float:
        """Convert decimal to American odds"""
        if decimal >= 2.0:
            return (decimal - 1) * 100
        return -100 / (decimal - 1)

    # ─────────────────────────────────────────────
    # Cache management
    # ─────────────────────────────────────────────

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def _get_cache(self, key: str) -> Optional[Any]:
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        mtime = os.path.getmtime(path)
        if time.time() - mtime > self.cache_ttl:
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _set_cache(self, key: str, data: Any):
        path = self._cache_path(key)
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def clear_cache(self):
        """Clear all cached data"""
        for filename in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(path):
                os.remove(path)
