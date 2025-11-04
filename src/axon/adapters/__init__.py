"""Storage adapters for different backend systems.

This module contains adapter implementations for:
- InMemoryAdapter (Sprint 1.2) ✅
- ChromaAdapter (Sprint 2.1) ✅
- QdrantAdapter (Sprint 2.1) 🚧
- RedisAdapter (Sprint 2.2)
- PineconeAdapter (Sprint 5.x)
- SQLAdapter, S3Adapter (Sprint 5.x)
"""

from .base import StorageAdapter
from .chroma import ChromaAdapter
from .memory import InMemoryAdapter
from .qdrant import QdrantAdapter

__all__ = [
    "StorageAdapter",
    "InMemoryAdapter",
    "ChromaAdapter",
    "QdrantAdapter",
]
