"""Embedding providers for text-to-vector conversion.

This module provides a unified interface for generating text embeddings
using various providers (OpenAI, Voyage AI, local models, etc.).

Available Embedders:
- OpenAIEmbedder: OpenAI's API-based embeddings (paid, high quality)
- VoyageAIEmbedder: Voyage AI's specialized embeddings (paid, domain-specific)
- SentenceTransformerEmbedder: Local Sentence Transformers (free, fast)
- HuggingFaceEmbedder: Local HuggingFace models (free, SOTA open-source)

All embedders implement the Embedder ABC interface and support:
- Async/sync APIs
- Automatic caching
- Batch processing
- Consistent error handling
"""

from typing import TYPE_CHECKING

from .base import Embedder
from .cache import EmbeddingCache, clear_global_cache, get_global_cache

# Lazy imports for heavy dependencies (avoid slow startup)
# OpenAI SDK takes ~5s, VoyageAI takes ~3s, HuggingFace takes ~2s
if TYPE_CHECKING:
    from .huggingface import HuggingFaceEmbedder
    from .openai import OpenAIEmbedder
    from .sentence_transformer import SentenceTransformerEmbedder
    from .voyage import VoyageAIEmbedder


def __getattr__(name: str):
    """Lazy load heavy embedder modules to improve import time.

    All embedders have large dependencies that add 5-10 seconds to import time.
    Only load them when actually used.
    """
    if name == "OpenAIEmbedder":
        from .openai import OpenAIEmbedder

        return OpenAIEmbedder
    elif name == "VoyageAIEmbedder":
        from .voyage import VoyageAIEmbedder

        return VoyageAIEmbedder
    elif name == "HuggingFaceEmbedder":
        from .huggingface import HuggingFaceEmbedder

        return HuggingFaceEmbedder
    elif name == "SentenceTransformerEmbedder":
        from .sentence_transformer import SentenceTransformerEmbedder

        return SentenceTransformerEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base class
    "Embedder",
    # Embedder implementations
    "OpenAIEmbedder",
    "VoyageAIEmbedder",
    "SentenceTransformerEmbedder",
    "HuggingFaceEmbedder",
    # Caching
    "EmbeddingCache",
    "get_global_cache",
    "clear_global_cache",
]
