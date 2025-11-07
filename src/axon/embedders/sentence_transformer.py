"""Sentence Transformers embedding provider (local, free).

Uses open-source Sentence Transformers library for local embedding
generation without API costs. Models run on CPU or GPU.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from .base import Embedder
from .cache import get_global_cache


class SentenceTransformerEmbedder(Embedder):
    """Sentence Transformers local embedding provider.

    Uses open-source SentenceTransformer models that run locally.
    No API costs, fully offline after initial model download.

    Popular models:
    - all-MiniLM-L6-v2: Fast, 384-dim, ~90MB
    - all-mpnet-base-v2: Better quality, 768-dim, ~420MB
    - paraphrase-multilingual-MiniLM-L12-v2: Multilingual, 384-dim

    Attributes:
        model_name: HuggingFace model identifier
        cache_enabled: Whether to use caching (default: True)
        device: Device to run on ('cpu', 'cuda', or None for auto)

    Example:
        >>> embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
        >>> embedding = await embedder.embed("Hello world")
        >>> print(len(embedding))  # 384
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_enabled: bool = True,
        device: str | None = None,
    ):
        """Initialize Sentence Transformer embedder.

        Args:
            model_name: HuggingFace model identifier (default: "all-MiniLM-L6-v2")
            cache_enabled: Enable caching (default: True)
            device: Device to run on ('cpu', 'cuda', or None for auto)

        Note:
            First initialization downloads the model (~90-500MB depending on model).
            Subsequent uses load from cache.
        """
        self._model_name = model_name
        self.cache_enabled = cache_enabled

        # Load model (downloads on first use)
        self._model = SentenceTransformer(model_name, device=device)

        # Get actual dimension from model
        self._dimension = self._model.get_sentence_embedding_dimension()

        # Get cache if enabled
        self._cache = get_global_cache() if cache_enabled else None

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name

    def get_dimension(self) -> int:
        """Return embedding dimension for this model."""
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text locally.

        Args:
            text: The text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache first
        if self._cache:
            cached = self._cache.get(text, self._model_name)
            if cached is not None:
                return cached

        try:
            # Generate embedding (runs locally)
            embedding = self._model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            # Convert numpy array to list
            embedding_list = embedding.tolist()

            # Cache result
            if self._cache:
                self._cache.put(text, self._model_name, embedding_list)

            return embedding_list

        except Exception as e:
            raise RuntimeError(f"Sentence Transformer embedding failed: {str(e)}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        Processes batch locally using vectorized operations for speed.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding generation fails
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
                cached = self._cache.get(text, self._model_name)
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

                # Batch encode (efficient)
                batch_embeddings = self._model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    batch_size=32,  # Process in batches of 32
                )

                # Store results in correct positions
                for (original_idx, text), embedding in zip(texts_to_embed, batch_embeddings, strict=False):
                    embedding_list = embedding.tolist()
                    embeddings[original_idx] = embedding_list

                    # Cache result
                    if self._cache:
                        self._cache.put(text, self._model_name, embedding_list)

            except Exception as e:
                raise RuntimeError(f"Sentence Transformer batch embedding failed: {str(e)}") from e

        # Type assertion (all should be filled now)
        return [e for e in embeddings if e is not None]
