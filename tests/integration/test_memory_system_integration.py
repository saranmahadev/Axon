"""
Integration tests for MemorySystem with real components.

Tests end-to-end workflows with Router, PolicyEngine, ScoringEngine,
and InMemoryAdapter to validate complete system behavior.
"""

import asyncio
from datetime import datetime

import pytest
import pytest_asyncio

from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.models.filter import Filter


@pytest.fixture
def memory_config():
    """Create a memory configuration with all three tiers."""
    return MemoryConfig(
        ephemeral=EphemeralPolicy(adapter_type="memory", max_entries=5, ttl_seconds=60),
        session=SessionPolicy(adapter_type="memory", max_entries=20, ttl_seconds=3600),
        persistent=PersistentPolicy(adapter_type="memory", max_entries=100),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True,
    )


@pytest_asyncio.fixture
async def memory_system(memory_config):
    """Create a MemorySystem with real components."""
    system = MemorySystem(config=memory_config)
    yield system
    await system.close()


class TestMemorySystemLifecycle:
    """Test complete lifecycle operations."""

    @pytest.mark.asyncio
    async def test_store_and_recall_basic(self, memory_system):
        """Test basic store and recall workflow."""
        # Store a memory
        entry_id = await memory_system.store(
            "Python is a high-level programming language", importance=0.8
        )

        assert entry_id is not None
        assert len(entry_id) == 36  # UUID format

        # Recall should find it (without vector search in memory adapter)
        # Note: InMemoryAdapter doesn't support semantic search without embeddings
        # So we test with metadata-based recall
        await memory_system.recall("programming", k=5)

        # Check trace events
        trace = memory_system.get_trace_events()
        assert len(trace) >= 2  # store + recall
        assert trace[0].operation == "recall"
        assert trace[1].operation == "store"
        assert trace[1].entry_id == entry_id

    @pytest.mark.asyncio
    async def test_store_multiple_and_recall(self, memory_system):
        """Test storing multiple memories and recalling them."""
        # Store multiple entries
        entries = [
            ("Python is great for data science", 0.9, ["python", "data"]),
            ("JavaScript runs in browsers", 0.7, ["javascript", "web"]),
            ("Rust is a systems programming language", 0.6, ["rust", "systems"]),
        ]

        stored_ids = []
        for content, importance, tags in entries:
            entry_id = await memory_system.store(content, importance=importance, tags=tags)
            stored_ids.append(entry_id)

        assert len(stored_ids) == 3
        assert len(set(stored_ids)) == 3  # All unique

        # Recall with limit
        results = await memory_system.recall("language", k=2)
        assert len(results) <= 2

        # Check statistics
        stats = memory_system.get_statistics()
        assert stats["total_operations"]["stores"] == 3
        # Recall queries all 3 tiers, so recall count is 3 (one per tier)
        assert stats["total_operations"]["recalls"] == 3

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, memory_system):
        """Test storing with custom metadata."""
        entry_id = await memory_system.store(
            "User preferences updated",
            metadata={"user_id": "alice", "action": "update"},
            importance=0.5,
            tags=["user", "preferences"],
        )

        assert entry_id is not None

        # Verify trace event has correct data
        trace = memory_system.get_trace_events(operation="store")
        assert len(trace) == 1
        assert trace[0].entry_id == entry_id
        assert trace[0].success is True


class TestTierSelection:
    """Test tier selection based on importance."""

    @pytest.mark.asyncio
    async def test_high_importance_goes_to_persistent(self, memory_system):
        """Test high importance entries go to persistent tier."""
        await memory_system.store("Critical system alert", importance=0.95)

        # Check that it was routed to persistent tier
        trace = memory_system.get_trace_events(operation="store")
        assert len(trace) == 1
        # Note: tier information would be in the trace if we tracked it

        stats = memory_system.get_statistics()
        # Persistent tier should have 1 store
        assert stats["tier_stats"]["persistent"]["stores"] >= 1

    @pytest.mark.asyncio
    async def test_low_importance_goes_to_ephemeral(self, memory_system):
        """Test low importance entries go to ephemeral tier."""
        await memory_system.store("Temporary cache entry", importance=0.1)

        stats = memory_system.get_statistics()
        # Ephemeral tier should have activity
        assert stats["tier_stats"]["ephemeral"]["stores"] >= 1

    @pytest.mark.asyncio
    async def test_medium_importance_goes_to_session(self, memory_system):
        """Test medium importance entries go to session tier."""
        await memory_system.store("User session data", importance=0.5)

        stats = memory_system.get_statistics()
        # Session tier should have activity
        assert stats["tier_stats"]["session"]["stores"] >= 1

    @pytest.mark.asyncio
    async def test_explicit_tier_override(self, memory_system):
        """Test explicit tier specification overrides scoring."""
        await memory_system.store(
            "Force to persistent",
            importance=0.1,  # Low importance
            tier="persistent",  # But force to persistent
        )

        stats = memory_system.get_statistics()
        # Should be in persistent despite low importance
        assert stats["tier_stats"]["persistent"]["stores"] >= 1


