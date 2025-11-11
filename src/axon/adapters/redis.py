"""Redis-based cache adapter for ephemeral and session memory tiers.

This adapter uses Redis for fast in-memory storage with automatic TTL-based
expiration. Ideal for session-scoped and ephemeral memory tiers where data
needs fast access but doesn't require vector similarity search.

Features:
- Fast in-memory operations (< 1ms latency)
- TTL-based automatic expiration
- Namespace isolation for multi-tenancy
- Connection pooling for performance
- Async + sync operations
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from .base import StorageAdapter

if TYPE_CHECKING:
    from ..models import Filter, MemoryEntry


class RedisAdapter(StorageAdapter):
    """Redis-based storage adapter with TTL support for ephemeral/session tiers.

    This adapter stores memory entries in Redis for fast access and automatic
    cleanup via TTL (time-to-live). Perfect for session-scoped data that needs
    quick retrieval but doesn't need vector similarity search.

    Args:
        host: Redis server hostname (default: localhost)
        port: Redis server port (default: 6379)
        db: Redis database number (default: 0)
        password: Optional Redis password
        namespace: Namespace prefix for keys (default: axon)
        default_ttl: Default TTL in seconds (None = no expiration)
        max_connections: Maximum connections in pool (default: 10)
        decode_responses: Decode Redis responses to strings (default: True)

    Example:
        >>> adapter = RedisAdapter(namespace="session_user123", default_ttl=3600)
        >>> await adapter.save(memory_entry)
        >>> results = await adapter.query(embedding, limit=10)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        namespace: str = "axon",
        default_ttl: int | None = None,
        max_connections: int = 10,
        decode_responses: bool = True,
        **kwargs,
    ):
        """Initialize Redis adapter with connection pool."""
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.namespace = namespace
        self.default_ttl = default_ttl

        # Create connection pool for async operations
        self.pool = aioredis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            decode_responses=decode_responses,
        )

        # Create Redis client
        self.redis = aioredis.Redis(connection_pool=self.pool)

    def _get_key(self, entry_id: str) -> str:
        """Generate namespaced Redis key for an entry.

        Args:
            entry_id: The memory entry ID

        Returns:
            Namespaced key: {namespace}:memory:{id}
        """
        return f"{self.namespace}:memory:{entry_id}"

    def _get_meta_key(self, entry_id: str) -> str:
        """Generate namespaced Redis key for entry metadata.

        Args:
            entry_id: The memory entry ID

        Returns:
            Namespaced metadata key: {namespace}:meta:{id}
        """
        return f"{self.namespace}:meta:{entry_id}"

    def _entry_to_redis(self, entry: MemoryEntry) -> dict[str, str]:
        """Convert MemoryEntry to Redis hash format.

        Args:
            entry: The memory entry to convert

        Returns:
            Dictionary suitable for Redis HSET
        """

        # Serialize complex fields to JSON
        data = {
            "id": entry.id,
            "text": entry.text,
            "embedding": json.dumps(entry.embedding) if entry.embedding else "",
            "created_at": (
                entry.metadata.created_at.isoformat() if entry.metadata.created_at else ""
            ),
            "user_id": entry.metadata.user_id or "",
            "session_id": entry.metadata.session_id or "",
            "source": entry.metadata.source,
            "privacy_level": entry.metadata.privacy_level,
            "importance": (
                str(entry.metadata.importance) if entry.metadata.importance is not None else ""
            ),
            "tags": json.dumps(entry.metadata.tags) if entry.metadata.tags else "[]",
        }

        # Add optional fields if present
        if entry.metadata.last_accessed_at:
            data["last_accessed_at"] = entry.metadata.last_accessed_at.isoformat()
        if entry.metadata.version:
            data["version"] = entry.metadata.version
        if entry.metadata.provenance:
            # Serialize provenance to JSON
            data["provenance"] = json.dumps(
                [
                    {
                        "action": p.action,
                        "by": p.by,
                        "timestamp": p.timestamp.isoformat(),
                        "metadata": p.metadata,
                    }
                    for p in entry.metadata.provenance
                ]
            )

        return data

    def _redis_to_entry(self, data: dict[str, str]) -> MemoryEntry:
        """Convert Redis hash to MemoryEntry.

        Args:
            data: Dictionary from Redis HGETALL

        Returns:
            Reconstructed MemoryEntry
        """
        from ..models import MemoryEntry, MemoryMetadata, ProvenanceEvent

        # Parse JSON fields
        embedding = json.loads(data["embedding"]) if data.get("embedding") else None
        tags = json.loads(data.get("tags", "[]"))

        # Parse provenance if present
        provenance = []
        if data.get("provenance"):
            provenance_data = json.loads(data["provenance"])
            provenance = [
                ProvenanceEvent(
                    action=p["action"],
                    by=p["by"],
                    timestamp=datetime.fromisoformat(p["timestamp"]),
                    metadata=p.get("metadata"),
                )
                for p in provenance_data
            ]

        # Reconstruct metadata
        metadata = MemoryMetadata(
            user_id=data.get("user_id") or None,
            session_id=data.get("session_id") or None,
            source=data.get("source", "app"),
            privacy_level=data.get("privacy_level", "public"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(timezone.utc)
            ),
            last_accessed_at=(
                datetime.fromisoformat(data["last_accessed_at"])
                if data.get("last_accessed_at")
                else None
            ),
            tags=tags,
            importance=float(data["importance"]) if data.get("importance") else 0.5,
            version=data.get("version", ""),
            provenance=provenance,
        )

        return MemoryEntry(
            id=data["id"],
            text=data["text"],
            embedding=embedding,
            metadata=metadata,
        )

    async def save(self, entry: MemoryEntry, ttl: int | None = None) -> str:
        """Save a memory entry to Redis with optional TTL.

        Args:
            entry: The memory entry to save
            ttl: Time-to-live in seconds (overrides default_ttl)

        Returns:
            The ID of the saved entry

        Raises:
            ValueError: If entry is invalid
        """
        if not entry.id:
            raise ValueError("Entry must have an ID")

        key = self._get_key(entry.id)
        data = self._entry_to_redis(entry)

        # Use pipeline for atomic operation
        async with self.redis.pipeline() as pipe:
            # Store entry data
            pipe.hset(key, mapping=data)

            # Set TTL if specified
            effective_ttl = ttl if ttl is not None else self.default_ttl
            if effective_ttl is not None:
                pipe.expire(key, effective_ttl)

            await pipe.execute()

        return entry.id

    async def query(
        self,
        vector: list[float] | None = None,
        k: int = 10,
        filter: Filter | None = None,
    ) -> list[MemoryEntry]:
        """Query entries with optional metadata filtering.

        Note: Redis doesn't support vector similarity search. This method
        scans entries and filters by metadata, then returns up to k results
        sorted by created_at (most recent first).

        Args:
            vector: Query embedding (ignored for Redis, no vector search)
            k: Maximum number of results to return
            filter: Optional metadata filter

        Returns:
            List of matching entries (up to k), sorted by recency
        """
        entries = []

        # Scan for all keys in namespace
        pattern = f"{self.namespace}:memory:*"
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                # Get entry data
                data = await self.redis.hgetall(key)
                if not data:
                    continue

                # Convert to entry
                entry = self._redis_to_entry(data)

                # Apply filter if provided
                if filter:
                    if not self._matches_filter(entry, filter):
                        continue

                entries.append(entry)

            if cursor == 0:
                break

        # Sort by created_at (most recent first)
        entries.sort(key=lambda e: e.metadata.created_at, reverse=True)

        # Apply limit
        return entries[:k]

    def _matches_filter(self, entry: MemoryEntry, filter: Filter) -> bool:
        """Check if entry matches filter criteria.

        Args:
            entry: The memory entry to check
            filter: The filter to apply

        Returns:
            True if entry matches all filter conditions
        """
        # User ID filter
        if filter.user_id and entry.metadata.user_id != filter.user_id:
            return False

        # Session ID filter
        if filter.session_id and entry.metadata.session_id != filter.session_id:
            return False

        # Privacy level filter
        if filter.privacy_level and entry.metadata.privacy_level != filter.privacy_level:
            return False

        # Tags filter (entry must have ALL specified tags)
        if filter.tags:
            entry_tags = set(entry.metadata.tags or [])
            if not all(tag in entry_tags for tag in filter.tags):
                return False

        # Importance range filter
        if filter.min_importance is not None:
            if (
                entry.metadata.importance is None
                or entry.metadata.importance < filter.min_importance
            ):
                return False
        if filter.max_importance is not None:
            if (
                entry.metadata.importance is None
                or entry.metadata.importance > filter.max_importance
            ):
                return False

        # Date range filter
        if filter.date_range:
            if filter.date_range.start and entry.metadata.created_at < filter.date_range.start:
                return False
            if filter.date_range.end and entry.metadata.created_at > filter.date_range.end:
                return False

        # Older than days filter
        if filter.older_than_days is not None:
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(days=filter.older_than_days)
            if entry.metadata.created_at > cutoff:
                return False

        return True

    async def get(self, id: str, refresh_ttl: bool = False) -> MemoryEntry | None:
        """Retrieve a memory entry by ID.

        Args:
            id: Unique identifier of the entry
            refresh_ttl: If True, reset TTL to default_ttl on access

        Returns:
            The memory entry, or None if not found
        """
        key = self._get_key(id)
        data = await self.redis.hgetall(key)

        if not data:
            return None

        # Optionally refresh TTL on access
        if refresh_ttl and self.default_ttl is not None:
            await self.redis.expire(key, self.default_ttl)

        return self._redis_to_entry(data)

    async def delete(self, id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            id: Unique identifier of the entry to delete

        Returns:
            True if entry was deleted, False if not found
        """
        key = self._get_key(id)
        result = await self.redis.delete(key)
        return result > 0

    async def bulk_save(self, entries: list[MemoryEntry], ttl: int | None = None) -> list[str]:
        """Save multiple memory entries efficiently using pipeline.

        Args:
            entries: List of memory entries to save
            ttl: Time-to-live in seconds (overrides default_ttl)

        Returns:
            List of IDs for the saved entries (in same order)

        Raises:
            ValueError: If entries list is empty or contains invalid entries
        """
        if not entries:
            raise ValueError("Entries list cannot be empty")

        effective_ttl = ttl if ttl is not None else self.default_ttl

        # Use pipeline for atomic batch operation
        async with self.redis.pipeline() as pipe:
            for entry in entries:
                if not entry.id:
                    raise ValueError("All entries must have IDs")

                key = self._get_key(entry.id)
                data = self._entry_to_redis(entry)

                pipe.hset(key, mapping=data)

                if effective_ttl is not None:
                    pipe.expire(key, effective_ttl)

            await pipe.execute()

        return [entry.id for entry in entries]

    async def reindex(self) -> None:
        """Rebuild index (no-op for Redis).

        Redis is a key-value store without indexes to rebuild.
        This method exists to satisfy the StorageAdapter interface.
        """
        # No-op for Redis
        pass

    async def count_async(self) -> int:
        """Count total entries in namespace.

        Returns:
            Number of entries in this namespace
        """
        pattern = f"{self.namespace}:memory:*"
        count = 0
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break

        return count

    async def list_ids_async(self) -> list[str]:
        """List all entry IDs in namespace.

        Returns:
            List of all entry IDs
        """
        pattern = f"{self.namespace}:memory:*"
        ids = []
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                # Extract ID from key: {namespace}:memory:{id}
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                id_part = key.split(":")[-1]
                ids.append(id_part)

            if cursor == 0:
                break

        return ids

    async def clear_async(self) -> None:
        """Clear all entries in namespace.

        Warning: This deletes all entries with this namespace prefix.
        """
        pattern = f"{self.namespace}:memory:*"
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            if keys:
                await self.redis.delete(*keys)

            if cursor == 0:
                break

    async def get_ttl(self, id: str) -> int:
        """Get remaining TTL for an entry.

        Args:
            id: Entry ID

        Returns:
            Remaining TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        key = self._get_key(id)
        return await self.redis.ttl(key)

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        await self.redis.aclose()
        await self.pool.aclose()

    # Sync wrappers
    def count_sync(self) -> int:
        """Synchronous wrapper for count_async()."""
        return asyncio.run(self.count_async())

    def list_ids_sync(self) -> list[str]:
        """Synchronous wrapper for list_ids_async()."""
        return asyncio.run(self.list_ids_async())

    def clear_sync(self) -> None:
        """Synchronous wrapper for clear_async()."""
        return asyncio.run(self.clear_async())

    def get_ttl_sync(self, id: str) -> int:
        """Synchronous wrapper for get_ttl()."""
        return asyncio.run(self.get_ttl(id))
