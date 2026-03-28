"""
Tests for NBA Data Loader
Uses importlib to bypass app.services package __init__.py
(which imports zep_cloud via graph_builder.
"""
import sys
import os
import tempfile
import importlib.util

# Set up mock zep_cloud FIRST (before any app imports)
_mock_zep = type(sys)('zep_cloud')
_mock_zep.client = type(sys)('zep_cloud.client')
_mock_zep.client.Zep = type('MockZep', (), {})

# Stub classes for graph_builder imports (needed if __init__ runs)
class MockEpisodeData:
    pass

class MockEntityEdgeSourceTarget:
    pass

_mock_zep.EpisodeData = MockEpisodeData
_mock_zep.EntityEdgeSourceTarget = MockEntityEdgeSourceTarget

sys.modules['zep_cloud'] = _mock_zep
sys.modules['zep_cloud.client'] = _mock_zep.client

# Now load nba_data_loader.py directly, bypassing app.services.__init__.py
_backend_dir = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location(
    "_nba_loader",
    os.path.join(_backend_dir, '..', 'app', 'services', 'nba_data_loader.py')
)
_nba_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nba_mod)
NBADataLoader = _nba_mod.NBADataLoader


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_loader_initializes():
    """Test loader initializes with data directory"""
    loader = NBADataLoader()
    assert 'nba_stats' in loader.data_dir
    assert NBADataLoader.SEASONS == ['2022-23', '2023-24', '2024-25']


def test_loader_with_custom_dir():
    """Test loader with custom data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        assert loader.data_dir == tmpdir


def test_get_player_vector_defaults():
    """Test get_player_vector returns defaults for unknown player"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        vector = loader.get_player_vector("Unknown Player", "2023-24")
        assert vector['pts'] == 0.0
        assert vector['reb'] == 0.0
        assert vector['efg_pct'] == 0.0
        assert 'ast' in vector
        assert 'usage_rate' in vector


def test_get_team_form_defaults():
    """Test get_team_form_tensor returns defaults for unknown team"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        form = loader.get_team_form_tensor("UNKNOWN", "2023-24")
        assert form['last_10_wins'] == 0
        assert form['pace'] == 0.0
        assert form['defensive_rating'] == 0.0
        assert 'home_record' in form
        assert 'streak' in form


def test_get_matchup_history_defaults():
    """Test get_matchup_history returns defaults for unknown matchup"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        h2h = loader.get_matchup_history("TEAM_A", "TEAM_B")
        assert h2h['team_a_wins'] == 0
        assert h2h['team_b_wins'] == 0


def test_build_game_context():
    """Test build_game_context creates complete context"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        game = {
            'home_team': 'LAL',
            'away_team': 'BOS',
            'game_date': '2024-03-15',
            'game_id': 'LAL@BOS-2024-03-15'
        }
        ctx = loader.build_game_context(game, '2023-24')
        assert ctx['home_team'] == 'LAL'
        assert ctx['away_team'] == 'BOS'
        assert ctx['season'] == '2023-24'
        assert 'home_stats' in ctx
        assert 'away_stats' in ctx
        assert 'h2h' in ctx
        assert 'home_players' in ctx
        assert 'away_players' in ctx


def test_sqlite_schema_created():
    """Test SQLite database and tables are created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        db_path = loader._db_path
        assert os.path.exists(db_path)
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'player_stats' in tables
        assert 'team_stats' in tables
        assert 'games' in tables
        assert 'matchups' in tables


def test_team_stats_aliases():
    """Test get_team_stats and get_team_form are aliases"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = NBADataLoader(data_dir=tmpdir)
        stats = loader.get_team_stats("TEST", "2023-24")
        form = loader.get_team_form("TEST", "2023-24")
        assert set(stats.keys()) == set(form.keys())