class TestRecallOperations:
    """Test recall with various parameters."""

    @pytest.mark.asyncio
    async def test_recall_with_k_limit(self, memory_system):
        """Test recall respects k parameter."""
        # Store multiple entries
        for i in range(10):
            await memory_system.store(f"Entry {i}", importance=0.5)

        # Recall with limit
        results = await memory_system.recall("Entry", k=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_recall_specific_tiers(self, memory_system):
        """Test recall from specific tiers only."""
        # Store to different tiers
        await memory_system.store("Ephemeral data", importance=0.1)
        await memory_system.store("Session data", importance=0.5)
        await memory_system.store("Persistent data", importance=0.9)

        # Recall from persistent only
        await memory_system.recall("data", k=10, tiers=["persistent"])

        # Should have results (at least from persistent)
        trace = memory_system.get_trace_events(operation="recall")
        assert len(trace) >= 1

    @pytest.mark.asyncio
    async def test_recall_with_min_importance(self, memory_system):
        """Test recall filters by minimum importance."""
        # Store entries with different importance
        await memory_system.store("Low importance", importance=0.2)
        await memory_system.store("Medium importance", importance=0.6)
        await memory_system.store("High importance", importance=0.9)

        # Recall with min_importance filter
        results = await memory_system.recall("importance", k=10, min_importance=0.5)

        # All results should have importance >= 0.5
        for entry in results:
            assert entry.metadata.importance >= 0.5

    @pytest.mark.asyncio
    async def test_recall_with_filter(self, memory_system):
        """Test recall with metadata filter."""
        # Store entries with tags
        await memory_system.store("Python tutorial", tags=["python", "tutorial"], importance=0.7)
        await memory_system.store("JavaScript guide", tags=["javascript", "guide"], importance=0.7)

        # Recall with tag filter
        filter_obj = Filter(tags=["python"])
        results = await memory_system.recall("tutorial", k=10, filter=filter_obj)

        # Results should only have python tag
        for entry in results:
            if entry.metadata.tags:
                assert "python" in entry.metadata.tags


class TestTracingAndMonitoring:
    """Test tracing and monitoring features."""

    @pytest.mark.asyncio
    async def test_trace_events_capture_operations(self, memory_system):
        """Test that trace events capture all operations."""
        # Perform multiple operations
        await memory_system.store("Test 1", importance=0.5)
        await memory_system.store("Test 2", importance=0.6)
        await memory_system.recall("Test", k=5)

        # Check trace events
        trace = memory_system.get_trace_events()
        assert len(trace) == 3

        # Check operation types
        operations = [e.operation for e in trace]
        assert "store" in operations
        assert "recall" in operations

    @pytest.mark.asyncio
    async def test_trace_events_have_timestamps(self, memory_system):
        """Test trace events have valid timestamps."""
        await memory_system.store("Test", importance=0.5)

        trace = memory_system.get_trace_events()
        assert len(trace) == 1

        event = trace[0]
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
        assert event.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_trace_events_can_be_filtered(self, memory_system):
        """Test filtering trace events by operation."""
        await memory_system.store("Test 1", importance=0.5)
        await memory_system.store("Test 2", importance=0.6)
        await memory_system.recall("Test", k=5)

        # Filter for store operations only
        store_events = memory_system.get_trace_events(operation="store")
        assert len(store_events) == 2
        assert all(e.operation == "store" for e in store_events)

        # Filter for recall operations only
        recall_events = memory_system.get_trace_events(operation="recall")
        assert len(recall_events) == 1
        assert recall_events[0].operation == "recall"

    @pytest.mark.asyncio
    async def test_trace_events_can_be_limited(self, memory_system):
        """Test limiting number of trace events returned."""
        # Create many operations
        for i in range(10):
            await memory_system.store(f"Test {i}", importance=0.5)

        # Get limited trace
        trace = memory_system.get_trace_events(limit=5)
        assert len(trace) == 5

    @pytest.mark.asyncio
    async def test_trace_can_be_cleared(self, memory_system):
        """Test clearing trace history."""
        await memory_system.store("Test", importance=0.5)

        trace = memory_system.get_trace_events()
        assert len(trace) > 0

        # Clear trace
        memory_system.clear_trace_events()

        trace = memory_system.get_trace_events()
        assert len(trace) == 0

    @pytest.mark.asyncio
    async def test_tracing_can_be_disabled(self, memory_system):
        """Test disabling tracing."""
        # Disable tracing
        memory_system.enable_tracing(False)

        await memory_system.store("Test", importance=0.5)

        # No trace events should be recorded
        trace = memory_system.get_trace_events()
        assert len(trace) == 0

        # Re-enable tracing
        memory_system.enable_tracing(True)

        await memory_system.store("Test 2", importance=0.5)

        # Now events should be recorded
        trace = memory_system.get_trace_events()
        assert len(trace) == 1


class TestStatistics:
    """Test statistics gathering."""

    @pytest.mark.asyncio
    async def test_statistics_track_operations(self, memory_system):
        """Test statistics track operation counts."""
        # Perform operations
        await memory_system.store("Test 1", importance=0.5)
        await memory_system.store("Test 2", importance=0.6)
        await memory_system.recall("Test", k=5)

        stats = memory_system.get_statistics()

        # Check total operations
        assert stats["total_operations"]["stores"] == 2
        # Recall queries all 3 tiers, so recall count is 3 (one per tier)
        assert stats["total_operations"]["recalls"] == 3

    @pytest.mark.asyncio
    async def test_statistics_per_tier(self, memory_system):
        """Test statistics are tracked per tier."""
        # Store to different tiers
        await memory_system.store("Ephemeral", importance=0.1)
        await memory_system.store("Session", importance=0.5)
        await memory_system.store("Persistent", importance=0.9)

        stats = memory_system.get_statistics()

        # Each tier should have stats
        assert "ephemeral" in stats["tier_stats"]
        assert "session" in stats["tier_stats"]
        assert "persistent" in stats["tier_stats"]

        # Total stores should equal sum of tier stores
        total_stores = sum(tier["stores"] for tier in stats["tier_stats"].values())
        assert total_stores == 3

    @pytest.mark.asyncio
    async def test_statistics_include_trace_count(self, memory_system):
        """Test statistics include trace event count."""
        await memory_system.store("Test 1", importance=0.5)
        await memory_system.store("Test 2", importance=0.6)

        stats = memory_system.get_statistics()

        assert "trace_events" in stats
        assert stats["trace_events"] == 2


class TestErrorHandling:
    """Test error handling and validation."""

    @pytest.mark.asyncio
    async def test_store_empty_content_raises(self, memory_system):
        """Test storing empty content raises error."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            await memory_system.store("")

    @pytest.mark.asyncio
    async def test_store_invalid_importance_raises(self, memory_system):
        """Test storing with invalid importance raises error."""
        with pytest.raises(ValueError, match="importance must be between"):
            await memory_system.store("Test", importance=1.5)

        with pytest.raises(ValueError, match="importance must be between"):
            await memory_system.store("Test", importance=-0.1)

    @pytest.mark.asyncio
    async def test_store_invalid_tier_raises(self, memory_system):
        """Test storing to invalid tier raises error."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await memory_system.store("Test", tier="nonexistent")

    @pytest.mark.asyncio
    async def test_recall_none_query_raises(self, memory_system):
        """Test recall with None query raises error."""
        with pytest.raises(ValueError, match="query cannot be None"):
            await memory_system.recall(None)

    @pytest.mark.asyncio
    async def test_recall_invalid_k_raises(self, memory_system):
        """Test recall with invalid k raises error."""
        with pytest.raises(ValueError, match="k must be greater than 0"):
            await memory_system.recall("test", k=0)

        with pytest.raises(ValueError, match="k must be greater than 0"):
            await memory_system.recall("test", k=-1)

    @pytest.mark.asyncio
    async def test_recall_invalid_tiers_raises(self, memory_system):
        """Test recall with invalid tiers raises error."""
        with pytest.raises(ValueError, match="Invalid tiers"):
            await memory_system.recall("test", tiers=["nonexistent"])

    @pytest.mark.asyncio
    async def test_recall_invalid_min_importance_raises(self, memory_system):
        """Test recall with invalid min_importance raises error."""
        with pytest.raises(ValueError, match="min_importance must be between"):
            await memory_system.recall("test", min_importance=1.5)


class TestContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, memory_config):
        """Test using MemorySystem as context manager."""
        async with MemorySystem(config=memory_config) as system:
            # Store and recall within context
            entry_id = await system.store("Test", importance=0.5)
            assert entry_id is not None

            await system.recall("Test", k=5)
            # Results may be empty with InMemoryAdapter without embeddings

        # System should be closed after context exit
        # No exception should be raised


