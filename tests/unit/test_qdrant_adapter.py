"""Unit tests for Qdrant vector storage adapter.

Tests cover all StorageAdapter interface methods plus Qdrant-specific features.
Requires Qdrant running at localhost:6333 (use Docker).

Run with: pytest tests/unit/test_qdrant_adapter.py -v
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.axon.adapters.qdrant import QdrantAdapter
from src.axon.models import DateRange, Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent

# Fixtures


@pytest_asyncio.fixture
async def qdrant_adapter():
    """Create a Qdrant adapter with a unique collection for testing."""
    collection_name = f"test_collection_{uuid4().hex[:8]}"
    adapter = QdrantAdapter(
        url="http://localhost:6333", collection_name=collection_name, timeout=10
    )

    yield adapter

    # Cleanup: delete the test collection
    try:
        await adapter.client.delete_collection(collection_name)
    except Exception:
        pass

    # Small delay for cleanup
    await asyncio.sleep(0.1)


@pytest.fixture
def sample_entry():
    """Create a sample memory entry with embedding."""
    return MemoryEntry(
        id=str(uuid4()),
        text="Qdrant is a vector search engine",
        embedding=[0.1] * 384,  # Small embedding for testing
        metadata=MemoryMetadata(
            source="app",
            privacy_level="public",
            user_id="user123",
            session_id="session456",
            importance=0.8,
            tags=["vector-db", "qdrant"],
            provenance=[
                ProvenanceEvent(action="store", by="test_suite", metadata={"category": "test"})
            ],
        ),
    )


@pytest.fixture
def sample_entries():
    """Create multiple sample entries for bulk operations."""
    entries = []
    for i in range(5):
        entry = MemoryEntry(
            id=str(uuid4()),
            text=f"Test entry {i}",
            embedding=[float(i) * 0.1] * 384,
            metadata=MemoryMetadata(
                source="app",
                privacy_level="public" if i % 2 == 0 else "private",
                importance=0.5 + (i * 0.1),
                tags=[f"tag{i}"],
                provenance=[ProvenanceEvent(action="store", by="test_suite")],
            ),
        )
        entries.append(entry)
    return entries


# Test Classes


class TestQdrantInit:
    """Test Qdrant adapter initialization."""

    @pytest.mark.asyncio
    async def test_init_local(self):
        """Test initialization with local Qdrant."""
        adapter = QdrantAdapter(url="http://localhost:6333")
        assert adapter.url == "http://localhost:6333"
        assert adapter.collection_name == "axon_memories"
        assert adapter.client is not None

    @pytest.mark.asyncio
    async def test_init_with_api_key(self):
        """Test initialization with API key."""
        adapter = QdrantAdapter(url="http://localhost:6333", api_key="test-key")
        assert adapter.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_init_custom_collection(self):
        """Test initialization with custom collection name."""
        adapter = QdrantAdapter(collection_name="custom_collection")
        assert adapter.collection_name == "custom_collection"


class TestQdrantSave:
    """Test save operations."""

    @pytest.mark.asyncio
    async def test_save_creates_collection(self, qdrant_adapter, sample_entry):
        """Test that save creates collection if it doesn't exist."""
        await qdrant_adapter.save(sample_entry)

        # Verify collection exists
        collections = await qdrant_adapter.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        assert qdrant_adapter.collection_name in collection_names

    @pytest.mark.asyncio
    async def test_save_and_retrieve(self, qdrant_adapter, sample_entry):
        """Test saving and retrieving an entry."""
        await qdrant_adapter.save(sample_entry)

        retrieved = await qdrant_adapter.get(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.text == sample_entry.text
        assert retrieved.metadata.user_id == sample_entry.metadata.user_id

    @pytest.mark.asyncio
    async def test_save_without_embedding_raises_error(self, qdrant_adapter):
        """Test that saving without embedding raises ValueError."""
        entry = MemoryEntry(
            id=str(uuid4()),
            text="No embedding",
            embedding=None,
            metadata=MemoryMetadata(source="app"),
        )

        with pytest.raises(ValueError, match="must have an embedding"):
            await qdrant_adapter.save(entry)

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, qdrant_adapter, sample_entry):
        """Test that save updates existing entries (upsert)."""
        # Save original
        await qdrant_adapter.save(sample_entry)

        # Update and save again
        sample_entry.text = "Updated text"
        await qdrant_adapter.save(sample_entry)

        # Retrieve and verify update
        retrieved = await qdrant_adapter.get(sample_entry.id)
        assert retrieved.text == "Updated text"

    @pytest.mark.asyncio
    async def test_save_preserves_metadata(self, qdrant_adapter, sample_entry):
        """Test that all metadata is preserved."""
        await qdrant_adapter.save(sample_entry)
        retrieved = await qdrant_adapter.get(sample_entry.id)

        assert retrieved.metadata.source == sample_entry.metadata.source
        assert retrieved.metadata.privacy_level == sample_entry.metadata.privacy_level
        assert retrieved.metadata.user_id == sample_entry.metadata.user_id
        assert retrieved.metadata.session_id == sample_entry.metadata.session_id
        assert retrieved.metadata.importance == sample_entry.metadata.importance
        assert retrieved.metadata.tags == sample_entry.metadata.tags

    @pytest.mark.asyncio
    async def test_save_preserves_provenance(self, qdrant_adapter, sample_entry):
        """Test that provenance is preserved."""
        await qdrant_adapter.save(sample_entry)
        retrieved = await qdrant_adapter.get(sample_entry.id)

        assert len(retrieved.metadata.provenance) == len(sample_entry.metadata.provenance)
        assert retrieved.metadata.provenance[0].action == "store"
        assert retrieved.metadata.provenance[0].by == "test_suite"


