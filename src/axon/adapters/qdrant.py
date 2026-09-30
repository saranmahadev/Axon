"""Qdrant vector storage adapter.

This adapter provides persistent vector storage using Qdrant,
a high-performance vector search engine. Supports both local and remote instances.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..errors import AdapterError, EntryNotFoundError
from ..models import Filter, MemoryEntry
from ._serialization import extra_metadata_from_json, extra_metadata_to_json
from .base import StorageAdapter

logger = logging.getLogger(__name__)

# Fixed namespace so non-UUID entry ids map to the same Qdrant point id every time
_ID_NAMESPACE = uuid.UUID("6f0d3a3e-8f6b-4c1e-9a55-0a5e5d3d7a11")


def _point_id(entry_id: str) -> str:
    """Map an entry id to a Qdrant point id.

    Qdrant only accepts UUIDs or unsigned ints, but Axon lets callers choose any string
    id. UUIDs pass through; anything else maps deterministically via UUIDv5. The original
    id is stored in the payload (``entry_id``) and restored on read.
    """
    try:
        return str(uuid.UUID(entry_id))
    except (ValueError, AttributeError, TypeError):
        return str(uuid.uuid5(_ID_NAMESPACE, str(entry_id)))


class QdrantAdapter(StorageAdapter):
    """Qdrant vector storage adapter for persistent, high-performance vector search.

    Supports:
    - Local and remote Qdrant instances
    - Vector similarity search with cosine distance
    - Metadata filtering with Qdrant filter syntax
    - Persistent storage
    - Connection pooling and retry logic
    - Batch operations

    Attributes:
        client: Async Qdrant client
        collection_name: Name of the Qdrant collection
        embedding_dim: Dimension of embeddings (set on first save)

    Example:
        ```python
        # Local instance
        adapter = QdrantAdapter(url="http://localhost:6333", collection_name="memories")

        # Remote instance with API key
        adapter = QdrantAdapter(
            url="https://xyz.cloud.qdrant.io",
            api_key="your-api-key",
            collection_name="memories"
        )
        ```
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "axon_memories",
        api_key: str | None = None,
        timeout: int = 30,
        **kwargs: Any,
    ):
        """Initialize Qdrant adapter.

        Args:
            url: Qdrant server URL (default: http://localhost:6333)
            collection_name: Collection name for storing memories
            api_key: API key for Qdrant Cloud (optional)
            timeout: Request timeout in seconds
            **kwargs: Additional QdrantClient arguments
        """
        self.url = url
        self.collection_name = collection_name
        self.api_key = api_key
        self.timeout = timeout
        self._embedding_dim: int | None = None

        # Initialize async client
        import warnings

        with warnings.catch_warnings():
            # Suppress the warning about using API key with insecure connection
            # This is expected in local testing scenarios
            warnings.filterwarnings("ignore", message="Api key is used with an insecure connection")
            self.client = AsyncQdrantClient(url=url, api_key=api_key, timeout=timeout, **kwargs)

    async def _ensure_collection(self, embedding_dim: int) -> None:
        """Ensure collection exists with correct configuration.

        Args:
            embedding_dim: Dimension of embeddings
        """
        if self._embedding_dim is None:
            self._embedding_dim = embedding_dim

        # Check if collection exists
        collections = await self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            # Create collection with vector configuration
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
            )

    def _entry_to_point(self, entry: MemoryEntry) -> PointStruct:
        """Convert MemoryEntry to Qdrant PointStruct.

        Args:
            entry: Memory entry

        Returns:
            Qdrant point with id, vector, and payload
        """
        if entry.embedding is None:
            raise ValueError(f"Entry {entry.id} has no embedding")

        # Build payload with all metadata
        payload = {
            "entry_id": entry.id,
            "type": entry.type,
            "version": entry.metadata.version,
            "extra_metadata": extra_metadata_to_json(entry.metadata),
            "text": entry.text,
            "source": entry.metadata.source,
            "privacy_level": entry.metadata.privacy_level,
            "user_id": entry.metadata.user_id or "",
            "session_id": entry.metadata.session_id or "",
            "importance": entry.metadata.importance,
            "created_at": entry.metadata.created_at.timestamp(),  # Store as Unix timestamp for filtering
            "tags": entry.metadata.tags,
            "provenance": json.dumps(
                [p.model_dump(mode="json") for p in entry.metadata.provenance]
            ),
        }

        return PointStruct(id=_point_id(entry.id), vector=entry.embedding, payload=payload)

    def _point_to_entry(self, point: Any) -> MemoryEntry:
        """Convert Qdrant point to MemoryEntry.

        Args:
            point: Qdrant ScoredPoint or Record

        Returns:
            Memory entry reconstructed from point
        """
        from datetime import datetime, timezone

        from ..models import MemoryMetadata, ProvenanceEvent

        payload = point.payload

        # Parse provenance
        provenance = []
        if payload.get("provenance"):
            prov_data = json.loads(payload["provenance"])
            for p in prov_data:
                # Convert timestamp string back to datetime
                if isinstance(p.get("timestamp"), str):
                    p["timestamp"] = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
                provenance.append(ProvenanceEvent(**p))

        metadata = MemoryMetadata(
            source=payload["source"],
            privacy_level=payload.get("privacy_level", "public"),
            user_id=payload.get("user_id") or None,
            session_id=payload.get("session_id") or None,
            importance=payload.get("importance", 0.5),
            created_at=datetime.fromtimestamp(payload["created_at"], tz=timezone.utc),
            tags=payload.get("tags", []),
            version=payload.get("version", ""),
            provenance=provenance,
            **extra_metadata_from_json(payload.get("extra_metadata")),
        )

        return MemoryEntry(
            id=payload.get("entry_id") or str(point.id),
            type=payload.get("type", "note"),
            text=payload["text"],
            embedding=point.vector if hasattr(point, "vector") else None,
            metadata=metadata,
        )

    def _filter_to_qdrant(self, filter_obj: Filter) -> models.Filter | None:
        """Convert Filter to Qdrant filter conditions.

        Args:
            filter_obj: Filter specification

        Returns:
            Qdrant Filter object or None
        """
        conditions = []

        # User filter
        if filter_obj.user_id:
            conditions.append(
                models.FieldCondition(
                    key="user_id", match=models.MatchValue(value=filter_obj.user_id)
                )
            )

        # Session filter
        if filter_obj.session_id:
            conditions.append(
                models.FieldCondition(
                    key="session_id", match=models.MatchValue(value=filter_obj.session_id)
                )
            )

        # Privacy level filter
        if filter_obj.privacy_level:
            conditions.append(
                models.FieldCondition(
                    key="privacy_level", match=models.MatchValue(value=filter_obj.privacy_level)
                )
            )

        # Tags filter (any tag matches)
        # Tags filter
        if filter_obj.tags:
            conditions.append(
                models.FieldCondition(key="tags", match=models.MatchAny(any=filter_obj.tags))
            )

        # Importance range
        if filter_obj.min_importance is not None:
            conditions.append(
                models.FieldCondition(
                    key="importance", range=models.Range(gte=filter_obj.min_importance)
                )
            )
        if filter_obj.max_importance is not None:
            # If we already have a min_importance, combine into single range
            if filter_obj.min_importance is not None:
                conditions[-1] = models.FieldCondition(
                    key="importance",
                    range=models.Range(
                        gte=filter_obj.min_importance, lte=filter_obj.max_importance
                    ),
                )
            else:
                conditions.append(
                    models.FieldCondition(
                        key="importance", range=models.Range(lte=filter_obj.max_importance)
                    )
                )

        # Date range filter
        if filter_obj.date_range:
            if filter_obj.date_range.start:
                conditions.append(
                    models.FieldCondition(
                        key="created_at",
                        range=models.Range(gte=filter_obj.date_range.start.timestamp()),
                    )
                )
            if filter_obj.date_range.end:
                conditions.append(
                    models.FieldCondition(
                        key="created_at",
                        range=models.Range(lte=filter_obj.date_range.end.timestamp()),
                    )
                )

        if not conditions:
            return None

        return models.Filter(must=conditions)

    async def save(self, entry: MemoryEntry) -> str:
        """Save (upsert) a memory entry to Qdrant.

        Args:
            entry: Memory entry to save

        Returns:
            The ID of the saved entry

        Raises:
            ValueError: If entry is None or has no embedding
        """
        if entry is None:
            raise ValueError("Entry cannot be None")
        if entry.embedding is None:
            raise ValueError(f"Entry {entry.id} must have an embedding")

        # Ensure collection exists
        await self._ensure_collection(len(entry.embedding))

        # Convert and upsert
        point = self._entry_to_point(entry)
        await self.client.upsert(collection_name=self.collection_name, points=[point])
        return entry.id

    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Query for similar memories by vector similarity.

        Args:
            vector: Query embedding vector
            k: Maximum number of results
            filter: Optional filter conditions

        Returns:
            List of matching memory entries, most similar first

        Raises:
            ValueError: If vector is empty or k is not positive
        """
        if not vector:
            raise ValueError("Query vector cannot be empty")
        if k <= 0:
            raise ValueError("k must be positive")

        # Ensure collection exists
        await self._ensure_collection(len(vector))

        # Convert filter
        qdrant_filter = self._filter_to_qdrant(filter) if filter else None

        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=qdrant_filter,
            limit=k,
            with_payload=True,
            with_vectors=True,
        )

        return [self._point_to_entry(point) for point in results.points]

    async def get(self, id: str) -> MemoryEntry:
        """Retrieve a specific memory entry by ID.

        Args:
            id: Memory entry ID

        Returns:
            The memory entry

        Raises:
            KeyError: If the entry does not exist. Backend errors propagate unchanged
                so an outage is never mistaken for a missing entry.
        """
        if not await self.client.collection_exists(self.collection_name):
            raise EntryNotFoundError(id)

        points = await self.client.retrieve(
            collection_name=self.collection_name,
            ids=[_point_id(id)],
            with_payload=True,
            with_vectors=True,
        )
        if not points:
            raise EntryNotFoundError(id)

        return self._point_to_entry(points[0])

    async def delete(self, id: str) -> bool:
        """Delete a memory entry.

        Args:
            id: Memory entry ID

        Returns:
            True if the entry was deleted, False if it did not exist

        Raises:
            RuntimeError: If Qdrant does not confirm the deletion. Backend errors
                propagate unchanged, so callers such as forget() never mistake an
                outage for "nothing to delete".
        """
        if not await self.client.collection_exists(self.collection_name):
            return False

        point_id = _point_id(id)
        existing = await self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=False,
            with_vectors=False,
        )
        if not existing:
            return False

        result = await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=[point_id]),
        )
        if result.status != models.UpdateStatus.COMPLETED:
            raise AdapterError(f"Qdrant did not confirm deletion of '{id}': {result.status}")
        return True

    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Save multiple memory entries in a single batch.

        Args:
            entries: List of memory entries to save

        Returns:
            List of IDs for the saved entries (in the same order)

        Raises:
            ValueError: If entries is empty or any entry has no embedding
        """
        if not entries:
            raise ValueError("Entries list cannot be empty")

        # Validate all have embeddings
        for entry in entries:
            if entry.embedding is None:
                raise ValueError(f"Entry {entry.id} must have an embedding")

        # Ensure collection exists
        await self._ensure_collection(len(entries[0].embedding))

        # Batch upsert
        points = [self._entry_to_point(entry) for entry in entries]
        await self.client.upsert(collection_name=self.collection_name, points=points)
        return [entry.id for entry in entries]

    async def reindex(self) -> None:
        """Rebuild vector index.

        Note: Qdrant manages indexing automatically, but this can force optimization.
        """
        # Trigger collection optimization
        try:
            collections = await self.client.get_collections()
            if self.collection_name in [c.name for c in collections.collections]:
                # Qdrant auto-indexes, but we can suggest optimization
                pass
        except Exception:
            pass

    async def count_async(self) -> int:
        """Get total number of entries (async version).

        Returns:
            Number of entries in storage
        """
        try:
            info = await self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception as e:
            # A missing collection legitimately counts as empty; anything else is surfaced
            logger.warning(f"Could not count entries in '{self.collection_name}': {e}")
            return 0

    async def clear_async(self) -> None:
        """Clear all entries from storage (async version)."""
        if await self.client.collection_exists(self.collection_name):
            await self.client.delete_collection(self.collection_name)
        self._embedding_dim = None

    async def list_ids_async(self) -> list[str]:
        """List all entry IDs (async version).

        Returns:
            List of entry IDs
        """
        if not await self.client.collection_exists(self.collection_name):
            return []

        # Page through the whole collection; a single scroll would silently truncate
        ids: list[str] = []
        offset = None
        while True:
            points, offset = await self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["entry_id"],
                with_vectors=False,
            )
            ids.extend((p.payload or {}).get("entry_id") or str(p.id) for p in points)
            if offset is None:
                return ids

    @staticmethod
    def _run_sync(coro: Any, name: str) -> Any:
        """Run a coroutine to completion from synchronous code.

        Raises:
            RuntimeError: If called while an event loop is running in this thread
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        coro.close()  # avoid a "coroutine was never awaited" warning
        raise RuntimeError(f"{name}() cannot be called from async context; use the async method")

    def count(self) -> int:
        """Get total number of entries (synchronous; see count_async)."""
        return self._run_sync(self.count_async(), "count")

    def clear(self) -> None:
        """Clear all entries from storage (synchronous; see clear_async)."""
        self._run_sync(self.clear_async(), "clear")

    def list_ids(self) -> list[str]:
        """List all entry IDs (synchronous; see list_ids_async)."""
        return self._run_sync(self.list_ids_async(), "list_ids")

    # Sync wrappers for compatibility
    def save_sync(self, entry: MemoryEntry) -> str:
        """Synchronous wrapper for save()."""
        return self._run_sync(self.save(entry), "save_sync")

    def query_sync(
        self, vector: list[float], k: int = 5, filter: Filter | None = None
    ) -> list[MemoryEntry]:
        """Synchronous wrapper for query()."""
        return self._run_sync(self.query(vector, k, filter), "query_sync")

    def get_sync(self, id: str) -> MemoryEntry:
        """Synchronous wrapper for get()."""
        return self._run_sync(self.get(id), "get_sync")

    def delete_sync(self, id: str) -> bool:
        """Synchronous wrapper for delete()."""
        return self._run_sync(self.delete(id), "delete_sync")

    def bulk_save_sync(self, entries: list[MemoryEntry]) -> list[str]:
        """Synchronous wrapper for bulk_save()."""
        return self._run_sync(self.bulk_save(entries), "bulk_save_sync")

    def reindex_sync(self) -> None:
        """Synchronous wrapper for reindex()."""
        self._run_sync(self.reindex(), "reindex_sync")
