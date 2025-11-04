"""In-memory storage adapter for testing and ephemeral storage.

This adapter stores memory entries in RAM using dictionaries and provides
vector similarity search using numpy for cosine similarity calculation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .base import StorageAdapter

if TYPE_CHECKING:
    from ..models import Filter, MemoryEntry


class InMemoryAdapter(StorageAdapter):
    """In-memory storage adapter using dictionaries and numpy.

    Stores memory entries in RAM with support for vector similarity search.
    Ideal for testing, development, and ephemeral memory tiers.

    Features:
        - Fast in-memory CRUD operations
        - Cosine similarity search with numpy
        - Metadata filtering via Filter model
        - No persistence (data lost on restart)

    Thread Safety:
        Not thread-safe. Use external synchronization for concurrent access.

    Attributes:
        _storage: Dictionary mapping entry IDs to MemoryEntry objects
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory storage."""
        self._storage: dict[str, MemoryEntry] = {}

    async def save(self, entry: MemoryEntry) -> str:
        """Save a memory entry to in-memory storage.

        Args:
            entry: The memory entry to save

        Returns:
            The ID of the saved entry

        Raises:
            ValueError: If entry is None
        """
        if entry is None:
            raise ValueError("Entry cannot be None")

        self._storage[entry.id] = entry
        return entry.id

    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Query by vector similarity with optional filtering.

        Uses cosine similarity to find the k most similar entries.
        Only considers entries that have embeddings.

        Args:
            vector: Query embedding vector
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of up to k matching entries, ordered by similarity

        Raises:
            ValueError: If vector is empty or k <= 0
        """
        if not vector:
            raise ValueError("Query vector cannot be empty")
        if k <= 0:
            raise ValueError("k must be positive")

        # Get all entries with embeddings
        entries_with_embeddings = [
            entry for entry in self._storage.values() if entry.has_embedding
        ]

        # Apply metadata filter if provided
        if filter is not None:
            entries_with_embeddings = [
                entry for entry in entries_with_embeddings if filter.matches(entry)
            ]

        # If no entries match, return empty list
        if not entries_with_embeddings:
            return []

        # Calculate cosine similarities
        query_vector = np.array(vector)
        query_norm = np.linalg.norm(query_vector)

        if query_norm == 0:
            raise ValueError("Query vector has zero magnitude")

        similarities: list[tuple[float, MemoryEntry]] = []

        for entry in entries_with_embeddings:
            entry_vector = np.array(entry.embedding)
            entry_norm = np.linalg.norm(entry_vector)

            if entry_norm == 0:
                # Skip entries with zero-magnitude embeddings
                continue

            # Cosine similarity = dot(a, b) / (||a|| * ||b||)
            similarity = np.dot(query_vector, entry_vector) / (query_norm * entry_norm)
            similarities.append((float(similarity), entry))

        # Sort by similarity (highest first) and return top k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in similarities[:k]]

    async def get(self, id: str) -> MemoryEntry:
        """Retrieve a memory entry by ID.

        Args:
            id: Unique identifier of the entry

        Returns:
            The memory entry

        Raises:
            KeyError: If entry with given ID does not exist
        """
        if id not in self._storage:
            raise KeyError(f"Entry with id '{id}' not found")
        return self._storage[id]

    async def delete(self, id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            id: Unique identifier of the entry to delete

        Returns:
            True if entry was deleted, False if not found
        """
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Save multiple memory entries.

        Args:
            entries: List of memory entries to save

        Returns:
            List of IDs for the saved entries

        Raises:
            ValueError: If entries is empty
        """
        if not entries:
            raise ValueError("Entries list cannot be empty")

        ids = []
        for entry in entries:
            await self.save(entry)
            ids.append(entry.id)
        return ids

    async def reindex(self) -> None:
        """Rebuild index (no-op for in-memory adapter).

        In-memory adapter doesn't use a persistent index,
        so this is a no-op.
        """
        pass

    # Utility methods

    def clear(self) -> None:
        """Clear all entries from storage.

        Useful for testing and resetting state.
        """
        self._storage.clear()

    def count(self) -> int:
        """Get the total number of entries in storage.

        Returns:
            Number of entries stored
        """
        return len(self._storage)

    def list_ids(self) -> list[str]:
        """Get list of all entry IDs in storage.

        Returns:
            List of entry IDs
        """
        return list(self._storage.keys())