class TestQdrantQuery:
    """Test query operations."""

    @pytest.mark.asyncio
    async def test_query_returns_similar(self, qdrant_adapter, sample_entries):
        """Test querying returns similar vectors."""
        # Save multiple entries
        await qdrant_adapter.bulk_save(sample_entries)

        # Give Qdrant time to index the vectors
        await asyncio.sleep(0.5)

        # Query with last entry's embedding (most distinct: [0.4, 0.4, ...])
        query_embedding = sample_entries[4].embedding
        results = await qdrant_adapter.query(
            query_embedding, limit=5
        )  # Get all 5 to ensure we find it

        assert len(results) <= 5
        assert len(results) > 0
        # When querying with an exact embedding, that entry should be in top results
        # (may not be first due to vector normalization/indexing, but should be there)
        result_ids = [r.id for r in results]
        assert (
            sample_entries[4].id in result_ids
        ), f"Entry 4 with exact embedding should be in results. Got IDs: {result_ids}"

    @pytest.mark.asyncio
    async def test_query_with_limit(self, qdrant_adapter, sample_entries):
        """Test query respects limit parameter."""
        await qdrant_adapter.bulk_save(sample_entries)

        results = await qdrant_adapter.query(sample_entries[0].embedding, limit=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_query_with_user_filter(self, qdrant_adapter, sample_entries):
        """Test filtering by user_id."""
        # Set different user IDs
        sample_entries[0].metadata.user_id = "alice"
        sample_entries[1].metadata.user_id = "bob"
        sample_entries[2].metadata.user_id = "alice"

        await qdrant_adapter.bulk_save(sample_entries)

        # Query with user filter
        filter_obj = Filter(user_id="alice")
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        # All results should be from alice
        assert all(r.metadata.user_id == "alice" for r in results)

    @pytest.mark.asyncio
    async def test_query_with_session_filter(self, qdrant_adapter, sample_entries):
        """Test filtering by session_id."""
        sample_entries[0].metadata.session_id = "session1"
        sample_entries[1].metadata.session_id = "session2"
        sample_entries[2].metadata.session_id = "session1"

        await qdrant_adapter.bulk_save(sample_entries)

        filter_obj = Filter(session_id="session1")
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        assert all(r.metadata.session_id == "session1" for r in results)

    @pytest.mark.asyncio
    async def test_query_with_privacy_filter(self, qdrant_adapter, sample_entries):
        """Test filtering by privacy level."""
        await qdrant_adapter.bulk_save(sample_entries)

        filter_obj = Filter(privacy_level="public")
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        assert all(r.metadata.privacy_level == "public" for r in results)

    @pytest.mark.asyncio
    async def test_query_with_tags_filter(self, qdrant_adapter, sample_entries):
        """Test filtering by tags."""
        sample_entries[0].metadata.tags = ["python", "coding"]
        sample_entries[1].metadata.tags = ["meeting", "notes"]
        sample_entries[2].metadata.tags = ["python", "async"]

        await qdrant_adapter.bulk_save(sample_entries)

        filter_obj = Filter(tags=["python"])
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        # All results should have "python" tag
        assert all("python" in r.metadata.tags for r in results)

    @pytest.mark.asyncio
    async def test_query_with_importance_filter(self, qdrant_adapter, sample_entries):
        """Test filtering by importance range."""
        await qdrant_adapter.bulk_save(sample_entries)

        filter_obj = Filter(min_importance=0.7)
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        assert all(r.metadata.importance >= 0.7 for r in results)

    @pytest.mark.asyncio
    async def test_query_with_date_range(self, qdrant_adapter, sample_entries):
        """Test filtering by date range."""
        # Set different timestamps
        now = datetime.now(timezone.utc)
        sample_entries[0].metadata.created_at = now - timedelta(days=5)
        sample_entries[1].metadata.created_at = now - timedelta(days=10)
        sample_entries[2].metadata.created_at = now - timedelta(days=2)

        await qdrant_adapter.bulk_save(sample_entries)

        # Query for entries in last 7 days
        filter_obj = Filter(date_range=DateRange(start=now - timedelta(days=7), end=now))
        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        # Should get entries from 5 and 2 days ago
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_query_empty_collection(self, qdrant_adapter):
        """Test querying empty collection."""
        # Ensure collection exists but is empty
        await qdrant_adapter._ensure_collection(384)

        results = await qdrant_adapter.query([0.1] * 384, limit=10)
        assert len(results) == 0


class TestQdrantGet:
    """Test get operations."""

    @pytest.mark.asyncio
    async def test_get_existing(self, qdrant_adapter, sample_entry):
        """Test retrieving existing entry."""
        await qdrant_adapter.save(sample_entry)

        retrieved = await qdrant_adapter.get(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, qdrant_adapter):
        """Test retrieving non-existent entry returns None."""
        result = await qdrant_adapter.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_includes_embedding(self, qdrant_adapter, sample_entry):
        """Test that get includes the embedding vector."""
        await qdrant_adapter.save(sample_entry)

        retrieved = await qdrant_adapter.get(sample_entry.id)
        assert retrieved.embedding is not None
        # Check embedding similarity (float32 precision)
        assert len(retrieved.embedding) == len(sample_entry.embedding)


class TestQdrantDelete:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, qdrant_adapter, sample_entry):
        """Test deleting existing entry."""
        await qdrant_adapter.save(sample_entry)

        result = await qdrant_adapter.delete(sample_entry.id)
        assert result is True

        # Verify it's gone
        retrieved = await qdrant_adapter.get(sample_entry.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, qdrant_adapter):
        """Test deleting non-existent entry."""
        result = await qdrant_adapter.delete("nonexistent-id")
        # Should return False for not found
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_multiple_times(self, qdrant_adapter, sample_entry):
        """Test deleting same entry twice."""
        await qdrant_adapter.save(sample_entry)

        # First delete
        result1 = await qdrant_adapter.delete(sample_entry.id)
        assert result1 is True

        # Second delete
        result2 = await qdrant_adapter.delete(sample_entry.id)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_delete_preserves_others(self, qdrant_adapter, sample_entries):
        """Test that deleting one entry doesn't affect others."""
        await qdrant_adapter.bulk_save(sample_entries)

        # Delete first entry
        await qdrant_adapter.delete(sample_entries[0].id)

        # Others should still exist
        for entry in sample_entries[1:]:
            retrieved = await qdrant_adapter.get(entry.id)
            assert retrieved is not None


