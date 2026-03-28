"""
MiroBet API Routes
"""
from flask import Blueprint, request, jsonify
import traceback

mirobet_bp = Blueprint('mirobet', __name__)


@mirobet_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "MiroBet"
    })


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
    """
    try:
        data = request.get_json() or {}
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not home_team or not away_team:
            return jsonify({
                "success": False,
                "error": "home_team and away_team are required"
            }), 400

        # TODO: Implement actual MiroFish consensus (Task 7-8)
        # For now, return mock data
        return jsonify({
            "success": True,
            "data": {
                "game_id": f"{home_team}@{away_team}",
                "status": "placeholder",
                "message": "Real consensus coming in Task 7-8",
                "consensus": {
                    "moneyline": {
                        "home_win": 0.62,
                        "polymarket_implied": 0.40,
                        "edge": 0.22
                    }
                }
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
