"""OpenAI embedding provider using official OpenAI API.

Supports all OpenAI embedding models including text-embedding-3-small,
text-embedding-3-large, and ada-002.
"""

from __future__ import annotations

from openai import AsyncOpenAI, OpenAI

from .base import Embedder
from .cache import get_global_cache


class OpenAIEmbedder(Embedder):
    """OpenAI embedding provider.

    Uses OpenAI's official API to generate embeddings. Supports automatic
    caching, retry logic, and multiple model variants.

    Attributes:
        api_key: OpenAI API key
        model: Model name (default: "text-embedding-3-small")
        cache_enabled: Whether to use caching (default: True)
        max_retries: Maximum number of API retries (default: 3)
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> embedder = OpenAIEmbedder(api_key="sk-...")
        >>> embedding = await embedder.embed("Hello world")
        >>> print(len(embedding))  # 1536
    """

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        cache_enabled: bool = True,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """Initialize OpenAI embedder.

        Args:
            api_key: OpenAI API key
            model: Model name (default: "text-embedding-3-small")
            cache_enabled: Enable caching (default: True)
            max_retries: Max API retries (default: 3)
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ValueError: If API key is empty or model is unsupported
        """
        if not api_key:
            raise ValueError("OpenAI API key cannot be empty")

        if model not in self.MODEL_DIMENSIONS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported models: {list(self.MODEL_DIMENSIONS.keys())}"
            )

        self.api_key = api_key
        self._model = model
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize clients
        self._async_client = AsyncOpenAI(
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        self._sync_client = OpenAI(
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )

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
        """Generate embedding for a single text using OpenAI API.

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
            # Call OpenAI API
            response = await self._async_client.embeddings.create(
                model=self._model,
                input=text,
            )
            embedding = response.data[0].embedding

            # Cache result
            if self._cache:
                self._cache.put(text, self._model, embedding)

            return embedding

        except Exception as e:
            raise RuntimeError(f"OpenAI embedding failed: {str(e)}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        Uses OpenAI's batch API endpoint to process multiple texts in
        a single request.

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

                response = await self._async_client.embeddings.create(
                    model=self._model,
                    input=batch_texts,
                )

                # Store results in correct positions
                for (original_idx, text), embedding_data in zip(texts_to_embed, response.data, strict=False):
                    embedding = embedding_data.embedding
                    embeddings[original_idx] = embedding

                    # Cache result
                    if self._cache:
                        self._cache.put(text, self._model, embedding)

            except Exception as e:
                raise RuntimeError(f"OpenAI batch embedding failed: {str(e)}") from e

        # Type assertion (all should be filled now)
        return [e for e in embeddings if e is not None]