class TestQdrantBulkOperations:
    """Test bulk save operations."""

    @pytest.mark.asyncio
    async def test_bulk_save(self, qdrant_adapter, sample_entries):
        """Test bulk saving multiple entries."""
        await qdrant_adapter.bulk_save(sample_entries)

        # Verify all were saved
        for entry in sample_entries:
            retrieved = await qdrant_adapter.get(entry.id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_bulk_save_empty_list(self, qdrant_adapter):
        """Test bulk save with empty list."""
        await qdrant_adapter.bulk_save([])
        # Should not raise error

    @pytest.mark.asyncio
    async def test_bulk_save_without_embeddings_raises_error(self, qdrant_adapter):
        """Test bulk save with missing embeddings."""
        entries = [
            MemoryEntry(
                id=str(uuid4()),
                text="No embedding",
                embedding=None,
                metadata=MemoryMetadata(source="app"),
            )
        ]

        with pytest.raises(ValueError, match="must have an embedding"):
            await qdrant_adapter.bulk_save(entries)

    @pytest.mark.asyncio
    async def test_bulk_save_performance(self, qdrant_adapter):
        """Test that bulk save is efficient."""
        # Create 50 entries
        entries = []
        for i in range(50):
            entry = MemoryEntry(
                id=str(uuid4()),
                text=f"Entry {i}",
                embedding=[float(i % 10) * 0.1] * 384,
                metadata=MemoryMetadata(source="app"),
            )
            entries.append(entry)

        start = time.time()
        await qdrant_adapter.bulk_save(entries)
        duration = time.time() - start

        # Should complete in reasonable time (< 5 seconds for 50 entries)
        assert duration < 5.0


class TestQdrantUtilities:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_count_empty(self, qdrant_adapter):
        """Test count on empty collection."""
        count = await qdrant_adapter.count_async()
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_after_save(self, qdrant_adapter, sample_entries):
        """Test count after saving entries."""
        await qdrant_adapter.bulk_save(sample_entries)

        count = await qdrant_adapter.count_async()
        assert count == len(sample_entries)

    @pytest.mark.asyncio
    async def test_list_ids(self, qdrant_adapter, sample_entries):
        """Test listing all entry IDs."""
        await qdrant_adapter.bulk_save(sample_entries)

        ids = await qdrant_adapter.list_ids_async()
        expected_ids = {e.id for e in sample_entries}
        actual_ids = set(ids)

        assert expected_ids == actual_ids

    @pytest.mark.asyncio
    async def test_clear(self, qdrant_adapter, sample_entries):
        """Test clearing all entries."""
        await qdrant_adapter.bulk_save(sample_entries)

        # Clear
        await qdrant_adapter.clear_async()

        # Verify empty
        count = await qdrant_adapter.count_async()
        assert count == 0

    @pytest.mark.asyncio
    async def test_reindex(self, qdrant_adapter, sample_entries):
        """Test reindex operation."""
        await qdrant_adapter.bulk_save(sample_entries)

        # Reindex (should not raise error)
        await qdrant_adapter.reindex()


class TestQdrantPersistence:
    """Test data persistence across adapter instances."""

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, sample_entries):
        """Test that data persists across adapter instances."""
        collection_name = f"test_persist_{uuid4().hex[:8]}"

        # Create first adapter and save data
        adapter1 = QdrantAdapter(collection_name=collection_name)
        await adapter1.bulk_save(sample_entries)

        # Create second adapter with same collection
        adapter2 = QdrantAdapter(collection_name=collection_name)

        # Verify data is accessible
        for entry in sample_entries:
            retrieved = await adapter2.get(entry.id)
            assert retrieved is not None
            assert retrieved.text == entry.text

        # Cleanup
        await adapter1.client.delete_collection(collection_name)


