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

from .base import Embedder
from .cache import EmbeddingCache, clear_global_cache, get_global_cache
from .huggingface import HuggingFaceEmbedder
from .openai import OpenAIEmbedder
from .sentence_transformer import SentenceTransformerEmbedder
from .voyage import VoyageAIEmbedder

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
