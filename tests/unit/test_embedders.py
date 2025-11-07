"""Unit tests for embedding providers.

Tests for Embedder ABC and all implementations (OpenAI, Voyage AI,
Sentence Transformers, HuggingFace) with mocked API calls.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from axon import (
    EmbeddingCache,
    HuggingFaceEmbedder,
    OpenAIEmbedder,
    SentenceTransformerEmbedder,
    VoyageAIEmbedder,
    clear_global_cache,
)


class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    def test_cache_initialization(self):
        """Test cache creation with custom max size."""
        cache = EmbeddingCache(max_size=100)
        assert cache.max_size == 100
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cache_put_and_get(self):
        """Test storing and retrieving embeddings."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        cache.put("test text", "model-1", embedding)
        result = cache.get("test text", "model-1")

        assert result == embedding
        assert cache._hits == 1
        assert cache._misses == 0

    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        cache = EmbeddingCache()
        result = cache.get("nonexistent", "model-1")

        assert result is None
        assert cache._misses == 1

    def test_cache_different_models(self):
        """Test that same text with different models are cached separately."""
        cache = EmbeddingCache()
        embedding1 = [0.1, 0.2]
        embedding2 = [0.3, 0.4]

        cache.put("same text", "model-1", embedding1)
        cache.put("same text", "model-2", embedding2)

        assert cache.get("same text", "model-1") == embedding1
        assert cache.get("same text", "model-2") == embedding2

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = EmbeddingCache()
        cache.put("text", "model", [0.1, 0.2])
        cache.get("text", "model")  # Hit

        cache.clear()

        assert cache.get("text", "model") is None
        assert cache._hits == 0
        assert cache._misses == 1

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = EmbeddingCache()
        cache.put("text1", "model", [0.1])
        cache.get("text1", "model")  # Hit
        cache.get("text2", "model")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate_percent"] == 50.0
        assert stats["cache_size"] == 1


class TestOpenAIEmbedder:
    """Tests for OpenAIEmbedder."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI API response."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536-dim
        return mock_response

    def test_initialization(self):
        """Test OpenAI embedder initialization."""
        embedder = OpenAIEmbedder(api_key="sk-test123")
        assert embedder.api_key == "sk-test123"
        assert embedder.model_name == "text-embedding-3-small"
        assert embedder.get_dimension() == 1536

    def test_initialization_invalid_api_key(self):
        """Test that empty API key raises error."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            OpenAIEmbedder(api_key="")

    def test_initialization_invalid_model(self):
        """Test that unsupported model raises error."""
        with pytest.raises(ValueError, match="Unsupported model"):
            OpenAIEmbedder(api_key="sk-test", model="invalid-model")

    def test_model_dimensions(self):
        """Test different model dimensions."""
        embedder_small = OpenAIEmbedder(api_key="sk-test", model="text-embedding-3-small")
        embedder_large = OpenAIEmbedder(api_key="sk-test", model="text-embedding-3-large")

        assert embedder_small.get_dimension() == 1536
        assert embedder_large.get_dimension() == 3072

    @pytest.mark.asyncio
    async def test_embed(self, mock_openai_response):
        """Test single text embedding."""
        embedder = OpenAIEmbedder(api_key="sk-test", cache_enabled=False)

        with patch.object(
            embedder._async_client.embeddings,
            "create",
            return_value=mock_openai_response,
        ):
            embedding = await embedder.embed("test text")
            assert len(embedding) == 1536
            assert isinstance(embedding, list)

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        """Test that empty text raises error."""
        embedder = OpenAIEmbedder(api_key="sk-test")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await embedder.embed("")

    @pytest.mark.asyncio
    async def test_embed_with_cache(self, mock_openai_response):
        """Test caching behavior."""
        clear_global_cache()
        embedder = OpenAIEmbedder(api_key="sk-test", cache_enabled=True)

        with patch.object(
            embedder._async_client.embeddings,
            "create",
            return_value=mock_openai_response,
        ) as mock_create:
            # First call - should hit API
            embedding1 = await embedder.embed("test text")
            assert mock_create.call_count == 1

            # Second call - should use cache
            embedding2 = await embedder.embed("test text")
            assert mock_create.call_count == 1  # No additional API call
            assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding."""
        embedder = OpenAIEmbedder(api_key="sk-test", cache_enabled=False)

        # Mock response with multiple embeddings
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536),
        ]

        with patch.object(
            embedder._async_client.embeddings,
            "create",
            return_value=mock_response,
        ):
            embeddings = await embedder.embed_batch(["text1", "text2", "text3"])
            assert len(embeddings) == 3
            assert all(len(e) == 1536 for e in embeddings)

    def test_sync_wrapper(self, mock_openai_response):
        """Test synchronous embed wrapper."""
        embedder = OpenAIEmbedder(api_key="sk-test", cache_enabled=False)

        with patch.object(
            embedder._async_client.embeddings,
            "create",
            return_value=mock_openai_response,
        ):
            embedding = embedder.embed_sync("test text")
            assert len(embedding) == 1536


class TestVoyageAIEmbedder:
    """Tests for VoyageAIEmbedder."""

    @pytest.fixture
    def mock_voyage_response(self):
        """Create mock Voyage AI response."""
        mock_response = Mock()
        mock_response.embeddings = [[0.1, 0.2] * 512]  # 1024-dim
        return mock_response

    def test_initialization(self):
        """Test Voyage AI embedder initialization."""
        embedder = VoyageAIEmbedder(api_key="pa-test123")
        assert embedder.api_key == "pa-test123"
        assert embedder.model_name == "voyage-2"
        assert embedder.get_dimension() == 1024

    def test_initialization_invalid_model(self):
        """Test that unsupported model raises error."""
        with pytest.raises(ValueError, match="Unsupported model"):
            VoyageAIEmbedder(api_key="pa-test", model="invalid-model")

    @pytest.mark.asyncio
    async def test_embed(self, mock_voyage_response):
        """Test single text embedding."""
        embedder = VoyageAIEmbedder(api_key="pa-test", cache_enabled=False)

        with patch.object(embedder._client, "embed", return_value=mock_voyage_response):
            embedding = await embedder.embed("test text")
            assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_voyage_response):
        """Test batch embedding."""
        embedder = VoyageAIEmbedder(api_key="pa-test", cache_enabled=False)

        # Mock multiple embeddings
        mock_voyage_response.embeddings = [[0.1] * 1024, [0.2] * 1024]

        with patch.object(embedder._client, "embed", return_value=mock_voyage_response):
            embeddings = await embedder.embed_batch(["text1", "text2"])
            assert len(embeddings) == 2
            assert all(len(e) == 1024 for e in embeddings)


class TestSentenceTransformerEmbedder:
    """Tests for SentenceTransformerEmbedder."""

    @pytest.fixture
    def mock_st_model(self):
        """Create mock SentenceTransformer model."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1] * 384)
        return mock_model

    def test_initialization(self, mock_st_model):
        """Test Sentence Transformer embedder initialization."""
        with patch(
            "axon.embedders.sentence_transformer.SentenceTransformer", return_value=mock_st_model
        ):
            embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
            assert embedder.model_name == "all-MiniLM-L6-v2"
            assert embedder.get_dimension() == 384

    @pytest.mark.asyncio
    async def test_embed(self, mock_st_model):
        """Test single text embedding."""
        with patch(
            "axon.embedders.sentence_transformer.SentenceTransformer", return_value=mock_st_model
        ):
            embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2", cache_enabled=False)
            embedding = await embedder.embed("test text")
            assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_st_model):
        """Test batch embedding."""
        # Mock batch encoding
        import numpy as np

        mock_embeddings = np.array([[0.1] * 384, [0.2] * 384])
        mock_st_model.encode.return_value = mock_embeddings

        with patch(
            "axon.embedders.sentence_transformer.SentenceTransformer", return_value=mock_st_model
        ):
            embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2", cache_enabled=False)
            embeddings = await embedder.embed_batch(["text1", "text2"])
            assert len(embeddings) == 2
            assert all(len(e) == 384 for e in embeddings)


