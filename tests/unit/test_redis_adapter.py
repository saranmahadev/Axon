"""Comprehensive test suite for RedisAdapter.

Tests cover:
- Initialization and configuration
- CRUD operations (save, get, delete)
- Query with metadata filtering
- Bulk operations
- TTL behavior and expiration
- Namespace isolation
- Utility methods (count, list, clear)
- Sync wrappers
- Edge cases
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.axon.adapters import RedisAdapter
from src.axon.models import DateRange, Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent

# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def redis_adapter():
    """Create a RedisAdapter with unique namespace for each test."""
    namespace = f"test_{uuid4().hex[:8]}"
    adapter = RedisAdapter(
        host="localhost", port=6379, namespace=namespace, default_ttl=300  # 5 minutes default
    )

    yield adapter

    # Cleanup: clear test namespace
    await adapter.clear_async()
    await adapter.close()


@pytest.fixture
def sample_entry():
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        id="test_entry_001",
        text="This is a test memory entry for Redis adapter validation.",
        embedding=[0.1, 0.2, 0.3, 0.4] * 96,  # 384 dimensions
        metadata=MemoryMetadata(
            user_id="user_123",
            session_id="session_456",
            source="app",
            privacy_level="private",
            tags=["test", "redis", "validation"],
            importance=0.8,
            provenance=[
                ProvenanceEvent(
                    action="create", by="test_suite", timestamp=datetime.now(timezone.utc)
                )
            ],
        ),
    )


@pytest.fixture
def sample_entries():
    """Create multiple sample entries for bulk testing."""
    return [
        MemoryEntry(
            id=f"bulk_entry_{i}",
            text=f"Bulk test entry number {i}",
            embedding=[(i + 1) * 0.1] * 384,
            metadata=MemoryMetadata(
                user_id=f"user_{i % 3}",  # 3 different users
                session_id=f"session_{i % 2}",  # 2 different sessions
                tags=["bulk", f"batch_{i // 2}"],
                importance=0.3 + (i * 0.05),  # 0.3 to 0.75 (max 0.75 for i=9)
                source="app",
            ),
        )
        for i in range(10)
    ]


# ============================================================================
# Test Class: Initialization
# ============================================================================


class TestRedisInit:
    """Test RedisAdapter initialization and configuration."""

    def test_default_initialization(self):
        """Test adapter with default parameters."""
        adapter = RedisAdapter()
        assert adapter.host == "localhost"
        assert adapter.port == 6379
        assert adapter.db == 0
        assert adapter.namespace == "axon"
        assert adapter.default_ttl is None

    def test_custom_configuration(self):
        """Test adapter with custom parameters."""
        adapter = RedisAdapter(
            host="127.0.0.1", port=6380, db=1, namespace="custom_namespace", default_ttl=3600
        )
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 6380
        assert adapter.db == 1
        assert adapter.namespace == "custom_namespace"
        assert adapter.default_ttl == 3600

    def test_namespace_key_generation(self):
        """Test namespace key generation."""
        adapter = RedisAdapter(namespace="test_ns")
        key = adapter._get_key("entry_123")
        assert key == "test_ns:memory:entry_123"


# ============================================================================
# Test Class: Save Operations
# ============================================================================


class TestRedisSave:
    """Test save operations and TTL management."""

    @pytest.mark.asyncio
    async def test_basic_save(self, redis_adapter, sample_entry):
        """Test basic save and retrieve."""
        entry_id = await redis_adapter.save(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = await redis_adapter.get(entry_id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.text == sample_entry.text
        assert retrieved.metadata.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_save_with_default_ttl(self, redis_adapter, sample_entry):
        """Test save with default TTL."""
        await redis_adapter.save(sample_entry)

        ttl = await redis_adapter.get_ttl(sample_entry.id)
        assert ttl > 0
        assert ttl <= 300  # Should be <= default TTL

    @pytest.mark.asyncio
    async def test_save_with_custom_ttl(self, redis_adapter, sample_entry):
        """Test save with custom TTL override."""
        custom_ttl = 60  # 1 minute
        await redis_adapter.save(sample_entry, ttl=custom_ttl)

        ttl = await redis_adapter.get_ttl(sample_entry.id)
        assert ttl > 0
        assert ttl <= custom_ttl

    @pytest.mark.asyncio
    async def test_save_with_full_metadata(self, redis_adapter):
        """Test save with complete metadata including provenance."""
        entry = MemoryEntry(
            id="full_metadata_test",
            text="Entry with full metadata",
            embedding=[0.5] * 384,
            metadata=MemoryMetadata(
                user_id="user_456",
                session_id="session_789",
                source="system",
                privacy_level="public",
                tags=["full", "metadata", "test"],
                importance=0.95,
                version="gpt-4-turbo-2024-04-09",
                provenance=[
                    ProvenanceEvent(
                        action="create",
                        by="system",
                        timestamp=datetime.now(timezone.utc),
                        metadata={"source": "automated"},
                    )
                ],
            ),
        )

        await redis_adapter.save(entry)
        retrieved = await redis_adapter.get(entry.id)

        assert retrieved.metadata.version == "gpt-4-turbo-2024-04-09"
        assert len(retrieved.metadata.provenance) == 1
        assert retrieved.metadata.provenance[0].action == "create"

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, redis_adapter, sample_entry):
        """Test that saving with same ID overwrites."""
        # Save original
        await redis_adapter.save(sample_entry)

        # Modify and save again
        sample_entry.text = "Modified text"
        await redis_adapter.save(sample_entry)

        # Retrieve and verify
        retrieved = await redis_adapter.get(sample_entry.id)
        assert retrieved.text == "Modified text"

    @pytest.mark.asyncio
    async def test_save_without_id_raises_error(self, redis_adapter):
        """Test that saving without ID raises ValueError."""
        entry = MemoryEntry(
            id="", text="No ID entry", embedding=[0.1] * 384, metadata=MemoryMetadata()  # Empty ID
        )

        with pytest.raises(ValueError, match="Entry must have an ID"):
            await redis_adapter.save(entry)


# ============================================================================
# Test Class: Query Operations
# ============================================================================


class TestRedisQuery:
    """Test query operations with filtering."""

    @pytest.mark.asyncio
    async def test_query_all_no_filter(self, redis_adapter, sample_entries):
        """Test query without filter returns all entries."""
        await redis_adapter.bulk_save(sample_entries)

        results = await redis_adapter.query(
            vector=[0.1] * 384, k=20  # Dummy vector (not used in Redis)
        )

        assert len(results) == len(sample_entries)

    @pytest.mark.asyncio
    async def test_query_with_limit(self, redis_adapter, sample_entries):
        """Test query respects limit parameter."""
        await redis_adapter.bulk_save(sample_entries)

        results = await redis_adapter.query(vector=[0.1] * 384, k=5)

        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_query_filter_by_user(self, redis_adapter, sample_entries):
        """Test filtering by user_id."""
        await redis_adapter.bulk_save(sample_entries)

        filter_obj = Filter(user_id="user_0")
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert all(r.metadata.user_id == "user_0" for r in results)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_query_filter_by_session(self, redis_adapter, sample_entries):
        """Test filtering by session_id."""
        await redis_adapter.bulk_save(sample_entries)

        filter_obj = Filter(session_id="session_0")
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert all(r.metadata.session_id == "session_0" for r in results)

    @pytest.mark.asyncio
    async def test_query_filter_by_tags(self, redis_adapter, sample_entries):
        """Test filtering by tags."""
        await redis_adapter.bulk_save(sample_entries)

        filter_obj = Filter(tags=["bulk"])
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert all("bulk" in r.metadata.tags for r in results)
        assert len(results) == len(sample_entries)

    @pytest.mark.asyncio
    async def test_query_filter_by_importance_range(self, redis_adapter, sample_entries):
        """Test filtering by importance range."""
        await redis_adapter.bulk_save(sample_entries)

        filter_obj = Filter(min_importance=0.5, max_importance=0.8)
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        for result in results:
            assert result.metadata.importance >= 0.5
            assert result.metadata.importance <= 0.8

    @pytest.mark.asyncio
    async def test_query_filter_by_privacy_level(self, redis_adapter):
        """Test filtering by privacy level."""
        entries = [
            MemoryEntry(
                id=f"privacy_{i}",
                text=f"Privacy test {i}",
                embedding=[0.1] * 384,
                metadata=MemoryMetadata(privacy_level="public" if i % 2 == 0 else "private"),
            )
            for i in range(6)
        ]
        await redis_adapter.bulk_save(entries)

        filter_obj = Filter(privacy_level="public")
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert all(r.metadata.privacy_level == "public" for r in results)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_filter_by_date_range(self, redis_adapter):
        """Test filtering by date range."""
        now = datetime.now(timezone.utc)

        entries = [
            MemoryEntry(
                id=f"date_{i}",
                text=f"Date test {i}",
                embedding=[0.1] * 384,
                metadata=MemoryMetadata(created_at=now - timedelta(days=i)),
            )
            for i in range(5)
        ]
        await redis_adapter.bulk_save(entries)

        # Filter for last 2 days
        filter_obj = Filter(date_range=DateRange(start=now - timedelta(days=2), end=now))
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert len(results) <= 3  # Days 0, 1, 2

    @pytest.mark.asyncio
    async def test_query_filter_older_than_days(self, redis_adapter):
        """Test filtering by older_than_days."""
        now = datetime.now(timezone.utc)

        entries = [
            MemoryEntry(
                id=f"age_{i}",
                text=f"Age test {i}",
                embedding=[0.1] * 384,
                metadata=MemoryMetadata(created_at=now - timedelta(days=i * 10)),
            )
            for i in range(5)
        ]
        await redis_adapter.bulk_save(entries)

        # Filter for entries older than 15 days
        filter_obj = Filter(older_than_days=15)
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        # Should get entries from days 20, 30, 40 (indices 2, 3, 4)
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_query_empty_results(self, redis_adapter, sample_entries):
        """Test query with filter that matches nothing."""
        await redis_adapter.bulk_save(sample_entries)

        filter_obj = Filter(user_id="nonexistent_user")
        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        assert len(results) == 0


# ============================================================================
# Test Class: Get Operations
# ============================================================================


class TestRedisGet:
    """Test get operations."""

    @pytest.mark.asyncio
    async def test_get_existing_entry(self, redis_adapter, sample_entry):
        """Test retrieving existing entry."""
        await redis_adapter.save(sample_entry)

        retrieved = await redis_adapter.get(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.text == sample_entry.text

    @pytest.mark.asyncio
    async def test_get_nonexistent_entry(self, redis_adapter):
        """Test retrieving non-existent entry returns None."""
        result = await redis_adapter.get("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_includes_embedding(self, redis_adapter, sample_entry):
        """Test that retrieved entry includes embedding."""
        await redis_adapter.save(sample_entry)

        retrieved = await redis_adapter.get(sample_entry.id)
        assert retrieved.embedding is not None
        assert len(retrieved.embedding) == len(sample_entry.embedding)
        assert retrieved.embedding == sample_entry.embedding

    @pytest.mark.asyncio
    async def test_get_with_ttl_refresh(self, redis_adapter, sample_entry):
        """Test TTL refresh on get."""
        await redis_adapter.save(sample_entry, ttl=60)

        # Wait a bit
        await asyncio.sleep(2)

        # Get original TTL
        ttl_before = await redis_adapter.get_ttl(sample_entry.id)

        # Get with refresh
        await redis_adapter.get(sample_entry.id, refresh_ttl=True)

        # Get new TTL
        ttl_after = await redis_adapter.get_ttl(sample_entry.id)

        # TTL should be refreshed (closer to default_ttl)
        assert ttl_after > ttl_before


# ============================================================================
# Test Class: Delete Operations
# ============================================================================


class TestRedisDelete:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete_existing_entry(self, redis_adapter, sample_entry):
        """Test deleting existing entry."""
        await redis_adapter.save(sample_entry)

        deleted = await redis_adapter.delete(sample_entry.id)
        assert deleted is True

        # Verify deletion
        retrieved = await redis_adapter.get(sample_entry.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self, redis_adapter):
        """Test deleting non-existent entry returns False."""
        deleted = await redis_adapter.delete("nonexistent_id")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_is_idempotent(self, redis_adapter, sample_entry):
        """Test that delete can be called multiple times."""
        await redis_adapter.save(sample_entry)

        # First delete
        deleted1 = await redis_adapter.delete(sample_entry.id)
        assert deleted1 is True

        # Second delete
        deleted2 = await redis_adapter.delete(sample_entry.id)
        assert deleted2 is False

    @pytest.mark.asyncio
    async def test_delete_doesnt_affect_others(self, redis_adapter, sample_entries):
        """Test that deleting one entry doesn't affect others."""
        await redis_adapter.bulk_save(sample_entries)

        # Delete first entry
        await redis_adapter.delete(sample_entries[0].id)

        # Verify others still exist
        for entry in sample_entries[1:]:
            retrieved = await redis_adapter.get(entry.id)
            assert retrieved is not None


