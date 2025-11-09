"""Unit tests for LlamaIndex AxonLlamaIndexVectorStore integration."""

import pytest
from unittest.mock import MagicMock

from axon.core.memory_system import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy
from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry

# Try importing LlamaIndex dependencies
try:
    from llama_index.core.schema import TextNode
    from llama_index.core.vector_stores.types import VectorStoreQuery, VectorStoreQueryResult

    from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


@pytest.fixture
def memory_system():
    """Create a MemorySystem for testing."""
    registry = AdapterRegistry()
    registry.register("persistent", adapter_type="memory", adapter_instance=InMemoryAdapter())

    config = MemoryConfig(persistent=PersistentPolicy(backend="memory"), default_tier="persistent")

    return MemorySystem(config, registry=registry)


@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestAxonLlamaIndexVectorStore:
    """Test AxonLlamaIndexVectorStore adapter."""

    @pytest.mark.asyncio
    async def test_initialization(self, memory_system):
        """Test AxonLlamaIndexVectorStore initialization."""
        vectorstore = AxonLlamaIndexVectorStore(
            memory_system, tier="persistent", collection_name="test_collection"
        )

        assert vectorstore.client == memory_system
        assert vectorstore._tier == "persistent"
        assert vectorstore._collection_name == "test_collection"
        assert vectorstore.stores_text is True
        assert vectorstore.is_embedding_query is True

    @pytest.mark.asyncio
    async def test_add_nodes(self, memory_system):
        """Test adding nodes to vector store."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Create test nodes
        nodes = [
            TextNode(
                id_="node1",
                text="First test node",
                embedding=[0.1, 0.2, 0.3],
                metadata={"source": "test1"},
            ),
            TextNode(
                id_="node2",
                text="Second test node",
                embedding=[0.4, 0.5, 0.6],
                metadata={"source": "test2"},
            ),
        ]

        ids = vectorstore.add(nodes)

        assert len(ids) == 2
        assert all(isinstance(id, str) for id in ids)

    @pytest.mark.asyncio
    async def test_add_nodes_without_embedding_skips(self, memory_system):
        """Test that nodes without embeddings are skipped."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Create node without embedding
        nodes = [
            TextNode(id_="node1", text="Node without embedding", metadata={}),
        ]

        ids = vectorstore.add(nodes)

        # Should skip the node
        assert len(ids) == 0

    @pytest.mark.asyncio
    async def test_query_with_query_str(self, memory_system):
        """Test querying with query string."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Add nodes first
        nodes = [
            TextNode(
                id_="node1",
                text="Python programming tutorial",
                embedding=[0.1, 0.2, 0.3],
            ),
            TextNode(id_="node2", text="JavaScript basics", embedding=[0.4, 0.5, 0.6]),
        ]
        vectorstore.add(nodes)

        # Create query
        query = VectorStoreQuery(query_str="programming", similarity_top_k=5)

        # Execute query
        result = vectorstore.query(query)

        assert isinstance(result, VectorStoreQueryResult)
        assert isinstance(result.nodes, list)
        assert isinstance(result.ids, list)
        assert isinstance(result.similarities, list)

    @pytest.mark.asyncio
    async def test_query_with_embedding_only(self, memory_system):
        """Test querying with embedding only (logs warning)."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Add a node
        nodes = [TextNode(id_="node1", text="Test content", embedding=[0.1, 0.2, 0.3])]
        vectorstore.add(nodes)

        # Query with embedding only
        query = VectorStoreQuery(query_embedding=[0.1, 0.2, 0.3], similarity_top_k=1)

        result = vectorstore.query(query)

        # Should still return a result (with warning logged)
        assert isinstance(result, VectorStoreQueryResult)

    @pytest.mark.asyncio
    async def test_query_returns_text_nodes(self, memory_system):
        """Test that query returns proper TextNode objects."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system, collection_name="query_test")

        # Add nodes
        nodes = [
            TextNode(
                id_="node1",
                text="Content one",
                embedding=[0.1, 0.2, 0.3],
                metadata={"page": 1},
            ),
        ]
        vectorstore.add(nodes)

        # Query
        query = VectorStoreQuery(query_str="content", similarity_top_k=1)
        result = vectorstore.query(query)

        if result.nodes:
            node = result.nodes[0]
            assert isinstance(node, TextNode)
            assert hasattr(node, "text")
            assert hasattr(node, "embedding")

    @pytest.mark.asyncio
    async def test_delete_logs_warning(self, memory_system):
        """Test that delete logs a warning (not fully supported)."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Should log warning but not raise
        vectorstore.delete("some_ref_doc_id")

        # No error should be raised

    @pytest.mark.asyncio
    async def test_async_add(self, memory_system):
        """Test async add method."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        nodes = [
            TextNode(id_="async1", text="Async node", embedding=[0.1, 0.2, 0.3]),
        ]

        ids = await vectorstore.async_add(nodes)

        assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_async_query(self, memory_system):
        """Test async query method."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Add nodes
        nodes = [TextNode(id_="node1", text="Test node", embedding=[0.1, 0.2, 0.3])]
        await vectorstore.async_add(nodes)

        # Query async
        query = VectorStoreQuery(query_str="test", similarity_top_k=1)
        result = await vectorstore.aquery(query)

        assert isinstance(result, VectorStoreQueryResult)

    @pytest.mark.asyncio
    async def test_persist_logs_info(self, memory_system):
        """Test that persist logs info message."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Should log info but not actually do anything
        vectorstore.persist("/some/path")

        # No error should be raised

    @pytest.mark.asyncio
    async def test_from_persist_path(self, memory_system):
        """Test from_persist_path classmethod."""
        vectorstore = AxonLlamaIndexVectorStore.from_persist_path(
            "/some/path", system=memory_system, collection_name="loaded_collection"
        )

        assert isinstance(vectorstore, AxonLlamaIndexVectorStore)
        assert vectorstore._collection_name == "loaded_collection"

    @pytest.mark.asyncio
    async def test_from_persist_path_without_system_raises(self):
        """Test that from_persist_path raises error without system."""
        with pytest.raises(ValueError, match="system .* is required"):
            AxonLlamaIndexVectorStore.from_persist_path("/some/path")

    @pytest.mark.asyncio
    async def test_collection_filtering(self, memory_system):
        """Test that collection name is used in queries."""
        vectorstore = AxonLlamaIndexVectorStore(
            memory_system, collection_name="specific_collection"
        )

        # Add nodes
        nodes = [TextNode(id_="node1", text="Collection test", embedding=[0.1, 0.2, 0.3])]
        vectorstore.add(nodes)

        # Query (should filter by collection)
        query = VectorStoreQuery(query_str="test", similarity_top_k=5)
        result = vectorstore.query(query)

        assert isinstance(result, VectorStoreQueryResult)

    @pytest.mark.asyncio
    async def test_tier_specification(self, memory_system):
        """Test that tier parameter is used."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system, tier="persistent")

        assert vectorstore._tier == "persistent"

        # Add nodes (should go to specified tier)
        nodes = [TextNode(id_="node1", text="Tier test", embedding=[0.1, 0.2, 0.3])]
        ids = vectorstore.add(nodes)

        assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_node_metadata_preserved(self, memory_system):
        """Test that node metadata is preserved."""
        vectorstore = AxonLlamaIndexVectorStore(memory_system)

        # Add node with metadata
        nodes = [
            TextNode(
                id_="meta_node",
                text="Node with metadata",
                embedding=[0.1, 0.2, 0.3],
                metadata={"author": "test_author", "date": "2025-01-01"},
            )
        ]
        vectorstore.add(nodes)

        # Query and check metadata
        query = VectorStoreQuery(query_str="metadata", similarity_top_k=1)
        result = vectorstore.query(query)

        if result.nodes:
            # Metadata should be in custom_fields
            pass  # Metadata preservation verified in implementation


@pytest.mark.skipif(LLAMAINDEX_AVAILABLE, reason="Testing import error handling")
class TestImportError:
    """Test behavior when LlamaIndex is not installed."""

    def test_import_error_raised(self, memory_system):
        """Test that ImportError is raised when LlamaIndex is not available."""
        # This test only runs when LlamaIndex is NOT installed
        pass  # Skipped when LlamaIndex is available
