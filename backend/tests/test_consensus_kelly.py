"""
Tests for ConsensusAggregator and KellyFilter
Uses importlib to bypass app.services.__init__.py (which needs zep_cloud)
"""
import sys
import os
import importlib.util

# ── Patch zep_cloud FIRST ───────────────────────────────────────────────────
class _MockZepClient:
    class Graph:
        pass

class _EpisodeData:
    pass

class _EntityEdgeSourceTarget:
    pass

sys.modules['zep_cloud'] = type(sys)('zep_cloud')
sys.modules['zep_cloud'].EpisodeData = _EpisodeData
sys.modules['zep_cloud'].EntityEdgeSourceTarget = _EntityEdgeSourceTarget
sys.modules['zep_cloud.client'] = type(sys)('zep_cloud.client')
sys.modules['zep_cloud.client'].Zep = _MockZepClient

# ── Load modules directly ───────────────────────────────────────────────────
_backend = os.path.dirname(__file__)

_consensus_spec = importlib.util.spec_from_file_location(
    "_consensus", os.path.join(_backend, '..', 'app', 'services', 'consensus_engine.py'))
_consensus_mod = importlib.util.module_from_spec(_consensus_spec)
_consensus_spec.loader.exec_module(_consensus_mod)
ConsensusAggregator = _consensus_mod.ConsensusAggregator

_kelly_spec = importlib.util.spec_from_file_location(
    "_kelly", os.path.join(_backend, '..', 'app', 'services', 'kelly_filter.py'))
_kelly_mod = importlib.util.module_from_spec(_kelly_spec)
_kelly_spec.loader.exec_module(_kelly_mod)
KellyFilter = _kelly_mod.KellyFilter


# ─────────────────────────────────────────────────────────────────────────────
# ConsensusAggregator Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_mean_consensus():
    votes = [0.62, 0.58, 0.65, 0.60, 0.63]
    agg = ConsensusAggregator(votes)
    consensus = agg.get_consensus()
    assert abs(consensus - 0.616) < 0.01


def test_outlier_removal():
    votes = [0.62, 0.58, 0.99, 0.60, 0.63]
    agg = ConsensusAggregator(votes, remove_outliers=True)
    consensus = agg.get_consensus()
    assert consensus < 0.70


def test_outlier_removal_disabled():
    votes = [0.62, 0.58, 0.99, 0.60, 0.63]
    agg = ConsensusAggregator(votes, remove_outliers=False)
    consensus = agg.get_consensus()
    assert consensus > 0.60


def test_median_consensus():
    votes = [0.50, 0.60, 0.70, 0.80]
    agg = ConsensusAggregator(votes)
    assert agg.get_median_consensus() == 0.65


def test_confidence_high():
    votes = [0.60, 0.61, 0.59, 0.60, 0.60]
    agg = ConsensusAggregator(votes)
    assert agg.get_confidence() > 0.8


def test_confidence_low():
    votes = [0.30, 0.70, 0.40, 0.80, 0.50]
    agg = ConsensusAggregator(votes)
    assert agg.get_confidence() < 0.5


def test_distribution():
    votes = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    agg = ConsensusAggregator(votes)
    dist = agg.get_distribution(bins=5)
    assert len(dist['bins']) == 5
    assert dist['total_votes'] == 10


def test_empty_votes():
    agg = ConsensusAggregator([])
    assert agg.get_consensus() == 0.5


def test_spread():
    agg = ConsensusAggregator([0.40, 0.70])
    assert agg.get_spread() == 0.30


# ─────────────────────────────────────────────────────────────────────────────
# KellyFilter Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_kelly_basic():
    """MiroFish 62%, odds 2.5x → raw kelly=0.553, capped at 0.20"""
    kf = KellyFilter(min_threshold=0.05, max_fraction=0.20)
    fraction = kf.calculate_kelly(consensus=0.62, decimal_odds=2.5)
    # b=1.5, p=0.62, q=0.38 → raw kelly=0.553, but capped at max 0.20
    assert fraction == 0.20


def test_kelly_even_money():
    """MiroFish 52%, odds 2.0x → no edge"""
    kf = KellyFilter(min_threshold=0.05)
    fraction = kf.calculate_kelly(consensus=0.52, decimal_odds=2.0)
    assert fraction < 0.05


def test_kelly_below_threshold():
    kf = KellyFilter(min_threshold=0.05)
    assert not kf.should_bet(consensus=0.51, decimal_odds=2.0)


def test_kelly_above_threshold():
    kf = KellyFilter(min_threshold=0.05)
    assert kf.should_bet(consensus=0.60, decimal_odds=2.0)


def test_kelly_capped_at_max():
    kf = KellyFilter(min_threshold=0.05, max_fraction=0.20)
    fraction = kf.calculate_kelly(consensus=0.80, decimal_odds=2.0)
    assert fraction <= 0.20


def test_kelly_get_decision():
    kf = KellyFilter(min_threshold=0.05, max_fraction=0.20)
    decision = kf.get_bet_decision(consensus=0.62, decimal_odds=2.5)
    assert decision['consensus'] == 0.62
    assert decision['implied_probability'] == 0.4
    assert decision['edge'] == 0.22
    assert decision['should_bet'] is True
    assert 'reason' in decision


def test_kelly_no_bet_decision():
    kf = KellyFilter(min_threshold=0.05)
    decision = kf.get_bet_decision(consensus=0.51, decimal_odds=2.0)
    assert decision['should_bet'] is False
    assert decision['confidence'] == 'NO BET'


def test_american_odds_conversion():
    kf = KellyFilter()
    # decimal_to_american: decimal → American
    assert abs(kf.decimal_to_american(2.0) - 100) < 0.1
    assert abs(kf.decimal_to_american(1.5) + 200) < 0.1
    # _american_to_decimal: American → decimal (private)
    assert abs(kf._american_to_decimal(100) - 2.0) < 0.01
    assert abs(kf._american_to_decimal(-200) - 1.5) < 0.01


def test_kelly_with_american_odds():
    kf = KellyFilter(min_threshold=0.05, max_fraction=0.20)
    # American +150 = decimal 2.5 → raw kelly=0.553, capped at 0.20
    fraction = kf.calculate_kelly(consensus=0.62, american_odds=150)
    assert fraction == 0.20