# ============================================================================
# Test Class: Bulk Operations
# ============================================================================


class TestRedisBulkOperations:
    """Test bulk save operations."""

    @pytest.mark.asyncio
    async def test_bulk_save_multiple_entries(self, redis_adapter, sample_entries):
        """Test saving multiple entries at once."""
        ids = await redis_adapter.bulk_save(sample_entries)

        assert len(ids) == len(sample_entries)
        assert ids == [e.id for e in sample_entries]

        # Verify all were saved
        count = await redis_adapter.count_async()
        assert count == len(sample_entries)

    @pytest.mark.asyncio
    async def test_bulk_save_with_ttl(self, redis_adapter, sample_entries):
        """Test bulk save with TTL."""
        ttl = 120
        await redis_adapter.bulk_save(sample_entries, ttl=ttl)

        # Check TTL on first entry
        ttl_value = await redis_adapter.get_ttl(sample_entries[0].id)
        assert ttl_value > 0
        assert ttl_value <= ttl

    @pytest.mark.asyncio
    async def test_bulk_save_empty_list_raises_error(self, redis_adapter):
        """Test that bulk save with empty list raises ValueError."""
        with pytest.raises(ValueError, match="Entries list cannot be empty"):
            await redis_adapter.bulk_save([])

    @pytest.mark.asyncio
    async def test_bulk_save_large_batch(self, redis_adapter):
        """Test bulk save with large number of entries."""
        large_batch = [
            MemoryEntry(
                id=f"large_{i}",
                text=f"Large batch entry {i}",
                embedding=[(i % 10 + 1) * 0.1] * 384,
                metadata=MemoryMetadata(tags=["large_batch"], importance=0.5),
            )
            for i in range(100)
        ]

        ids = await redis_adapter.bulk_save(large_batch)
        assert len(ids) == 100

        count = await redis_adapter.count_async()
        assert count == 100


