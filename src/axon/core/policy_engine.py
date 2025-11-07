"""
Policy Engine for orchestrating memory lifecycle decisions.

This module provides the PolicyEngine class that integrates ScoringEngine
and tier policies to make intelligent promotion/demotion decisions and
manage tier capacity.
"""

import logging
from typing import Any

from axon.core.adapter_registry import AdapterRegistry
from axon.core.policy import Policy
from axon.core.scoring import ScoringEngine
from axon.models.entry import MemoryEntry

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Orchestrates memory lifecycle decisions using scoring and policies.

    The PolicyEngine integrates:
    - ScoringEngine: Calculates promotion/demotion scores
    - Tier Policies: Define tier behavior (capacity, TTL, etc.)
    - AdapterRegistry: Provides tier statistics for capacity checks

    It makes intelligent decisions about:
    - When to promote entries to higher tiers
    - When to demote entries to lower tiers
    - When to compact/evict entries due to capacity
    - Optimal tier paths for promotion/demotion

    Tier Hierarchy:
        ephemeral → session → persistent
        (lower)              (higher)

    Example:
        >>> engine = PolicyEngine(
        ...     registry=registry,
        ...     scoring_engine=scoring_engine,
        ...     tier_policies={
        ...         "ephemeral": ephemeral_policy,
        ...         "session": session_policy,
        ...         "persistent": persistent_policy
        ...     }
        ... )
        >>> should_promote = engine.should_promote(entry, "ephemeral", "session")
        >>> next_tier = engine.get_promotion_path(entry, "ephemeral")
    """

    # Tier hierarchy order (lower to higher)
    _TIER_ORDER = ["ephemeral", "session", "persistent"]

    def __init__(
        self,
        registry: AdapterRegistry,
        scoring_engine: ScoringEngine,
        tier_policies: dict[str, Policy],
    ):
        """
        Initialize PolicyEngine.

        Args:
            registry: AdapterRegistry for accessing tier statistics
            scoring_engine: ScoringEngine for calculating scores
            tier_policies: Dict mapping tier names to Policy instances

        Raises:
            ValueError: If tier_policies is empty or missing tiers
        """
        if not tier_policies:
            raise ValueError("tier_policies cannot be empty")

        self._registry = registry
        self._scoring = scoring_engine
        self._policies = tier_policies

        logger.info(
            f"PolicyEngine initialized with {len(tier_policies)} tiers: "
            f"{', '.join(sorted(tier_policies.keys()))}"
        )

    def should_promote(
        self,
        entry: MemoryEntry,
        current_tier: str,
        target_tier: str,
        capacity_pressure: float = 0.0,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Determine if entry should be promoted from current to target tier.

        Args:
            entry: MemoryEntry to evaluate
            current_tier: Current tier name
            target_tier: Target tier name
            capacity_pressure: Current capacity pressure (0.0-1.0)

        Returns:
            Tuple of (should_promote: bool, details: dict)
            details contains: score, threshold, components, reason

        Example:
            >>> should, details = engine.should_promote(entry, "ephemeral", "session")
            >>> if should:
            ...     print(f"Promote! Score: {details['score']:.3f}")
        """
        # Validate tier path first
        if not self._is_valid_promotion_path(current_tier, target_tier):
            return False, {
                "should_promote": False,
                "score": 0.0,
                "threshold": self._scoring.config.promotion_threshold,
                "reason": f"Invalid promotion path: {current_tier} → {target_tier}",
                "tier_order": self._TIER_ORDER,
            }

        # Check if target tier exists in policies
        if target_tier not in self._policies:
            return False, {
                "should_promote": False,
                "score": 0.0,
                "threshold": self._scoring.config.promotion_threshold,
                "reason": f"Target tier '{target_tier}' not found in policies",
                "available_tiers": list(self._policies.keys()),
            }

        # Calculate promotion score
        score, score_details = self._scoring.calculate_promotion_score(entry)

        # Add score to details for consistency
        score_details["score"] = score

        # Add tier transition context
        score_details["current_tier"] = current_tier
        score_details["target_tier"] = target_tier
        score_details["capacity_pressure"] = capacity_pressure

        # Check if score meets threshold
        should_promote = score_details["should_promote"]

        if should_promote:
            score_details["reason"] = (
                f"Entry qualifies for promotion: score {score:.3f} ≥ "
                f"threshold {score_details['threshold']:.3f}"
            )
        else:
            score_details["reason"] = (
                f"Entry does not qualify: score {score:.3f} < "
                f"threshold {score_details['threshold']:.3f}"
            )

        logger.debug(
            f"Promotion check: {current_tier}→{target_tier}, "
            f"score={score:.3f}, decision={should_promote}"
        )

        return should_promote, score_details

    def should_demote(
        self,
        entry: MemoryEntry,
        current_tier: str,
        target_tier: str,
        capacity_pressure: float = 0.0,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Determine if entry should be demoted from current to target tier.

        Args:
            entry: MemoryEntry to evaluate
            current_tier: Current tier name
            target_tier: Target tier name
            capacity_pressure: Current capacity pressure (0.0-1.0)

        Returns:
            Tuple of (should_demote: bool, details: dict)
            details contains: score, threshold, components, reason

        Example:
            >>> should, details = engine.should_demote(entry, "session", "ephemeral")
            >>> if should:
            ...     print(f"Demote! Score: {details['score']:.3f}")
        """
        # Validate tier path first
        if not self._is_valid_demotion_path(current_tier, target_tier):
            return False, {
                "should_demote": False,
                "score": 0.0,
                "threshold": self._scoring.config.demotion_threshold,
                "reason": f"Invalid demotion path: {current_tier} → {target_tier}",
                "tier_order": self._TIER_ORDER,
            }

        # Check if target tier exists in policies
        if target_tier not in self._policies:
            return False, {
                "should_demote": False,
                "score": 0.0,
                "threshold": self._scoring.config.demotion_threshold,
                "reason": f"Target tier '{target_tier}' not found in policies",
                "available_tiers": list(self._policies.keys()),
            }

        # Calculate demotion score
        score, score_details = self._scoring.calculate_demotion_score(
            entry, capacity_pressure=capacity_pressure
        )

        # Add score to details for consistency
        score_details["score"] = score

        # Add tier transition context
        score_details["current_tier"] = current_tier
        score_details["target_tier"] = target_tier
        score_details["capacity_pressure"] = capacity_pressure

        # Check if score meets threshold
        should_demote = score_details["should_demote"]

        if should_demote:
            score_details["reason"] = (
                f"Entry qualifies for demotion: score {score:.3f} ≥ "
                f"threshold {score_details['threshold']:.3f}"
            )
        else:
            score_details["reason"] = (
                f"Entry does not qualify: score {score:.3f} < "
                f"threshold {score_details['threshold']:.3f}"
            )

        logger.debug(
            f"Demotion check: {current_tier}→{target_tier}, "
            f"score={score:.3f}, decision={should_demote}"
        )

        return should_demote, score_details

    def check_overflow(self, tier_name: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if tier has exceeded capacity (overflow).

        Args:
            tier_name: Name of tier to check

        Returns:
            Tuple of (is_overflow: bool, details: dict)
            details contains: entry_count, max_entries, overflow_amount

        Example:
            >>> is_overflow, details = engine.check_overflow("ephemeral")
            >>> if is_overflow:
            ...     print(f"Overflow by {details['overflow_amount']} entries")
        """
        if tier_name not in self._policies:
            return False, {
                "is_overflow": False,
                "reason": f"Tier '{tier_name}' not found in policies",
                "available_tiers": list(self._policies.keys()),
            }

        policy = self._policies[tier_name]

        # If no max_entries, cannot overflow
        if policy.max_entries is None:
            return False, {
                "is_overflow": False,
                "tier": tier_name,
                "reason": "Tier has unlimited capacity (no max_entries)",
                "max_entries": None,
            }

        # Get current entry count
        entry_count = 0  # TODO: Get from registry.get_statistics(tier_name)

        is_overflow = entry_count > policy.max_entries
        overflow_amount = max(0, entry_count - policy.max_entries)

        details = {
            "is_overflow": is_overflow,
            "tier": tier_name,
            "entry_count": entry_count,
            "max_entries": policy.max_entries,
            "overflow_amount": overflow_amount,
            "capacity_utilization": entry_count / policy.max_entries,
        }

        if is_overflow:
            details["reason"] = (
                f"Tier has {entry_count} entries, exceeds max_entries "
                f"of {policy.max_entries} by {overflow_amount}"
            )
        else:
            details["reason"] = (
                f"Tier has {entry_count} entries, within max_entries " f"of {policy.max_entries}"
            )

        logger.debug(
            f"Overflow check for '{tier_name}': count={entry_count}, "
            f"max={policy.max_entries}, overflow={is_overflow}"
        )

        return is_overflow, details

    def get_promotion_path(self, entry: MemoryEntry, from_tier: str) -> str | None:
        """
        Determine optimal target tier for promoting an entry.

        Args:
            entry: MemoryEntry to find promotion path for
            from_tier: Current tier name

        Returns:
            Target tier name if promotion is possible, None otherwise

        Example:
            >>> target = engine.get_promotion_path(entry, "ephemeral")
            >>> if target:
            ...     print(f"Promote to: {target}")
        """
        if from_tier not in self._policies:
            logger.warning(f"Source tier '{from_tier}' not found in policies")
            return None

        # Get tier index in hierarchy
        try:
            current_index = self._TIER_ORDER.index(from_tier)
        except ValueError:
            logger.warning(f"Tier '{from_tier}' not in tier hierarchy")
            return None

        # Cannot promote from highest tier
        if current_index >= len(self._TIER_ORDER) - 1:
            logger.debug(f"Tier '{from_tier}' is already highest tier")
            return None

        # Next tier in hierarchy
        next_tier = self._TIER_ORDER[current_index + 1]

        # Check if next tier exists in policies
        if next_tier not in self._policies:
            logger.warning(f"Next tier '{next_tier}' not found in policies")
            return None

        # Check if entry qualifies for promotion
        should_promote, details = self.should_promote(entry, from_tier, next_tier)

        if should_promote:
            logger.debug(
                f"Promotion path found: {from_tier} → {next_tier} "
                f"(score: {details['score']:.3f})"
            )
            return next_tier
        else:
            logger.debug(
                f"Entry does not qualify for promotion to {next_tier} "
                f"(score: {details['score']:.3f} < threshold: {details['threshold']:.3f})"
            )
            return None

    def get_demotion_path(
        self, entry: MemoryEntry, from_tier: str, capacity_pressure: float = 0.0
    ) -> str | None:
        """
        Determine optimal target tier for demoting an entry.

        Args:
            entry: MemoryEntry to find demotion path for
            from_tier: Current tier name
            capacity_pressure: Current capacity pressure (0.0-1.0)

        Returns:
            Target tier name if demotion is needed, None otherwise

        Example:
            >>> target = engine.get_demotion_path(entry, "session", capacity_pressure=0.9)
            >>> if target:
            ...     print(f"Demote to: {target}")
        """
        if from_tier not in self._policies:
            logger.warning(f"Source tier '{from_tier}' not found in policies")
            return None

        # Get tier index in hierarchy
        try:
            current_index = self._TIER_ORDER.index(from_tier)
        except ValueError:
            logger.warning(f"Tier '{from_tier}' not in tier hierarchy")
            return None

        # Cannot demote from lowest tier
        if current_index <= 0:
            logger.debug(f"Tier '{from_tier}' is already lowest tier")
            return None

        # Previous tier in hierarchy
        prev_tier = self._TIER_ORDER[current_index - 1]

        # Check if previous tier exists in policies
        if prev_tier not in self._policies:
            logger.warning(f"Previous tier '{prev_tier}' not found in policies")
            return None

        # Check if entry should be demoted
        should_demote, details = self.should_demote(
            entry, from_tier, prev_tier, capacity_pressure=capacity_pressure
        )

        if should_demote:
            logger.debug(
                f"Demotion path found: {from_tier} → {prev_tier} "
                f"(score: {details['score']:.3f}, pressure: {capacity_pressure:.2f})"
            )
            return prev_tier
        else:
            logger.debug(
                f"Entry does not qualify for demotion to {prev_tier} "
                f"(score: {details['score']:.3f} < threshold: {details['threshold']:.3f})"
            )
            return None

    def _is_valid_promotion_path(self, from_tier: str, to_tier: str) -> bool:
        """
        Check if promotion path is valid (moving up the hierarchy).

        Args:
            from_tier: Source tier name
            to_tier: Target tier name

        Returns:
            True if valid promotion path, False otherwise
        """
        try:
            from_index = self._TIER_ORDER.index(from_tier)
            to_index = self._TIER_ORDER.index(to_tier)
            return to_index > from_index  # Must move up
        except ValueError:
            return False

    def _is_valid_demotion_path(self, from_tier: str, to_tier: str) -> bool:
        """
        Check if demotion path is valid (moving down the hierarchy).

        Args:
            from_tier: Source tier name
            to_tier: Target tier name

        Returns:
            True if valid demotion path, False otherwise
        """
        try:
            from_index = self._TIER_ORDER.index(from_tier)
            to_index = self._TIER_ORDER.index(to_tier)
            return to_index < from_index  # Must move down
        except ValueError:
            return False

    def should_compact(
        self, tier_name: str, current_count: int | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if a tier should be compacted based on policy.

        Compaction is triggered when a tier exceeds its compaction_threshold
        as defined in the tier's policy. This helps manage storage costs
        and query performance by summarizing old/less important entries.

        Args:
            tier_name: Name of tier to check for compaction
            current_count: Current entry count (None = query from adapter)

        Returns:
            Tuple of (should_compact: bool, details: dict)

            details contains:
                - tier: str - Tier name
                - current_count: int - Current entry count
                - threshold: int|None - Compaction threshold from policy
                - over_threshold: int - How many entries over threshold
                - reason: str - Human-readable explanation

        Example:
            >>> should, details = engine.should_compact("persistent")
            >>> if should:
            ...     print(f"Compact {details['tier']}: {details['reason']}")
            ...     # Compact persistent: 15,000 entries exceeds threshold of 10,000

            >>> should, details = engine.should_compact("session", current_count=5000)
            >>> if not should:
            ...     print(f"No compaction needed: {details['reason']}")
        """
        # Get policy for tier
        policy = self._policies.get(tier_name)
        if not policy:
            return False, {
                "tier": tier_name,
                "current_count": 0,
                "threshold": None,
                "over_threshold": 0,
                "reason": f"Tier '{tier_name}' not found in policies",
            }

        # Check if compaction is enabled for this tier
        if policy.compaction_threshold is None:
            # Check if this is because tier has unlimited capacity (no max_entries)
            if policy.max_entries is None:
                reason = f"Tier '{tier_name}' has unlimited capacity (no compaction needed)"
            else:
                reason = f"Tier '{tier_name}' has no compaction_threshold configured"

            return False, {
                "tier": tier_name,
                "current_count": current_count or 0,
                "threshold": None,
                "over_threshold": 0,
                "max_entries": policy.max_entries,
                "reason": reason,
            }

        # Get current entry count
        if current_count is None:
            try:
                adapter = self.adapter_registry.get_adapter(tier_name)
                current_count = adapter.count()
            except Exception as e:
                logger.warning(
                    f"Failed to get count for tier '{tier_name}': {e}. " "Assuming count = 0"
                )
                current_count = 0

        # Check if threshold is exceeded
        threshold = policy.compaction_threshold
        if current_count >= threshold:
            over_threshold = current_count - threshold
            return True, {
                "tier": tier_name,
                "current_count": current_count,
                "threshold": threshold,
                "over_threshold": over_threshold,
                "reason": (
                    f"{current_count:,} entries exceeds threshold of {threshold:,} "
                    f"(over by {over_threshold:,})"
                ),
            }
        else:
            under_threshold = threshold - current_count
            return False, {
                "tier": tier_name,
                "current_count": current_count,
                "threshold": threshold,
                "over_threshold": 0,
                "reason": (
                    f"{current_count:,} entries is below threshold of {threshold:,} "
                    f"(under by {under_threshold:,})"
                ),
            }
