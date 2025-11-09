"""
LangChain VectorStore Adapter for Axon

This module provides AxonVectorStore, a LangChain-compatible vector store that
uses Axon's MemorySystem as the backend. This allows LangChain applications to
use Axon for document storage and semantic search in RAG pipelines.

Example:
    >>> from axon import MemorySystem
    >>> from axon.integrations.langchain import AxonVectorStore
    >>> from langchain_openai import OpenAIEmbeddings
    >>>
    >>> # Create Axon-backed vector store
    >>> system = MemorySystem.from_template("balanced")
    >>> embeddings = OpenAIEmbeddings()
    >>> vectorstore = AxonVectorStore(system, embeddings)
    >>>
    >>> # Add documents
    >>> vectorstore.add_texts(
    ...     ["Document 1 text", "Document 2 text"],
    ...     metadatas=[{"source": "doc1"}, {"source": "doc2"}]
    ... )
    >>>
    >>> # Search
    >>> results = vectorstore.similarity_search("query", k=5)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type

try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    VectorStore = object  # type: ignore
    Document = object  # type: ignore
    Embeddings = object  # type: ignore

from ...core.memory_system import MemorySystem
from ...models import Filter, MemoryEntry, MemoryMetadata

logger = logging.getLogger(__name__)


class AxonVectorStore(VectorStore):
    """
    LangChain-compatible vector store backed by Axon MemorySystem.

    This adapter implements LangChain's VectorStore interface, storing documents
    in Axon's multi-tier memory system. It provides:
    - Semantic search over stored documents
    - Multi-tier storage with automatic tier selection
    - Policy-driven lifecycle management
    - Integration with LangChain RAG pipelines

    Attributes:
        system: The Axon MemorySystem instance to use for storage
        embedding: LangChain Embeddings instance for text embedding
        tier: Optional tier name to use for storage (default: auto-select)
        collection_name: Optional collection identifier for document grouping

    Example:
        >>> from axon import MemorySystem
        >>> from axon.integrations.langchain import AxonVectorStore
        >>> from langchain_openai import OpenAIEmbeddings
        >>>
        >>> system = MemorySystem.from_template("balanced")
        >>> embeddings = OpenAIEmbeddings()
        >>> vectorstore = AxonVectorStore(system, embeddings)
        >>>
        >>> # Use with retriever
        >>> retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    """

    def __init__(
        self,
        system: MemorySystem,
        embedding: Embeddings,
        tier: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize AxonVectorStore.

        Args:
            system: Axon MemorySystem instance
            embedding: LangChain Embeddings instance
            tier: Optional tier name for storage (default: policy-based routing)
            collection_name: Optional collection name for grouping documents

        Raises:
            ImportError: If langchain_core is not installed
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain_core is required for AxonVectorStore. "
                "Install it with: pip install langchain-core"
            )

        self.system = system
        self.embedding = embedding
        self.tier = tier
        self.collection_name = collection_name

        logger.info(
            f"AxonVectorStore initialized with tier={tier}, " f"collection={collection_name}"
        )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        *,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Add texts to the vector store.

        Args:
            texts: Iterable of text strings to add
            metadatas: Optional list of metadata dicts (one per text)
            ids: Optional list of IDs (one per text)
            **kwargs: Additional arguments

        Returns:
            List of IDs for the added texts

        Raises:
            RuntimeError: If async store operation fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            return loop.run_until_complete(self._add_texts_async(texts, metadatas, ids, **kwargs))

        except Exception as e:
            logger.error(f"Failed to add texts: {e}")
            raise

    async def _add_texts_async(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]],
        ids: Optional[List[str]],
        **kwargs: Any,
    ) -> List[str]:
        """
        Async implementation of add_texts.

        Args:
            texts: Iterable of texts
            metadatas: Optional metadata list
            ids: Optional ID list
            **kwargs: Additional arguments

        Returns:
            List of entry IDs
        """
        text_list = list(texts)
        metadatas = metadatas or [{} for _ in text_list]
        ids = ids or [None] * len(text_list)  # type: ignore

        # Embed texts
        embeddings = await self.embedding.aembed_documents(text_list)

        # Store in Axon
        entry_ids = []
        for i, (text, embedding, metadata) in enumerate(zip(text_list, embeddings, metadatas)):
            # Build tags
            tags = ["langchain_document"]
            if self.collection_name:
                tags.append(f"collection:{self.collection_name}")

            # Merge custom fields from metadata
            custom_fields = {
                "source": metadata.get("source", ""),
                "page": metadata.get("page", None),
                **{k: v for k, v in metadata.items() if k not in ["source", "page"]},
            }

            # Store entry (first arg is content, custom_fields go in metadata)
            entry_id = await self.system.store(
                text,  # content parameter (positional)
                metadata=custom_fields,  # custom fields as metadata
                tier=self.tier,
                tags=tags,
                importance=0.5,
            )
            # Note: embedding is generated automatically by the system's embedder

            entry_ids.append(entry_id)

        logger.debug(f"Added {len(entry_ids)} documents to Axon vector store")
        return entry_ids

    def similarity_search(
        self, query: str, k: int = 4, filter: Optional[dict] = None, **kwargs: Any
    ) -> List[Document]:
        """
        Search for documents similar to query.

        Args:
            query: Query string
            k: Number of results to return
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of Document objects ordered by similarity

        Raises:
            RuntimeError: If async recall operation fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            return loop.run_until_complete(
                self._similarity_search_async(query, k, filter, **kwargs)
            )

        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            raise

    async def _similarity_search_async(
        self, query: str, k: int, filter: Optional[dict], **kwargs: Any
    ) -> List[Document]:
        """
        Async implementation of similarity search.

        Args:
            query: Query string
            k: Number of results
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of Documents
        """
        # Build Axon filter
        axon_filter = None
        if filter or self.collection_name:
            filter_dict: dict[str, Any] = {}

            # Add collection filter
            if self.collection_name:
                filter_dict["tags"] = [f"collection:{self.collection_name}"]

            # Merge user filter (simplified - may need more sophisticated mapping)
            if filter:
                filter_dict.update(filter)

            axon_filter = Filter(**filter_dict)

        # Perform semantic search
        results = await self.system.recall(query, k=k, filter=axon_filter)

        # Convert MemoryEntry to Document
        documents = []
        for entry in results:
            # Build metadata dict from entry metadata
            # Start with standard fields
            metadata = {
                "id": entry.id,
                "importance": entry.metadata.importance,
                "timestamp": entry.metadata.created_at.isoformat(),
            }
            
            # Add custom fields (stored as attributes on metadata due to extra="allow")
            # Get all non-standard fields
            for key, value in entry.metadata.model_dump().items():
                if key not in ["user_id", "session_id", "source", "privacy_level", 
                               "created_at", "last_accessed_at", "tags", "importance",
                               "version", "provenance"]:
                    metadata[key] = value

            doc = Document(page_content=entry.text, metadata=metadata)
            documents.append(doc)

        return documents

    def similarity_search_with_score(
        self, query: str, k: int = 4, filter: Optional[dict] = None, **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """
        Search for documents with similarity scores.

        Args:
            query: Query string
            k: Number of results
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of (Document, score) tuples
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            return loop.run_until_complete(
                self._similarity_search_with_score_async(query, k, filter, **kwargs)
            )

        except Exception as e:
            logger.error(f"Failed to perform similarity search with score: {e}")
            raise

    async def _similarity_search_with_score_async(
        self, query: str, k: int, filter: Optional[dict], **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """
        Async implementation of similarity search with scores.

        Note: Axon doesn't currently return similarity scores, so we use
        importance scores as a proxy.

        Args:
            query: Query string
            k: Number of results
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of (Document, score) tuples
        """
        # Build Axon filter
        axon_filter = None
        if filter or self.collection_name:
            filter_dict: dict[str, Any] = {}

            if self.collection_name:
                filter_dict["tags"] = [f"collection:{self.collection_name}"]

            if filter:
                filter_dict.update(filter)

            axon_filter = Filter(**filter_dict)

        # Perform semantic search
        results = await self.system.recall(query, k=k, filter=axon_filter)

        # Convert to (Document, score) tuples
        # Note: Using importance as score proxy since Axon doesn't return similarity scores
        doc_score_pairs = []
        for entry in results:
            # Build metadata dict from entry metadata
            metadata = {
                "id": entry.id,
                "importance": entry.metadata.importance,
                "timestamp": entry.metadata.created_at.isoformat(),
            }
            
            # Add custom fields (stored as attributes on metadata due to extra="allow")
            for key, value in entry.metadata.model_dump().items():
                if key not in ["user_id", "session_id", "source", "privacy_level",
                               "created_at", "last_accessed_at", "tags", "importance",
                               "version", "provenance"]:
                    metadata[key] = value

            doc = Document(page_content=entry.text, metadata=metadata)
            score = entry.metadata.importance  # Use importance as score proxy
            doc_score_pairs.append((doc, score))

        return doc_score_pairs

    @classmethod
    def from_texts(
        cls: Type["AxonVectorStore"],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        *,
        ids: Optional[List[str]] = None,
        system: Optional[MemorySystem] = None,
        tier: Optional[str] = None,
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> "AxonVectorStore":
        """
        Create AxonVectorStore from texts.

        Args:
            texts: List of text strings
            embedding: Embeddings instance
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs
            system: MemorySystem instance (required)
            tier: Optional tier name
            collection_name: Optional collection name
            **kwargs: Additional arguments

        Returns:
            AxonVectorStore instance with texts loaded

        Raises:
            ValueError: If system is not provided
        """
        if system is None:
            raise ValueError("system (MemorySystem instance) is required for from_texts")

        # Create instance
        vectorstore = cls(
            system=system,
            embedding=embedding,
            tier=tier,
            collection_name=collection_name,
        )

        # Add texts
        vectorstore.add_texts(texts, metadatas=metadatas, ids=ids, **kwargs)

        return vectorstore

    async def aadd_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        *,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Async version of add_texts.

        Args:
            texts: Iterable of texts
            metadatas: Optional metadata list
            ids: Optional ID list
            **kwargs: Additional arguments

        Returns:
            List of entry IDs
        """
        return await self._add_texts_async(texts, metadatas, ids, **kwargs)

    async def asimilarity_search(
        self, query: str, k: int = 4, filter: Optional[dict] = None, **kwargs: Any
    ) -> List[Document]:
        """
        Async version of similarity_search.

        Args:
            query: Query string
            k: Number of results
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of Documents
        """
        return await self._similarity_search_async(query, k, filter, **kwargs)

    async def asimilarity_search_with_score(
        self, query: str, k: int = 4, filter: Optional[dict] = None, **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """
        Async version of similarity_search_with_score.

        Args:
            query: Query string
            k: Number of results
            filter: Optional metadata filter
            **kwargs: Additional arguments

        Returns:
            List of (Document, score) tuples
        """
        return await self._similarity_search_with_score_async(query, k, filter, **kwargs)
