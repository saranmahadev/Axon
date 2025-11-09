"""Advanced compaction strategies for intelligent memory management.

This module provides different strategies for compacting memory entries:
- SemanticCompactionStrategy: Groups semantically similar entries
- ImportanceCompactionStrategy: Prioritizes low-importance entries
- TimeBasedCompactionStrategy: Compacts older entries first
- HybridCompactionStrategy: Combines multiple strategies

Each strategy determines which entries to compact and how to group them
for summarization, enabling fine-grained control over memory lifecycle.
"""

import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from ..models.entry import MemoryEntry


class CompactionStrategy(ABC):
    """Abstract base class for compaction strategies.

    A compaction strategy determines:
    1. Which entries should be compacted
    2. How to group entries for summarization
    3. Priority/ordering of compaction operations

    Implementations should consider:
    - Memory efficiency (reduce storage)
    - Semantic coherence (group related entries)
    - Importance preservation (keep critical information)
    - Temporal relevance (handle recency appropriately)
    """

    @abstractmethod
    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select which entries should be compacted.

        Args:
            entries: All entries in the tier
            threshold: Target number of entries after compaction
            **kwargs: Strategy-specific parameters

        Returns:
            List of entries selected for compaction
        """
        pass

    @abstractmethod
    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Group entries for batch summarization.

        Args:
            entries: Entries to group
            batch_size: Maximum entries per group
            **kwargs: Strategy-specific parameters

        Returns:
            List of entry groups, where each group will be summarized together
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging and identification."""
        pass


