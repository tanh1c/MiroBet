"""
MiroBet API Routes
"""
import os
from flask import Blueprint, request, jsonify
import traceback
import json

mirobet_bp = Blueprint('mirobet', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@mirobet_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "MiroBet",
        "version": "0.1.0"
    })


# ─────────────────────────────────────────────────────────────────────────────
# Predict (Single Game)
# ─────────────────────────────────────────────────────────────────────────────

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
                    "moneyline": { "home_win": 0.62, ... },
                    "spread": { "home_cover": 0.55, ... },
                    "over_under": { "over": 0.48, ... }
                },
                "kelly": { "home_ml": {...}, ... },
                "signal": "HOME_ML"
            }
        }
    """
    try:
        data = request.get_json() or {}
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        season = data.get('season', '2024-25')
        game_date = data.get('game_date', '')

        if not home_team or not away_team:
            return jsonify({
                "success": False,
                "error": "home_team and away_team are required"
            }), 400

        # Lazy imports to avoid heavy deps at startup
        from ..services.nba_data_loader import NBADataLoader
        from ..services.odds_fetcher import PolymarketFetcher
        from ..services.agent_voter import AgentVoter
        from ..services.consensus_engine import ConsensusAggregator
        from ..services.kelly_filter import KellyFilter

        # Build game context
        loader = NBADataLoader()
        game = {'home_team': home_team, 'away_team': away_team,
                'game_date': game_date, 'game_id': f"{home_team}@{away_team}-{game_date}"}
        ctx = loader.build_game_context(game, season)

        # Get odds
        odds_fetcher = PolymarketFetcher()
        ml_odds = odds_fetcher.get_implied_probability(home_team, away_team)
        spread_data = odds_fetcher.get_spread_and_total(home_team, away_team)

        # Run agent voting
        voter = AgentVoter()
        ctx['spread'] = spread_data.get('spread', -4.5)
        ctx['over_under'] = spread_data.get('over_under', 225.5)

        ml_votes = voter.run_all_personas(ctx, bet_type="moneyline")
        spread_votes = voter.run_all_personas(ctx, bet_type="spread")
        ou_votes = voter.run_all_personas(ctx, bet_type="over_under")

        # Aggregate
        agg_ml = ConsensusAggregator(ml_votes)
        agg_spread = ConsensusAggregator(spread_votes)
        agg_ou = ConsensusAggregator(ou_votes)

        consensus_ml = agg_ml.get_consensus()
        consensus_spread = agg_spread.get_consensus()
        consensus_ou = agg_ou.get_consensus()

        # Kelly decisions
        kelly = KellyFilter()
        home_decimal = 1 / ml_odds.get('home_win', 0.5)
        ml_decision = kelly.get_bet_decision(consensus_ml, home_decimal)
        spread_decimal = 1 / spread_data.get('home_spread_price', 1.91)
        spread_decision = kelly.get_bet_decision(consensus_spread, spread_decimal)
        ou_decimal = 1 / spread_data.get('over_price', 1.91)
        ou_decision = kelly.get_bet_decision(consensus_ou, ou_decimal)

        # Determine signal
        bets = [
            ('HOME_ML', ml_decision['should_bet'], ml_decision['edge']),
            ('AWAY_ML', ml_decision['should_bet'] and ml_odds.get('away_win', 0.5) > 0.5, -ml_decision['edge']),
            ('HOME_SPREAD', spread_decision['should_bet'], spread_decision['edge']),
            ('OVER', ou_decision['should_bet'], ou_decision['edge']),
        ]
        signal = max(bets, key=lambda x: x[2] if x[1] else -999)[0]

        return jsonify({
            "success": True,
            "data": {
                "game_id": game['game_id'],
                "home_team": home_team,
                "away_team": away_team,
                "consensus": {
                    "moneyline": {
                        "home_win": consensus_ml,
                        "away_win": round(1 - consensus_ml, 4),
                        "polymarket_implied": ml_odds.get('home_win', 0.5),
                        "edge": round(consensus_ml - ml_odds.get('home_win', 0.5), 4)
                    },
                    "spread": {
                        "home_cover": consensus_spread,
                        "away_cover": round(1 - consensus_spread, 4),
                        "line": spread_data.get('spread', -4.5),
                        "edge": round(consensus_spread - 0.5, 4)
                    },
                    "over_under": {
                        "over": consensus_ou,
                        "under": round(1 - consensus_ou, 4),
                        "line": spread_data.get('over_under', 225.5),
                        "edge": round(consensus_ou - 0.5, 4)
                    }
                },
                "kelly": {
                    "home_ml": ml_decision,
                    "home_spread": spread_decision,
                    "over": ou_decision
                },
                "confidence": {
                    "moneyline": agg_ml.get_confidence(),
                    "spread": agg_spread.get_confidence(),
                    "over_under": agg_ou.get_confidence()
                },
                "signal": signal if any(b[1] for b in bets) else "NO_BET"
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# Backtest
# ─────────────────────────────────────────────────────────────────────────────

@mirobet_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """
    Run backtest for a single season

    Body:
        {
            "season": "2023-24"
        }
    """
    try:
        data = request.get_json() or {}
        season = data.get('season', '2023-24')

        from ..services.backtest_runner import BacktestRunner

        runner = BacktestRunner()
        result = runner.run_season(season)

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# Historical odds (for backtest)
# ─────────────────────────────────────────────────────────────────────────────

@mirobet_bp.route('/odds/import', methods=['POST'])
def import_odds():
    """
    Import historical odds CSV for backtest

    Body:
        {
            "file_path": "/path/to/odds.csv"
        }
    """
    try:
        data = request.get_json() or {}
        file_path = data.get('file_path')

        if not file_path or not os.path.exists(file_path):
            return jsonify({"success": False, "error": "file_path required"}), 400

        from ..services.backtest_runner import BacktestRunner
        runner = BacktestRunner()
        count = runner.import_odds_csv(file_path)

        return jsonify({
            "success": True,
            "data": {"imported": count}
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
