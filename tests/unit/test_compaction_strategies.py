"""Unit tests for compaction strategies."""

import pytest
from datetime import datetime, timedelta, timezone

from axon.core.compaction_strategies import (
    CompactionStrategy,
    SemanticCompactionStrategy,
    ImportanceCompactionStrategy,
    TimeBasedCompactionStrategy,
    HybridCompactionStrategy,
    CountCompactionStrategy,
    get_strategy,
)
from axon.models.entry import MemoryEntry, MemoryMetadata


@pytest.fixture
def sample_entries():
    """Create sample entries for testing."""
    now = datetime.now(timezone.utc)
    entries = []

    # Create 10 entries with varying properties
    for i in range(10):
        entry = MemoryEntry(
            text=f"Entry {i}: Sample content",
            embedding=[float(i)] * 128 if i % 2 == 0 else None,  # Half have embeddings
            metadata=MemoryMetadata(
                importance=i / 10.0,  # 0.0 to 0.9
                created_at=now - timedelta(days=i * 10),  # 0 to 90 days old
                tags=[f"tag_{i % 3}"],
            ),
        )
        entries.append(entry)

    return entries


class TestSemanticCompactionStrategy:
    """Test semantic similarity-based compaction."""

    def test_initialization(self):
        """Test strategy initialization with valid parameters."""
        strategy = SemanticCompactionStrategy(similarity_threshold=0.9)
        assert strategy.similarity_threshold == 0.9
        assert strategy.name == "semantic"

    def test_initialization_invalid_threshold(self):
        """Test initialization with invalid threshold raises error."""
        with pytest.raises(ValueError, match="similarity_threshold must be in"):
            SemanticCompactionStrategy(similarity_threshold=1.5)

    def test_select_entries_to_compact(self, sample_entries):
        """Test selecting entries for compaction."""
        strategy = SemanticCompactionStrategy()

        # Should select bottom 5 entries (threshold=5)
        selected = strategy.select_entries_to_compact(sample_entries, threshold=5)

        # Should only select entries with embeddings (5 entries)
        assert all(e.has_embedding for e in selected)
        assert len(selected) <= 5

    def test_select_entries_no_embeddings(self):
        """Test selection when no entries have embeddings."""
        entries = [MemoryEntry(text=f"Entry {i}", embedding=None) for i in range(5)]

        strategy = SemanticCompactionStrategy()
        selected = strategy.select_entries_to_compact(entries, threshold=2)

        assert len(selected) == 0

    def test_group_entries_by_similarity(self):
        """Test grouping entries by semantic similarity."""
        # Create entries with similar embeddings
        entries = []
        for i in range(6):
            # Create two clusters: [0,1,2] and [3,4,5]
            base_val = 0.0 if i < 3 else 1.0
            embedding = [base_val + (i % 3) * 0.01] * 128

            entry = MemoryEntry(
                text=f"Entry {i}", embedding=embedding, metadata=MemoryMetadata(importance=0.5)
            )
            entries.append(entry)

        strategy = SemanticCompactionStrategy(similarity_threshold=0.95, min_cluster_size=2)
        groups = strategy.group_entries(entries, batch_size=10)

        # Should create clusters of similar entries
        assert len(groups) >= 1
        for group in groups:
            assert len(group) >= 2  # min_cluster_size

    def test_group_entries_without_embeddings(self):
        """Test fallback batching when embeddings not available."""
        entries = [MemoryEntry(text=f"Entry {i}", embedding=None) for i in range(5)]

        strategy = SemanticCompactionStrategy()
        groups = strategy.group_entries(entries, batch_size=2)

        # Should fall back to simple batching
        assert len(groups) == 3  # 5 entries / 2 per batch = 3 groups


class TestImportanceCompactionStrategy:
    """Test importance-based compaction."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = ImportanceCompactionStrategy(importance_threshold=0.6)
        assert strategy.importance_threshold == 0.6
        assert strategy.name == "importance"

    def test_select_low_importance_entries(self, sample_entries):
        """Test selecting low-importance entries."""
        strategy = ImportanceCompactionStrategy(importance_threshold=0.5)

        selected = strategy.select_entries_to_compact(sample_entries, threshold=5)

        # Should select entries with importance < 0.5
        assert all(e.metadata.importance < 0.5 for e in selected)
        # Should select lower importance entries first
        if len(selected) > 1:
            importances = [e.metadata.importance for e in selected]
            assert importances == sorted(importances)

    def test_group_by_importance_tier(self, sample_entries):
        """Test grouping by importance similarity."""
        strategy = ImportanceCompactionStrategy()

        groups = strategy.group_entries(sample_entries, batch_size=3)

        # Should create groups sorted by importance
        for group in groups:
            assert len(group) <= 3
            # Check that group is sorted by importance
            importances = [e.metadata.importance for e in group]
            assert importances == sorted(importances)


class TestTimeBasedCompactionStrategy:
    """Test time-based compaction."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = TimeBasedCompactionStrategy(age_threshold_days=60)
        assert strategy.age_threshold_days == 60
        assert strategy.name == "time"

    def test_select_old_entries(self, sample_entries):
        """Test selecting older entries."""
        strategy = TimeBasedCompactionStrategy(age_threshold_days=30)

        selected = strategy.select_entries_to_compact(sample_entries, threshold=5)

        # Should select older entries
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        # Most selected entries should be older than cutoff
        old_entries = [
            e for e in selected if e.metadata.created_at.replace(tzinfo=timezone.utc) < cutoff
        ]
        assert len(old_entries) > 0

    def test_group_chronologically(self, sample_entries):
        """Test grouping by time period."""
        strategy = TimeBasedCompactionStrategy()

        groups = strategy.group_entries(sample_entries, batch_size=3)

        # Should create chronologically ordered groups
        for group in groups:
            assert len(group) <= 3
            # Check that group is sorted by date
            dates = [e.metadata.created_at for e in group]
            assert dates == sorted(dates)


