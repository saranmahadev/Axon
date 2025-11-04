"""Axon - Unified Memory SDK for LLM Applications.

Axon provides a single programmable API that abstracts multiple memory tiers,
lifecycle policies, summarization/compaction flows, and pluggable storage adapters
for building intelligent LLM applications.

Example:
    >>> from axon import MemorySystem, MemoryEntry, Policy
    >>> 
    >>> mem = MemorySystem(policy=my_policy)
    >>> mem.store(MemoryEntry(text="User prefers sci-fi", metadata={"user_id": "u123"}))
    >>> results = mem.recall("What does the user like?", k=3)

Key Features:
    - Multi-tier memory (Ephemeral / Session / Persistent / Archive)
    - Pluggable backends (in-memory, Redis, vector DBs, object stores)
    - Policy-driven lifecycle and summarization
    - Auditability and explainability
    - Caching & deterministic response support
    - Privacy and encryption hooks
"""

from .adapters import InMemoryAdapter, StorageAdapter
from .embedders import (
    Embedder,
    EmbeddingCache,
    HuggingFaceEmbedder,
    OpenAIEmbedder,
    SentenceTransformerEmbedder,
    VoyageAIEmbedder,
    clear_global_cache,
    get_global_cache,
)
from .models import (
    DateRange,
    Filter,
    MemoryEntry,
    MemoryEntryType,
    MemoryMetadata,
    MemoryTier,
    PrivacyLevel,
    ProvenanceEvent,
    SourceType,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Models
    "MemoryEntry",
    "MemoryMetadata",
    "Filter",
    "DateRange",
    # Enums and types
    "MemoryTier",
    "PrivacyLevel",
    "SourceType",
    "MemoryEntryType",
    "ProvenanceEvent",
    # Adapters
    "StorageAdapter",
    "InMemoryAdapter",
    # Embedders
    "Embedder",
    "OpenAIEmbedder",
    "VoyageAIEmbedder",
    "SentenceTransformerEmbedder",
    "HuggingFaceEmbedder",
    "EmbeddingCache",
    "get_global_cache",
    "clear_global_cache",
]