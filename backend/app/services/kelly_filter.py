"""
Kelly Criterion Filter
Determines bet sizing based on edge between MiroFish consensus
and Polymarket odds using the Kelly formula.
"""
from typing import Dict, Any, Optional

try:
    from .mirobet_config import MiroBetConfig
    KELLY_MIN = MiroBetConfig.KELLY_MIN_THRESHOLD
    KELLY_MAX = MiroBetConfig.KELLY_MAX_FRACTION
except Exception:
    KELLY_MIN = 0.05
    KELLY_MAX = 0.20


class KellyFilter:
    """
    Kelly Criterion calculator for bet sizing.

    Formula: f* = (bp - q) / b
    Where:
        b = decimal_odds - 1
        p = MiroFish consensus probability
        q = 1 - p
    """

    def __init__(self, min_threshold: float = None, max_fraction: float = None):
        self.min_threshold = min_threshold if min_threshold is not None else KELLY_MIN
        self.max_fraction = max_fraction if max_fraction is not None else KELLY_MAX

    def calculate_kelly(
        self,
        consensus: float,
        decimal_odds: float = None,
        american_odds: float = None
    ) -> float:
        """
        Calculate Kelly fraction.

        Args:
            consensus: MiroFish consensus probability (0.0-1.0)
            decimal_odds: Decimal odds (e.g., 2.50 for 3/2)
            american_odds: American odds (e.g., +150). Used if decimal_odds not provided.

        Returns:
            Kelly fraction (0.0-1.0), capped between min_threshold and max_fraction
        """
        if decimal_odds is None and american_odds is not None:
            decimal_odds = self._american_to_decimal(american_odds)
        elif decimal_odds is None:
            return 0.0

        if decimal_odds <= 1.0:
            return 0.0

        b = decimal_odds - 1
        p = consensus
        q = 1 - p

        kelly = (b * p - q) / b

        # Apply constraints
        kelly = max(0.0, min(kelly, self.max_fraction))
        return round(kelly, 4)

    def should_bet(self, consensus: float, decimal_odds: float = None, american_odds: float = None) -> bool:
        """Return True if Kelly fraction exceeds minimum threshold"""
        kelly_fraction = self.calculate_kelly(consensus, decimal_odds, american_odds)
        return kelly_fraction >= self.min_threshold

    def get_bet_decision(
        self,
        consensus: float,
        decimal_odds: float = None,
        american_odds: float = None,
        implied_probability: float = None
    ) -> Dict[str, Any]:
        """
        Return full bet decision with all metrics.

        Returns:
            Dict with: consensus, decimal_odds, implied_probability, edge,
            kelly_fraction, should_bet, reason, confidence
        """
        if decimal_odds is None and american_odds is not None:
            decimal_odds = self._american_to_decimal(american_odds)

        implied = implied_probability
        if implied is None and decimal_odds:
            implied = round(1 / decimal_odds, 4)

        edge = round(consensus - implied, 4) if implied else 0.0
        kelly_fraction = self.calculate_kelly(consensus, decimal_odds, american_odds)

        return {
            "consensus": round(consensus, 4),
            "decimal_odds": round(decimal_odds, 4) if decimal_odds else 0,
            "implied_probability": implied or 0,
            "edge": edge,
            "edge_pct": f"{edge * 100:+.1f}%" if edge else "0%",
            "kelly_fraction": kelly_fraction,
            "kelly_pct": f"{kelly_fraction * 100:.1f}%",
            "should_bet": kelly_fraction >= self.min_threshold,
            "bet_size_unit": self._kelly_to_units(kelly_fraction),
            "reason": self._get_reason(kelly_fraction, edge),
            "confidence": self._get_confidence_label(kelly_fraction, edge)
        }

    def _get_reason(self, kelly_fraction: float, edge: float) -> str:
        if kelly_fraction >= self.min_threshold:
            return f"Edge found (Kelly={kelly_fraction:.1%}, edge={edge:+.1%})"
        return f"No edge (Kelly={kelly_fraction:.1%} < {self.min_threshold:.1%} threshold)"

    def _get_confidence_label(self, kelly_fraction: float, edge: float) -> str:
        if kelly_fraction >= 0.20:
            return "HIGH"
        elif kelly_fraction >= 0.10:
            return "MEDIUM"
        elif kelly_fraction >= self.min_threshold:
            return "LOW"
        return "NO BET"

    def _kelly_to_units(self, kelly_fraction: float) -> str:
        """Convert Kelly fraction to bankroll units (1 unit = 1% of bankroll)"""
        units = kelly_fraction * 100
        return f"{units:.1f} units"

    def _american_to_decimal(self, american: float) -> float:
        if american > 0:
            return 1 + (american / 100)
        return 1 + (100 / abs(american))

    def decimal_to_american(self, decimal: float) -> float:
        if decimal >= 2.0:
            return (decimal - 1) * 100
        return -100 / (decimal - 1)

    def fractional_to_decimal(self, numerator: float, denominator: float) -> float:
        """Convert fractional odds to decimal (e.g., 3/2 -> 2.5)"""
        return 1 + (numerator / denominator)
