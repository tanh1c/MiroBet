"""
Consensus Aggregator
Aggregates agent votes into a single consensus probability using
multiple aggregation methods (mean, median, weighted).
"""
import statistics
from typing import List, Dict, Any, Optional


class ConsensusAggregator:
    """
    Aggregates votes from multiple agents into a consensus probability.
    Supports outlier removal and confidence scoring.
    """

    def __init__(self, votes: List[float] = None, remove_outliers: bool = True):
        self.votes = votes or []
        self.remove_outliers = remove_outliers
        self._cleaned_votes: List[float] = []

    @property
    def cleaned_votes(self) -> List[float]:
        """Returns votes with outliers removed"""
        if not self._cleaned_votes:
            self._cleaned_votes = self._remove_outliers(self.votes)
        return self._cleaned_votes

    def _remove_outliers(self, votes: List[float]) -> List[float]:
        """Remove statistical outliers using 2-sigma rule"""
        if len(votes) < 4:
            return list(votes)

        mean = statistics.mean(votes)
        if len(votes) > 1:
            stdev = statistics.stdev(votes)
        else:
            stdev = 0

        if stdev == 0:
            return list(votes)

        lower = mean - 2 * stdev
        upper = mean + 2 * stdev
        cleaned = [v for v in votes if lower <= v <= upper]
        return cleaned if cleaned else list(votes)

    def get_consensus(self) -> float:
        """
        Get consensus using arithmetic mean of cleaned votes.
        Returns probability between 0.0 and 1.0.
        """
        votes = self.cleaned_votes if self.remove_outliers else self.votes
        if not votes:
            return 0.5

        mean = statistics.mean(votes)
        return round(max(0.0, min(1.0, mean)), 4)

    def get_median_consensus(self) -> float:
        """Get consensus using median (more robust to outliers)"""
        votes = self.cleaned_votes if self.remove_outliers else self.votes
        if not votes:
            return 0.5
        return round(statistics.median(votes), 4)

    def get_confidence(self) -> float:
        """
        Return confidence score based on agreement among agents.
        Lower stdev = higher confidence. Returns 0.0 to 1.0.
        """
        if len(self.votes) < 2:
            return 0.0

        stdev = statistics.stdev(self.votes)
        # Map stdev range to confidence
        # stdev of 0.15 or more = 0 confidence
        # stdev of 0 = 1 confidence
        confidence = max(0.0, 1.0 - (stdev / 0.15))
        return round(confidence, 4)

    def get_spread(self) -> float:
        """Return the spread between max and min votes"""
        if not self.votes:
            return 0.0
        return round(max(self.votes) - min(self.votes), 4)

    def get_distribution(self, bins: int = 5) -> Dict[str, Any]:
        """
        Return vote distribution as histogram bins.
        Useful for frontend visualization.
        """
        votes = self.cleaned_votes if self.remove_outliers else self.votes
        if not votes:
            return {"bins": [], "counts": []}

        bin_size = 1.0 / bins
        bin_edges = [i * bin_size for i in range(bins + 1)]
        counts = [0] * bins

        for v in votes:
            idx = min(int(v / bin_size), bins - 1)
            counts[idx] += 1

        return {
            "bins": [round(bin_edges[i] + bin_size / 2, 2) for i in range(bins)],
            "counts": counts,
            "total_votes": len(votes),
            "mean": round(statistics.mean(votes), 4),
            "median": round(statistics.median(votes), 4),
            "stdev": round(statistics.stdev(votes) if len(votes) > 1 else 0, 4),
        }

    def should_include_vote(self, vote: float) -> bool:
        """Check if a vote should be included (not an outlier)"""
        if self.remove_outliers and len(self.votes) >= 4:
            cleaned = self.cleaned_votes
            return vote in cleaned
        return True
