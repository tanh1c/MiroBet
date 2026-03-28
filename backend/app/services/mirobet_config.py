"""
MiroBet configuration
"""
import os
from dotenv import load_dotenv

# Load .env from project root
project_root_env = os.path.join(os.path.dirname(__file__), '../../../.env')
if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)


class MiroBetConfig:
    """MiroBet configuration"""

    # LLM config (Groq preferred - free tier)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.groq.com/openai/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'llama-3.3-70b-versatile')

    # MiroBet specific
    AGENT_COUNT = int(os.environ.get('MIROBET_AGENT_COUNT', '64'))
    AGENTS_PER_PERSONA = 16
    MAX_TOKENS_PER_CALL = 500
    KELLY_MIN_THRESHOLD = 0.05
    KELLY_MAX_FRACTION = 0.20
    BACKTEST_SEASONS = 3

    # Data paths
    DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')
    NBA_STATS_DIR = os.path.join(DATA_DIR, 'nba_stats')
    PREDICTIONS_DIR = os.path.join(DATA_DIR, 'predictions')
    POLYMARKET_CACHE_DIR = os.path.join(DATA_DIR, 'polymarket_cache')
