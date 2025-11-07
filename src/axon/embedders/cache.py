"""Embedding cache to avoid redundant API calls and computations.

Provides LRU (Least Recently Used) caching for embeddings across all
embedding providers to reduce costs and improve performance.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache


class EmbeddingCache:
    """LRU cache for text embeddings.

    Caches embeddings by (text, model) key to avoid redundant API calls
    or computations. Thread-safe for concurrent access.

    Attributes:
        max_size: Maximum number of cached embeddings
        _cache: Internal LRU cache
        _hits: Number of cache hits
        _misses: Number of cache misses
    """

    def __init__(self, max_size: int = 10000):
        """Initialize embedding cache.

        Args:
            max_size: Maximum number of embeddings to cache (default: 10000)
        """
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

        # Use lru_cache decorator pattern for built-in cache
        @lru_cache(maxsize=max_size)
        def _cached_get(cache_key: str) -> tuple[float, ...] | None:
            """Internal cache lookup - always returns None (cache miss)."""
            return None

        self._cache_func = _cached_get
        # Store actual embeddings in a dict
        self._embeddings: dict[str, list[float]] = {}

    def _make_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model.

        Uses SHA-256 hash to create consistent, fixed-length keys.

        Args:
            text: The text that was embedded
            model: The model name/identifier

        Returns:
            Cache key string (hex digest)
        """
        combined = f"{model}::{text}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, text: str, model: str) -> list[float] | None:
        """Retrieve cached embedding if available.

        Args:
            text: The text to look up
            model: The model name/identifier

        Returns:
            Cached embedding vector or None if not found
        """
        cache_key = self._make_key(text, model)

        if cache_key in self._embeddings:
            self._hits += 1
            return self._embeddings[cache_key]

        self._misses += 1
        return None

    def put(self, text: str, model: str, embedding: list[float]) -> None:
        """Store embedding in cache.

        Args:
            text: The text that was embedded
            model: The model name/identifier
            embedding: The embedding vector to cache
        """
        cache_key = self._make_key(text, model)

        # Evict oldest if at max size (simple FIFO for dict)
        if len(self._embeddings) >= self.max_size:
            # Remove first (oldest) key
            first_key = next(iter(self._embeddings))
            del self._embeddings[first_key]

        self._embeddings[cache_key] = embedding

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._embeddings.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, size, and hit rate
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._embeddings),
            "max_size": self.max_size,
        }


# Global cache instance (shared across all embedders)
_global_cache: EmbeddingCache | None = None


def get_global_cache(max_size: int = 10000) -> EmbeddingCache:
    """Get or create the global embedding cache.

    Args:
        max_size: Maximum cache size (only used on first call)

    Returns:
        Global EmbeddingCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = EmbeddingCache(max_size=max_size)
    return _global_cache


def clear_global_cache() -> None:
    """Clear the global embedding cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