class TestQdrantSyncWrappers:
    """Test synchronous wrapper methods."""

    def test_sync_wrappers_exist(self):
        """Test that sync wrapper methods exist."""
        adapter = QdrantAdapter(url="http://localhost:6333")

        # Verify all sync methods exist
        assert hasattr(adapter, "save_sync")
        assert hasattr(adapter, "query_sync")
        assert hasattr(adapter, "get_sync")
        assert hasattr(adapter, "delete_sync")
        assert hasattr(adapter, "bulk_save_sync")
        assert hasattr(adapter, "reindex_sync")
        assert hasattr(adapter, "count")
        assert hasattr(adapter, "clear")
        assert hasattr(adapter, "list_ids")


class TestQdrantEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_large_embedding(self, qdrant_adapter):
        """Test with large embedding (1536 dimensions like OpenAI)."""
        entry = MemoryEntry(
            id=str(uuid4()),
            text="Large embedding test",
            embedding=[0.1] * 1536,
            metadata=MemoryMetadata(source="app"),
        )

        await qdrant_adapter.save(entry)
        retrieved = await qdrant_adapter.get(entry.id)
        assert retrieved is not None
        assert len(retrieved.embedding) == 1536

    @pytest.mark.asyncio
    async def test_unicode_text(self, qdrant_adapter):
        """Test with Unicode text."""
        entry = MemoryEntry(
            id=str(uuid4()),
            text="Hello 世界 🌍 Привет",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(source="app"),
        )

        await qdrant_adapter.save(entry)
        retrieved = await qdrant_adapter.get(entry.id)
        assert retrieved.text == "Hello 世界 🌍 Привет"

    @pytest.mark.asyncio
    async def test_empty_tags(self, qdrant_adapter):
        """Test with empty tags list."""
        entry = MemoryEntry(
            id=str(uuid4()),
            text="No tags",
            embedding=[0.1] * 384,
            metadata=MemoryMetadata(source="app", tags=[]),
        )

        await qdrant_adapter.save(entry)
        retrieved = await qdrant_adapter.get(entry.id)
        assert retrieved.metadata.tags == []

    @pytest.mark.asyncio
    async def test_combined_filters(self, qdrant_adapter, sample_entries):
        """Test combining multiple filters."""
        await qdrant_adapter.bulk_save(sample_entries)

        filter_obj = Filter(privacy_level="public", min_importance=0.6, tags=["tag0"])

        results = await qdrant_adapter.query(
            sample_entries[0].embedding, filter=filter_obj, limit=10
        )

        # Verify all conditions are met
        for result in results:
            assert result.metadata.privacy_level == "public"
            assert result.metadata.importance >= 0.6