# ============================================================================
# Test Class: Utility Methods
# ============================================================================


class TestRedisUtilities:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_count_entries(self, redis_adapter, sample_entries):
        """Test counting entries in namespace."""
        await redis_adapter.bulk_save(sample_entries)

        count = await redis_adapter.count_async()
        assert count == len(sample_entries)

    @pytest.mark.asyncio
    async def test_count_empty_namespace(self, redis_adapter):
        """Test count on empty namespace."""
        count = await redis_adapter.count_async()
        assert count == 0

    @pytest.mark.asyncio
    async def test_list_ids(self, redis_adapter, sample_entries):
        """Test listing all entry IDs."""
        await redis_adapter.bulk_save(sample_entries)

        ids = await redis_adapter.list_ids_async()
        assert len(ids) == len(sample_entries)

        expected_ids = {e.id for e in sample_entries}
        actual_ids = set(ids)
        assert expected_ids == actual_ids

    @pytest.mark.asyncio
    async def test_clear_namespace(self, redis_adapter, sample_entries):
        """Test clearing all entries in namespace."""
        await redis_adapter.bulk_save(sample_entries)

        # Verify entries exist
        count_before = await redis_adapter.count_async()
        assert count_before == len(sample_entries)

        # Clear
        await redis_adapter.clear_async()

        # Verify empty
        count_after = await redis_adapter.count_async()
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_reindex_is_noop(self, redis_adapter):
        """Test that reindex is a no-op for Redis."""
        # Should not raise any errors
        await redis_adapter.reindex()

    @pytest.mark.asyncio
    async def test_get_ttl_for_existing_key(self, redis_adapter, sample_entry):
        """Test getting TTL for existing key."""
        await redis_adapter.save(sample_entry, ttl=600)

        ttl = await redis_adapter.get_ttl(sample_entry.id)
        assert ttl > 0
        assert ttl <= 600

    @pytest.mark.asyncio
    async def test_get_ttl_for_nonexistent_key(self, redis_adapter):
        """Test getting TTL for non-existent key."""
        ttl = await redis_adapter.get_ttl("nonexistent")
        assert ttl == -2  # Redis returns -2 for non-existent keys