class TestHuggingFaceEmbedder:
    """Tests for HuggingFaceEmbedder."""

    @pytest.fixture
    def mock_hf_components(self):
        """Create mock HuggingFace components."""
        import torch

        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }

        mock_model = Mock()
        mock_model.config.hidden_size = 768
        mock_output = (torch.randn(1, 3, 768),)  # (batch, seq_len, hidden_size)
        mock_model.return_value = mock_output
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = None

        return mock_tokenizer, mock_model

    def test_initialization(self, mock_hf_components):
        """Test HuggingFace embedder initialization."""
        mock_tokenizer, mock_model = mock_hf_components

        with patch(
            "axon.embedders.huggingface.AutoTokenizer.from_pretrained", return_value=mock_tokenizer
        ):
            with patch(
                "axon.embedders.huggingface.AutoModel.from_pretrained", return_value=mock_model
            ):
                embedder = HuggingFaceEmbedder("BAAI/bge-base-en-v1.5")
                assert embedder.model_name == "BAAI/bge-base-en-v1.5"
                assert embedder.get_dimension() == 768

    @pytest.mark.asyncio
    async def test_embed(self, mock_hf_components):
        """Test single text embedding."""
        mock_tokenizer, mock_model = mock_hf_components

        with patch(
            "axon.embedders.huggingface.AutoTokenizer.from_pretrained", return_value=mock_tokenizer
        ):
            with patch(
                "axon.embedders.huggingface.AutoModel.from_pretrained", return_value=mock_model
            ):
                embedder = HuggingFaceEmbedder("BAAI/bge-base-en-v1.5", cache_enabled=False)
                embedding = await embedder.embed("test text")
                assert len(embedding) == 768
                assert isinstance(embedding, list)


class TestEmbedderInterface:
    """Tests for Embedder ABC interface."""

    def test_cannot_instantiate_abc(self):
        """Test that Embedder ABC cannot be instantiated directly."""
        from axon.embedders.base import Embedder

        with pytest.raises(TypeError):
            Embedder()

    def test_all_embedders_implement_interface(self):
        """Test that all embedders implement required methods."""
        # Just check initialization doesn't raise (implementation details tested above)
        embedders = [
            OpenAIEmbedder(api_key="sk-test"),
            VoyageAIEmbedder(api_key="pa-test"),
        ]

        for embedder in embedders:
            assert hasattr(embedder, "embed")
            assert hasattr(embedder, "embed_batch")
            assert hasattr(embedder, "get_dimension")
            assert hasattr(embedder, "model_name")
            assert hasattr(embedder, "embed_sync")
            assert hasattr(embedder, "embed_batch_sync")
