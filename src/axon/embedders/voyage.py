"""Voyage AI embedding provider using official Voyage AI API.

Supports Voyage AI's specialized embedding models optimized for
specific domains and use cases.
"""

from __future__ import annotations

import voyageai

from .base import Embedder
from .cache import get_global_cache


class VoyageAIEmbedder(Embedder):
    """Voyage AI embedding provider.

    Uses Voyage AI's API to generate domain-specialized embeddings.
    Supports automatic caching and error handling.

    Attributes:
        api_key: Voyage AI API key
        model: Model name (default: "voyage-2")
        cache_enabled: Whether to use caching (default: True)

    Example:
        >>> embedder = VoyageAIEmbedder(api_key="pa-...")
        >>> embedding = await embedder.embed("Hello world")
        >>> print(len(embedding))  # 1024
    """

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "voyage-2": 1024,
        "voyage-large-2": 1536,
        "voyage-code-2": 1536,
        "voyage-lite-02-instruct": 1024,
    }

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-2",
        cache_enabled: bool = True,
    ):
        """Initialize Voyage AI embedder.

        Args:
            api_key: Voyage AI API key
            model: Model name (default: "voyage-2")
            cache_enabled: Enable caching (default: True)

        Raises:
            ValueError: If API key is empty or model is unsupported
        """
        if not api_key:
            raise ValueError("Voyage AI API key cannot be empty")

        if model not in self.MODEL_DIMENSIONS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported models: {list(self.MODEL_DIMENSIONS.keys())}"
            )

        self.api_key = api_key
        self._model = model
        self.cache_enabled = cache_enabled

        # Initialize Voyage AI client
        self._client = voyageai.Client(api_key=api_key)

        # Get cache if enabled
        self._cache = get_global_cache() if cache_enabled else None

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model

    def get_dimension(self) -> int:
        """Return embedding dimension for this model."""
        return self.MODEL_DIMENSIONS[self._model]

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text using Voyage AI API.

        Args:
            text: The text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            RuntimeError: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache first
        if self._cache:
            cached = self._cache.get(text, self._model)
            if cached is not None:
                return cached

        try:
            # Call Voyage AI API (synchronous client)
            # Voyage AI doesn't have async client yet, so we use sync
            result = self._client.embed(
                texts=[text],
                model=self._model,
            )
            embedding = result.embeddings[0]

            # Cache result
            if self._cache:
                self._cache.put(text, self._model, embedding)

            return embedding

        except Exception as e:
            raise RuntimeError(f"Voyage AI embedding failed: {str(e)}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        Uses Voyage AI's batch API endpoint to process multiple texts
        in a single request.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If API call fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        # Check cache for each text
        embeddings: list[list[float] | None] = []
        texts_to_embed: list[tuple[int, str]] = []  # (index, text)

        for i, text in enumerate(valid_texts):
            if self._cache:
                cached = self._cache.get(text, self._model)
                if cached is not None:
                    embeddings.append(cached)
                    continue

            # Need to embed this text
            embeddings.append(None)
            texts_to_embed.append((i, text))

        # Embed uncached texts in batch
        if texts_to_embed:
            try:
                batch_texts = [text for _, text in texts_to_embed]

                result = self._client.embed(
                    texts=batch_texts,
                    model=self._model,
                )

                # Store results in correct positions
                for (original_idx, text), embedding in zip(texts_to_embed, result.embeddings, strict=False):
                    embeddings[original_idx] = embedding

                    # Cache result
                    if self._cache:
                        self._cache.put(text, self._model, embedding)

            except Exception as e:
                raise RuntimeError(f"Voyage AI batch embedding failed: {str(e)}") from e

        # Type assertion (all should be filled now)
        return [e for e in embeddings if e is not None]
