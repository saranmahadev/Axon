"""Tests for ChromaDB storage adapter.

This test suite validates the ChromaDB adapter implementation,
including persistence, vector search, and metadata filtering.
"""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.axon.adapters.chroma import ChromaAdapter
from src.axon.models import (
    DateRange,
    Filter,
    MemoryEntry,
    MemoryMetadata,
    ProvenanceEvent,
)


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB storage."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir
        # Give ChromaDB time to release file handles on Windows
        time.sleep(0.1)


@pytest.fixture
def adapter(temp_chroma_dir):
    """Create a ChromaDB adapter with temporary storage."""
    adapter = ChromaAdapter(collection_name="test_memories", persist_directory=temp_chroma_dir)
    yield adapter
    # Explicitly close the client to release file handles
    try:
        adapter.client._producer.stop()
        adapter.client._consumer.stop()
    except Exception:  # Cleanup may fail if already stopped
        pass


@pytest.fixture
def sample_entry():
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        type="note",
        text="Python is great for AI development",
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        metadata=MemoryMetadata(
            user_id="user123",
            session_id="session456",
            source="app",
            tags=["python", "ai"],
            importance=0.8,
        ),
    )


@pytest.fixture
def sample_entries():
    """Create multiple sample entries for bulk operations."""
    return [
        MemoryEntry(
            type="note",
            text="Python is great for AI",
            embedding=[0.9, 0.1, 0.0, 0.0, 0.0],
            metadata=MemoryMetadata(
                user_id="user1",
                tags=["python", "ai"],
                importance=0.9,
            ),
        ),
        MemoryEntry(
            type="note",
            text="JavaScript for web development",
            embedding=[0.1, 0.9, 0.0, 0.0, 0.0],
            metadata=MemoryMetadata(
                user_id="user1",
                tags=["javascript", "web"],
                importance=0.7,
            ),
        ),
        MemoryEntry(
            type="conversation_turn",
            text="Rust is memory safe",
            embedding=[0.0, 0.1, 0.9, 0.0, 0.0],
            metadata=MemoryMetadata(
                user_id="user2",
                tags=["rust", "systems"],
                importance=0.6,
            ),
        ),
    ]


class TestChromaAdapterInit:
    """Test ChromaDB adapter initialization."""

    def test_init_creates_collection(self, temp_chroma_dir):
        """Test that initialization creates a collection."""
        adapter = ChromaAdapter(collection_name="test_init", persist_directory=temp_chroma_dir)
        try:
            assert adapter.collection_name == "test_init"
            assert adapter.persist_directory == temp_chroma_dir
            assert adapter.collection is not None
            assert adapter.client is not None
        finally:
            try:
                adapter.client._producer.stop()
                adapter.client._consumer.stop()
            except Exception:  # Cleanup may fail if already stopped
                pass
            time.sleep(0.1)

    def test_init_persists_to_disk(self, temp_chroma_dir):
        """Test that ChromaDB creates persistent storage."""
        adapter = ChromaAdapter(collection_name="test_persist", persist_directory=temp_chroma_dir)
        try:
            # Check that directory was created
            assert Path(temp_chroma_dir).exists()
            # ChromaDB creates a chroma.sqlite3 file
            assert any(Path(temp_chroma_dir).glob("*.sqlite3"))
        finally:
            try:
                adapter.client._producer.stop()
                adapter.client._consumer.stop()
            except Exception:  # Cleanup may fail if already stopped
                pass
            time.sleep(0.1)

    def test_init_reuses_existing_collection(self, temp_chroma_dir):
        """Test that re-initializing uses existing collection."""
        adapter1 = ChromaAdapter(collection_name="reuse_test", persist_directory=temp_chroma_dir)
        count1 = adapter1.count()
        try:
            adapter1.client._producer.stop()
            adapter1.client._consumer.stop()
        except Exception:  # Cleanup may fail if already stopped
            pass
        time.sleep(0.1)

        # Create new adapter instance
        adapter2 = ChromaAdapter(collection_name="reuse_test", persist_directory=temp_chroma_dir)
        try:
            count2 = adapter2.count()
            assert count1 == count2  # Should have same data
        finally:
            try:
                adapter2.client._producer.stop()
                adapter2.client._consumer.stop()
            except Exception:  # Cleanup may fail if already stopped
                pass
            time.sleep(0.1)


