"""
LlamaIndex VectorStore Adapter for Axon

This module provides AxonLlamaIndexVectorStore, a LlamaIndex-compatible vector store
that uses Axon's MemorySystem as the backend. This allows LlamaIndex applications to
use Axon for document indexing and retrieval in RAG pipelines.

Example:
    >>> from axon import MemorySystem
    >>> from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
    >>> from llama_index.core import VectorStoreIndex, StorageContext
    >>>
    >>> # Create Axon-backed vector store
    >>> system = MemorySystem.from_template("balanced")
    >>> vectorstore = AxonLlamaIndexVectorStore(system)
    >>>
    >>> # Use with LlamaIndex
    >>> storage_context = StorageContext.from_defaults(vector_store=vectorstore)
    >>> index = VectorStoreIndex.from_documents(
    ...     documents, storage_context=storage_context
    ... )
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

try:
    from llama_index.core.schema import BaseNode, TextNode
    from llama_index.core.vector_stores.types import (
        BasePydanticVectorStore,
        VectorStoreQuery,
        VectorStoreQueryResult,
    )

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    BasePydanticVectorStore = object  # type: ignore
    BaseNode = object  # type: ignore
    TextNode = object  # type: ignore
    VectorStoreQuery = object  # type: ignore
    VectorStoreQueryResult = object  # type: ignore

from ...core.memory_system import MemorySystem
from ...models import Filter, MemoryEntry, MemoryMetadata

logger = logging.getLogger(__name__)


class AxonLlamaIndexVectorStore(BasePydanticVectorStore):
    """
    LlamaIndex-compatible vector store backed by Axon MemorySystem.

    This adapter implements LlamaIndex's BasePydanticVectorStore interface, storing
    nodes in Axon's multi-tier memory system. It provides:
    - Semantic search over indexed documents
    - Multi-tier storage with automatic tier selection
    - Policy-driven lifecycle management
    - Integration with LlamaIndex query engines

    Attributes:
        system: The Axon MemorySystem instance to use for storage
        tier: Optional tier name to use for storage (default: auto-select)
        collection_name: Optional collection identifier for node grouping
        stores_text: Indicates whether text is stored (always True for Axon)
        is_embedding_query: Whether queries use embeddings (always True)

    Example:
        >>> from axon import MemorySystem
        >>> from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
        >>> from llama_index.core import VectorStoreIndex
        >>>
        >>> system = MemorySystem.from_template("balanced")
        >>> vectorstore = AxonLlamaIndexVectorStore(system)
        >>> index = VectorStoreIndex.from_vector_store(vectorstore)
    """

    # Class attributes required by BasePydanticVectorStore
    stores_text: bool = True
    is_embedding_query: bool = True

    def __init__(
        self,
        system: MemorySystem,
        tier: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize AxonLlamaIndexVectorStore.

        Args:
            system: Axon MemorySystem instance
            tier: Optional tier name for storage (default: policy-based routing)
            collection_name: Optional collection name for grouping nodes

        Raises:
            ImportError: If llama_index is not installed
        """
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError(
                "llama_index is required for AxonLlamaIndexVectorStore. "
                "Install it with: pip install llama-index-core"
            )

        super().__init__()
        self._system = system
        self._tier = tier
        self._collection_name = collection_name

        logger.info(
            f"AxonLlamaIndexVectorStore initialized with tier={tier}, "
            f"collection={collection_name}"
        )

    @property
    def client(self) -> Any:
        """Get the underlying Axon MemorySystem client."""
        return self._system

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """
        Add nodes to the vector store.

        Args:
            nodes: List of BaseNode objects to add
            **add_kwargs: Additional keyword arguments

        Returns:
            List of node IDs

        Raises:
            RuntimeError: If async store operation fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            return loop.run_until_complete(self._add_async(nodes, **add_kwargs))

        except Exception as e:
            logger.error(f"Failed to add nodes: {e}")
            raise

    async def _add_async(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """
        Async implementation of add.

        Args:
            nodes: List of nodes to add
            **add_kwargs: Additional arguments

        Returns:
            List of node IDs
        """
        node_ids = []

        for node in nodes:
            # Extract text content
            text = node.get_content(metadata_mode="none")

            # Extract embedding - check if it exists before calling get_embedding()
            # get_embedding() raises ValueError if embedding is None
            if node.embedding is None:
                logger.warning(f"Node {node.node_id} has no embedding, skipping")
                continue
            
            embedding = node.get_embedding()

            # Build tags
            tags = ["llamaindex_node"]
            if self._collection_name:
                tags.append(f"collection:{self._collection_name}")

            # Add node type tag
            if hasattr(node, "class_name"):
                tags.append(f"node_type:{node.class_name()}")

            # Extract metadata
            metadata_dict = node.metadata or {}
            # Build metadata dict with custom fields for store()
            # Use get_node_info() instead of deprecated node_info property
            node_info = node.get_node_info() if hasattr(node, "get_node_info") else {}
            store_metadata = {
                "node_id": node.node_id,
                "ref_doc_id": node.ref_doc_id or "",
                "node_info": node_info,
                **metadata_dict,
            }

            # Store in Axon - content as positional arg, metadata dict for custom fields
            # Note: System will generate embeddings internally; we don't pass pre-computed embeddings
            entry_id = await self._system.store(
                text,  # content as positional arg
                metadata=store_metadata,  # metadata dict
                tier=self._tier,
                tags=tags,
                importance=0.5,
            )

            node_ids.append(entry_id)

        logger.debug(f"Added {len(node_ids)} nodes to Axon vector store")
        return node_ids

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Delete nodes by reference document ID.

        Args:
            ref_doc_id: Reference document ID to delete
            **delete_kwargs: Additional keyword arguments

        Note:
            Axon doesn't currently support bulk delete by filter.
            This logs a warning.
        """
        logger.warning(
            f"AxonLlamaIndexVectorStore.delete(ref_doc_id={ref_doc_id}) not fully supported. "
            "Axon does not currently support bulk delete by filter. "
            "Individual entries must be deleted by ID."
        )
        # TODO: Implement when Axon supports bulk delete by filter

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """
        Query the vector store.

        Args:
            query: VectorStoreQuery object containing query parameters
            **kwargs: Additional keyword arguments

        Returns:
            VectorStoreQueryResult with matching nodes

        Raises:
            RuntimeError: If async recall operation fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            return loop.run_until_complete(self._query_async(query, **kwargs))

        except Exception as e:
            logger.error(f"Failed to query vector store: {e}")
            raise

    async def _query_async(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """
        Async implementation of query.

        Args:
            query: VectorStoreQuery object
            **kwargs: Additional arguments

        Returns:
            VectorStoreQueryResult
        """
        # Build Axon filter
        axon_filter = None
        filter_dict: dict[str, Any] = {}

        # Add collection filter
        if self._collection_name:
            filter_dict["tags"] = [f"collection:{self._collection_name}"]

        # Add filters from query
        if query.filters:
            # Note: LlamaIndex filters may need more sophisticated mapping
            logger.warning("Query filters are not fully supported yet")

        if filter_dict:
            axon_filter = Filter(**filter_dict)

        # Determine k (similarity_top_k has priority)
        k = query.similarity_top_k or 10

        # Perform semantic search
        # Note: LlamaIndex typically provides query embeddings, but we'll use query_str if available
        if query.query_str:
            results = await self._system.recall(query.query_str, k=k, filter=axon_filter)
        elif query.query_embedding:
            # If only embedding is provided, we need to use Axon's query method
            # This requires extending MemorySystem to support embedding-only queries
            logger.warning(
                "Query by embedding only is not fully supported. Using empty query string."
            )
            results = await self._system.recall("", k=k, filter=axon_filter)
        else:
            logger.warning("No query string or embedding provided")
            results = []

        # Convert MemoryEntry to nodes
        nodes = []
        ids = []
        similarities = []

        for entry in results:
            # Reconstruct node from entry - access metadata fields directly
            node_id = getattr(entry.metadata, "node_id", entry.id)
            ref_doc_id = getattr(entry.metadata, "ref_doc_id", None)

            # Extract custom metadata - iterate model_dump() excluding standard fields
            metadata_dict = {}
            for k, v in entry.metadata.model_dump().items():
                if k not in ["node_id", "ref_doc_id", "node_info", "importance", "created_at", "last_accessed", "access_count", "tier"]:
                    metadata_dict[k] = v

            # Create TextNode with ref_doc_id during construction (it's read-only)
            node = TextNode(
                id_=node_id,
                text=entry.text,
                embedding=entry.embedding,
                metadata=metadata_dict,
                ref_doc_id=ref_doc_id,  # Pass during construction, not after
            )

            nodes.append(node)
            ids.append(node_id)
            # Use importance as similarity proxy
            similarities.append(entry.metadata.importance)

        return VectorStoreQueryResult(nodes=nodes, ids=ids, similarities=similarities)

    async def async_add(self, nodes: List[BaseNode], **kwargs: Any) -> List[str]:
        """
        Async version of add.

        Args:
            nodes: List of nodes to add
            **kwargs: Additional arguments

        Returns:
            List of node IDs
        """
        return await self._add_async(nodes, **kwargs)

    async def adelete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Async version of delete.

        Args:
            ref_doc_id: Reference document ID
            **delete_kwargs: Additional arguments
        """
        self.delete(ref_doc_id, **delete_kwargs)  # Same limitation as sync

    async def aquery(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """
        Async version of query.

        Args:
            query: VectorStoreQuery object
            **kwargs: Additional arguments

        Returns:
            VectorStoreQueryResult
        """
        return await self._query_async(query, **kwargs)

    def persist(self, persist_path: str, fs: Optional[Any] = None, **kwargs: Any) -> None:
        """
        Persist vector store to disk.

        Note: Axon persistence is handled by the MemorySystem's adapters.
        This method is a no-op as Axon handles persistence automatically
        based on tier policies.

        Args:
            persist_path: Path to persist to (unused)
            fs: Filesystem to use (unused)
            **kwargs: Additional arguments
        """
        logger.info(
            "AxonLlamaIndexVectorStore.persist() called, but persistence is "
            "handled automatically by Axon's tier policies."
        )

    @classmethod
    def from_persist_path(
        cls, persist_path: str, fs: Optional[Any] = None, **kwargs: Any
    ) -> "AxonLlamaIndexVectorStore":
        """
        Load vector store from persisted path.

        Note: Not applicable for Axon as persistence is handled by adapters.

        Args:
            persist_path: Path to load from
            fs: Filesystem to use
            **kwargs: Additional arguments including 'system'

        Returns:
            AxonLlamaIndexVectorStore instance

        Raises:
            ValueError: If system is not provided
        """
        system = kwargs.get("system")
        if system is None:
            raise ValueError("system (MemorySystem instance) is required")

        logger.info(
            "Loading from persist_path is not applicable for Axon. "
            "Creating new instance with provided MemorySystem."
        )

        return cls(
            system=system, tier=kwargs.get("tier"), collection_name=kwargs.get("collection_name")
        )