# ============================================================================
# Test Class: TTL Behavior
# ============================================================================


class TestRedisTTL:
    """Test TTL behavior and expiration."""

    @pytest.mark.asyncio
    async def test_entry_with_no_ttl(self):
        """Test entry saved without TTL (persistent in Redis)."""
        adapter = RedisAdapter(namespace=f"test_{uuid4().hex[:8]}", default_ttl=None)

        entry = MemoryEntry(
            id="no_ttl", text="No TTL entry", embedding=[0.1] * 384, metadata=MemoryMetadata()
        )

        await adapter.save(entry)

        ttl = await adapter.get_ttl(entry.id)
        assert ttl == -1  # -1 means no expiration

        await adapter.clear_async()
        await adapter.close()

    @pytest.mark.asyncio
    async def test_ttl_override_per_entry(self, redis_adapter):
        """Test that per-entry TTL overrides default."""
        entry1 = MemoryEntry(
            id="entry_default_ttl",
            text="Default TTL",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(),
        )

        entry2 = MemoryEntry(
            id="entry_custom_ttl",
            text="Custom TTL",
            embedding=[0.2] * 384,
            metadata=MemoryMetadata(),
        )

        await redis_adapter.save(entry1)  # Uses default TTL (300)
        await redis_adapter.save(entry2, ttl=60)  # Uses custom TTL

        ttl1 = await redis_adapter.get_ttl(entry1.id)
        ttl2 = await redis_adapter.get_ttl(entry2.id)

        assert ttl1 > ttl2  # Default TTL should be longer

    @pytest.mark.asyncio
    async def test_ttl_countdown(self, redis_adapter, sample_entry):
        """Test that TTL counts down over time."""
        await redis_adapter.save(sample_entry, ttl=10)

        ttl_start = await redis_adapter.get_ttl(sample_entry.id)

        # Wait 2 seconds
        await asyncio.sleep(2)

        ttl_after = await redis_adapter.get_ttl(sample_entry.id)

        assert ttl_after < ttl_start

    @pytest.mark.asyncio
    async def test_expired_entry_auto_removed(self, redis_adapter):
        """Test that expired entries are automatically removed."""
        entry = MemoryEntry(
            id="expiring_entry",
            text="This will expire",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(),
        )

        # Save with 2 second TTL
        await redis_adapter.save(entry, ttl=2)

        # Verify it exists
        retrieved = await redis_adapter.get(entry.id)
        assert retrieved is not None

        # Wait for expiration
        await asyncio.sleep(3)

        # Verify it's gone
        retrieved_after = await redis_adapter.get(entry.id)
        assert retrieved_after is None


