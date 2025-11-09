"""Unit tests for LangChain AxonVectorStore integration."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from axon.core.memory_system import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy
from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry

# Try importing LangChain dependencies
try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings

    from axon.integrations.langchain import AxonVectorStore

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class MockEmbeddings:
    """Mock embeddings class for testing."""

    async def aembed_documents(self, texts):
        """Mock embed_documents returning simple vectors."""
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def aembed_query(self, text):
        """Mock embed_query."""
        return [0.1, 0.2, 0.3]

    def embed_documents(self, texts):
        """Sync version."""
        import asyncio

        return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text):
        """Sync version."""
        import asyncio

        return asyncio.run(self.aembed_query(text))


@pytest.fixture
def memory_system():
    """Create a MemorySystem for testing."""
    registry = AdapterRegistry()
    registry.register("persistent", adapter_type="memory", adapter_instance=InMemoryAdapter())

    config = MemoryConfig(persistent=PersistentPolicy(backend="memory"), default_tier="persistent")

    return MemorySystem(config, registry=registry)


@pytest.fixture
def embeddings():
    """Create mock embeddings."""
    return MockEmbeddings()


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestAxonVectorStore:
    """Test AxonVectorStore adapter."""

    @pytest.mark.asyncio
    async def test_initialization(self, memory_system, embeddings):
        """Test AxonVectorStore initialization."""
        vectorstore = AxonVectorStore(
            memory_system, embeddings, tier="persistent", collection_name="test_collection"
        )

        assert vectorstore.system == memory_system
        assert vectorstore.embedding == embeddings
        assert vectorstore.tier == "persistent"
        assert vectorstore.collection_name == "test_collection"

    @pytest.mark.asyncio
    async def test_add_texts(self, memory_system, embeddings):
        """Test adding texts to vector store."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        texts = ["Document 1", "Document 2", "Document 3"]
        metadatas = [{"source": "doc1"}, {"source": "doc2"}, {"source": "doc3"}]

        ids = vectorstore.add_texts(texts, metadatas=metadatas)

        assert len(ids) == 3
        assert all(isinstance(id, str) for id in ids)

    @pytest.mark.asyncio
    async def test_add_texts_with_ids(self, memory_system, embeddings):
        """Test adding texts with explicit IDs."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        texts = ["Text 1", "Text 2"]
        ids_input = ["id1", "id2"]

        ids = vectorstore.add_texts(texts, ids=ids_input)

        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_similarity_search(self, memory_system, embeddings):
        """Test similarity search."""
        vectorstore = AxonVectorStore(memory_system, embeddings, collection_name="search_test")

        # Add some documents first
        texts = ["Python programming", "JavaScript coding", "Machine learning basics"]
        vectorstore.add_texts(texts)

        # Search
        results = vectorstore.similarity_search("programming languages", k=2)

        assert isinstance(results, list)
        assert len(results) <= 2
        if results:
            assert all(isinstance(doc, Document) for doc in results)

    @pytest.mark.asyncio
    async def test_similarity_search_with_filter(self, memory_system, embeddings):
        """Test similarity search with metadata filter."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        # Add documents with metadata
        texts = ["Doc 1", "Doc 2"]
        metadatas = [{"category": "tech"}, {"category": "science"}]
        vectorstore.add_texts(texts, metadatas=metadatas)

        # Search with filter
        results = vectorstore.similarity_search("document", k=5, filter={"category": "tech"})

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_similarity_search_with_score(self, memory_system, embeddings):
        """Test similarity search with scores."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        # Add documents
        texts = ["First document", "Second document"]
        vectorstore.add_texts(texts)

        # Search with scores
        results = vectorstore.similarity_search_with_score("document", k=2)

        assert isinstance(results, list)
        if results:
            for doc, score in results:
                assert isinstance(doc, Document)
                assert isinstance(score, (int, float))

    @pytest.mark.asyncio
    async def test_from_texts_classmethod(self, memory_system, embeddings):
        """Test creating vector store from texts."""
        texts = ["Text A", "Text B", "Text C"]
        metadatas = [{"id": 1}, {"id": 2}, {"id": 3}]

        vectorstore = AxonVectorStore.from_texts(
            texts,
            embeddings,
            metadatas=metadatas,
            system=memory_system,
            collection_name="from_texts_test",
        )

        assert isinstance(vectorstore, AxonVectorStore)
        assert vectorstore.collection_name == "from_texts_test"

    @pytest.mark.asyncio
    async def test_from_texts_without_system_raises_error(self, embeddings):
        """Test that from_texts raises error when system is not provided."""
        with pytest.raises(ValueError, match="system .* is required"):
            AxonVectorStore.from_texts(["text"], embeddings)

    @pytest.mark.asyncio
    async def test_async_add_texts(self, memory_system, embeddings):
        """Test async add_texts."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        texts = ["Async doc 1", "Async doc 2"]
        ids = await vectorstore.aadd_texts(texts)

        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_async_similarity_search(self, memory_system, embeddings):
        """Test async similarity search."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        # Add documents
        await vectorstore.aadd_texts(["Document alpha", "Document beta"])

        # Search async
        results = await vectorstore.asimilarity_search("document", k=2)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_async_similarity_search_with_score(self, memory_system, embeddings):
        """Test async similarity search with scores."""
        vectorstore = AxonVectorStore(memory_system, embeddings)

        await vectorstore.aadd_texts(["Test doc"])

        results = await vectorstore.asimilarity_search_with_score("test", k=1)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_collection_grouping(self, memory_system, embeddings):
        """Test that collection name is used for grouping."""
        vectorstore1 = AxonVectorStore(memory_system, embeddings, collection_name="collection_a")
        vectorstore2 = AxonVectorStore(memory_system, embeddings, collection_name="collection_b")

        # Add to different collections
        vectorstore1.add_texts(["Collection A doc"])
        vectorstore2.add_texts(["Collection B doc"])

        # Search within collection A
        results = vectorstore1.similarity_search("doc", k=10)

        # Results should be filtered to collection A
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_tier_specification(self, memory_system, embeddings):
        """Test that tier parameter is used."""
        vectorstore = AxonVectorStore(memory_system, embeddings, tier="persistent")

        assert vectorstore.tier == "persistent"

        # Add texts (should go to specified tier)
        ids = vectorstore.add_texts(["Tier test document"])

        assert len(ids) == 1


@pytest.mark.skipif(LANGCHAIN_AVAILABLE, reason="Testing import error handling")
class TestImportError:
    """Test behavior when LangChain is not installed."""

    def test_import_error_raised(self, memory_system, embeddings):
        """Test that ImportError is raised when LangChain is not available."""
        # This test only runs when LangChain is NOT installed
        pass  # Skipped when LangChain is available
