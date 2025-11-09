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

from typing import TYPE_CHECKING

from .adapters import InMemoryAdapter, StorageAdapter
from .core.memory_system import MemorySystem
from .embedders import (
    Embedder,
    EmbeddingCache,
    clear_global_cache,
    get_global_cache,
)

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    from .embedders import (
        HuggingFaceEmbedder,
        OpenAIEmbedder,
        SentenceTransformerEmbedder,
        VoyageAIEmbedder,
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

from .core.logging_config import (
    get_logger,
    setup_structured_logging,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    log_performance,
)

from .core.compaction_strategies import (
    CompactionStrategy,
    SemanticCompactionStrategy,
    ImportanceCompactionStrategy,
    TimeBasedCompactionStrategy,
    HybridCompactionStrategy,
    CountCompactionStrategy,
    get_strategy,
)


def __getattr__(name: str):
    """Lazy load heavy embedders to improve import time."""
    if name == "OpenAIEmbedder":
        from .embedders import OpenAIEmbedder

        return OpenAIEmbedder
    elif name == "VoyageAIEmbedder":
        from .embedders import VoyageAIEmbedder

        return VoyageAIEmbedder
    elif name == "HuggingFaceEmbedder":
        from .embedders import HuggingFaceEmbedder

        return HuggingFaceEmbedder
    elif name == "SentenceTransformerEmbedder":
        from .embedders import SentenceTransformerEmbedder

        return SentenceTransformerEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "MemorySystem",
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
    # Logging
    "get_logger",
    "setup_structured_logging",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "log_performance",
    # Compaction Strategies
    "CompactionStrategy",
    "SemanticCompactionStrategy",
    "ImportanceCompactionStrategy",
    "TimeBasedCompactionStrategy",
    "HybridCompactionStrategy",
    "CountCompactionStrategy",
    "get_strategy",
]
