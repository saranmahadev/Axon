"""Storage adapters for different backend systems.

This module contains adapter implementations for:
- InMemoryAdapter (Sprint 1.2) ✅
- ChromaAdapter (Sprint 2.1a) ✅
- QdrantAdapter (Sprint 2.1b) ✅
- PineconeAdapter (Sprint 2.1c) 🚧
- RedisAdapter (Sprint 2.2)
- SQLAdapter, S3Adapter (Sprint 5.x)
"""

from .base import StorageAdapter
from .chroma import ChromaAdapter
from .memory import InMemoryAdapter
from .pinecone import PineconeAdapter
from .qdrant import QdrantAdapter

__all__ = [
    "StorageAdapter",
    "InMemoryAdapter",
    "ChromaAdapter",
    "QdrantAdapter",
    "PineconeAdapter",
]

