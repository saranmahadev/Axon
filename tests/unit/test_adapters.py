"""Unit tests for storage adapters.

Tests for StorageAdapter ABC and InMemoryAdapter implementation.
"""

from __future__ import annotations

import pytest

from axon import Filter, InMemoryAdapter, MemoryEntry


class TestInMemoryAdapter:
    """Tests for InMemoryAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh InMemoryAdapter for each test."""
        return InMemoryAdapter()

    @pytest.fixture
    def sample_entry(self):
        """Create a sample memory entry without embedding."""
        return MemoryEntry(
            text="User mentioned they love Python programming",
            type="note",
            metadata={"user_id": "u123", "topic": "programming"},
        )

    @pytest.fixture
    def sample_entry_with_embedding(self):
        """Create a sample memory entry with embedding."""
        return MemoryEntry(
            text="User prefers science fiction movies",
            type="note",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            metadata={"user_id": "u123", "topic": "movies"},
        )

    # Test: Save and Get
    @pytest.mark.asyncio
    async def test_save_and_get(self, adapter, sample_entry):
        """Test saving and retrieving an entry."""
        entry_id = await adapter.save(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = await adapter.get(entry_id)
        assert retrieved.id == sample_entry.id
        assert retrieved.text == sample_entry.text

    @pytest.mark.asyncio
    async def test_save_none_raises_error(self, adapter):
        """Test that saving None raises ValueError."""
        with pytest.raises(ValueError, match="Entry cannot be None"):
            await adapter.save(None)

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_keyerror(self, adapter):
        """Test that getting nonexistent entry raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            await adapter.get("nonexistent-id")

    # Test: Delete
    @pytest.mark.asyncio
    async def test_delete_existing_entry(self, adapter, sample_entry):
        """Test deleting an existing entry."""
        await adapter.save(sample_entry)
        result = await adapter.delete(sample_entry.id)
        assert result is True

        with pytest.raises(KeyError):
            await adapter.get(sample_entry.id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self, adapter):
        """Test deleting nonexistent entry returns False."""
        result = await adapter.delete("nonexistent-id")
        assert result is False

    # Test: Bulk Save
    @pytest.mark.asyncio
    async def test_bulk_save(self, adapter):
        """Test bulk saving multiple entries."""
        entries = [MemoryEntry(text=f"Entry {i}", type="note") for i in range(5)]
        ids = await adapter.bulk_save(entries)

        assert len(ids) == 5
        for entry_id, entry in zip(ids, entries, strict=False):
            assert entry_id == entry.id
            retrieved = await adapter.get(entry_id)
            assert retrieved.text == entry.text

    @pytest.mark.asyncio
    async def test_bulk_save_empty_raises_error(self, adapter):
        """Test that bulk saving empty list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter.bulk_save([])

    # Test: Query - Vector Similarity
    @pytest.mark.asyncio
    async def test_query_vector_similarity(self, adapter):
        """Test querying by vector similarity."""
        # Create entries with different embeddings
        entry1 = MemoryEntry(
            text="Entry 1",
            type="note",
            embedding=[1.0, 0.0, 0.0],
        )
        entry2 = MemoryEntry(
            text="Entry 2",
            type="note",
            embedding=[0.9, 0.1, 0.0],  # Very similar to entry1
        )
        entry3 = MemoryEntry(
            text="Entry 3",
            type="note",
            embedding=[0.0, 0.0, 1.0],  # Orthogonal to entry1
        )

        await adapter.bulk_save([entry1, entry2, entry3])

        # Query with vector similar to entry1
        results = await adapter.query(vector=[1.0, 0.0, 0.0], k=2)

        assert len(results) == 2
        # entry1 should be most similar (cosine = 1.0)
        assert results[0].id == entry1.id
        # entry2 should be second (cosine ~ 0.99)
        assert results[1].id == entry2.id

    @pytest.mark.asyncio
    async def test_query_with_filter(self, adapter):
        """Test querying with metadata filter."""
        entry1 = MemoryEntry(
            text="Entry 1",
            type="note",
            embedding=[1.0, 0.0, 0.0],
            metadata={"category": "tech"},
        )
        entry2 = MemoryEntry(
            text="Entry 2",
            type="note",
            embedding=[0.9, 0.1, 0.0],
            metadata={"category": "sports"},
        )

        await adapter.bulk_save([entry1, entry2])

        # Query with filter for "tech" category
        filter_tech = Filter(custom={"category": "tech"})
        results = await adapter.query(vector=[1.0, 0.0, 0.0], k=10, filter=filter_tech)

        assert len(results) == 1
        assert results[0].id == entry1.id

    @pytest.mark.asyncio
    async def test_query_empty_vector_raises_error(self, adapter):
        """Test that querying with empty vector raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter.query(vector=[], k=5)

    @pytest.mark.asyncio
    async def test_query_invalid_k_raises_error(self, adapter):
        """Test that querying with k <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            await adapter.query(vector=[1.0, 0.0], k=0)

    @pytest.mark.asyncio
    async def test_query_zero_magnitude_vector_raises_error(self, adapter):
        """Test that querying with zero-magnitude vector raises ValueError."""
        entry = MemoryEntry(
            text="Entry",
            type="note",
            embedding=[1.0, 0.0],
        )
        await adapter.save(entry)

        with pytest.raises(ValueError, match="zero magnitude"):
            await adapter.query(vector=[0.0, 0.0], k=5)

    @pytest.mark.asyncio
    async def test_query_no_embeddings_returns_empty(self, adapter):
        """Test that querying when no entries have embeddings returns empty list."""
        entry = MemoryEntry(text="Entry without embedding", type="note")
        await adapter.save(entry)

        results = await adapter.query(vector=[1.0, 0.0], k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_query_skips_zero_magnitude_embeddings(self, adapter):
        """Test that query skips entries with zero-magnitude embeddings."""
        entry1 = MemoryEntry(
            text="Good entry",
            type="note",
            embedding=[1.0, 0.0],
        )
        entry2 = MemoryEntry(
            text="Bad entry",
            type="note",
            embedding=[0.0, 0.0],  # Zero magnitude
        )
        await adapter.bulk_save([entry1, entry2])

        results = await adapter.query(vector=[1.0, 0.0], k=10)
        assert len(results) == 1
        assert results[0].id == entry1.id

    # Test: Reindex
    @pytest.mark.asyncio
    async def test_reindex_no_op(self, adapter):
        """Test that reindex is a no-op for in-memory adapter."""
        await adapter.reindex()  # Should not raise

    # Test: Utility Methods
    def test_count(self, adapter, sample_entry):
        """Test count method."""
        assert adapter.count() == 0

        adapter.save_sync(sample_entry)
        assert adapter.count() == 1

        adapter.save_sync(MemoryEntry(text="Another entry", type="note"))
        assert adapter.count() == 2

    def test_clear(self, adapter, sample_entry):
        """Test clear method."""
        adapter.save_sync(sample_entry)
        assert adapter.count() == 1

        adapter.clear()
        assert adapter.count() == 0

    def test_list_ids(self, adapter):
        """Test list_ids method."""
        entries = [MemoryEntry(text=f"Entry {i}", type="note") for i in range(3)]
        ids = adapter.bulk_save_sync(entries)

        listed_ids = adapter.list_ids()
        assert len(listed_ids) == 3
        assert set(listed_ids) == set(ids)

    # Test: Sync Wrappers
    def test_save_sync(self, adapter, sample_entry):
        """Test synchronous save wrapper."""
        entry_id = adapter.save_sync(sample_entry)
        assert entry_id == sample_entry.id

    def test_get_sync(self, adapter, sample_entry):
        """Test synchronous get wrapper."""
        adapter.save_sync(sample_entry)
        retrieved = adapter.get_sync(sample_entry.id)
        assert retrieved.id == sample_entry.id

    def test_delete_sync(self, adapter, sample_entry):
        """Test synchronous delete wrapper."""
        adapter.save_sync(sample_entry)
        result = adapter.delete_sync(sample_entry.id)
        assert result is True

    def test_bulk_save_sync(self, adapter):
        """Test synchronous bulk_save wrapper."""
        entries = [MemoryEntry(text=f"Entry {i}", type="note") for i in range(3)]
        ids = adapter.bulk_save_sync(entries)
        assert len(ids) == 3

    def test_query_sync(self, adapter, sample_entry_with_embedding):
        """Test synchronous query wrapper."""
        adapter.save_sync(sample_entry_with_embedding)
        results = adapter.query_sync(vector=[0.1, 0.2, 0.3, 0.4, 0.5], k=1)
        assert len(results) == 1

    def test_reindex_sync(self, adapter):
        """Test synchronous reindex wrapper."""
        adapter.reindex_sync()  # Should not raise


class TestStorageAdapterInterface:
    """Tests for StorageAdapter ABC interface."""

    def test_cannot_instantiate_abc(self):
        """Test that StorageAdapter ABC cannot be instantiated directly."""
        from axon.adapters.base import StorageAdapter

        with pytest.raises(TypeError):
            StorageAdapter()

    def test_inmemory_implements_all_methods(self):
        """Test that InMemoryAdapter implements all required methods."""
        adapter = InMemoryAdapter()

        # Check all abstract methods are implemented
        assert hasattr(adapter, "save")
        assert hasattr(adapter, "query")
        assert hasattr(adapter, "get")
        assert hasattr(adapter, "delete")
        assert hasattr(adapter, "bulk_save")
        assert hasattr(adapter, "reindex")

        # Check sync wrappers exist
        assert hasattr(adapter, "save_sync")
        assert hasattr(adapter, "query_sync")
        assert hasattr(adapter, "get_sync")
        assert hasattr(adapter, "delete_sync")
        assert hasattr(adapter, "bulk_save_sync")
        assert hasattr(adapter, "reindex_sync")