class TestChromaAdapterSave:
    """Test save operations."""

    @pytest.mark.asyncio
    async def test_save_entry(self, adapter, sample_entry):
        """Test saving a single entry."""
        entry_id = await adapter.save(sample_entry)
        assert entry_id == sample_entry.id
        assert adapter.count() == 1

    @pytest.mark.asyncio
    async def test_save_without_embedding_raises_error(self, adapter):
        """Test that saving without embedding raises error."""
        entry = MemoryEntry(
            type="note", text="No embedding", embedding=None, metadata=MemoryMetadata()
        )
        with pytest.raises(ValueError, match="must have an embedding"):
            await adapter.save(entry)

    @pytest.mark.asyncio
    async def test_save_none_raises_error(self, adapter):
        """Test that saving None raises error."""
        with pytest.raises(ValueError, match="Cannot save None"):
            await adapter.save(None)

    @pytest.mark.asyncio
    async def test_save_upserts_existing(self, adapter, sample_entry):
        """Test that saving existing entry updates it."""
        # Save original
        await adapter.save(sample_entry)
        assert adapter.count() == 1

        # Modify and save again
        sample_entry.text = "Updated text"
        sample_entry.embedding = [0.5, 0.4, 0.3, 0.2, 0.1]
        await adapter.save(sample_entry)

        # Should still have 1 entry (upserted, not duplicated)
        assert adapter.count() == 1

        # Verify updated content
        retrieved = await adapter.get(sample_entry.id)
        assert retrieved.text == "Updated text"
        # ChromaDB stores as float32, so compare with tolerance
        assert len(retrieved.embedding) == 5
        for i, val in enumerate([0.5, 0.4, 0.3, 0.2, 0.1]):
            assert abs(retrieved.embedding[i] - val) < 0.0001

    @pytest.mark.asyncio
    async def test_save_preserves_metadata(self, adapter):
        """Test that all metadata fields are preserved."""
        entry = MemoryEntry(
            type="note",
            text="Test metadata preservation",
            embedding=[0.1] * 10,
            metadata=MemoryMetadata(
                user_id="user123",
                session_id="session456",
                source="app",
                privacy_level="private",
                tags=["tag1", "tag2", "tag3"],
                importance=0.95,
                version="v1.0",
                provenance=[
                    ProvenanceEvent(
                        action="created",
                        by="test_user",
                        timestamp=datetime.now(),
                        details={"tool": "test"},
                    )
                ],
            ),
        )

        await adapter.save(entry)
        retrieved = await adapter.get(entry.id)

        assert retrieved.metadata.user_id == "user123"
        assert retrieved.metadata.session_id == "session456"
        assert retrieved.metadata.source == "app"
        assert retrieved.metadata.privacy_level == "private"
        assert retrieved.metadata.tags == ["tag1", "tag2", "tag3"]
        assert retrieved.metadata.importance == 0.95
        assert retrieved.metadata.version == "v1.0"
        assert len(retrieved.metadata.provenance) == 1
        assert retrieved.metadata.provenance[0].action == "created"
        assert retrieved.metadata.provenance[0].by == "test_user"

    def test_save_sync(self, adapter, sample_entry):
        """Test synchronous save wrapper."""
        entry_id = adapter.save_sync(sample_entry)
        assert entry_id == sample_entry.id
        assert adapter.count() == 1