class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_stores(self, memory_system):
        """Test multiple concurrent store operations."""
        # Store multiple entries concurrently
        tasks = [memory_system.store(f"Entry {i}", importance=0.5) for i in range(10)]

        entry_ids = await asyncio.gather(*tasks)

        assert len(entry_ids) == 10
        assert len(set(entry_ids)) == 10  # All unique

        # Check statistics
        stats = memory_system.get_statistics()
        assert stats["total_operations"]["stores"] == 10

    @pytest.mark.asyncio
    async def test_concurrent_recalls(self, memory_system):
        """Test multiple concurrent recall operations."""
        # Store some data first
        await memory_system.store("Test data", importance=0.5)

        # Perform concurrent recalls
        tasks = [memory_system.recall("Test", k=5) for _ in range(5)]

        results_list = await asyncio.gather(*tasks)

        assert len(results_list) == 5

        # Check statistics
        stats = memory_system.get_statistics()
        # 5 recalls x 3 tiers = 15 total
        assert stats["total_operations"]["recalls"] == 15

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, memory_system):
        """Test concurrent mix of stores and recalls."""
        # Mix of operations
        tasks = []

        # Add stores
        for i in range(5):
            tasks.append(memory_system.store(f"Entry {i}", importance=0.5))

        # Add recalls
        for _ in range(5):
            tasks.append(memory_system.recall("Entry", k=5))

        results = await asyncio.gather(*tasks)

        assert len(results) == 10

        # Check statistics
        stats = memory_system.get_statistics()
        assert stats["total_operations"]["stores"] == 5
        # 5 recalls x 3 tiers = 15 total
        assert stats["total_operations"]["recalls"] == 15


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_conversation_memory_workflow(self, memory_system):
        """Test storing and recalling conversation history."""
        # Simulate a conversation
        conversation = [
            ("User: What is Python?", 0.7),
            ("Assistant: Python is a programming language", 0.8),
            ("User: What are its main features?", 0.6),
            ("Assistant: Python has dynamic typing, garbage collection...", 0.9),
        ]

        # Store conversation
        for message, importance in conversation:
            await memory_system.store(
                message, importance=importance, tags=["conversation"], metadata={"type": "chat"}
            )

        # Recall conversation
        await memory_system.recall(
            "Python features", k=10, filter=Filter(tags=["conversation"])
        )

        # Should have conversation entries
        stats = memory_system.get_statistics()
        assert stats["total_operations"]["stores"] == 4
        # 1 recall x 3 tiers = 3 total
        assert stats["total_operations"]["recalls"] == 3

    @pytest.mark.asyncio
    async def test_user_preference_workflow(self, memory_system):
        """Test storing and updating user preferences."""
        # Store initial preferences
        await memory_system.store(
            "User prefers dark mode",
            importance=0.9,
            tags=["preference", "ui"],
            metadata={"user_id": "alice"},
        )

        # Store another preference
        await memory_system.store(
            "User prefers Python for scripting",
            importance=0.8,
            tags=["preference", "language"],
            metadata={"user_id": "alice"},
        )

        # Recall user preferences
        await memory_system.recall(
            "user preferences", k=10, filter=Filter(tags=["preference"])
        )

        # Should have preferences
        trace = memory_system.get_trace_events()
        assert len(trace) >= 3  # 2 stores + 1 recall

    @pytest.mark.asyncio
    async def test_knowledge_base_workflow(self, memory_system):
        """Test building and querying a knowledge base."""
        # Store knowledge articles
        articles = [
            ("Machine learning is a subset of AI", 0.9, ["ml", "ai"]),
            ("Neural networks are used in deep learning", 0.9, ["dl", "nn"]),
            ("Supervised learning uses labeled data", 0.8, ["ml", "supervised"]),
            ("Unsupervised learning finds patterns", 0.8, ["ml", "unsupervised"]),
        ]

        for content, importance, tags in articles:
            await memory_system.store(
                content, importance=importance, tags=tags, metadata={"type": "article"}
            )

        # Query knowledge base
        results = await memory_system.recall(
            "machine learning", k=10, filter=Filter(tags=["ml"]), min_importance=0.7
        )

        # All results should be high quality
        for entry in results:
            assert entry.metadata.importance >= 0.7

        # Check statistics
        stats = memory_system.get_statistics()
        assert stats["total_operations"]["stores"] == 4
        # 1 recall x 3 tiers = 3 total
        assert stats["total_operations"]["recalls"] == 3
