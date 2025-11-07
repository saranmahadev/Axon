"""Pinecone cloud vector database adapter.

This adapter provides integration with Pinecone's cloud-managed vector database,
supporting both serverless and pod-based deployments.

Features:
    - Serverless and pod-based index support
    - Namespace isolation for multi-tenancy
    - Metadata filtering with Pinecone query syntax
    - Async/sync operations
    - Batch operations with automatic chunking
"""

import asyncio
import json
from datetime import datetime, timezone

from pinecone import Pinecone, ServerlessSpec

from ..models import Filter, MemoryEntry
from .base import StorageAdapter


class PineconeAdapter(StorageAdapter):
    """Pinecone cloud vector database adapter.

    Provides persistent vector storage in Pinecone's cloud infrastructure
    with support for serverless auto-scaling and namespace-based isolation.

    Examples:
        >>> # Serverless index (recommended)
        >>> adapter = PineconeAdapter(
        ...     api_key="your-api-key",
        ...     index_name="memories",
        ...     cloud="aws",
        ...     region="us-east-1"
        ... )

        >>> # With namespace for multi-tenancy
        >>> adapter = PineconeAdapter(
        ...     api_key="your-api-key",
        ...     index_name="memories",
        ...     namespace="user_123"
        ... )
    """

    def __init__(
        self,
        api_key: str,
        index_name: str = "axon-memories",
        namespace: str = "",
        cloud: str = "aws",
        region: str = "us-east-1",
        metric: str = "cosine",
    ):
        """Initialize Pinecone adapter.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            namespace: Namespace for vector isolation (default: "" for default namespace)
            cloud: Cloud provider for serverless (aws, gcp, azure)
            region: Cloud region for serverless
            metric: Distance metric (cosine, euclidean, dotproduct)
        """
        self.api_key = api_key
        self.index_name = index_name
        self.namespace = namespace
        self.cloud = cloud
        self.region = region
        self.metric = metric

        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        self.index = None
        self._dimension = None

    async def _ensure_index(self, dimension: int) -> None:
        """Ensure index exists and is ready.

        Creates a serverless index if it doesn't exist and waits for it to be ready.

        Args:
            dimension: Vector dimension for the index
        """
        if self._dimension is not None and self._dimension != dimension:
            raise ValueError(f"Dimension mismatch: index has {self._dimension}, got {dimension}")

        self._dimension = dimension

        # Check if index exists
        existing_indexes = self.pc.list_indexes().names()

        if self.index_name not in existing_indexes:
            # Create serverless index
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=self.metric,
                spec=ServerlessSpec(cloud=self.cloud, region=self.region),
            )

            # Wait for index to be ready (can take 30-60 seconds)
            max_wait = 120  # 2 minutes
            waited = 0
            while waited < max_wait:
                try:
                    desc = self.pc.describe_index(self.index_name)
                    if desc.status.get("ready", False):
                        break
                except Exception:
                    pass

                await asyncio.sleep(5)
                waited += 5

            if waited >= max_wait:
                raise TimeoutError(f"Index {self.index_name} not ready after {max_wait}s")

        # Get index connection
        self.index = self.pc.Index(self.index_name)

    def _entry_to_vector(self, entry: MemoryEntry) -> dict:
        """Convert MemoryEntry to Pinecone vector format.

        Args:
            entry: Memory entry to convert

        Returns:
            Dict with id, values, and metadata for Pinecone
        """
        # Build metadata (all values must be strings, numbers, booleans, or lists)
        metadata = {
            "text": entry.text,
            "source": entry.metadata.source,
            "privacy_level": entry.metadata.privacy_level,
            "user_id": entry.metadata.user_id or "",
            "session_id": entry.metadata.session_id or "",
            "importance": float(entry.metadata.importance),
            "created_at": entry.metadata.created_at.timestamp(),
            "tags": entry.metadata.tags,
            "provenance": json.dumps(
                [p.model_dump(mode="json") for p in entry.metadata.provenance]
            ),
        }

        return {"id": entry.id, "values": entry.embedding, "metadata": metadata}

    def _vector_to_entry(self, vector) -> MemoryEntry:
        """Convert Pinecone vector to MemoryEntry.

        Args:
            vector: Pinecone vector object or dict with id, values, metadata

        Returns:
            Reconstructed memory entry
        """
        from ..models import MemoryMetadata, ProvenanceEvent

        # Handle both Vector object and dict
        if hasattr(vector, "to_dict"):
            # Convert Vector object to dict
            vector_dict = vector.to_dict()
            vector_id = vector_dict["id"]
            vector_values = vector_dict.get("values")
            metadata_dict = vector_dict.get("metadata", {})
        elif hasattr(vector, "id"):
            # Access Vector object attributes directly
            vector_id = vector.id
            vector_values = vector.values
            metadata_dict = vector.metadata or {}
        else:
            # Plain dict
            vector_id = vector["id"]
            vector_values = vector.get("values")
            metadata_dict = vector.get("metadata", {})

        # Parse provenance
        provenance = []
        if metadata_dict.get("provenance"):
            prov_data = json.loads(metadata_dict["provenance"])
            provenance = [
                ProvenanceEvent(
                    action=p["action"],
                    by=p["by"],
                    timestamp=datetime.fromisoformat(p["timestamp"]),
                    metadata=p.get("metadata", {}),
                )
                for p in prov_data
            ]

        metadata = MemoryMetadata(
            source=metadata_dict["source"],
            privacy_level=metadata_dict.get("privacy_level", "public"),
            user_id=metadata_dict.get("user_id") or None,
            session_id=metadata_dict.get("session_id") or None,
            importance=metadata_dict.get("importance", 0.5),
            created_at=datetime.fromtimestamp(metadata_dict["created_at"], tz=timezone.utc),
            tags=metadata_dict.get("tags", []),
            provenance=provenance,
        )

        return MemoryEntry(
            id=vector_id, text=metadata_dict["text"], embedding=vector_values, metadata=metadata
        )

    def _filter_to_pinecone(self, filter_obj: Filter) -> dict | None:
        """Convert Filter to Pinecone metadata filter.

        Args:
            filter_obj: Filter specification

        Returns:
            Pinecone filter dict or None
        """
        conditions = []

        # User filter
        if filter_obj.user_id:
            conditions.append({"user_id": {"$eq": filter_obj.user_id}})

        # Session filter
        if filter_obj.session_id:
            conditions.append({"session_id": {"$eq": filter_obj.session_id}})

        # Privacy filter
        if filter_obj.privacy_level:
            conditions.append({"privacy_level": {"$eq": filter_obj.privacy_level}})

        # Tags filter (any match)
        if filter_obj.tags:
            conditions.append({"tags": {"$in": filter_obj.tags}})

        # Importance range
        if filter_obj.min_importance is not None:
            conditions.append({"importance": {"$gte": filter_obj.min_importance}})

        # Date range filter (convert to Unix timestamps)
        if filter_obj.date_range:
            if filter_obj.date_range.start:
                conditions.append({"created_at": {"$gte": filter_obj.date_range.start.timestamp()}})
            if filter_obj.date_range.end:
                conditions.append({"created_at": {"$lte": filter_obj.date_range.end.timestamp()}})

        if not conditions:
            return None

        # Combine with $and if multiple conditions
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    async def save(self, entry: MemoryEntry) -> None:
        """Save a memory entry to Pinecone.

        Args:
            entry: Memory entry to save

        Raises:
            ValueError: If entry has no embedding
        """
        if entry.embedding is None:
            raise ValueError(f"Entry {entry.id} must have an embedding")

        # Ensure index exists
        await self._ensure_index(len(entry.embedding))

        # Convert to Pinecone format
        vector = self._entry_to_vector(entry)

        # Upsert (insert or update)
        self.index.upsert(vectors=[vector], namespace=self.namespace)

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
        # Ensure index exists
        await self._ensure_index(len(embedding))

        # Convert filter
        pinecone_filter = self._filter_to_pinecone(filter) if filter else None

        # Query with metadata filtering
        results = self.index.query(
            vector=embedding,
            top_k=limit,
            filter=pinecone_filter,
            namespace=self.namespace,
            include_metadata=True,
            include_values=True,
        )

        # Convert results
        entries = []
        # Handle both dict and QueryResponse object
        matches = (
            results.get("matches", [])
            if isinstance(results, dict)
            else (results.matches if hasattr(results, "matches") else [])
        )
        for match in matches:
            # Match objects have id, values, metadata attributes
            entries.append(self._vector_to_entry(match))

        return entries

    async def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID.

        Args:
            entry_id: Memory entry ID

        Returns:
            Memory entry if found, None otherwise
        """
        if self.index is None:
            return None

        try:
            result = self.index.fetch(ids=[entry_id], namespace=self.namespace)

            # Pinecone returns a FetchResponse object with a .vectors dict attribute
            if hasattr(result, "vectors") and entry_id in result.vectors:
                vector_data = result.vectors[entry_id]
                return self._vector_to_entry(vector_data)

            return None
        except Exception:
            # Return None on any fetch error
            return None

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: Memory entry ID

        Returns:
            True if deleted, False if not found
        """
        if self.index is None:
            return False

        try:
            # Check if exists first
            existing = await self.get(entry_id)
            if not existing:
                return False

            # Delete
            self.index.delete(ids=[entry_id], namespace=self.namespace)
            return True
        except Exception:
            return False

    async def bulk_save(self, entries: list[MemoryEntry]) -> None:
        """Save multiple memory entries in batches.

        Pinecone has a limit of 100 vectors per upsert, so we chunk the data.

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

        # Ensure index exists
        await self._ensure_index(len(entries[0].embedding))

        # Convert all entries
        vectors = [self._entry_to_vector(entry) for entry in entries]

        # Upsert in chunks of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.namespace)

    async def count_async(self) -> int:
        """Get total number of vectors in the namespace.

        Returns:
            Number of vectors
        """
        if self.index is None:
            return 0

        try:
            stats = self.index.describe_index_stats()

            # Get count for specific namespace
            if self.namespace:
                namespaces = stats.get("namespaces", {})
                ns_stats = namespaces.get(self.namespace, {})
                return ns_stats.get("vector_count", 0)
            else:
                # Default namespace
                return stats.get("total_vector_count", 0)
        except Exception:
            return 0

    async def list_ids_async(self, limit: int = 100) -> list[str]:
        """List vector IDs in the namespace.

        Note: Pinecone doesn't have a direct list API, so we use a dummy query.
        This is a workaround and may not return all IDs for large namespaces.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of vector IDs
        """
        if self.index is None or self._dimension is None:
            return []

        try:
            # Query with a dummy vector to get IDs
            dummy_vector = [0.0] * self._dimension
            results = self.index.query(
                vector=dummy_vector,
                top_k=limit,
                namespace=self.namespace,
                include_metadata=False,
                include_values=False,
            )

            return [match["id"] for match in results.get("matches", [])]
        except Exception:
            return []

    async def clear_async(self) -> None:
        """Delete all vectors in the namespace."""
        if self.index is None:
            return

        self.index.delete(delete_all=True, namespace=self.namespace)

    async def reindex(self, entries: list[MemoryEntry]) -> None:
        """Clear and rebuild the index with new entries.

        Args:
            entries: New entries to populate index with
        """
        await self.clear_async()
        await self.bulk_save(entries)

    # Sync wrapper methods
    def save_sync(self, entry: MemoryEntry) -> None:
        """Synchronous wrapper for save()."""
        try:
            asyncio.get_running_loop()
            # Already in async context
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop, safe to use asyncio.run()
                asyncio.run(self.save(entry))
            else:
                raise

    def query_sync(
        self, embedding: list[float], filter: Filter | None = None, limit: int = 10
    ) -> list[MemoryEntry]:
        """Synchronous wrapper for query()."""
        try:
            asyncio.get_running_loop()
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                return asyncio.run(self.query(embedding, filter, limit))
            else:
                raise

    def get_sync(self, entry_id: str) -> MemoryEntry | None:
        """Synchronous wrapper for get()."""
        try:
            asyncio.get_running_loop()
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                return asyncio.run(self.get(entry_id))
            else:
                raise

    def delete_sync(self, entry_id: str) -> bool:
        """Synchronous wrapper for delete()."""
        try:
            asyncio.get_running_loop()
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                return asyncio.run(self.delete(entry_id))
            else:
                raise

    def bulk_save_sync(self, entries: list[MemoryEntry]) -> None:
        """Synchronous wrapper for bulk_save()."""
        try:
            asyncio.get_running_loop()
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                asyncio.run(self.bulk_save(entries))
            else:
                raise

    def reindex_sync(self, entries: list[MemoryEntry]) -> None:
        """Synchronous wrapper for reindex()."""
        try:
            asyncio.get_running_loop()
            raise RuntimeError("Cannot call sync method from async context")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                asyncio.run(self.reindex(entries))
            else:
                raise
