"""
Scoring engine for memory promotion and demotion decisions.

Implements weighted scoring algorithms to evaluate whether memories should
be promoted to higher tiers (faster access) or demoted to lower tiers
(free up capacity) based on access patterns, importance, and recency.
"""

from dataclasses import dataclass
from datetime import datetime

from axon.models.entry import MemoryEntry


@dataclass
class ScoringConfig:
    """
    Configuration for scoring algorithms.

    Controls weights, thresholds, and decay parameters for promotion
    and demotion scoring.

    Attributes:
        Promotion weights (sum should be ~1.0):
            promotion_frequency_weight: Weight for access frequency (0.0-1.0)
            promotion_importance_weight: Weight for importance score (0.0-1.0)
            promotion_recency_weight: Weight for recency of access (0.0-1.0)
            promotion_velocity_weight: Weight for access velocity (0.0-1.0)

        Demotion weights (sum should be ~1.0):
            demotion_decay_weight: Weight for time-based decay (0.0-1.0)
            demotion_importance_weight: Weight for low importance (0.0-1.0)
            demotion_capacity_weight: Weight for capacity pressure (0.0-1.0)
            demotion_staleness_weight: Weight for staleness (0.0-1.0)

        Thresholds:
            promotion_threshold: Score above which to promote (0.0-1.0)
            demotion_threshold: Score above which to demote (0.0-1.0)

        Decay parameters:
            recency_half_life_hours: Hours for recency to decay 50%
            velocity_window_hours: Time window for velocity calculation
            staleness_threshold_days: Days after which memory is stale
    """

    # Promotion weights
    promotion_frequency_weight: float = 0.30
    promotion_importance_weight: float = 0.35
    promotion_recency_weight: float = 0.20
    promotion_velocity_weight: float = 0.15

    # Demotion weights
    demotion_decay_weight: float = 0.25
    demotion_importance_weight: float = 0.30
    demotion_capacity_weight: float = 0.25
    demotion_staleness_weight: float = 0.20

    # Thresholds
    promotion_threshold: float = 0.70
    demotion_threshold: float = 0.60

    # Decay parameters
    recency_half_life_hours: float = 24.0
    velocity_window_hours: float = 24.0
    staleness_threshold_days: int = 30

    def __post_init__(self):
        """Validate configuration."""
        # Check weight ranges
        for attr in dir(self):
            if attr.endswith("_weight"):
                value = getattr(self, attr)
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"{attr} must be between 0.0 and 1.0, got {value}")

        # Check threshold ranges
        if not 0.0 <= self.promotion_threshold <= 1.0:
            raise ValueError("promotion_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.demotion_threshold <= 1.0:
            raise ValueError("demotion_threshold must be between 0.0 and 1.0")

        # Warn if weights don't sum close to 1.0
        promo_sum = (
            self.promotion_frequency_weight
            + self.promotion_importance_weight
            + self.promotion_recency_weight
            + self.promotion_velocity_weight
        )
        if abs(promo_sum - 1.0) > 0.1:
            import warnings

            warnings.warn(f"Promotion weights sum to {promo_sum:.2f}, recommended ~1.0", stacklevel=2)

        demo_sum = (
            self.demotion_decay_weight
            + self.demotion_importance_weight
            + self.demotion_capacity_weight
            + self.demotion_staleness_weight
        )
        if abs(demo_sum - 1.0) > 0.1:
            import warnings

            warnings.warn(f"Demotion weights sum to {demo_sum:.2f}, recommended ~1.0", stacklevel=2)


class ScoringEngine:
    """
    Engine for calculating promotion and demotion scores.

    Uses weighted algorithms to score memories based on:
    - Access patterns (frequency, recency, velocity)
    - Intrinsic properties (importance)
    - Extrinsic factors (capacity pressure, staleness)

    All scores are normalized to [0.0, 1.0] range.

    Example:
        ```python
        config = ScoringConfig(
            promotion_frequency_weight=0.3,
            promotion_importance_weight=0.4,
            promotion_recency_weight=0.2,
            promotion_velocity_weight=0.1,
            promotion_threshold=0.70
        )

        engine = ScoringEngine(config)

        # Calculate promotion score
        score, details = engine.calculate_promotion_score(entry)
        if score >= config.promotion_threshold:
            print(f"Promote! Score: {score:.2f}")
            print(engine.explain_score(details))
        ```
    """

    def __init__(self, config: ScoringConfig | None = None):
        """
        Initialize scoring engine.

        Args:
            config: Scoring configuration (uses defaults if not provided)
        """
        self.config = config or ScoringConfig()

    def calculate_promotion_score(
        self, entry: MemoryEntry, current_tier: str = "ephemeral"
    ) -> tuple[float, dict[str, float]]:
        """
        Calculate promotion score for a memory entry.

        Promotion score = (
            w1 * frequency_score +
            w2 * importance_score +
            w3 * recency_score +
            w4 * velocity_score
        )

        All component scores are normalized to [0.0, 1.0].

        Args:
            entry: Memory entry to score
            current_tier: Current tier of the entry

        Returns:
            Tuple of (total_score, component_scores)
            - total_score: Weighted sum of components (0.0-1.0)
            - component_scores: Dict with individual component scores
        """
        # Calculate component scores
        frequency_score = self._calculate_frequency_score(entry)
        importance_score = entry.metadata.importance  # Direct attribute access
        recency_score = self._calculate_recency_score(entry)
        velocity_score = self._calculate_velocity_score(entry)

        # Weighted sum
        total_score = (
            self.config.promotion_frequency_weight * frequency_score
            + self.config.promotion_importance_weight * importance_score
            + self.config.promotion_recency_weight * recency_score
            + self.config.promotion_velocity_weight * velocity_score
        )

        # Build details
        details = {
            "total": total_score,
            "frequency": frequency_score,
            "importance": importance_score,
            "recency": recency_score,
            "velocity": velocity_score,
            "weights": {
                "frequency": self.config.promotion_frequency_weight,
                "importance": self.config.promotion_importance_weight,
                "recency": self.config.promotion_recency_weight,
                "velocity": self.config.promotion_velocity_weight,
            },
            "threshold": self.config.promotion_threshold,
            "should_promote": total_score >= self.config.promotion_threshold,
        }

        return total_score, details

    def calculate_demotion_score(
        self, entry: MemoryEntry, current_tier: str = "session", capacity_pressure: float = 0.0
    ) -> tuple[float, dict[str, float]]:
        """
        Calculate demotion score for a memory entry.

        Demotion score = (
            w1 * decay_score +
            w2 * importance_drop_score +
            w3 * capacity_pressure +
            w4 * staleness_score
        )

        All component scores are normalized to [0.0, 1.0].

        Args:
            entry: Memory entry to score
            current_tier: Current tier of the entry
            capacity_pressure: External pressure from tier capacity (0.0-1.0)

        Returns:
            Tuple of (total_score, component_scores)
            - total_score: Weighted sum of components (0.0-1.0)
            - component_scores: Dict with individual component scores
        """
        # Calculate component scores
        decay_score = self._calculate_decay_score(entry)
        importance_drop_score = 1.0 - entry.metadata.importance  # Inverse of importance
        staleness_score = self._calculate_staleness_score(entry)

        # Weighted sum
        total_score = (
            self.config.demotion_decay_weight * decay_score
            + self.config.demotion_importance_weight * importance_drop_score
            + self.config.demotion_capacity_weight * capacity_pressure
            + self.config.demotion_staleness_weight * staleness_score
        )

        # Build details
        details = {
            "total": total_score,
            "decay": decay_score,
            "importance_drop": importance_drop_score,
            "capacity_pressure": capacity_pressure,
            "staleness": staleness_score,
            "weights": {
                "decay": self.config.demotion_decay_weight,
                "importance_drop": self.config.demotion_importance_weight,
                "capacity_pressure": self.config.demotion_capacity_weight,
                "staleness": self.config.demotion_staleness_weight,
            },
            "threshold": self.config.demotion_threshold,
            "should_demote": total_score >= self.config.demotion_threshold,
        }

        return total_score, details

    def _calculate_frequency_score(self, entry: MemoryEntry) -> float:
        """
        Calculate frequency score based on access count.

        Uses logarithmic scaling to prevent unbounded growth:
        score = log(1 + access_count) / log(101)

        This gives:
        - 0 accesses → 0.0
        - 10 accesses → 0.52
        - 100 accesses → 1.0

        Args:
            entry: Memory entry

        Returns:
            Frequency score (0.0-1.0)
        """
        import math

        # Access custom field from __pydantic_extra__
        access_count = getattr(entry.metadata, "access_count", 0)
        if hasattr(entry.metadata, "__pydantic_extra__") and entry.metadata.__pydantic_extra__:
            access_count = entry.metadata.__pydantic_extra__.get("access_count", 0)

        # Logarithmic scaling: log(1 + x) / log(101)
        # Maps 0→0, 100→1.0, with diminishing returns
        if access_count == 0:
            return 0.0

        score = math.log(1 + access_count) / math.log(101)
        return min(1.0, score)

    def _calculate_recency_score(self, entry: MemoryEntry) -> float:
        """
        Calculate recency score based on last access time.

        Uses exponential decay with configurable half-life:
        score = 2^(-hours_since_access / half_life)

        With default half_life=24 hours:
        - Just accessed → 1.0
        - 24 hours ago → 0.5
        - 48 hours ago → 0.25
        - 96 hours ago → 0.0625

        Args:
            entry: Memory entry

        Returns:
            Recency score (0.0-1.0)
        """

        last_accessed = entry.metadata.last_accessed_at
        if last_accessed is None:
            # Never accessed, use created_at
            last_accessed = entry.metadata.created_at

        # Handle both datetime and string formats
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))

        now = datetime.now(last_accessed.tzinfo) if last_accessed.tzinfo else datetime.now()
        hours_since_access = (now - last_accessed).total_seconds() / 3600

        # Exponential decay: 2^(-t/half_life)
        half_life = self.config.recency_half_life_hours
        score = 2 ** (-hours_since_access / half_life)

        return min(1.0, max(0.0, score))

    def _calculate_velocity_score(self, entry: MemoryEntry) -> float:
        """
        Calculate velocity score based on access rate.

        Velocity = accesses per hour over recent window

        Uses linear scaling:
        score = min(1.0, velocity / 10)

        This gives:
        - 0 accesses/hour → 0.0
        - 5 accesses/hour → 0.5
        - 10+ accesses/hour → 1.0

        Args:
            entry: Memory entry

        Returns:
            Velocity score (0.0-1.0)
        """
        # Access custom field from __pydantic_extra__
        access_count = 0
        if hasattr(entry.metadata, "__pydantic_extra__") and entry.metadata.__pydantic_extra__:
            access_count = entry.metadata.__pydantic_extra__.get("access_count", 0)

        # Calculate age in hours
        created_at = entry.metadata.created_at
        now = (
            datetime.now(created_at.tzinfo)
            if (hasattr(created_at, "tzinfo") and created_at.tzinfo)
            else datetime.now()
        )
        age_hours = (now - created_at).total_seconds() / 3600

        # Use velocity window (default 24 hours)
        effective_hours = min(age_hours, self.config.velocity_window_hours)

        if effective_hours == 0:
            return 0.0

        # Accesses per hour
        velocity = access_count / effective_hours

        # Linear scaling: 10 accesses/hour = 1.0
        score = velocity / 10.0

        return min(1.0, max(0.0, score))

    def _calculate_decay_score(self, entry: MemoryEntry) -> float:
        """
        Calculate time-based decay score.

        Higher score = more decayed = better candidate for demotion

        Uses inverse of recency score:
        decay = 1.0 - recency

        Args:
            entry: Memory entry

        Returns:
            Decay score (0.0-1.0)
        """
        recency = self._calculate_recency_score(entry)
        return 1.0 - recency

    def _calculate_staleness_score(self, entry: MemoryEntry) -> float:
        """
        Calculate staleness score based on age without access.

        Higher score = more stale = better candidate for demotion

        Uses step function:
        - < threshold days → 0.0
        - >= threshold days → linear ramp to 1.0 over next threshold days

        With default threshold=30 days:
        - 0-29 days → 0.0
        - 30 days → 0.0
        - 60 days → 1.0

        Args:
            entry: Memory entry

        Returns:
            Staleness score (0.0-1.0)
        """
        last_accessed = entry.metadata.last_accessed_at
        if last_accessed is None:
            last_accessed = entry.metadata.created_at

        # Handle both datetime and string formats
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))

        now = datetime.now(last_accessed.tzinfo) if last_accessed.tzinfo else datetime.now()
        days_since_access = (now - last_accessed).total_seconds() / 86400

        threshold_days = self.config.staleness_threshold_days

        if days_since_access < threshold_days:
            return 0.0

        # Linear ramp from threshold to 2*threshold
        excess_days = days_since_access - threshold_days
        score = excess_days / threshold_days

        return min(1.0, score)

    def explain_score(self, score_details: dict[str, float]) -> str:
        """
        Generate human-readable explanation of a score.

        Args:
            score_details: Score details dict from calculate_promotion_score
                          or calculate_demotion_score

        Returns:
            Formatted explanation string
        """
        lines = [
            f"Total Score: {score_details['total']:.3f}",
            f"Threshold: {score_details['threshold']:.3f}",
            f"Decision: {'✅ YES' if score_details.get('should_promote') or score_details.get('should_demote') else '❌ NO'}",
            "",
            "Component Breakdown:",
        ]

        # Filter out non-component keys
        exclude_keys = {"total", "threshold", "should_promote", "should_demote", "weights"}
        components = {k: v for k, v in score_details.items() if k not in exclude_keys}

        weights = score_details.get("weights", {})

        for name, value in components.items():
            weight = weights.get(name, 0.0)
            contribution = weight * value
            lines.append(f"  {name:20s}: {value:5.3f} × {weight:.2f} = {contribution:.3f}")

        return "\n".join(lines)