class SemanticCompactionStrategy(CompactionStrategy):
    """Compact entries based on semantic similarity using embeddings.

    This strategy:
    1. Identifies semantically similar entries using cosine similarity
    2. Groups similar entries into clusters
    3. Compacts each cluster into a single summary

    Benefits:
    - Reduces redundancy by merging similar information
    - Preserves semantic diversity
    - Maintains coherent summaries within clusters

    Example:
        >>> strategy = SemanticCompactionStrategy(similarity_threshold=0.85)
        >>> groups = strategy.group_entries(entries)
        >>> # Entries with >85% similarity are grouped together
    """

    def __init__(self, similarity_threshold: float = 0.85, min_cluster_size: int = 2):
        """Initialize semantic compaction strategy.

        Args:
            similarity_threshold: Minimum cosine similarity (0.0-1.0) to group entries
            min_cluster_size: Minimum entries needed to form a cluster

        Raises:
            ValueError: If similarity_threshold not in [0.0, 1.0]
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be in [0.0, 1.0], got {similarity_threshold}"
            )

        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size

    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select entries with embeddings for semantic compaction.

        Prioritizes:
        1. Entries with embeddings (required for similarity)
        2. Lower importance entries
        3. Older entries

        Args:
            entries: All entries in tier
            threshold: Target entry count
            **kwargs: Additional parameters

        Returns:
            Entries selected for compaction (with embeddings)
        """
        # Filter to only entries with embeddings
        entries_with_embeddings = [e for e in entries if e.has_embedding]

        if not entries_with_embeddings:
            return []

        # Calculate how many to compact
        entries_to_compact_count = max(0, len(entries) - threshold)

        if entries_to_compact_count == 0:
            return []

        # Sort by importance (low first) and date (old first)
        sorted_entries = sorted(
            entries_with_embeddings, key=lambda e: (e.metadata.importance, e.metadata.created_at)
        )

        # Select bottom entries
        return sorted_entries[:entries_to_compact_count]

    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Group entries by semantic similarity using clustering.

        Uses greedy clustering algorithm:
        1. Start with first entry as cluster seed
        2. Add similar entries (above threshold) to cluster
        3. Continue with remaining entries

        Args:
            entries: Entries to group (must have embeddings)
            batch_size: Maximum entries per group
            **kwargs: Additional parameters

        Returns:
            List of semantically similar entry groups
        """
        if not entries:
            return []

        # Filter entries with embeddings
        entries_with_emb = [e for e in entries if e.has_embedding]

        if not entries_with_emb:
            # Fallback to simple batching
            return self._simple_batching(entries, batch_size)

        clusters: list[list[MemoryEntry]] = []
        remaining = entries_with_emb.copy()

        while remaining:
            # Start new cluster with first remaining entry
            seed = remaining.pop(0)
            cluster = [seed]
            seed_embedding = np.array(seed.embedding)

            # Find similar entries
            to_remove = []
            for i, entry in enumerate(remaining):
                if len(cluster) >= batch_size:
                    break

                # Calculate cosine similarity
                entry_embedding = np.array(entry.embedding)
                similarity = self._cosine_similarity(seed_embedding, entry_embedding)

                if similarity >= self.similarity_threshold:
                    cluster.append(entry)
                    to_remove.append(i)

            # Remove entries added to cluster
            for i in reversed(to_remove):
                remaining.pop(i)

            # Only create cluster if it meets minimum size
            if len(cluster) >= self.min_cluster_size:
                clusters.append(cluster)
            else:
                # Don't compact single/small clusters - keep original entries
                pass

        return clusters

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _simple_batching(
        self, entries: list[MemoryEntry], batch_size: int
    ) -> list[list[MemoryEntry]]:
        """Fallback batching when embeddings not available."""
        batches = []
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            if batch:
                batches.append(batch)
        return batches

    @property
    def name(self) -> str:
        return "semantic"


class ImportanceCompactionStrategy(CompactionStrategy):
    """Compact low-importance entries first.

    This strategy:
    1. Sorts entries by importance score
    2. Selects lowest-importance entries for compaction
    3. Groups entries by importance tier

    Benefits:
    - Preserves high-value memories
    - Reduces storage of low-priority information
    - Simple and predictable behavior

    Example:
        >>> strategy = ImportanceCompactionStrategy(importance_threshold=0.5)
        >>> selected = strategy.select_entries_to_compact(entries, threshold=1000)
        >>> # Compacts entries with importance < 0.5
    """

    def __init__(self, importance_threshold: float = 0.5):
        """Initialize importance-based compaction.

        Args:
            importance_threshold: Compact entries below this threshold first
        """
        if not 0.0 <= importance_threshold <= 1.0:
            raise ValueError(
                f"importance_threshold must be in [0.0, 1.0], got {importance_threshold}"
            )

        self.importance_threshold = importance_threshold

    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select lowest-importance entries for compaction.

        Args:
            entries: All entries in tier
            threshold: Target entry count
            **kwargs: Additional parameters

        Returns:
            Low-importance entries selected for compaction
        """
        if len(entries) <= threshold:
            return []

        # Sort by importance (lowest first), then by date (oldest first)
        sorted_entries = sorted(
            entries, key=lambda e: (e.metadata.importance, e.metadata.created_at)
        )

        # Calculate how many to compact
        entries_to_compact_count = len(entries) - threshold

        # Select bottom entries
        selected = sorted_entries[:entries_to_compact_count]

        # Filter to only entries below threshold
        selected = [e for e in selected if e.metadata.importance < self.importance_threshold]

        return selected

    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Group entries by importance tier.

        Creates groups where entries have similar importance scores,
        making summaries more coherent.

        Args:
            entries: Entries to group
            batch_size: Maximum entries per group
            **kwargs: Additional parameters

        Returns:
            Groups of similarly-important entries
        """
        if not entries:
            return []

        # Sort by importance
        sorted_entries = sorted(entries, key=lambda e: e.metadata.importance)

        # Group into batches
        groups = []
        for i in range(0, len(sorted_entries), batch_size):
            batch = sorted_entries[i : i + batch_size]
            if batch:
                groups.append(batch)

        return groups

    @property
    def name(self) -> str:
        return "importance"


class TimeBasedCompactionStrategy(CompactionStrategy):
    """Compact older entries first.

    This strategy:
    1. Identifies entries older than a threshold
    2. Groups entries by time period
    3. Preserves recent memories

    Benefits:
    - Recency bias (keep recent information)
    - Predictable aging of memories
    - Good for time-series data

    Example:
        >>> strategy = TimeBasedCompactionStrategy(age_threshold_days=30)
        >>> selected = strategy.select_entries_to_compact(entries, threshold=1000)
        >>> # Compacts entries older than 30 days
    """

    def __init__(self, age_threshold_days: int = 30):
        """Initialize time-based compaction.

        Args:
            age_threshold_days: Compact entries older than this many days
        """
        if age_threshold_days < 0:
            raise ValueError(f"age_threshold_days must be >= 0, got {age_threshold_days}")

        self.age_threshold_days = age_threshold_days

    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select entries older than threshold.

        Args:
            entries: All entries in tier
            threshold: Target entry count
            **kwargs: Additional parameters

        Returns:
            Old entries selected for compaction
        """
        if len(entries) <= threshold:
            return []

        # Calculate age cutoff
        cutoff_date = datetime.now() - timedelta(days=self.age_threshold_days)

        # Filter old entries
        old_entries = [
            e for e in entries if e.metadata.created_at.replace(tzinfo=None) < cutoff_date
        ]

        if not old_entries:
            # If no old entries, fall back to oldest entries
            sorted_entries = sorted(entries, key=lambda e: e.metadata.created_at)
            entries_to_compact_count = len(entries) - threshold
            return sorted_entries[:entries_to_compact_count]

        # Sort old entries by date (oldest first)
        sorted_old = sorted(old_entries, key=lambda e: e.metadata.created_at)

        # Calculate how many to compact
        entries_to_compact_count = len(entries) - threshold

        # Return oldest entries up to the limit
        return sorted_old[:entries_to_compact_count]

    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Group entries by time period.

        Groups entries from similar time periods together for
        chronologically coherent summaries.

        Args:
            entries: Entries to group
            batch_size: Maximum entries per group
            **kwargs: Additional parameters

        Returns:
            Chronologically grouped entries
        """
        if not entries:
            return []

        # Sort by date (oldest first)
        sorted_entries = sorted(entries, key=lambda e: e.metadata.created_at)

        # Group into batches
        groups = []
        for i in range(0, len(sorted_entries), batch_size):
            batch = sorted_entries[i : i + batch_size]
            if batch:
                groups.append(batch)

        return groups

    @property
    def name(self) -> str:
        return "time"


class HybridCompactionStrategy(CompactionStrategy):
    """Combine multiple compaction strategies.

    This strategy:
    1. Uses multiple strategies in sequence
    2. Each strategy filters/scores entries
    3. Final selection based on combined scores

    Benefits:
    - Flexible multi-criteria compaction
    - Balances different priorities
    - Customizable weighting

    Example:
        >>> strategy = HybridCompactionStrategy(
        ...     strategies=[
        ...         ImportanceCompactionStrategy(importance_threshold=0.4),
        ...         TimeBasedCompactionStrategy(age_threshold_days=60)
        ...     ],
        ...     weights=[0.6, 0.4]  # 60% importance, 40% time
        ... )
    """

    def __init__(self, strategies: list[CompactionStrategy], weights: list[float] | None = None):
        """Initialize hybrid strategy.

        Args:
            strategies: List of strategies to combine
            weights: Optional weights for each strategy (must sum to 1.0)

        Raises:
            ValueError: If strategies empty or weights invalid
        """
        if not strategies:
            raise ValueError("strategies list cannot be empty")

        if weights is not None:
            if len(weights) != len(strategies):
                raise ValueError(
                    f"weights length ({len(weights)}) must match strategies length ({len(strategies)})"
                )
            if not abs(sum(weights) - 1.0) < 0.01:
                raise ValueError(f"weights must sum to 1.0, got {sum(weights)}")
        else:
            # Equal weights
            weights = [1.0 / len(strategies)] * len(strategies)

        self.strategies = strategies
        self.weights = weights

    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select entries using combined strategy scores.

        Args:
            entries: All entries in tier
            threshold: Target entry count
            **kwargs: Additional parameters

        Returns:
            Entries selected by combined strategies
        """
        if len(entries) <= threshold:
            return []

        # Get selections from each strategy
        selections = []
        for strategy in self.strategies:
            selected = strategy.select_entries_to_compact(entries, threshold, **kwargs)
            selections.append(set(e.id for e in selected))

        # Score entries based on how many strategies selected them
        entry_scores = {}
        for entry in entries:
            score = 0.0
            for i, selection in enumerate(selections):
                if entry.id in selection:
                    score += self.weights[i]
            entry_scores[entry.id] = score

        # Sort by combined score (highest score = most strategies want to compact)
        sorted_entries = sorted(
            entries, key=lambda e: (entry_scores[e.id], -e.metadata.importance), reverse=True
        )

        # Select top entries
        entries_to_compact_count = len(entries) - threshold
        return sorted_entries[:entries_to_compact_count]

    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Group entries using first strategy's grouping logic.

        Args:
            entries: Entries to group
            batch_size: Maximum entries per group
            **kwargs: Additional parameters

        Returns:
            Groups from first strategy
        """
        # Use first strategy's grouping logic
        return self.strategies[0].group_entries(entries, batch_size, **kwargs)

    @property
    def name(self) -> str:
        strategy_names = [s.name for s in self.strategies]
        return f"hybrid({'+'.join(strategy_names)})"


class CountCompactionStrategy(CompactionStrategy):
    """Simple count-based compaction (legacy compatibility).

    This is the original compaction strategy that compacts when
    entry count exceeds a threshold. Kept for backward compatibility.

    Compacts bottom 50% of entries by importance when threshold exceeded.
    """

    def select_entries_to_compact(
        self, entries: list[MemoryEntry], threshold: int, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Select bottom 50% of entries by importance."""
        if len(entries) <= threshold:
            return []

        # Sort by importance (low first) and date (old first)
        sorted_entries = sorted(
            entries, key=lambda e: (e.metadata.importance, e.metadata.created_at)
        )

        # Compact to 80% of threshold
        target_count = int(threshold * 0.8)
        entries_to_compact_count = len(entries) - target_count

        return sorted_entries[:entries_to_compact_count]

    def group_entries(
        self, entries: list[MemoryEntry], batch_size: int = 100, **kwargs: Any
    ) -> list[list[MemoryEntry]]:
        """Simple batching."""
        groups = []
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            if batch:
                groups.append(batch)
        return groups

    @property
    def name(self) -> str:
        return "count"


def get_strategy(strategy_name: str, **kwargs: Any) -> CompactionStrategy:
    """Factory function to create compaction strategies by name.

    Args:
        strategy_name: Name of strategy ("semantic", "importance", "time", "count")
        **kwargs: Strategy-specific parameters

    Returns:
        CompactionStrategy instance

    Raises:
        ValueError: If strategy_name is invalid

    Example:
        >>> strategy = get_strategy("semantic", similarity_threshold=0.9)
        >>> strategy = get_strategy("importance", importance_threshold=0.3)
        >>> strategy = get_strategy("time", age_threshold_days=90)
    """
    strategies = {
        "semantic": SemanticCompactionStrategy,
        "importance": ImportanceCompactionStrategy,
        "time": TimeBasedCompactionStrategy,
        "count": CountCompactionStrategy,
    }

    if strategy_name not in strategies:
        raise ValueError(
            f"Unknown strategy: '{strategy_name}'. "
            f"Available strategies: {list(strategies.keys())}"
        )

    strategy_class = strategies[strategy_name]
    return strategy_class(**kwargs)