class TestChromaAdapterQuery:
    """Test query operations."""

    @pytest.mark.asyncio
    async def test_query_returns_similar_entries(self, adapter, sample_entries):
        """Test that query returns semantically similar entries."""
        # Save all entries
        await adapter.bulk_save(sample_entries)

        # Query with vector similar to first entry (Python/AI)
        query_vector = [0.95, 0.05, 0.0, 0.0, 0.0]
        results = await adapter.query(query_vector, k=2)

        assert len(results) <= 2
        assert results[0].text == "Python is great for AI"

    @pytest.mark.asyncio
    async def test_query_respects_k_limit(self, adapter, sample_entries):
        """Test that query returns at most k results."""
        await adapter.bulk_save(sample_entries)

        results = await adapter.query([0.1] * 5, k=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_query_empty_vector_raises_error(self, adapter):
        """Test that empty query vector raises error."""
        with pytest.raises(ValueError, match="vector cannot be empty"):
            await adapter.query([], k=5)

    @pytest.mark.asyncio
    async def test_query_invalid_k_raises_error(self, adapter):
        """Test that k <= 0 raises error."""
        with pytest.raises(ValueError, match="k must be positive"):
            await adapter.query([0.1] * 5, k=0)

    @pytest.mark.asyncio
    async def test_query_empty_collection_returns_empty(self, adapter):
        """Test that querying empty collection returns empty list."""
        results = await adapter.query([0.1] * 5, k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_query_with_user_filter(self, adapter, sample_entries):
        """Test filtering by user_id."""
        await adapter.bulk_save(sample_entries)

        filter = Filter(user_id="user1")
        results = await adapter.query([0.1] * 5, k=10, filter=filter)

        assert len(results) == 2
        assert all(r.metadata.user_id == "user1" for r in results)

    @pytest.mark.asyncio
    async def test_query_with_importance_filter(self, adapter, sample_entries):
        """Test filtering by importance range."""
        await adapter.bulk_save(sample_entries)

        filter = Filter(min_importance=0.7, max_importance=1.0)
        results = await adapter.query([0.1] * 5, k=10, filter=filter)

        assert len(results) == 2  # Should get entries with importance >= 0.7
        assert all(r.metadata.importance >= 0.7 for r in results)

    @pytest.mark.asyncio
    async def test_query_with_tags_filter(self, adapter, sample_entries):
        """Test filtering by tags."""
        await adapter.bulk_save(sample_entries)

        filter = Filter(tags=["python"])
        results = await adapter.query([0.1] * 5, k=10, filter=filter)

        assert len(results) == 1
        assert "python" in results[0].metadata.tags

    @pytest.mark.asyncio
    async def test_query_with_date_filter(self, adapter, sample_entries):
        """Test filtering by date range."""
        await adapter.bulk_save(sample_entries)

        # Filter for entries from last hour
        now = datetime.now()
        filter = Filter(
            date_range=DateRange(start=now - timedelta(hours=1), end=now + timedelta(hours=1))
        )
        results = await adapter.query([0.1] * 5, k=10, filter=filter)

        assert len(results) == 3  # All entries were just created

    @pytest.mark.asyncio
    async def test_query_with_multiple_filters(self, adapter, sample_entries):
        """Test combining multiple filters."""
        await adapter.bulk_save(sample_entries)

        filter = Filter(user_id="user1", min_importance=0.8, max_importance=1.0)
        results = await adapter.query([0.1] * 5, k=10, filter=filter)

        assert len(results) == 1  # Only Python entry matches both
        assert results[0].metadata.user_id == "user1"
        assert results[0].metadata.importance >= 0.8

    def test_query_sync(self, adapter, sample_entries):
        """Test synchronous query wrapper."""
        adapter.bulk_save_sync(sample_entries)
        results = adapter.query_sync([0.9, 0.1, 0.0, 0.0, 0.0], k=2)
        assert len(results) <= 2


class TestChromaAdapterGet:
    """Test get operations."""

    @pytest.mark.asyncio
    async def test_get_existing_entry(self, adapter, sample_entry):
        """Test retrieving an existing entry by ID."""
        await adapter.save(sample_entry)
        retrieved = await adapter.get(sample_entry.id)

        assert retrieved.id == sample_entry.id
        assert retrieved.text == sample_entry.text
        assert retrieved.type == sample_entry.type
        # ChromaDB uses float32, compare with tolerance
        assert len(retrieved.embedding) == len(sample_entry.embedding)
        for i in range(len(sample_entry.embedding)):
            assert abs(retrieved.embedding[i] - sample_entry.embedding[i]) < 0.0001

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_error(self, adapter):
        """Test that getting nonexistent entry raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            await adapter.get("nonexistent-id")

    def test_get_sync(self, adapter, sample_entry):
        """Test synchronous get wrapper."""
        adapter.save_sync(sample_entry)
        retrieved = adapter.get_sync(sample_entry.id)
        assert retrieved.id == sample_entry.id


class TestChromaAdapterDelete:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete_existing_entry(self, adapter, sample_entry):
        """Test deleting an existing entry."""
        await adapter.save(sample_entry)
        assert adapter.count() == 1

        result = await adapter.delete(sample_entry.id)
        assert result is True
        assert adapter.count() == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, adapter):
        """Test that deleting nonexistent entry returns False."""
        result = await adapter.delete("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_makes_entry_unretrievable(self, adapter, sample_entry):
        """Test that deleted entry cannot be retrieved."""
        await adapter.save(sample_entry)
        await adapter.delete(sample_entry.id)

        with pytest.raises(KeyError):
            await adapter.get(sample_entry.id)

    def test_delete_sync(self, adapter, sample_entry):
        """Test synchronous delete wrapper."""
        adapter.save_sync(sample_entry)
        result = adapter.delete_sync(sample_entry.id)
        assert result is True


class TestChromaAdapterBulkSave:
    """Test bulk save operations."""

    @pytest.mark.asyncio
    async def test_bulk_save_multiple_entries(self, adapter, sample_entries):
        """Test saving multiple entries at once."""
        ids = await adapter.bulk_save(sample_entries)

        assert len(ids) == 3
        assert adapter.count() == 3

    @pytest.mark.asyncio
    async def test_bulk_save_empty_raises_error(self, adapter):
        """Test that bulk saving empty list raises error."""
        with pytest.raises(ValueError, match="empty list"):
            await adapter.bulk_save([])

    @pytest.mark.asyncio
    async def test_bulk_save_preserves_all_entries(self, adapter, sample_entries):
        """Test that all bulk saved entries can be retrieved."""
        ids = await adapter.bulk_save(sample_entries)

        for entry_id in ids:
            retrieved = await adapter.get(entry_id)
            assert retrieved is not None

    def test_bulk_save_sync(self, adapter, sample_entries):
        """Test synchronous bulk_save wrapper."""
        ids = adapter.bulk_save_sync(sample_entries)
        assert len(ids) == 3


class TestChromaAdapterReindex:
    """Test reindex operations."""

    @pytest.mark.asyncio
    async def test_reindex_is_noop(self, adapter, sample_entries):
        """Test that reindex doesn't break anything (it's a no-op)."""
        await adapter.bulk_save(sample_entries)
        count_before = adapter.count()

        await adapter.reindex()

        count_after = adapter.count()
        assert count_before == count_after

    def test_reindex_sync(self, adapter):
        """Test synchronous reindex wrapper."""
        adapter.reindex_sync()  # Should not raise


class TestChromaAdapterUtilities:
    """Test utility methods."""

    def test_count_empty_collection(self, adapter):
        """Test count on empty collection."""
        assert adapter.count() == 0

    def test_count_after_saves(self, adapter, sample_entries):
        """Test count after saving entries."""
        adapter.bulk_save_sync(sample_entries)
        assert adapter.count() == 3

    def test_list_ids_empty(self, adapter):
        """Test list_ids on empty collection."""
        ids = adapter.list_ids()
        assert ids == []

    def test_list_ids_returns_all_ids(self, adapter, sample_entries):
        """Test that list_ids returns all entry IDs."""
        saved_ids = adapter.bulk_save_sync(sample_entries)
        listed_ids = adapter.list_ids()

        assert set(listed_ids) == set(saved_ids)

    def test_clear_removes_all_entries(self, adapter, sample_entries):
        """Test that clear removes all entries."""
        adapter.bulk_save_sync(sample_entries)
        assert adapter.count() == 3

        adapter.clear()
        assert adapter.count() == 0


class TestChromaAdapterPersistence:
    """Test persistence across adapter instances."""

    def test_data_persists_across_instances(self, temp_chroma_dir, sample_entry):
        """Test that data persists when adapter is recreated."""
        # Save with first adapter
        adapter1 = ChromaAdapter(collection_name="persist_test", persist_directory=temp_chroma_dir)
        adapter1.save_sync(sample_entry)
        count1 = adapter1.count()
        try:
            adapter1.client._producer.stop()
            adapter1.client._consumer.stop()
        except Exception:  # Cleanup may fail if already stopped
            pass
        time.sleep(0.1)

        # Create new adapter instance
        adapter2 = ChromaAdapter(collection_name="persist_test", persist_directory=temp_chroma_dir)
        try:
            count2 = adapter2.count()
            assert count1 == count2 == 1

            # Verify data is accessible
            retrieved = adapter2.get_sync(sample_entry.id)
            assert retrieved.text == sample_entry.text
        finally:
            try:
                adapter2.client._producer.stop()
                adapter2.client._consumer.stop()
            except Exception:  # Cleanup may fail if already stopped
                pass
            time.sleep(0.1)


class TestChromaAdapterEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_unicode_text_handling(self, adapter):
        """Test that unicode text is handled correctly."""
        entry = MemoryEntry(
            type="note", text="Hello 世界 🌍 Привет", embedding=[0.1] * 5, metadata=MemoryMetadata()
        )

        await adapter.save(entry)
        retrieved = await adapter.get(entry.id)
        assert retrieved.text == "Hello 世界 🌍 Привет"

    @pytest.mark.asyncio
    async def test_large_embedding_dimensions(self, adapter):
        """Test with large embedding (like OpenAI's 1536 dims)."""
        entry = MemoryEntry(
            type="note",
            text="Large embedding test",
            embedding=[0.001] * 1536,
            metadata=MemoryMetadata(),
        )

        await adapter.save(entry)
        retrieved = await adapter.get(entry.id)
        assert len(retrieved.embedding) == 1536

    @pytest.mark.asyncio
    async def test_empty_tags_list(self, adapter):
        """Test handling of empty tags list."""
        entry = MemoryEntry(
            type="note", text="No tags", embedding=[0.1] * 5, metadata=MemoryMetadata(tags=[])
        )

        await adapter.save(entry)
        retrieved = await adapter.get(entry.id)
        assert retrieved.metadata.tags == []

    @pytest.mark.asyncio
    async def test_minimal_metadata(self, adapter):
        """Test handling of minimal metadata fields."""
        entry = MemoryEntry(
            type="note",
            text="Minimal metadata",
            embedding=[0.1] * 5,
            metadata=MemoryMetadata(),  # Use defaults
        )

        await adapter.save(entry)
        retrieved = await adapter.get(entry.id)
        assert retrieved.metadata.user_id is None
        assert retrieved.metadata.session_id is None
        assert retrieved.metadata.tags == []
        assert retrieved.metadata.provenance == []