# ============================================================================
# Test Class: Namespace Isolation
# ============================================================================


class TestRedisNamespaces:
    """Test namespace isolation."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that different namespaces don't interfere."""
        adapter1 = RedisAdapter(namespace="namespace_1")
        adapter2 = RedisAdapter(namespace="namespace_2")

        entry1 = MemoryEntry(
            id="shared_id",
            text="Entry in namespace 1",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(),
        )

        entry2 = MemoryEntry(
            id="shared_id",  # Same ID
            text="Entry in namespace 2",
            embedding=[0.2] * 384,
            metadata=MemoryMetadata(),
        )

        await adapter1.save(entry1)
        await adapter2.save(entry2)

        # Retrieve from each namespace
        retrieved1 = await adapter1.get("shared_id")
        retrieved2 = await adapter2.get("shared_id")

        assert retrieved1.text == "Entry in namespace 1"
        assert retrieved2.text == "Entry in namespace 2"

        # Cleanup
        await adapter1.clear_async()
        await adapter2.clear_async()
        await adapter1.close()
        await adapter2.close()

    @pytest.mark.asyncio
    async def test_clear_only_affects_own_namespace(self):
        """Test that clear only affects own namespace."""
        adapter1 = RedisAdapter(namespace="ns_clear_1")
        adapter2 = RedisAdapter(namespace="ns_clear_2")

        entry = MemoryEntry(
            id="test_entry", text="Test", embedding=[0.1] * 384, metadata=MemoryMetadata()
        )

        await adapter1.save(entry)
        await adapter2.save(entry)

        # Clear namespace 1
        await adapter1.clear_async()

        # Verify namespace 1 is empty
        count1 = await adapter1.count_async()
        assert count1 == 0

        # Verify namespace 2 still has data
        count2 = await adapter2.count_async()
        assert count2 == 1

        # Cleanup
        await adapter2.clear_async()
        await adapter1.close()
        await adapter2.close()


