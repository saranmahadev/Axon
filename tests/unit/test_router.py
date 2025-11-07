"""
Tests for Router.

Validates tier selection, routing operations (store/recall/forget),
automatic promotion logic, and statistics tracking.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.core.policy_engine import PolicyEngine
from axon.core.router import Router
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter


def create_test_entry(
    text: str = "test memory", importance: float = 0.5, entry_id: str = None, access_count: int = 0
) -> MemoryEntry:
    """Helper to create test MemoryEntry."""
    metadata = MemoryMetadata(
        importance=importance,
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        tags=["test"],
        user_id="test_user",
    )

    # Add access_count to extra fields
    metadata.__pydantic_extra__ = {"access_count": access_count}

    return MemoryEntry(text=text, metadata=metadata, id=entry_id or "test-entry-id")


@pytest.fixture
def mock_config():
    """Create mock MemoryConfig."""
    config = Mock(spec=MemoryConfig)
    config.tiers = {
        "ephemeral": EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
        "session": SessionPolicy(adapter_type="redis", ttl_seconds=3600),
        "persistent": PersistentPolicy(adapter_type="chroma"),
    }
    return config


@pytest.fixture
def mock_registry():
    """Create mock AdapterRegistry."""
    registry = Mock(spec=AdapterRegistry)

    # Mock adapter instances
    mock_adapter = AsyncMock()
    mock_adapter.save = AsyncMock(return_value="saved-id-123")
    mock_adapter.query = AsyncMock(return_value=[])
    mock_adapter.delete = AsyncMock(return_value=1)

    registry.get_adapter = AsyncMock(return_value=mock_adapter)
    registry.get_all_tiers = Mock(return_value=["ephemeral", "session", "persistent"])

    return registry


@pytest.fixture
def mock_policy_engine():
    """Create mock PolicyEngine."""
    engine = Mock(spec=PolicyEngine)
    engine.get_promotion_path = Mock(return_value=None)
    engine.get_demotion_path = Mock(return_value=None)
    engine.check_overflow = Mock(return_value=(False, {"is_overflow": False}))
    return engine


@pytest.fixture
def router(mock_config, mock_registry):
    """Create Router without policy engine."""
    return Router(config=mock_config, registry=mock_registry)


@pytest.fixture
def router_with_policy(mock_config, mock_registry, mock_policy_engine):
    """Create Router with policy engine."""
    return Router(config=mock_config, registry=mock_registry, policy_engine=mock_policy_engine)


# ============================================================================
# Test Initialization
# ============================================================================


class TestRouterInit:
    """Test Router initialization."""

    def test_init_success(self, mock_config, mock_registry):
        """Test successful initialization."""
        router = Router(config=mock_config, registry=mock_registry)

        assert router.config is mock_config
        assert router.registry is mock_registry
        assert router.policy_engine is None
        assert "ephemeral" in router._tier_stats
        assert "session" in router._tier_stats
        assert "persistent" in router._tier_stats

    def test_init_with_policy_engine(self, mock_config, mock_registry, mock_policy_engine):
        """Test initialization with policy engine."""
        router = Router(
            config=mock_config, registry=mock_registry, policy_engine=mock_policy_engine
        )

        assert router.policy_engine is mock_policy_engine


# ============================================================================
# Test Tier Selection
# ============================================================================


class TestTierSelection:
    """Test tier selection logic."""

    @pytest.mark.asyncio
    async def test_select_tier_high_importance(self, router):
        """Test tier selection for high importance entry."""
        entry = create_test_entry(importance=0.9)
        tier = await router.select_tier(entry)
        assert tier == "persistent"

    @pytest.mark.asyncio
    async def test_select_tier_medium_importance(self, router):
        """Test tier selection for medium importance entry."""
        entry = create_test_entry(importance=0.5)
        tier = await router.select_tier(entry)
        assert tier == "session"

    @pytest.mark.asyncio
    async def test_select_tier_low_importance(self, router):
        """Test tier selection for low importance entry."""
        entry = create_test_entry(importance=0.2)
        tier = await router.select_tier(entry)
        assert tier == "ephemeral"

    @pytest.mark.asyncio
    async def test_select_tier_with_explicit_hint(self, router):
        """Test tier selection with explicit tier hint in metadata."""
        entry = create_test_entry(importance=0.5)
        entry.metadata.__pydantic_extra__ = {"tier": "persistent"}

        tier = await router.select_tier(entry)
        assert tier == "persistent"

    @pytest.mark.asyncio
    async def test_select_tier_boundary_persistent(self, router):
        """Test tier selection at persistent boundary (0.7)."""
        entry = create_test_entry(importance=0.7)
        tier = await router.select_tier(entry)
        assert tier == "persistent"

    @pytest.mark.asyncio
    async def test_select_tier_boundary_session(self, router):
        """Test tier selection at session boundary (0.3)."""
        entry = create_test_entry(importance=0.3)
        tier = await router.select_tier(entry)
        assert tier == "session"


# ============================================================================
# Test Route Store
# ============================================================================


class TestRouteStore:
    """Test route_store operation."""

    @pytest.mark.asyncio
    async def test_store_basic(self, router, mock_registry):
        """Test basic store operation."""
        entry = create_test_entry(importance=0.5)

        entry_id = await router.route_store(entry)

        assert entry_id == "saved-id-123"
        mock_registry.get_adapter.assert_called_once_with("session")
        assert router._tier_stats["session"]["stores"] == 1

    @pytest.mark.asyncio
    async def test_store_with_explicit_tier(self, router, mock_registry):
        """Test store with explicit tier parameter."""
        entry = create_test_entry(importance=0.2)

        entry_id = await router.route_store(entry, tier="persistent")

        assert entry_id == "saved-id-123"
        mock_registry.get_adapter.assert_called_once_with("persistent")
        assert router._tier_stats["persistent"]["stores"] == 1

    @pytest.mark.asyncio
    async def test_store_invalid_tier_raises(self, router):
        """Test store with invalid tier raises KeyError."""
        entry = create_test_entry()

        with pytest.raises(KeyError, match="not found in configuration"):
            await router.route_store(entry, tier="nonexistent")

    @pytest.mark.asyncio
    async def test_store_checks_overflow_with_policy(self, router_with_policy, mock_policy_engine):
        """Test that store checks for overflow when policy engine present."""
        entry = create_test_entry(importance=0.5)

        # Mock overflow condition
        mock_policy_engine.check_overflow.return_value = (
            True,
            {"is_overflow": True, "overflow_amount": 5},
        )

        await router_with_policy.route_store(entry)

        mock_policy_engine.check_overflow.assert_called_once_with("session")

    @pytest.mark.asyncio
    async def test_store_updates_statistics(self, router):
        """Test that store updates tier statistics."""
        entry1 = create_test_entry(importance=0.9)
        entry2 = create_test_entry(importance=0.9)

        await router.route_store(entry1)
        await router.route_store(entry2)

        assert router._tier_stats["persistent"]["stores"] == 2


# ============================================================================
# Test Route Recall
# ============================================================================


class TestRouteRecall:
    """Test route_recall operation."""

    @pytest.mark.asyncio
    async def test_recall_basic(self, router, mock_registry):
        """Test basic recall operation."""
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [
            create_test_entry(entry_id="entry-1"),
            create_test_entry(entry_id="entry-2"),
        ]

        results = await router.route_recall("test query", k=5)

        assert len(results) == 2
        assert results[0].id == "entry-1"

    @pytest.mark.asyncio
    async def test_recall_specific_tiers(self, router, mock_registry):
        """Test recall from specific tiers only."""
        # Reset call count from fixture setup
        mock_registry.get_adapter.reset_mock()

        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [create_test_entry(entry_id="entry-1")]

        await router.route_recall("test", k=5, tiers=["session"])

        # Should query session tier (1 call in test setup + 1 in route_recall)
        assert mock_registry.get_adapter.call_count == 2
        # Verify it was called with "session"
        mock_registry.get_adapter.assert_called_with("session")

    @pytest.mark.asyncio
    async def test_recall_deduplicates_results(self, router, mock_registry):
        """Test that recall deduplicates entries across tiers."""
        # Same entry returned from multiple tiers
        duplicate_entry = create_test_entry(entry_id="duplicate-1")

        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [duplicate_entry]

        results = await router.route_recall("test", k=10)

        # Should only return one instance despite multiple tiers
        entry_ids = [r.id for r in results]
        assert entry_ids.count("duplicate-1") == 1

    @pytest.mark.asyncio
    async def test_recall_updates_access_metadata(self, router, mock_registry):
        """Test that recall updates access metadata."""
        entry = create_test_entry(entry_id="entry-1", access_count=5)

        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [entry]

        results = await router.route_recall("test", k=5)

        # Access count should be incremented
        assert results[0].metadata.__pydantic_extra__["access_count"] == 6
        # Last accessed should be updated
        assert results[0].metadata.last_accessed_at is not None

    @pytest.mark.asyncio
    async def test_recall_checks_promotions(
        self, router_with_policy, mock_registry, mock_policy_engine
    ):
        """Test that recall checks for promotion opportunities."""
        entry = create_test_entry(entry_id="entry-1")

        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [entry]

        # Mock promotion path
        mock_policy_engine.get_promotion_path.return_value = "persistent"

        await router_with_policy.route_recall("test", k=5)

        # Should check promotion path
        mock_policy_engine.get_promotion_path.assert_called()

    @pytest.mark.asyncio
    async def test_recall_executes_promotions(
        self, router_with_policy, mock_registry, mock_policy_engine
    ):
        """Test that recall executes promotions."""
        entry = create_test_entry(entry_id="entry-1")

        # Setup mock adapters for both query and promotion operations
        session_adapter = AsyncMock()
        session_adapter.query = AsyncMock(return_value=[entry])
        session_adapter.delete = AsyncMock(return_value=1)

        persistent_adapter = AsyncMock()
        persistent_adapter.save = AsyncMock(return_value="entry-1")

        # Configure get_adapter to return correct adapter based on tier
        async def get_adapter_side_effect(tier):
            if tier == "session":
                return session_adapter
            elif tier == "persistent":
                return persistent_adapter
            else:
                return AsyncMock()

        mock_registry.get_adapter = AsyncMock(side_effect=get_adapter_side_effect)

        # Mock promotion to persistent
        mock_policy_engine.get_promotion_path.return_value = "persistent"

        await router_with_policy.route_recall("test", k=5)

        # Should update statistics
        assert router_with_policy._tier_stats["session"]["promotions"] == 1

    @pytest.mark.asyncio
    async def test_recall_handles_query_errors_gracefully(self, router, mock_registry):
        """Test that recall continues on query errors."""
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.side_effect = RuntimeError("Query failed")

        # Should not raise, just log and continue
        results = await router.route_recall("test", k=5)

        assert results == []


# ============================================================================
# Test Route Forget
# ============================================================================


class TestRouteForget:
    """Test route_forget operation."""

    @pytest.mark.asyncio
    async def test_forget_by_id(self, router, mock_registry):
        """Test forget operation by entry ID."""
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.delete.return_value = 1

        deleted = await router.route_forget(entry_id="test-id")

        assert deleted >= 1
        mock_adapter.delete.assert_called()

    @pytest.mark.asyncio
    async def test_forget_by_filter(self, router, mock_registry):
        """Test forget operation by filter."""
        mock_filter = Filter(tags=["test"])
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.delete.return_value = 3

        deleted = await router.route_forget(filter=mock_filter)

        assert deleted >= 3

    @pytest.mark.asyncio
    async def test_forget_specific_tier(self, router, mock_registry):
        """Test forget from specific tier only."""
        # Reset call count from fixture setup
        mock_registry.get_adapter.reset_mock()

        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.delete.return_value = 1

        deleted = await router.route_forget(entry_id="test-id", tier="session")

        # Should only query session tier once (in route_forget, not counting fixture setup)
        assert deleted == 1
        # Verify it was called with "session"
        mock_registry.get_adapter.assert_called_with("session")

    @pytest.mark.asyncio
    async def test_forget_without_params_raises(self, router):
        """Test forget without entry_id or filter raises ValueError."""
        with pytest.raises(ValueError, match="Must provide either"):
            await router.route_forget()

    @pytest.mark.asyncio
    async def test_forget_invalid_tier_raises(self, router):
        """Test forget with invalid tier raises KeyError."""
        with pytest.raises(KeyError, match="not found in configuration"):
            await router.route_forget(entry_id="test-id", tier="nonexistent")

    @pytest.mark.asyncio
    async def test_forget_updates_statistics(self, router, mock_registry):
        """Test that forget updates tier statistics."""
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.delete.return_value = 2

        await router.route_forget(entry_id="test-id")

        # Statistics should be updated (exact count depends on tier querying)
        total_forgets = sum(router._tier_stats[t]["forgets"] for t in router._tier_stats)
        assert total_forgets >= 2


# ============================================================================
# Test Statistics and Monitoring
# ============================================================================


class TestStatistics:
    """Test statistics tracking."""

    def test_get_tier_stats_single_tier(self, router):
        """Test getting statistics for single tier."""
        router._tier_stats["session"]["stores"] = 5

        stats = router.get_tier_stats("session")

        assert stats["stores"] == 5
        assert "recalls" in stats

    def test_get_tier_stats_all_tiers(self, router):
        """Test getting statistics for all tiers."""
        stats = router.get_tier_stats()

        assert "ephemeral" in stats
        assert "session" in stats
        assert "persistent" in stats

    def test_reset_stats(self, router):
        """Test resetting statistics."""
        router._tier_stats["session"]["stores"] = 10
        router._tier_stats["persistent"]["recalls"] = 5

        router.reset_stats()

        assert router._tier_stats["session"]["stores"] == 0
        assert router._tier_stats["persistent"]["recalls"] == 0


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestHelperMethods:
    """Test internal helper methods."""

    def test_update_access_metadata(self, router):
        """Test _update_access_metadata helper."""
        entry = create_test_entry(access_count=3)
        original_time = entry.metadata.last_accessed_at

        router._update_access_metadata(entry)

        # Access count should increment
        assert entry.metadata.__pydantic_extra__["access_count"] == 4
        # Timestamp should be updated
        assert entry.metadata.last_accessed_at >= original_time

    @pytest.mark.asyncio
    async def test_promote_entry(self, router, mock_registry):
        """Test _promote_entry helper."""
        entry = create_test_entry(entry_id="test-id")

        await router._promote_entry(entry, "ephemeral", "session")

        # Should save to target and delete from source
        assert mock_registry.get_adapter.call_count == 2
        # Tier hint should be updated
        assert entry.metadata.__pydantic_extra__["tier"] == "session"

    @pytest.mark.asyncio
    async def test_demote_entry(self, router, mock_registry):
        """Test _demote_entry helper."""
        entry = create_test_entry(entry_id="test-id")

        await router._demote_entry(entry, "persistent", "session")

        # Should save to target and delete from source
        assert mock_registry.get_adapter.call_count == 2
        # Tier hint should be updated
        assert entry.metadata.__pydantic_extra__["tier"] == "session"


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_recall_with_empty_results(self, router, mock_registry):
        """Test recall with no results."""
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = []

        results = await router.route_recall("test query", k=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_recall_respects_k_limit(self, router, mock_registry):
        """Test that recall respects k parameter."""
        # Return more entries than k
        mock_adapter = await mock_registry.get_adapter("session")
        mock_adapter.query.return_value = [
            create_test_entry(entry_id=f"entry-{i}") for i in range(10)
        ]

        results = await router.route_recall("test", k=3)

        assert len(results) <= 3

    def test_repr(self, router_with_policy):
        """Test string representation."""
        repr_str = repr(router_with_policy)

        assert "Router" in repr_str
        assert "policy_engine=True" in repr_str
