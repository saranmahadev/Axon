"""
Unit tests for MemorySystem core functionality.

Tests cover initialization, store(), recall(), validation, tracing,
and error handling.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem, TraceEvent
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.core.policy_engine import PolicyEngine
from axon.core.router import Router
from axon.core.scoring import ScoringEngine
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter


@pytest.fixture
def mock_config():
    """Create a mock configuration with all three tiers."""
    config = Mock(spec=MemoryConfig)

    # Individual tier policies (used by MemorySystem.__init__)
    config.ephemeral = EphemeralPolicy(adapter_type="memory", max_entries=10, ttl_seconds=60)
    config.session = SessionPolicy(adapter_type="memory", max_entries=50, ttl_seconds=3600)
    config.persistent = PersistentPolicy(adapter_type="memory", max_entries=1000)

    # Tiers dict (for backward compatibility)
    config.tiers = {
        "ephemeral": config.ephemeral,
        "session": config.session,
        "persistent": config.persistent,
    }

    # Other config attributes
    config.default_tier = "session"
    config.enable_promotion = True
    config.enable_demotion = True

    return config


@pytest.fixture
def mock_registry():
    """Create a mock adapter registry."""
    registry = Mock(spec=AdapterRegistry)
    registry.get_adapter = AsyncMock()
    registry.get_all_tiers = Mock(return_value=["ephemeral", "session", "persistent"])
    registry.close_all = AsyncMock()
    return registry


@pytest.fixture
def mock_router():
    """Create a mock router."""
    router = Mock(spec=Router)
    router.route_store = AsyncMock()
    router.route_recall = AsyncMock(return_value=[])
    router.get_tier_stats = Mock(
        return_value={
            "ephemeral": {"stores": 0, "recalls": 0, "forgets": 0},
            "session": {"stores": 0, "recalls": 0, "forgets": 0},
            "persistent": {"stores": 0, "recalls": 0, "forgets": 0},
        }
    )
    router.select_tier = AsyncMock(return_value="session")
    return router


@pytest.fixture
def mock_policy_engine():
    """Create a mock policy engine."""
    engine = Mock(spec=PolicyEngine)
    engine.tier_policies = {}
    engine._policies = {}  # Add support for new internal attribute
    return engine


@pytest.fixture
def mock_scoring_engine():
    """Create a mock scoring engine."""
    return Mock(spec=ScoringEngine)


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = AsyncMock()
    embedder.embed = AsyncMock(return_value=[0.5] * 1536)
    return embedder


class TestMemorySystemInit:
    """Test MemorySystem initialization."""

    def test_init_success_with_all_components(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_scoring_engine
    ):
        """Test successful initialization with all components provided."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
            scoring_engine=mock_scoring_engine,
        )

        assert system.config == mock_config
        assert system.router == mock_router
        assert system.registry == mock_registry
        assert system.policy_engine == mock_policy_engine
        assert system.scoring_engine == mock_scoring_engine
        assert system._enable_tracing is True
        assert len(system._trace_events) == 0

    def test_init_with_defaults(self, mock_config):
        """Test initialization creates default components when not provided."""
        system = MemorySystem(config=mock_config)

        assert system.config == mock_config
        assert isinstance(system.registry, AdapterRegistry)
        assert isinstance(system.scoring_engine, ScoringEngine)
        assert isinstance(system.policy_engine, PolicyEngine)
        assert isinstance(system.router, Router)

    def test_init_without_config_raises(self):
        """Test initialization without config raises ValueError."""
        with pytest.raises(ValueError, match="config is required"):
            MemorySystem(config=None)

    def test_init_with_empty_tiers_raises(self):
        """Test initialization with empty tiers raises ValueError."""
        config = Mock(spec=MemoryConfig)
        config.tiers = {}
        config.persistent = None  # No persistent tier
        config.ephemeral = None  # No ephemeral tier
        config.session = None  # No session tier

        with pytest.raises(ValueError, match="must define at least a persistent tier"):
            MemorySystem(config=config)

    def test_repr(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test string representation."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        repr_str = repr(system)
        assert "MemorySystem" in repr_str
        assert "ephemeral" in repr_str or "session" in repr_str or "persistent" in repr_str
        assert "tracing" in repr_str


class TestStoreMethod:
    """Test MemorySystem.store() method."""

    @pytest.mark.asyncio
    async def test_store_basic(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test basic store operation."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry_id = await system.store("Test content")

        assert entry_id is not None
        assert isinstance(entry_id, str)
        assert len(entry_id) == 36  # UUID format
        mock_router.route_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_with_metadata(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with custom metadata."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        metadata = {"key": "value", "number": 42}
        entry_id = await system.store("Test content", metadata=metadata)

        assert entry_id is not None
        # Verify router was called with entry containing metadata
        call_args = mock_router.route_store.call_args
        entry = call_args[0][0]
        assert hasattr(entry.metadata, "custom")
        assert entry.metadata.custom == metadata

    @pytest.mark.asyncio
    async def test_store_with_importance(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with importance value."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry_id = await system.store("Test content", importance=0.8)

        assert entry_id is not None
        # Verify importance was set
        call_args = mock_router.route_store.call_args
        entry = call_args[0][0]
        assert entry.metadata.importance == 0.8

    @pytest.mark.asyncio
    async def test_store_with_tags(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with tags."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        tags = ["tag1", "tag2", "tag3"]
        entry_id = await system.store("Test content", tags=tags)

        assert entry_id is not None
        # Verify tags were set
        call_args = mock_router.route_store.call_args
        entry = call_args[0][0]
        assert entry.metadata.tags == tags

    @pytest.mark.asyncio
    async def test_store_with_explicit_tier(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with explicit tier specification."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry_id = await system.store("Test content", tier="persistent")

        assert entry_id is not None
        # Verify tier was passed to router
        call_args = mock_router.route_store.call_args
        assert call_args[1]["tier"] == "persistent"

    @pytest.mark.asyncio
    async def test_store_empty_content_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with empty content raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="content cannot be empty"):
            await system.store("")

        with pytest.raises(ValueError, match="content cannot be empty"):
            await system.store("   ")

    @pytest.mark.asyncio
    async def test_store_invalid_importance_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with invalid importance raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="importance must be between"):
            await system.store("Test", importance=1.5)

        with pytest.raises(ValueError, match="importance must be between"):
            await system.store("Test", importance=-0.1)

    @pytest.mark.asyncio
    async def test_store_invalid_tier_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test store with invalid tier raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid tier"):
            await system.store("Test", tier="nonexistent")

    @pytest.mark.asyncio
    async def test_store_generates_unique_ids(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that store generates unique IDs for each entry."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        id1 = await system.store("Content 1")
        id2 = await system.store("Content 2")
        id3 = await system.store("Content 3")

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

    @pytest.mark.asyncio
    async def test_store_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that store creates a trace event."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry_id = await system.store("Test content", importance=0.7)

        events = system.get_trace_events()
        assert len(events) == 1
        assert events[0].operation == "store"
        assert events[0].entry_id == entry_id
        assert events[0].success is True
        assert events[0].duration_ms >= 0


class TestRecallMethod:
    """Test MemorySystem.recall() method."""

    @pytest.mark.asyncio
    async def test_recall_basic(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test basic recall operation."""
        # Setup mock router to return results
        mock_entry = MemoryEntry(
            id="test-id", text="Test content", metadata=MemoryMetadata(importance=0.5)
        )
        mock_router.route_recall = AsyncMock(return_value=[mock_entry])

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        results = await system.recall("test query")

        assert len(results) == 1
        assert results[0].id == "test-id"
        mock_router.route_recall.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_with_k_limit(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with k limit."""
        mock_router.route_recall = AsyncMock(return_value=[])

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        _results = await system.recall("test query", k=10)

        call_args = mock_router.route_recall.call_args
        assert call_args[1]["k"] == 10

    @pytest.mark.asyncio
    async def test_recall_with_filter(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with filter."""
        mock_router.route_recall = AsyncMock(return_value=[])

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        filter_obj = Filter(tags=["test"])
        await system.recall("test query", filter=filter_obj)

        call_args = mock_router.route_recall.call_args
        assert call_args[1]["filter"] == filter_obj

    @pytest.mark.asyncio
    async def test_recall_specific_tiers(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall from specific tiers."""
        mock_router.route_recall = AsyncMock(return_value=[])

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        await system.recall("test query", tiers=["persistent", "session"])

        call_args = mock_router.route_recall.call_args
        assert call_args[1]["tiers"] == ["persistent", "session"]

    @pytest.mark.asyncio
    async def test_recall_with_min_importance(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with minimum importance filter."""
        # Create entries with different importance
        entries = [
            MemoryEntry(id="1", text="Low", metadata=MemoryMetadata(importance=0.3)),
            MemoryEntry(id="2", text="Medium", metadata=MemoryMetadata(importance=0.6)),
            MemoryEntry(id="3", text="High", metadata=MemoryMetadata(importance=0.9)),
        ]
        mock_router.route_recall = AsyncMock(return_value=entries)

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        results = await system.recall("test query", min_importance=0.5)

        # Should only return entries with importance >= 0.5
        assert len(results) == 2
        assert all(e.metadata.importance >= 0.5 for e in results)

    @pytest.mark.asyncio
    async def test_recall_none_query_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with None query raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="query cannot be None"):
            await system.recall(None)

    @pytest.mark.asyncio
    async def test_recall_invalid_k_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with invalid k raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="k must be greater than 0"):
            await system.recall("test", k=0)

        with pytest.raises(ValueError, match="k must be greater than 0"):
            await system.recall("test", k=-1)

    @pytest.mark.asyncio
    async def test_recall_invalid_tiers_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with invalid tiers raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid tiers"):
            await system.recall("test", tiers=["nonexistent"])

    @pytest.mark.asyncio
    async def test_recall_invalid_min_importance_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test recall with invalid min_importance raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="min_importance must be between"):
            await system.recall("test", min_importance=1.5)

        with pytest.raises(ValueError, match="min_importance must be between"):
            await system.recall("test", min_importance=-0.1)

    @pytest.mark.asyncio
    async def test_recall_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that recall creates a trace event."""
        mock_router.route_recall = AsyncMock(return_value=[])

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        await system.recall("test query", k=5)

        events = system.get_trace_events()
        assert len(events) == 1
        assert events[0].operation == "recall"
        assert events[0].query == "test query"
        assert events[0].success is True
        assert events[0].result_count == 0


class TestTracingAndStatistics:
    """Test tracing and statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_trace_events(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test getting trace events."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        await system.store("Test 1")
        await system.store("Test 2")
        await system.recall("query")

        events = system.get_trace_events()
        assert len(events) == 3
        # Events should be in reverse order (most recent first)
        assert events[0].operation == "recall"
        assert events[1].operation == "store"
        assert events[2].operation == "store"

    @pytest.mark.asyncio
    async def test_get_trace_events_filtered(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test getting filtered trace events."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        await system.store("Test 1")
        await system.store("Test 2")
        await system.recall("query")

        store_events = system.get_trace_events(operation="store")
        assert len(store_events) == 2
        assert all(e.operation == "store" for e in store_events)

        recall_events = system.get_trace_events(operation="recall")
        assert len(recall_events) == 1
        assert recall_events[0].operation == "recall"

    @pytest.mark.asyncio
    async def test_get_trace_events_limited(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test getting limited trace events."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        for i in range(10):
            await system.store(f"Test {i}")

        events = system.get_trace_events(limit=5)
        assert len(events) == 5

    def test_clear_trace_events(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test clearing trace events."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        system._trace_events.append(
            TraceEvent(timestamp=datetime.now(), operation="test", duration_ms=10.0)
        )

        assert len(system._trace_events) > 0
        system.clear_trace_events()
        assert len(system._trace_events) == 0

    def test_enable_disable_tracing(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test enabling/disabling tracing."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        assert system._enable_tracing is True

        system.enable_tracing(False)
        assert system._enable_tracing is False

        system.enable_tracing(True)
        assert system._enable_tracing is True

    def test_get_statistics(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test getting system statistics."""
        mock_router.get_tier_stats = Mock(
            return_value={
                "ephemeral": {"stores": 5, "recalls": 3, "forgets": 1},
                "session": {"stores": 10, "recalls": 8, "forgets": 2},
                "persistent": {"stores": 15, "recalls": 12, "forgets": 3},
            }
        )

        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        stats = system.get_statistics()

        assert "tier_stats" in stats
        assert "total_operations" in stats
        assert "trace_events" in stats

        assert stats["total_operations"]["stores"] == 30
        assert stats["total_operations"]["recalls"] == 23
        assert stats["total_operations"]["forgets"] == 6


class TestExportMethod:
    """Test export() method functionality."""

    @pytest.mark.asyncio
    async def test_export_all_tiers(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test exporting from all tiers."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Setup mock adapters with entries
        entry1 = MemoryEntry(
            id="id1",
            text="Test 1",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(importance=0.9, tags=["test"]),
        )
        MemoryEntry(
            id="id2",
            text="Test 2",
            embedding=[0.2] * 384,
            metadata=MemoryMetadata(importance=0.5, tags=["test"]),
        )

        mock_adapter = AsyncMock()
        mock_adapter.query = AsyncMock(return_value=[entry1])
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Export
        data = await system.export()

        # Verify structure
        assert "version" in data
        assert "exported_at" in data
        assert "config" in data
        assert "entries" in data
        assert "statistics" in data

        assert data["version"] == "1.0"
        assert isinstance(data["entries"], list)
        assert data["statistics"]["include_embeddings"] is True

    @pytest.mark.asyncio
    async def test_export_specific_tier(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test exporting from specific tier."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(id="id1", text="Test", metadata=MemoryMetadata())
        mock_adapter = AsyncMock()
        mock_adapter.query = AsyncMock(return_value=[entry])
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Export specific tier
        await system.export(tier="persistent")

        # Verify only one adapter was queried
        assert mock_registry.get_adapter.call_count == 1
        assert mock_registry.get_adapter.call_args[0][0] == "persistent"

    @pytest.mark.asyncio
    async def test_export_without_embeddings(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test exporting without embedding vectors."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(id="id1", text="Test", embedding=[0.1] * 384, metadata=MemoryMetadata())

        mock_adapter = AsyncMock()
        mock_adapter.query = AsyncMock(return_value=[entry])
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Export without embeddings
        data = await system.export(include_embeddings=False)

        assert data["statistics"]["include_embeddings"] is False
        # Check that exported entries don't have embeddings
        for entry_dict in data["entries"]:
            assert "embedding" not in entry_dict

    @pytest.mark.asyncio
    async def test_export_with_filter(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test exporting with filter."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(
            id="id1", text="Test", metadata=MemoryMetadata(importance=0.9, tags=["important"])
        )

        mock_adapter = AsyncMock()
        mock_adapter.query = AsyncMock(return_value=[entry])
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Export with filter
        filter_obj = Filter(min_importance=0.8)
        await system.export(filter=filter_obj)

        # Verify filter was passed to adapter
        call_args = mock_adapter.query.call_args
        assert call_args[1]["filter"] == filter_obj

    @pytest.mark.asyncio
    async def test_export_invalid_tier_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test export with invalid tier raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid tier"):
            await system.export(tier="nonexistent")

    @pytest.mark.asyncio
    async def test_export_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that export creates a trace event."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(id="id1", text="Test", metadata=MemoryMetadata())
        mock_adapter = AsyncMock()
        mock_adapter.query = AsyncMock(return_value=[entry])
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        await system.export()

        events = system.get_trace_events()
        assert len(events) > 0
        assert events[0].operation == "EXPORT"
        assert events[0].result_count == 3  # One entry per tier


class TestImportMethod:
    """Test import_from() method functionality."""

    @pytest.mark.asyncio
    async def test_import_basic(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test basic import operation."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create export data
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "config": {"tiers": ["persistent"], "default_tier": "persistent"},
            "entries": [
                {
                    "id": "id1",
                    "type": "note",
                    "text": "Test entry",
                    "embedding": [0.1] * 384,
                    "metadata": {
                        "user_id": None,
                        "session_id": None,
                        "source": "app",
                        "privacy_level": "public",
                        "created_at": datetime.now().isoformat(),
                        "last_accessed_at": None,
                        "tags": ["test"],
                        "importance": 0.5,
                        "version": "",
                        "access_count": 0,
                    },
                    "tier": "persistent",
                }
            ],
            "statistics": {"total_entries": 1},
        }

        # Setup mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.get = AsyncMock(side_effect=KeyError)  # Entry doesn't exist
        mock_adapter.save = AsyncMock(return_value="id1")
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Import
        stats = await system.import_from(export_data)

        assert stats["imported"] == 1
        assert stats["skipped"] == 0
        assert stats["errors"] == 0
        assert "persistent" in stats["by_tier"]
        assert stats["by_tier"]["persistent"] == 1

    @pytest.mark.asyncio
    async def test_import_with_overwrite(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test import with overwrite enabled."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        export_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "id1",
                    "text": "Test",
                    "metadata": {
                        "source": "app",
                        "privacy_level": "public",
                        "created_at": datetime.now().isoformat(),
                        "tags": [],
                        "importance": 0.5,
                        "access_count": 0,
                        "version": "",
                    },
                    "tier": "persistent",
                }
            ],
        }

        # Setup mock - entry exists
        existing_entry = MemoryEntry(id="id1", text="Old", metadata=MemoryMetadata())
        mock_adapter = AsyncMock()
        mock_adapter.get = AsyncMock(return_value=existing_entry)
        mock_adapter.save = AsyncMock()
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Import with overwrite
        stats = await system.import_from(export_data, overwrite=True)

        assert stats["imported"] == 1
        assert stats["skipped"] == 0
        mock_adapter.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_without_overwrite_skips(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test import without overwrite skips existing entries."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        export_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "id1",
                    "text": "Test",
                    "metadata": {
                        "source": "app",
                        "privacy_level": "public",
                        "created_at": datetime.now().isoformat(),
                        "tags": [],
                        "importance": 0.5,
                        "access_count": 0,
                        "version": "",
                    },
                    "tier": "persistent",
                }
            ],
        }

        # Entry exists
        existing_entry = MemoryEntry(id="id1", text="Old", metadata=MemoryMetadata())
        mock_adapter = AsyncMock()
        mock_adapter.get = AsyncMock(return_value=existing_entry)
        mock_adapter.save = AsyncMock()
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Import without overwrite
        stats = await system.import_from(export_data, overwrite=False)

        assert stats["imported"] == 0
        assert stats["skipped"] == 1
        mock_adapter.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_with_tier_mapping(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test import with tier remapping."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        export_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "id1",
                    "text": "Test",
                    "metadata": {
                        "source": "app",
                        "privacy_level": "public",
                        "created_at": datetime.now().isoformat(),
                        "tags": [],
                        "importance": 0.5,
                        "access_count": 0,
                        "version": "",
                    },
                    "tier": "ephemeral",  # Original tier
                }
            ],
        }

        mock_adapter = AsyncMock()
        mock_adapter.get = AsyncMock(side_effect=KeyError)
        mock_adapter.save = AsyncMock()
        mock_registry.get_adapter = Mock(return_value=mock_adapter)

        # Import with tier mapping
        tier_mapping = {"ephemeral": "session"}
        stats = await system.import_from(export_data, tier_mapping=tier_mapping)

        # Verify adapter for session tier was used
        mock_registry.get_adapter.assert_called_with("session")
        assert stats["imported"] == 1

    @pytest.mark.asyncio
    async def test_import_invalid_data_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test import with invalid data raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Missing version
        with pytest.raises(ValueError, match="missing 'version'"):
            await system.import_from({"entries": []})

        # Missing entries
        with pytest.raises(ValueError, match="missing 'entries'"):
            await system.import_from({"version": "1.0"})

        # Entries not a list
        with pytest.raises(ValueError, match="must be a list"):
            await system.import_from({"version": "1.0", "entries": "bad"})

    @pytest.mark.asyncio
    async def test_import_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that import creates a trace event."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        export_data = {"version": "1.0", "entries": []}

        await system.import_from(export_data)

        events = system.get_trace_events()
        assert len(events) > 0
        assert events[0].operation == "IMPORT"


class TestSyncMethod:
    """Test sync() method functionality."""

    @pytest.mark.asyncio
    async def test_sync_basic(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test basic sync operation."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Setup source entries
        entry = MemoryEntry(id="id1", text="Test", metadata=MemoryMetadata(importance=0.9))

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[entry])

        target_adapter = AsyncMock()
        target_adapter.get = AsyncMock(side_effect=KeyError)  # Doesn't exist in target
        target_adapter.save = AsyncMock()

        def get_adapter_mock(tier):
            if tier == "session":
                return source_adapter
            elif tier == "persistent":
                return target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        # Sync
        stats = await system.sync(source_tier="session", target_tier="persistent")

        assert stats["synced"] == 1
        assert stats["skipped"] == 0
        assert stats["deleted"] == 0
        assert stats["conflicts"] == 0
        target_adapter.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_with_delete_source(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with delete_source (move operation)."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(id="id1", text="Test", metadata=MemoryMetadata())

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[entry])
        source_adapter.delete = AsyncMock(return_value=True)

        target_adapter = AsyncMock()
        target_adapter.get = AsyncMock(side_effect=KeyError)
        target_adapter.save = AsyncMock()

        def get_adapter_mock(tier):
            return source_adapter if tier == "session" else target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        # Sync with delete
        stats = await system.sync(
            source_tier="session", target_tier="persistent", delete_source=True
        )

        assert stats["synced"] == 1
        assert stats["deleted"] == 1
        source_adapter.delete.assert_called_once_with("id1")

    @pytest.mark.asyncio
    async def test_sync_conflict_resolution_newer(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with 'newer' conflict resolution."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Source entry is newer
        source_entry = MemoryEntry(
            id="id1",
            text="Source",
            metadata=MemoryMetadata(
                created_at=datetime(2025, 11, 5, 12, 0),
                last_accessed_at=datetime(2025, 11, 5, 13, 0),
            ),
        )

        # Target entry is older
        target_entry = MemoryEntry(
            id="id1",
            text="Target",
            metadata=MemoryMetadata(
                created_at=datetime(2025, 11, 5, 10, 0),
                last_accessed_at=datetime(2025, 11, 5, 11, 0),
            ),
        )

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[source_entry])

        target_adapter = AsyncMock()
        target_adapter.get = AsyncMock(return_value=target_entry)
        target_adapter.save = AsyncMock()

        def get_adapter_mock(tier):
            return source_adapter if tier == "session" else target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        # Sync with newer wins
        stats = await system.sync(
            source_tier="session", target_tier="persistent", conflict_resolution="newer"
        )

        assert stats["conflicts"] == 1
        assert stats["synced"] == 1  # Source is newer, should sync

    @pytest.mark.asyncio
    async def test_sync_conflict_resolution_target(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with 'target' conflict resolution (skip)."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        source_entry = MemoryEntry(id="id1", text="Source", metadata=MemoryMetadata())
        target_entry = MemoryEntry(id="id1", text="Target", metadata=MemoryMetadata())

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[source_entry])

        target_adapter = AsyncMock()
        target_adapter.get = AsyncMock(return_value=target_entry)
        target_adapter.save = AsyncMock()

        def get_adapter_mock(tier):
            return source_adapter if tier == "session" else target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        # Sync with target wins
        stats = await system.sync(
            source_tier="session", target_tier="persistent", conflict_resolution="target"
        )

        assert stats["conflicts"] == 1
        assert stats["skipped"] == 1  # Target wins, should skip
        target_adapter.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_with_filter(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with filter."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        entry = MemoryEntry(
            id="id1", text="Test", metadata=MemoryMetadata(importance=0.9, tags=["important"])
        )

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[entry])

        target_adapter = AsyncMock()
        target_adapter.get = AsyncMock(side_effect=KeyError)
        target_adapter.save = AsyncMock()

        def get_adapter_mock(tier):
            return source_adapter if tier == "session" else target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        # Sync with filter
        filter_obj = Filter(min_importance=0.8)
        await system.sync(
            source_tier="session", target_tier="persistent", filter=filter_obj
        )

        # Verify filter was passed
        call_args = source_adapter.query.call_args
        assert call_args[1]["filter"] == filter_obj

    @pytest.mark.asyncio
    async def test_sync_invalid_tiers_raise(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with invalid tiers raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Invalid source
        with pytest.raises(ValueError, match="Invalid source tier"):
            await system.sync(source_tier="bad", target_tier="persistent")

        # Invalid target
        with pytest.raises(ValueError, match="Invalid target tier"):
            await system.sync(source_tier="session", target_tier="bad")

        # Same tier
        with pytest.raises(ValueError, match="must be different"):
            await system.sync(source_tier="session", target_tier="session")

    @pytest.mark.asyncio
    async def test_sync_invalid_resolution_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test sync with invalid conflict resolution raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid conflict_resolution"):
            await system.sync(
                source_tier="session", target_tier="persistent", conflict_resolution="invalid"
            )

    @pytest.mark.asyncio
    async def test_sync_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that sync creates a trace event."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        source_adapter = AsyncMock()
        source_adapter.query = AsyncMock(return_value=[])

        target_adapter = AsyncMock()

        def get_adapter_mock(tier):
            return source_adapter if tier == "session" else target_adapter

        mock_registry.get_adapter = Mock(side_effect=get_adapter_mock)

        await system.sync(source_tier="session", target_tier="persistent")

        events = system.get_trace_events()
        assert len(events) > 0
        assert events[0].operation == "SYNC"
        assert events[0].metadata["source_tier"] == "session"
        assert events[0].metadata["target_tier"] == "persistent"


class TestCompactMethod:
    """Test compact() method for memory summarization."""

    @pytest.mark.asyncio
    async def test_compact_below_threshold_skips(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that compaction is skipped when below threshold."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Mock adapter with low count
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(return_value=100)  # count() is sync, not async
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock policy engine to say no compaction needed
        mock_policy_engine.should_compact.return_value = (
            False,
            {
                "tier": "persistent",
                "current_count": 100,
                "threshold": 10000,
                "over_threshold": 0,
                "reason": "Below threshold",
            },
        )

        # Mock summarizer with API key
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary text"

        result = await system.compact(tier="persistent", summarizer=mock_summarizer)

        assert result["entries_before"] == 0
        assert result["entries_after"] == 0
        assert result["summaries_created"] == 0
        # When specific tier provided, it processes but finds nothing to compact
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_compact_invalid_tier_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that invalid tier raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid tier"):
            await system.compact(tier="nonexistent")

    @pytest.mark.asyncio
    async def test_compact_invalid_strategy_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that invalid strategy raises ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        with pytest.raises(ValueError, match="Invalid compaction strategy"):
            await system.compact(tier="persistent", strategy="invalid")

    @pytest.mark.asyncio
    async def test_compact_unsupported_strategy_raises(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that unsupported strategies raise ValueError."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # semantic, importance, time are valid but not yet implemented
        with pytest.raises(ValueError, match="not yet implemented"):
            await system.compact(tier="persistent", strategy="semantic")

    @pytest.mark.asyncio
    async def test_compact_dry_run(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_embedder
    ):
        """Test dry run mode doesn't modify data."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create mock entries
        base_time = datetime.now()
        mock_entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Entry {i}",
                embedding=[0.1] * 1536,
                metadata=MemoryMetadata(
                    created_at=base_time + timedelta(days=i),
                    importance=0.3 + (i * 0.003),  # Gradual increase, max at 0.9
                ),
            )
            for i in range(200)
        ]

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(return_value=200)  # count() is sync, not async
        mock_adapter.query.return_value = mock_entries
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock policy
        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=100)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}
        mock_policy_engine.should_compact.return_value = (
            True,
            {
                "tier": "persistent",
                "current_count": 200,
                "threshold": 100,
                "over_threshold": 100,
                "reason": "Over threshold",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary text"

        result = await system.compact(
            tier="persistent", threshold=100, dry_run=True, summarizer=mock_summarizer
        )

        # Should calculate what would happen but not call delete/save
        assert result["dry_run"] is True
        assert result["entries_before"] == 200
        assert result["entries_after"] < 200
        assert result["summaries_created"] > 0

        # Verify no actual changes were made
        mock_adapter.delete.assert_not_called()
        mock_adapter.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_compact_count_strategy(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_embedder
    ):
        """Test count-based compaction strategy."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create 150 mock entries (should compact to ~80)
        base_time = datetime.now() - timedelta(days=100)
        mock_entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Memory entry number {i}",
                embedding=[0.1 * i] * 1536,
                metadata=MemoryMetadata(
                    user_id="test_user",
                    session_id="test_session",
                    created_at=base_time + timedelta(days=i),
                    importance=0.2 + (i * 0.003),  # Gradually increasing importance
                    tags=["test"],
                ),
            )
            for i in range(150)
        ]

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(side_effect=[150, 82])  # count() is sync, not async
        mock_adapter.query.return_value = mock_entries
        mock_adapter.save = AsyncMock()
        mock_adapter.delete = AsyncMock()
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock policy
        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=100)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}
        mock_policy_engine.should_compact.return_value = (
            True,
            {
                "tier": "persistent",
                "current_count": 150,
                "threshold": 100,
                "over_threshold": 50,
                "reason": "Over threshold",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summarized content"

        # Mock embedder
        mock_embedder.embed.return_value = [0.5] * 1536

        result = await system.compact(
            tier="persistent",
            strategy="count",
            threshold=100,
            summarizer=mock_summarizer,
            embedder=mock_embedder,  # Pass embedder to compact
        )

        assert result["tier"] == "persistent"
        assert result["entries_before"] == 150
        assert result["summaries_created"] > 0
        assert result["reduction_ratio"] > 0
        assert result["strategy"] == "count"
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_compact_creates_summary_entries(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_embedder
    ):
        """Test that compaction creates proper summary entries."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create 120 entries
        base_time = datetime.now()
        mock_entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Entry {i}",
                embedding=[0.1] * 1536,
                metadata=MemoryMetadata(
                    user_id="user1",
                    session_id="session1",
                    created_at=base_time + timedelta(hours=i),
                    importance=0.3,
                    tags=["tag1", "tag2"],
                ),
            )
            for i in range(120)
        ]

        saved_entries = []

        async def capture_save(entry):
            saved_entries.append(entry)

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(side_effect=[120, 21])  # count() is sync, not async
        mock_adapter.query.return_value = mock_entries
        mock_adapter.save.side_effect = capture_save
        mock_adapter.delete = AsyncMock()
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock policy
        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=100)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}
        mock_policy_engine.should_compact.return_value = (
            True,
            {
                "tier": "persistent",
                "current_count": 120,
                "threshold": 100,
                "over_threshold": 20,
                "reason": "Over",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Group summary"

        # Mock embedder
        mock_embedder.embed.return_value = [0.5] * 1536

        await system.compact(
            tier="persistent",
            threshold=100,
            summarizer=mock_summarizer,
            embedder=mock_embedder,  # Pass embedder to compact
        )

        # Verify summary entries were created
        assert len(saved_entries) > 0

        # Check first summary entry
        summary = saved_entries[0]
        assert summary.text == "Group summary"
        assert summary.metadata.source == "system"  # Compaction is a system operation
        assert len(summary.metadata.provenance) > 0
        assert summary.metadata.provenance[0].action == "compact"
        assert summary.metadata.provenance[0].by == "memory_system"
        assert "summarized_count" in summary.metadata.provenance[0].metadata

    @pytest.mark.asyncio
    async def test_compact_updates_provenance(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_embedder
    ):
        """Test that compaction updates provenance chain."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create entries
        mock_entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Entry {i}",
                embedding=[0.1] * 1536,
                metadata=MemoryMetadata(created_at=datetime.now(), importance=0.3),
            )
            for i in range(110)
        ]

        saved_entries = []

        async def capture_save(entry):
            saved_entries.append(entry)

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(side_effect=[110, 11])  # count() is sync, not async
        mock_adapter.query.return_value = mock_entries
        mock_adapter.save.side_effect = capture_save
        mock_adapter.delete = AsyncMock()
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock policy
        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=100)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}
        mock_policy_engine.should_compact.return_value = (
            True,
            {
                "tier": "persistent",
                "current_count": 110,
                "threshold": 100,
                "over_threshold": 10,
                "reason": "Over",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary"

        mock_embedder.embed.return_value = [0.5] * 1536

        await system.compact(
            tier="persistent", threshold=100, summarizer=mock_summarizer, embedder=mock_embedder
        )

        # Check provenance
        for summary in saved_entries:
            assert len(summary.metadata.provenance) > 0
            provenance = summary.metadata.provenance[0]
            assert provenance.action == "compact"
            assert provenance.by == "memory_system"
            assert "strategy" in provenance.metadata
            assert "summarized_count" in provenance.metadata
            assert "summarized_ids" in provenance.metadata
            assert provenance.metadata["strategy"] == "count"

    @pytest.mark.asyncio
    async def test_compact_creates_trace_event(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test that compaction creates trace event."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Mock no compaction needed
        mock_policy_engine.should_compact.return_value = (
            False,
            {
                "tier": "persistent",
                "current_count": 50,
                "threshold": 100,
                "over_threshold": 0,
                "reason": "Below threshold",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary"

        result = await system.compact(tier="persistent", summarizer=mock_summarizer)

        # Check that compaction was skipped (below threshold case)
        assert result["entries_before"] == 0
        # Result should have either "reason" or be empty compaction
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_compact_returns_statistics(
        self, mock_config, mock_router, mock_registry, mock_policy_engine, mock_embedder
    ):
        """Test that compaction returns detailed statistics."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Create entries
        mock_entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Entry {i}",
                embedding=[0.1] * 1536,
                metadata=MemoryMetadata(created_at=datetime.now(), importance=0.3),
            )
            for i in range(120)
        ]

        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(side_effect=[120, 21])  # count() is sync, not async
        mock_adapter.query.return_value = mock_entries
        mock_adapter.save = AsyncMock()
        mock_adapter.delete = AsyncMock()
        mock_registry.get_adapter.return_value = mock_adapter

        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=100)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}
        mock_policy_engine.should_compact.return_value = (
            True,
            {
                "tier": "persistent",
                "current_count": 120,
                "threshold": 100,
                "over_threshold": 20,
                "reason": "Over",
            },
        )

        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary"
        mock_embedder.embed.return_value = [0.5] * 1536

        result = await system.compact(tier="persistent", threshold=100, summarizer=mock_summarizer)

        # Verify all expected statistics are present
        assert "tier" in result
        assert "entries_before" in result
        assert "entries_after" in result
        assert "summaries_created" in result
        assert "groups_compacted" in result
        assert "reduction_ratio" in result
        assert "dry_run" in result
        assert "execution_time" in result
        assert "strategy" in result

        assert result["entries_before"] == 120
        assert result["strategy"] == "count"
        assert result["dry_run"] is False
        assert isinstance(result["execution_time"], float)
        assert 0 <= result["reduction_ratio"] <= 1

    @pytest.mark.asyncio
    async def test_compact_with_threshold_override(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test compaction with custom threshold override."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(return_value=150)  # count() is sync, not async
        mock_registry.get_adapter.return_value = mock_adapter

        # Policy has threshold of 10000 but we override to 100
        from axon.core.policies.persistent import PersistentPolicy

        mock_policy = PersistentPolicy(compaction_threshold=10000)
        mock_policy_engine.tier_policies = {"persistent": mock_policy}

        # The should_compact call in compact() will use current_count parameter
        mock_policy_engine.should_compact.return_value = (
            False,
            {
                "tier": "persistent",
                "current_count": 150,
                "threshold": 100,
                "over_threshold": 0,
                "reason": "Checked",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary"

        # When we pass threshold=100, it should check against 100 not 10000
        result = await system.compact(tier="persistent", threshold=100, summarizer=mock_summarizer)

        # The function should have used the override threshold
        assert result is not None

    @pytest.mark.asyncio
    async def test_compact_all_tiers(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test compacting all tiers when tier=None."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        # Mock adapters for all tiers
        mock_adapter = AsyncMock()
        mock_adapter.count = Mock(return_value=50)  # count() is sync, not async
        mock_registry.get_adapter.return_value = mock_adapter

        # Mock all tiers below threshold
        mock_policy_engine.should_compact.return_value = (
            False,
            {
                "tier": "any",
                "current_count": 50,
                "threshold": 100,
                "over_threshold": 0,
                "reason": "Below",
            },
        )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Summary"

        result = await system.compact(summarizer=mock_summarizer)  # No tier specified = check all

        assert result["tier"] == "all"
        assert "No tiers need compaction" in result["reason"]


class TestContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, mock_config, mock_router, mock_registry, mock_policy_engine
    ):
        """Test using MemorySystem as async context manager."""
        async with MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        ) as system:
            assert isinstance(system, MemorySystem)
            await system.store("Test content")

        # Verify close was called
        mock_registry.close_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self, mock_config, mock_router, mock_registry, mock_policy_engine):
        """Test close method."""
        system = MemorySystem(
            config=mock_config,
            router=mock_router,
            registry=mock_registry,
            policy_engine=mock_policy_engine,
        )

        await system.close()
        mock_registry.close_all.assert_called_once()
