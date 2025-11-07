"""Text embedding generation for semantic search.

This module provides abstract base class and implementations for converting
text into dense vector embeddings using various providers (OpenAI, Voyage AI,
local models, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Abstract base class for text embedding generation.

    All embedding providers must implement this interface to provide
    consistent embedding operations across different backends (APIs or local models).

    Methods:
        embed: Generate embedding for a single text
        embed_batch: Generate embeddings for multiple texts efficiently
        get_dimension: Return the embedding dimension
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        Implementations should optimize batch processing where possible
        (e.g., single API call for multiple texts).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            ValueError: If texts list is empty or contains invalid entries
            RuntimeError: If embedding generation fails
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimension of embeddings produced by this embedder.

        Returns:
            Integer dimension (e.g., 384, 768, 1536, 3072)
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name/identifier of the embedding model.

        Returns:
            Model name string (e.g., "text-embedding-3-small", "all-MiniLM-L6-v2")
        """
        pass

    # Sync wrappers for convenience
    def embed_sync(self, text: str) -> list[float]:
        """Synchronous wrapper for embed().

        Args:
            text: The text to embed

        Returns:
            Embedding vector as list of floats
        """
        import asyncio

        return asyncio.run(self.embed(text))

    def embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous wrapper for embed_batch().

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        import asyncio

        return asyncio.run(self.embed_batch(texts))