# ============================================================================
# Test Class: Sync Wrappers
# ============================================================================


class TestRedisSyncWrappers:
    """Test synchronous wrapper methods."""

    def test_sync_wrappers_exist(self):
        """Test that all sync wrapper methods exist."""
        adapter = RedisAdapter()

        # Check that sync methods exist
        assert hasattr(adapter, "save_sync")
        assert hasattr(adapter, "query_sync")
        assert hasattr(adapter, "get_sync")
        assert hasattr(adapter, "delete_sync")
        assert hasattr(adapter, "bulk_save_sync")
        assert hasattr(adapter, "reindex_sync")
        assert hasattr(adapter, "count_sync")
        assert hasattr(adapter, "list_ids_sync")
        assert hasattr(adapter, "clear_sync")
        assert hasattr(adapter, "get_ttl_sync")


# ============================================================================
# Test Class: Edge Cases
# ============================================================================


class TestRedisEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_unicode_text_support(self, redis_adapter):
        """Test support for Unicode text."""
        entry = MemoryEntry(
            id="unicode_test",
            text="Hello 世界 🌍 مرحبا Привет",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(tags=["unicode", "test", "🎉"]),
        )

        await redis_adapter.save(entry)
        retrieved = await redis_adapter.get(entry.id)

        assert retrieved.text == entry.text
        assert "🎉" in retrieved.metadata.tags

    @pytest.mark.asyncio
    async def test_large_embedding(self, redis_adapter):
        """Test with large embedding (1536 dimensions)."""
        entry = MemoryEntry(
            id="large_embedding",
            text="Large embedding test",
            embedding=[i * 0.001 for i in range(1536)],
            metadata=MemoryMetadata(),
        )

        await redis_adapter.save(entry)
        retrieved = await redis_adapter.get(entry.id)

        assert len(retrieved.embedding) == 1536
        assert retrieved.embedding == entry.embedding

    @pytest.mark.asyncio
    async def test_empty_tags_list(self, redis_adapter):
        """Test entry with empty tags list."""
        entry = MemoryEntry(
            id="empty_tags", text="No tags", embedding=[0.1] * 384, metadata=MemoryMetadata(tags=[])
        )

        await redis_adapter.save(entry)
        retrieved = await redis_adapter.get(entry.id)

        assert retrieved.metadata.tags == []

    @pytest.mark.asyncio
    async def test_combined_filters(self, redis_adapter):
        """Test query with multiple filter conditions."""
        entries = [
            MemoryEntry(
                id=f"combined_{i}",
                text=f"Combined filter test {i}",
                embedding=[i * 0.1] * 384,
                metadata=MemoryMetadata(
                    user_id="user_test",
                    session_id=f"session_{i % 2}",
                    tags=["test", "combined"],
                    importance=0.5 + (i * 0.04),  # 0.5 to 0.86 (max 0.86 for i=9)
                    privacy_level="public" if i % 2 == 0 else "private",
                ),
            )
            for i in range(10)
        ]

        await redis_adapter.bulk_save(entries)

        # Filter by user + session + tags + importance + privacy
        filter_obj = Filter(
            user_id="user_test",
            session_id="session_0",
            tags=["test"],
            min_importance=0.6,
            privacy_level="public",
        )

        results = await redis_adapter.query(vector=[0.1] * 384, k=20, filter=filter_obj)

        # Verify all conditions
        for result in results:
            assert result.metadata.user_id == "user_test"
            assert result.metadata.session_id == "session_0"
            assert "test" in result.metadata.tags
            assert result.metadata.importance >= 0.6
            assert result.metadata.privacy_level == "public"
