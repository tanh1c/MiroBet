"""
Tests for MiroBet config
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import directly from module file, bypassing app/__init__.py (which needs zep_cloud)
# Use importlib to avoid triggering app/services/__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "mirobet_config",
    os.path.join(os.path.dirname(__file__), '..', 'app', 'services', 'mirobet_config.py')
)
mirobet_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirobet_config_module)
MiroBetConfig = mirobet_config_module.MiroBetConfig


def test_config_defaults():
    """Test MiroBetConfig default values"""
    assert MiroBetConfig.AGENT_COUNT == 64
    assert MiroBetConfig.KELLY_MIN_THRESHOLD == 0.05
    assert MiroBetConfig.MAX_TOKENS_PER_CALL == 500
    assert MiroBetConfig.AGENTS_PER_PERSONA == 16


def test_kelly_bounds():
    """Test Kelly threshold bounds"""
    assert MiroBetConfig.KELLY_MIN_THRESHOLD >= 0
    assert MiroBetConfig.KELLY_MAX_FRACTION <= 1.0
    assert MiroBetConfig.KELLY_MIN_THRESHOLD < MiroBetConfig.KELLY_MAX_FRACTION


def test_backtest_seasons():
    """Test backtest season count"""
    assert MiroBetConfig.BACKTEST_SEASONS == 3


def test_data_dirs():
    """Test data directory paths"""
    assert MiroBetConfig.NBA_STATS_DIR.endswith('nba_stats')
    assert MiroBetConfig.PREDICTIONS_DIR.endswith('predictions')
    assert MiroBetConfig.POLYMARKET_CACHE_DIR.endswith('polymarket_cache')


def test_llm_config():
    """Test LLM configuration defaults"""
    assert MiroBetConfig.LLM_BASE_URL == 'https://api.groq.com/openai/v1'
    assert MiroBetConfig.LLM_MODEL_NAME == 'llama-3.3-70b-versatile'
