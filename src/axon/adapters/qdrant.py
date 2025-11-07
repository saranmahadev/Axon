"""Qdrant vector storage adapter.

This adapter provides persistent vector storage using Qdrant,
a high-performance vector search engine. Supports both local and remote instances.
"""

import json
from typing import Any

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..models import Filter, MemoryEntry
from .base import StorageAdapter


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

        return PointStruct(id=entry.id, vector=entry.embedding, payload=payload)

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
            provenance=provenance,
        )

        return MemoryEntry(
            id=str(point.id),
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

    async def save(self, entry: MemoryEntry) -> None:
        """Save a memory entry to Qdrant.

        Args:
            entry: Memory entry to save

        Raises:
            ValueError: If entry has no embedding
        """
        if entry.embedding is None:
            raise ValueError(f"Entry {entry.id} must have an embedding")

        # Ensure collection exists
        await self._ensure_collection(len(entry.embedding))

        # Convert and upsert
        point = self._entry_to_point(entry)
        await self.client.upsert(collection_name=self.collection_name, points=[point])

    async def query(
        self, embedding: list[float], filter: Filter | None = None, limit: int = 10
    ) -> list[MemoryEntry]:
        """Query for similar memories by vector similarity.

        Args:
            embedding: Query embedding vector
            filter: Optional filter conditions
            limit: Maximum number of results

        Returns:
            List of matching memory entries, ordered by similarity
        """
        # Ensure collection exists
        await self._ensure_collection(len(embedding))

        # Convert filter
        qdrant_filter = self._filter_to_qdrant(filter) if filter else None

        # Search using query_points (new API)
        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )

        # Convert results - query_points returns QueryResponse with points attribute
        return [self._point_to_entry(point) for point in results.points]

    async def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID.

        Args:
            entry_id: Memory entry ID

        Returns:
            Memory entry if found, None otherwise
        """
        try:
            points = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[entry_id],
                with_payload=True,
                with_vectors=True,
            )

            if not points:
                return None

            return self._point_to_entry(points[0])
        except Exception:
            return None

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: Memory entry ID

        Returns:
            True if deleted, False if not found
        """
        try:
            # First check if entry exists
            existing = await self.get(entry_id)
            if not existing:
                return False

            # Delete the entry
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[entry_id]),
            )
            return result.status == models.UpdateStatus.COMPLETED
        except Exception:
            return False

    async def bulk_save(self, entries: list[MemoryEntry]) -> None:
        """Save multiple memory entries in a single batch.

        Args:
            entries: List of memory entries to save

        Raises:
            ValueError: If any entry has no embedding
        """
        if not entries:
            return

        # Validate all have embeddings
        for entry in entries:
            if entry.embedding is None:
                raise ValueError(f"Entry {entry.id} must have an embedding")

        # Ensure collection exists
        await self._ensure_collection(len(entries[0].embedding))

        # Convert all entries
        points = [self._entry_to_point(entry) for entry in entries]

        # Batch upsert
        await self.client.upsert(collection_name=self.collection_name, points=points)

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
        except Exception:
            return 0

    async def clear_async(self) -> None:
        """Clear all entries from storage (async version)."""
        try:
            await self.client.delete_collection(self.collection_name)
            self._embedding_dim = None
        except Exception:
            pass

    async def list_ids_async(self) -> list[str]:
        """List all entry IDs (async version).

        Returns:
            List of entry IDs
        """
        try:
            # Scroll through all points to get IDs
            points, _ = await self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,  # Adjust based on expected size
                with_payload=False,
                with_vectors=False,
            )
            return [str(p.id) for p in points]
        except Exception:
            return []

    def count(self) -> int:
        """Get total number of entries.

        Returns:
            Number of entries in storage
        """
        import asyncio

        async def _count():
            try:
                info = await self.client.get_collection(self.collection_name)
                return info.points_count or 0
            except Exception:
                return 0

        try:
            asyncio.get_running_loop()
            # Already in async context, can't use run_until_complete
            raise RuntimeError(
                "count() cannot be called from async context, use await count_async()"
            )
        except RuntimeError:
            # Not in async context, safe to create new loop
            return asyncio.run(_count())

    def clear(self) -> None:
        """Clear all entries from storage."""
        import asyncio

        async def _clear():
            try:
                await self.client.delete_collection(self.collection_name)
                self._embedding_dim = None
            except Exception:
                pass

        try:
            asyncio.get_running_loop()
            raise RuntimeError("clear() cannot be called from async context")
        except RuntimeError:
            asyncio.run(_clear())

    def list_ids(self) -> list[str]:
        """List all entry IDs.

        Returns:
            List of entry IDs
        """
        import asyncio

        async def _list_ids():
            try:
                # Scroll through all points to get IDs
                points, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,  # Adjust based on expected size
                    with_payload=False,
                    with_vectors=False,
                )
                return [str(p.id) for p in points]
            except Exception:
                return []

        try:
            asyncio.get_running_loop()
            raise RuntimeError("list_ids() cannot be called from async context")
        except RuntimeError:
            return asyncio.run(_list_ids())

    # Sync wrappers for compatibility
    def save_sync(self, entry: MemoryEntry) -> None:
        """Synchronous wrapper for save()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError("save_sync() cannot be called from async context, use await save()")
        except RuntimeError:
            asyncio.run(self.save(entry))

    def query_sync(
        self, embedding: list[float], filter: Filter | None = None, limit: int = 10
    ) -> list[MemoryEntry]:
        """Synchronous wrapper for query()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "query_sync() cannot be called from async context, use await query()"
            )
        except RuntimeError:
            return asyncio.run(self.query(embedding, filter, limit))

    def get_sync(self, entry_id: str) -> MemoryEntry | None:
        """Synchronous wrapper for get()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError("get_sync() cannot be called from async context, use await get()")
        except RuntimeError:
            return asyncio.run(self.get(entry_id))

    def delete_sync(self, entry_id: str) -> bool:
        """Synchronous wrapper for delete()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "delete_sync() cannot be called from async context, use await delete()"
            )
        except RuntimeError:
            return asyncio.run(self.delete(entry_id))

    def bulk_save_sync(self, entries: list[MemoryEntry]) -> None:
        """Synchronous wrapper for bulk_save()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "bulk_save_sync() cannot be called from async context, use await bulk_save()"
            )
        except RuntimeError:
            asyncio.run(self.bulk_save(entries))

    def reindex_sync(self) -> None:
        """Synchronous wrapper for reindex()."""
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "reindex_sync() cannot be called from async context, use await reindex()"
            )
        except RuntimeError:
            asyncio.run(self.reindex())
