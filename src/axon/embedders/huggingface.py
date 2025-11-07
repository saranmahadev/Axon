"""HuggingFace Transformers embedding provider (local, free).

Uses HuggingFace Transformers library for state-of-the-art open-source
embedding models, particularly BGE (BAAI General Embedding) models.
"""

from __future__ import annotations

import torch
from transformers import AutoModel, AutoTokenizer

from .base import Embedder
from .cache import get_global_cache


class HuggingFaceEmbedder(Embedder):
    """HuggingFace Transformers local embedding provider.

    Uses HuggingFace Transformers for advanced open-source models.
    Particularly good for BGE models which are state-of-the-art free embeddings.

    Popular models:
    - BAAI/bge-small-en-v1.5: Fast, 384-dim, ~130MB
    - BAAI/bge-base-en-v1.5: Best quality, 768-dim, ~440MB
    - BAAI/bge-large-en-v1.5: Maximum quality, 1024-dim, ~1.3GB

    Attributes:
        model_name: HuggingFace model identifier
        cache_enabled: Whether to use caching (default: True)
        device: Device to run on ('cpu', 'cuda', or None for auto)

    Example:
        >>> embedder = HuggingFaceEmbedder("BAAI/bge-base-en-v1.5")
        >>> embedding = await embedder.embed("Hello world")
        >>> print(len(embedding))  # 768
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        cache_enabled: bool = True,
        device: str | None = None,
    ):
        """Initialize HuggingFace embedder.

        Args:
            model_name: HuggingFace model identifier (default: "BAAI/bge-base-en-v1.5")
            cache_enabled: Enable caching (default: True)
            device: Device to run on ('cpu', 'cuda', or None for auto)

        Note:
            First initialization downloads the model (~130MB-1.3GB depending on model).
            Subsequent uses load from cache.
        """
        self._model_name = model_name
        self.cache_enabled = cache_enabled

        # Auto-detect device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        # Load tokenizer and model
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModel.from_pretrained(model_name)
        self._model.to(device)
        self._model.eval()  # Set to evaluation mode

        # Get dimension from model config
        self._dimension = self._model.config.hidden_size

        # Get cache if enabled
        self._cache = get_global_cache() if cache_enabled else None

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name

    def get_dimension(self) -> int:
        """Return embedding dimension for this model."""
        return self._dimension

    def _mean_pooling(
        self,
        model_output: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Apply mean pooling to model output.

        Args:
            model_output: Model's last hidden state
            attention_mask: Attention mask from tokenizer

        Returns:
            Pooled tensor
        """
        token_embeddings = model_output[0]  # First element of model_output
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

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
            # Tokenize
            encoded_input = self._tokenizer(
                text,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}

            # Generate embedding
            with torch.no_grad():
                model_output = self._model(**encoded_input)
                embedding = self._mean_pooling(model_output, encoded_input["attention_mask"])
                # Normalize (important for BGE models)
                embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

            # Convert to list
            embedding_list = embedding[0].cpu().tolist()

            # Cache result
            if self._cache:
                self._cache.put(text, self._model_name, embedding_list)

            return embedding_list

        except Exception as e:
            raise RuntimeError(f"HuggingFace embedding failed: {str(e)}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.

        Processes batch locally using GPU/CPU for speed.

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

                # Tokenize batch
                encoded_input = self._tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                )
                encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}

                # Generate embeddings
                with torch.no_grad():
                    model_output = self._model(**encoded_input)
                    batch_embeddings = self._mean_pooling(
                        model_output, encoded_input["attention_mask"]
                    )
                    # Normalize
                    batch_embeddings = torch.nn.functional.normalize(batch_embeddings, p=2, dim=1)

                # Store results in correct positions
                for (original_idx, text), embedding in zip(texts_to_embed, batch_embeddings, strict=False):
                    embedding_list = embedding.cpu().tolist()
                    embeddings[original_idx] = embedding_list

                    # Cache result
                    if self._cache:
                        self._cache.put(text, self._model_name, embedding_list)

            except Exception as e:
                raise RuntimeError(f"HuggingFace batch embedding failed: {str(e)}") from e

        # Type assertion (all should be filled now)
        return [e for e in embeddings if e is not None]