class TestCountCompactionStrategy:
    """Test legacy count-based compaction."""

    def test_select_bottom_entries(self, sample_entries):
        """Test selecting bottom 50% by importance."""
        strategy = CountCompactionStrategy()

        selected = strategy.select_entries_to_compact(sample_entries, threshold=8)

        # Should select entries to reach 80% of threshold
        # With 10 entries, threshold=8, target=6.4, so compact 10-6=4 entries
        assert len(selected) <= 4

        # Should select lower importance entries
        if len(selected) > 1:
            importances = [e.metadata.importance for e in selected]
            assert importances == sorted(importances)

    def test_simple_batching(self, sample_entries):
        """Test simple batching logic."""
        strategy = CountCompactionStrategy()

        groups = strategy.group_entries(sample_entries, batch_size=3)

        assert len(groups) == 4  # 10 entries / 3 per batch = 4 groups
        assert all(len(g) <= 3 for g in groups)


class TestHybridCompactionStrategy:
    """Test hybrid multi-strategy compaction."""

    def test_initialization(self):
        """Test hybrid strategy initialization."""
        strategies = [ImportanceCompactionStrategy(), TimeBasedCompactionStrategy()]

        hybrid = HybridCompactionStrategy(strategies, weights=[0.6, 0.4])
        assert len(hybrid.strategies) == 2
        assert hybrid.weights == [0.6, 0.4]
        assert "hybrid" in hybrid.name

    def test_initialization_equal_weights(self):
        """Test initialization with default equal weights."""
        strategies = [ImportanceCompactionStrategy(), TimeBasedCompactionStrategy()]

        hybrid = HybridCompactionStrategy(strategies)
        assert hybrid.weights == [0.5, 0.5]

    def test_initialization_invalid_weights(self):
        """Test initialization with invalid weights."""
        strategies = [ImportanceCompactionStrategy(), TimeBasedCompactionStrategy()]

        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            HybridCompactionStrategy(strategies, weights=[0.5, 0.6])

    def test_combined_selection(self, sample_entries):
        """Test combined selection from multiple strategies."""
        strategies = [
            ImportanceCompactionStrategy(importance_threshold=0.5),
            TimeBasedCompactionStrategy(age_threshold_days=45),
        ]

        hybrid = HybridCompactionStrategy(strategies, weights=[0.5, 0.5])
        selected = hybrid.select_entries_to_compact(sample_entries, threshold=5)

        # Should select entries that both strategies agree on
        assert len(selected) <= len(sample_entries) - 5


class TestGetStrategyFactory:
    """Test strategy factory function."""

    def test_get_semantic_strategy(self):
        """Test creating semantic strategy by name."""
        strategy = get_strategy("semantic", similarity_threshold=0.9)

        assert isinstance(strategy, SemanticCompactionStrategy)
        assert strategy.similarity_threshold == 0.9

    def test_get_importance_strategy(self):
        """Test creating importance strategy by name."""
        strategy = get_strategy("importance", importance_threshold=0.4)

        assert isinstance(strategy, ImportanceCompactionStrategy)
        assert strategy.importance_threshold == 0.4

    def test_get_time_strategy(self):
        """Test creating time strategy by name."""
        strategy = get_strategy("time", age_threshold_days=90)

        assert isinstance(strategy, TimeBasedCompactionStrategy)
        assert strategy.age_threshold_days == 90

    def test_get_count_strategy(self):
        """Test creating count strategy by name."""
        strategy = get_strategy("count")

        assert isinstance(strategy, CountCompactionStrategy)

    def test_get_invalid_strategy(self):
        """Test error on invalid strategy name."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("invalid_strategy")


class TestStrategyIntegration:
    """Integration tests for strategy combinations."""

    def test_semantic_with_real_embeddings(self):
        """Test semantic strategy with realistic embeddings."""
        # Create entries with similar and dissimilar embeddings
        entries = []

        # Cluster 1: Similar embeddings (0.1, 0.1, ...)
        for i in range(3):
            embedding = [0.1 + i * 0.01] * 128
            entries.append(
                MemoryEntry(
                    text=f"Similar entry {i}",
                    embedding=embedding,
                    metadata=MemoryMetadata(importance=0.3),
                )
            )

        # Cluster 2: Different embeddings (0.9, 0.9, ...)
        for i in range(3):
            embedding = [0.9 + i * 0.01] * 128
            entries.append(
                MemoryEntry(
                    text=f"Different entry {i}",
                    embedding=embedding,
                    metadata=MemoryMetadata(importance=0.3),
                )
            )

        strategy = SemanticCompactionStrategy(similarity_threshold=0.98, min_cluster_size=2)
        groups = strategy.group_entries(entries)

        # Should create at least 1 cluster with minimum size
        assert len(groups) >= 1
        assert all(len(g) >= 2 for g in groups)

    def test_all_strategies_return_valid_groups(self, sample_entries):
        """Test that all strategies return valid group structures."""
        strategies = [
            SemanticCompactionStrategy(),
            ImportanceCompactionStrategy(),
            TimeBasedCompactionStrategy(),
            CountCompactionStrategy(),
        ]

        for strategy in strategies:
            selected = strategy.select_entries_to_compact(sample_entries, threshold=5)
            groups = strategy.group_entries(selected if selected else sample_entries)

            # All groups should be non-empty lists
            assert isinstance(groups, list)
            assert all(isinstance(g, list) for g in groups)
            assert all(len(g) > 0 for g in groups)

            # All group items should be MemoryEntry
            for group in groups:
                assert all(isinstance(e, MemoryEntry) for e in group)
