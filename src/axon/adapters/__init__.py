"""Storage adapters for different backend systems.

This module contains adapter implementations for:
- InMemoryAdapter (Sprint 1.2) ✅
- ChromaAdapter (Sprint 2.1a) ✅
- QdrantAdapter (Sprint 2.1b) ✅
- PineconeAdapter (Sprint 2.1c) ✅
- RedisAdapter (Sprint 2.2) 🚧
- SQLAdapter, S3Adapter (Sprint 5.x)
"""

from typing import TYPE_CHECKING

from .base import StorageAdapter
from .memory import InMemoryAdapter

# Lazy imports for heavy dependencies (ChromaDB, Qdrant, Pinecone, Redis)
if TYPE_CHECKING:
    from .chroma import ChromaAdapter
    from .pinecone import PineconeAdapter
    from .qdrant import QdrantAdapter
    from .redis import RedisAdapter


def __getattr__(name: str):
    """Lazy load heavy adapter modules to improve import time.

    ChromaDB, Qdrant, Pinecone, and Redis have large dependencies.
    Only load them when actually used.
    """
    if name == "ChromaAdapter":
        from .chroma import ChromaAdapter

        return ChromaAdapter
    elif name == "QdrantAdapter":
        from .qdrant import QdrantAdapter

        return QdrantAdapter
    elif name == "PineconeAdapter":
        from .pinecone import PineconeAdapter

        return PineconeAdapter
    elif name == "RedisAdapter":
        from .redis import RedisAdapter

        return RedisAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "StorageAdapter",
    "InMemoryAdapter",
    "ChromaAdapter",
    "QdrantAdapter",
    "PineconeAdapter",
    "RedisAdapter",
]
