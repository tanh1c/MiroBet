"""
Backtest Runner
Runs MiroFish consensus across 2-3 seasons of historical games
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from .nba_data_loader import NBADataLoader
from .odds_fetcher import PolymarketFetcher
from .agent_voter import AgentVoter
from .consensus_engine import ConsensusAggregator
from .kelly_filter import KellyFilter


class BacktestRunner:
    """
    Runs MiroBet consensus across historical games and evaluates against
    actual results. Produces ROI, hit rate, edge metrics.
    """

    def __init__(self):
        self.loader = NBADataLoader()
        self.odds_fetcher = PolymarketFetcher()
        self.agent_voter = None  # Lazy init (needs LLM API key)
        self.kelly = KellyFilter()

    def _get_voter(self):
        if self.agent_voter is None:
            self.agent_voter = AgentVoter()
        return self.agent_voter

    def run_season(self, season: str) -> Dict[str, Any]:
        """
        Run backtest for all games in a season.
        Returns summary metrics.
        """
        games = self.loader.get_season_games(season)

        if not games:
            return {
                "season": season,
                "status": "no_data",
                "message": f"No games found for season {season}. "
                           "Import game data first using import_games_csv()."
            }

        voter = self._get_voter()
        results = []

        for game in games:
            try:
                result = self._run_single_game(game, season, voter)
                results.append(result)
            except Exception:
                continue

        return self._summarize(results, season)

    def run_games(self, games: List[Dict], season: str = '2024-25') -> List[Dict[str, Any]]:
        """Run backtest for a specific list of games"""
        voter = self._get_voter()
        results = []
        for game in games:
            try:
                result = self._run_single_game(game, season, voter)
                results.append(result)
            except Exception:
                continue
        return results

    def _run_single_game(
        self,
        game: Dict,
        season: str,
        voter: AgentVoter = None
    ) -> Dict[str, Any]:
        """Run consensus + Kelly for a single game"""
        if voter is None:
            voter = self._get_voter()

        # Build game context
        ctx = self.loader.build_game_context(game, season)

        # Run agents (moneyline only for backtest efficiency)
        ml_votes = voter.run_all_personas(ctx, bet_type="moneyline")
        agg = ConsensusAggregator(ml_votes)
        consensus = agg.get_consensus()

        # Get historical odds (from database or cache)
        odds = self._get_historical_odds(game.get('market_id', game.get('game_id', '')))

        if not odds or odds.get('home_win', 0) == 0:
            # No odds available
            return self._make_result(game, consensus, None, agg)

        home_decimal = 1 / odds['home_win']
        kelly_decision = self.kelly.get_bet_decision(consensus, home_decimal)

        return self._make_result(game, consensus, kelly_decision, agg, odds)

    def _make_result(
        self,
        game: Dict,
        consensus: float,
        kelly_decision: Dict = None,
        agg: ConsensusAggregator = None,
        odds: Dict = None
    ) -> Dict[str, Any]:
        """Build a single game result dict"""
        actual_win = game.get('home_score', 0) > game.get('away_score', 0)

        return {
            'game_id': game.get('game_id', ''),
            'game_date': game.get('game_date', ''),
            'home_team': game.get('home_team', ''),
            'away_team': game.get('away_team', ''),
            'actual_result': 'home_win' if actual_win else 'away_win',
            'consensus': consensus,
            'confidence': agg.get_confidence() if agg else 0,
            'kelly_decision': kelly_decision,
            'bet_made': kelly_decision.get('should_bet', False) if kelly_decision else False,
            'edge': kelly_decision.get('edge', 0) if kelly_decision else 0,
            'kelly_fraction': kelly_decision.get('kelly_fraction', 0) if kelly_decision else 0,
            # Outcome
            'bet_correct': self._is_bet_correct(
                kelly_decision, consensus, actual_win, odds
            ) if kelly_decision else None,
            'profit': self._calc_profit(
                kelly_decision, consensus, actual_win, odds
            ) if kelly_decision else 0,
        }

    def _is_bet_correct(self, kelly: Dict, consensus: float,
                        actual_win: bool, odds: Dict) -> bool:
        if not kelly or not kelly.get('should_bet'):
            return None
        home_bet = kelly.get('consensus', 0) > 0.5
        return home_bet == actual_win

    def _calc_profit(self, kelly: Dict, consensus: float,
                    actual_win: bool, odds: Dict) -> float:
        if not kelly or not kelly.get('should_bet'):
            return 0.0
        home_bet = kelly.get('consensus', 0) > 0.5
        frac = kelly.get('kelly_fraction', 0)
        if frac <= 0:
            return 0.0
        if home_bet == actual_win:
            decimal = 1 / odds.get('home_win', 0.5) if odds else 2.0
            return frac * (decimal - 1)
        return -frac

    def _summarize(self, results: List[Dict], season: str) -> Dict[str, Any]:
        """Calculate backtest summary metrics"""
        total = len(results)
        if total == 0:
            return {"season": season, "status": "no_results"}

        bets = [r for r in results if r.get('bet_made')]
        correct = [r for r in results if r.get('bet_correct') is True]
        wrong = [r for r in results if r.get('bet_correct') is False]
        no_bet = [r for r in results if r.get('bet_correct') is None]

        total_profit = sum(r.get('profit', 0) for r in results)
        edges = [r.get('edge', 0) for r in bets]

        return {
            "season": season,
            "status": "completed",
            "total_games": total,
            "total_bets": len(bets),
            "no_bets": len(no_bet),
            "correct_bets": len(correct),
            "wrong_bets": len(wrong),
            "win_rate": round(len(correct) / len(bets), 4) if bets else 0,
            "total_profit": round(total_profit, 4),
            "roi": round(total_profit / len(bets), 4) if bets else 0,
            "avg_edge": round(sum(edges) / len(edges), 4) if edges else 0,
            "edge_per_bet": [
                {"game_id": r['game_id'], "edge": r.get('edge', 0)}
                for r in sorted(results, key=lambda x: x.get('edge', 0), reverse=True)[:10]
            ],
            "results": results
        }

    def _get_historical_odds(self, market_id: str) -> Dict:
        """Get historical odds from cache or DB"""
        # Check cache
        cache_path = os.path.join(
            self.odds_fetcher.cache_dir,
            f"historical_{market_id}.json"
        )
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def import_odds_csv(self, csv_path: str) -> int:
        """Import historical odds from CSV file"""
        import pandas as pd
        df = pd.read_csv(csv_path)
        count = 0
        for _, row in df.iterrows():
            game_id = row.get('game_id', '')
            if not game_id:
                continue
            cache_path = os.path.join(
                self.odds_fetcher.cache_dir,
                f"historical_{game_id}.json"
            )
            try:
                with open(cache_path, 'w') as f:
                    json.dump({
                        'home_win': float(row.get('home_prob', 0.5)),
                        'away_win': float(row.get('away_prob', 0.5)),
                        'market_id': game_id
                    }, f)
                count += 1
            except Exception:
                continue
        return count
