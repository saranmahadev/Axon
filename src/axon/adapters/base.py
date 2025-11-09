"""Storage adapter base classes and interfaces.

This module defines the abstract StorageAdapter interface that all
storage backends must implement for the Axon memory system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Filter, MemoryEntry


class StorageAdapter(ABC):
    """Abstract base class for storage adapters.

    All storage backends (InMemory, Redis, Vector DBs, SQL, S3) must
    implement this interface to provide consistent storage operations
    across different persistence layers.

    Methods:
        save: Store a single memory entry
        query: Search by vector similarity with optional filtering
        get: Retrieve entry by ID
        delete: Remove entry by ID
        bulk_save: Store multiple entries efficiently
        reindex: Rebuild index for vector stores
    """

    @abstractmethod
    async def save(self, entry: MemoryEntry) -> str:
        """Save a memory entry and return its ID.

        Args:
            entry: The memory entry to save

        Returns:
            The ID of the saved entry

        Raises:
            ValueError: If entry is invalid
        """
        pass

    @abstractmethod
    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Query by vector similarity with optional metadata filtering.

        Performs semantic search using cosine similarity between the query
        vector and stored embeddings. Results can be filtered by metadata.

        Args:
            vector: Query embedding vector
            k: Number of results to return (top-k)
            filter: Optional metadata filter to apply

        Returns:
            List of matching memory entries, ordered by similarity (highest first)

        Raises:
            ValueError: If vector is empty or k is invalid
        """
        pass

    @abstractmethod
    async def get(self, id: str) -> MemoryEntry:
        """Retrieve a memory entry by ID.

        Args:
            id: Unique identifier of the entry

        Returns:
            The memory entry

        Raises:
            KeyError: If entry with given ID does not exist
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            id: Unique identifier of the entry to delete

        Returns:
            True if entry was deleted, False if not found

        Raises:
            ValueError: If id is invalid
        """
        pass

    @abstractmethod
    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Save multiple memory entries efficiently.

        Implementations should optimize this for batch operations where possible.

        Args:
            entries: List of memory entries to save

        Returns:
            List of IDs for the saved entries (in same order)

        Raises:
            ValueError: If entries list is empty or contains invalid entries
        """
        pass

    @abstractmethod
    async def reindex(self) -> None:
        """Rebuild the index for vector search.

        For vector stores, this rebuilds the similarity index.
        For other stores, this may be a no-op.

        Raises:
            RuntimeError: If reindexing fails
        """
        pass

    # Optional transaction support methods
    # Adapters that support transactions should override these

    async def supports_transactions(self) -> bool:
        """
        Check if adapter supports transactions.

        Returns:
            True if adapter implements prepare/commit/abort, False otherwise
        """
        return False

    async def prepare_transaction(self, transaction_id: str) -> bool:
        """
        Prepare for transaction commit (Phase 1 of 2PC).

        This method should validate that all pending operations can be
        committed and reserve necessary resources.

        Args:
            transaction_id: Unique transaction identifier

        Returns:
            True if ready to commit, False if cannot prepare

        Raises:
            NotImplementedError: If adapter doesn't support transactions
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support transactions")

    async def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit transaction (Phase 2 of 2PC).

        This method should apply all pending changes atomically.

        Args:
            transaction_id: Unique transaction identifier

        Returns:
            True if commit succeeded, False otherwise

        Raises:
            NotImplementedError: If adapter doesn't support transactions
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support transactions")

    async def abort_transaction(self, transaction_id: str) -> bool:
        """
        Abort transaction and rollback changes.

        This method should discard all pending changes for the transaction.

        Args:
            transaction_id: Unique transaction identifier

        Returns:
            True if abort succeeded, False otherwise

        Raises:
            NotImplementedError: If adapter doesn't support transactions
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support transactions")

    # Sync wrappers for convenience
    def save_sync(self, entry: MemoryEntry) -> str:
        """Synchronous wrapper for save()."""
        import asyncio

        return asyncio.run(self.save(entry))

    def query_sync(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Synchronous wrapper for query()."""
        import asyncio

        return asyncio.run(self.query(vector, k, filter))

    def get_sync(self, id: str) -> MemoryEntry:
        """Synchronous wrapper for get()."""
        import asyncio

        return asyncio.run(self.get(id))

    def delete_sync(self, id: str) -> bool:
        """Synchronous wrapper for delete()."""
        import asyncio

        return asyncio.run(self.delete(id))

    def bulk_save_sync(self, entries: list[MemoryEntry]) -> list[str]:
        """Synchronous wrapper for bulk_save()."""
        import asyncio

        return asyncio.run(self.bulk_save(entries))

    def reindex_sync(self) -> None:
        """Synchronous wrapper for reindex()."""
        import asyncio

        return asyncio.run(self.reindex())
