"""ChromaDB vector storage adapter.

This module provides a persistent vector storage adapter using ChromaDB,
an embedded vector database that stores data on disk.

ChromaDB is ideal for:
- Local development and prototyping
- Small to medium scale deployments (up to ~1M vectors)
- Applications that need persistent storage without external dependencies
- Scenarios where embedded databases are preferred over client-server
"""

import asyncio
import json
from typing import TYPE_CHECKING

import chromadb
from chromadb.config import Settings

from ..models import Filter, MemoryEntry
from .base import StorageAdapter

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection


class ChromaAdapter(StorageAdapter):
    """Persistent vector storage using ChromaDB.

    ChromaDB is an embedded vector database that provides:
    - Persistent storage to disk
    - Vector similarity search with cosine distance
    - Metadata filtering
    - No separate server needed (embedded mode)

    Example:
        >>> adapter = ChromaAdapter(
        ...     collection_name="my_memories",
        ...     persist_directory="./chroma_db"
        ... )
        >>> await adapter.save(memory_entry)
        >>> results = await adapter.query(embedding, k=10)

    Attributes:
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory where ChromaDB stores data
        client: ChromaDB client instance
        collection: ChromaDB collection instance
    """

    def __init__(
        self,
        collection_name: str = "axon_memories",
        persist_directory: str = "./chroma_db",
        **kwargs,
    ):
        """Initialize ChromaDB adapter.

        Args:
            collection_name: Name of the collection to use
            persist_directory: Directory for persistent storage
            **kwargs: Additional ChromaDB settings

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        try:
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection
            self.collection: Collection = self.client.get_or_create_collection(
                name=collection_name, metadata={"description": "Axon Memory SDK storage"}
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChromaDB: {str(e)}") from e

    def _entry_to_chroma_format(self, entry: MemoryEntry) -> tuple[str, list[float], dict, str]:
        """Convert MemoryEntry to ChromaDB format.

        Args:
            entry: The memory entry to convert

        Returns:
            Tuple of (id, embedding, metadata, document)

        Raises:
            ValueError: If entry has no embedding
        """
        if not entry.embedding:
            raise ValueError(f"Entry {entry.id} must have an embedding for ChromaDB storage")

        # Build metadata dict (ChromaDB supports flat dicts)
        metadata = {
            "type": entry.type,
            "user_id": entry.metadata.user_id or "",
            "session_id": entry.metadata.session_id or "",
            "source": entry.metadata.source,
            "privacy_level": entry.metadata.privacy_level,
            "importance": entry.metadata.importance,
            "created_at": entry.metadata.created_at.isoformat(),
            "created_at_timestamp": entry.metadata.created_at.timestamp(),  # For filtering
            "version": entry.metadata.version,
        }

        # Add last_accessed_at if present
        if entry.metadata.last_accessed_at:
            metadata["last_accessed_at"] = entry.metadata.last_accessed_at.isoformat()

        # Serialize tags as JSON string (ChromaDB doesn't support list filtering well)
        if entry.metadata.tags:
            metadata["tags"] = json.dumps(entry.metadata.tags)

        # Serialize provenance as JSON string (use mode='json' to serialize datetimes)
        if entry.metadata.provenance:
            metadata["provenance"] = json.dumps(
                [p.model_dump(mode="json") for p in entry.metadata.provenance]
            )

        return (entry.id, entry.embedding, metadata, entry.text)

    def _chroma_to_entry(
        self, id: str, embedding: list[float], metadata: dict, document: str
    ) -> MemoryEntry:
        """Convert ChromaDB result to MemoryEntry.

        Args:
            id: Entry ID
            embedding: Vector embedding
            metadata: Metadata dict from ChromaDB
            document: Text content

        Returns:
            Reconstructed MemoryEntry
        """
        from datetime import datetime

        from ..models import MemoryMetadata, ProvenanceEvent

        # Parse dates
        created_at = datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat()))
        last_accessed_at = None
        if metadata.get("last_accessed_at"):
            last_accessed_at = datetime.fromisoformat(metadata["last_accessed_at"])

        # Parse tags
        tags = []
        if metadata.get("tags"):
            try:
                tags = json.loads(metadata["tags"])
            except (json.JSONDecodeError, TypeError):
                tags = []

        # Parse provenance
        provenance = []
        if metadata.get("provenance"):
            try:
                provenance_data = json.loads(metadata["provenance"])
                provenance = [ProvenanceEvent(**p) for p in provenance_data]
            except (json.JSONDecodeError, TypeError, ValueError):
                provenance = []

        # Build MemoryMetadata
        memory_metadata = MemoryMetadata(
            user_id=metadata.get("user_id") or None,
            session_id=metadata.get("session_id") or None,
            source=metadata.get("source", "app"),
            privacy_level=metadata.get("privacy_level", "public"),
            created_at=created_at,
            last_accessed_at=last_accessed_at,
            tags=tags,
            importance=metadata.get("importance", 0.5),
            version=metadata.get("version", ""),
            provenance=provenance,
        )

        # Build MemoryEntry
        return MemoryEntry(
            id=id,
            type=metadata.get("type", "note"),
            text=document,
            embedding=embedding,
            metadata=memory_metadata,
        )

    def _filter_to_chroma_where(self, filter: Filter) -> dict | None:
        """Convert Axon Filter to ChromaDB where clause.

        Args:
            filter: Axon filter object

        Returns:
            ChromaDB where clause dict, or None if no filters
        """
        conditions = []

        # User ID filter
        if filter.user_id:
            conditions.append({"user_id": filter.user_id})

        # Session ID filter
        if filter.session_id:
            conditions.append({"session_id": filter.session_id})

        # Importance range filter (min/max)
        if filter.min_importance is not None:
            conditions.append({"importance": {"$gte": filter.min_importance}})

        if filter.max_importance is not None:
            conditions.append({"importance": {"$lte": filter.max_importance}})

        # Tags filter (need to check if JSON contains any of the tags)
        # Note: ChromaDB's filtering for JSON strings is limited
        # For production, consider storing tags differently
        if filter.tags:
            # This is a simplified approach - checks if tags field contains the tag string
            # For better tag filtering, consider using a different metadata structure
            pass  # Skip for now - would need custom filtering post-query

        #  Date range filter - ChromaDB needs timestamps as Unix time (float)
        if filter.date_range and filter.date_range.start:
            # Convert datetime to timestamp
            timestamp = filter.date_range.start.timestamp()
            conditions.append({"created_at_timestamp": {"$gte": timestamp}})

        if filter.date_range and filter.date_range.end:
            # Convert datetime to timestamp
            timestamp = filter.date_range.end.timestamp()
            conditions.append({"created_at_timestamp": {"$lte": timestamp}})

        # Combine conditions
        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    async def save(self, entry: MemoryEntry) -> str:
        """Store a memory entry in ChromaDB.

        Args:
            entry: The memory entry to store

        Returns:
            The ID of the stored entry

        Raises:
            ValueError: If entry is None or has no embedding
            RuntimeError: If ChromaDB operation fails
        """
        if entry is None:
            raise ValueError("Cannot save None entry")

        try:
            id, embedding, metadata, document = self._entry_to_chroma_format(entry)

            # ChromaDB add/update (upsert behavior)
            self.collection.upsert(
                ids=[id], embeddings=[embedding], metadatas=[metadata], documents=[document]
            )

            return id

        except ValueError:
            # Re-raise ValueErrors (like missing embedding) directly
            raise
        except Exception as e:
            raise RuntimeError(f"ChromaDB save failed: {str(e)}") from e

    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Query by vector similarity with optional filtering.

        Args:
            vector: Query embedding vector
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of up to k matching entries, ordered by similarity

        Raises:
            ValueError: If vector is empty or k <= 0
            RuntimeError: If ChromaDB query fails
        """
        if not vector:
            raise ValueError("Query vector cannot be empty")
        if k <= 0:
            raise ValueError("k must be positive")

        try:
            # Build where clause from filter
            where = None
            if filter:
                where = self._filter_to_chroma_where(filter)

            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=k,
                where=where,
                include=["embeddings", "metadatas", "documents"],
            )

            # Convert results to MemoryEntry objects
            entries = []
            if results and results["ids"] and results["ids"][0]:
                for i, id in enumerate(results["ids"][0]):
                    entry = self._chroma_to_entry(
                        id=id,
                        embedding=results["embeddings"][0][i],
                        metadata=results["metadatas"][0][i],
                        document=results["documents"][0][i],
                    )
                    entries.append(entry)

            # Post-filter for tags if needed (since ChromaDB tag filtering is limited)
            if filter and filter.tags:
                entries = [e for e in entries if any(tag in e.metadata.tags for tag in filter.tags)]

            return entries

        except Exception as e:
            raise RuntimeError(f"ChromaDB query failed: {str(e)}") from e

    async def get(self, id: str) -> MemoryEntry:
        """Retrieve a memory entry by ID.

        Args:
            id: The entry ID

        Returns:
            The memory entry

        Raises:
            KeyError: If entry not found
            RuntimeError: If ChromaDB operation fails
        """
        try:
            results = self.collection.get(
                ids=[id], include=["embeddings", "metadatas", "documents"]
            )

            if not results or not results["ids"]:
                raise KeyError(f"Entry {id} not found")

            return self._chroma_to_entry(
                id=results["ids"][0],
                embedding=results["embeddings"][0],
                metadata=results["metadatas"][0],
                document=results["documents"][0],
            )

        except KeyError:
            raise
        except Exception as e:
            raise RuntimeError(f"ChromaDB get failed: {str(e)}") from e

    async def delete(self, id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            id: The entry ID

        Returns:
            True if deleted, False if not found

        Raises:
            RuntimeError: If ChromaDB operation fails
        """
        try:
            # Check if exists first
            try:
                await self.get(id)
            except KeyError:
                return False

            # Delete from ChromaDB
            self.collection.delete(ids=[id])
            return True

        except Exception as e:
            raise RuntimeError(f"ChromaDB delete failed: {str(e)}") from e

    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Save multiple memory entries efficiently.

        Args:
            entries: List of entries to save

        Returns:
            List of IDs of saved entries

        Raises:
            ValueError: If entries list is empty
            RuntimeError: If ChromaDB operation fails
        """
        if not entries:
            raise ValueError("Cannot bulk save empty list")

        try:
            ids = []
            embeddings = []
            metadatas = []
            documents = []

            for entry in entries:
                id, embedding, metadata, document = self._entry_to_chroma_format(entry)
                ids.append(id)
                embeddings.append(embedding)
                metadatas.append(metadata)
                documents.append(document)

            # Bulk upsert
            self.collection.upsert(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )

            return ids

        except Exception as e:
            raise RuntimeError(f"ChromaDB bulk_save failed: {str(e)}") from e

    async def reindex(self) -> None:
        """Rebuild indices (no-op for ChromaDB as it auto-indexes).

        ChromaDB automatically maintains indices, so this is a no-op.
        Included for interface compliance.
        """
        # ChromaDB handles indexing automatically
        pass

    # Utility methods specific to ChromaDB

    def count(self) -> int:
        """Get total number of entries in collection.

        Returns:
            Count of entries
        """
        return self.collection.count()

    def clear(self) -> None:
        """Delete all entries from collection.

        Warning: This deletes all data in the collection!
        """
        # Delete and recreate collection
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name, metadata={"description": "Axon Memory SDK storage"}
        )

    def list_ids(self) -> list[str]:
        """Get all entry IDs in collection.

        Returns:
            List of all entry IDs
        """
        results = self.collection.get(include=[])
        return results["ids"] if results and results["ids"] else []

    def close(self) -> None:
        """Close the ChromaDB client and release resources.

        This is important on Windows to release file locks.
        """
        try:
            # Clear internal references
            self.collection = None
            # ChromaDB client cleanup
            if hasattr(self.client, "_system"):
                self.client._system.stop()
            self.client = None
        except Exception:
            # Ignore cleanup errors
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False

    # Sync wrappers for compatibility

    def save_sync(self, entry: MemoryEntry) -> str:
        """Synchronous wrapper for save()."""
        return asyncio.run(self.save(entry))

    def query_sync(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Synchronous wrapper for query()."""
        return asyncio.run(self.query(vector, k, filter))

    def get_sync(self, id: str) -> MemoryEntry:
        """Synchronous wrapper for get()."""
        return asyncio.run(self.get(id))

    def delete_sync(self, id: str) -> bool:
        """Synchronous wrapper for delete()."""
        return asyncio.run(self.delete(id))

    def bulk_save_sync(self, entries: list[MemoryEntry]) -> list[str]:
        """Synchronous wrapper for bulk_save()."""
        return asyncio.run(self.bulk_save(entries))

    def reindex_sync(self) -> None:
        """Synchronous wrapper for reindex()."""
        asyncio.run(self.reindex())
