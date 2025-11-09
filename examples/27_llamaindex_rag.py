"""
LlamaIndex RAG with Axon Vector Store

This example demonstrates using Axon as the vector store backend for LlamaIndex RAG
(Retrieval-Augmented Generation) applications. Axon provides multi-tier storage,
semantic indexing, and policy-driven document lifecycle management.

Features demonstrated:
- AxonLlamaIndexVectorStore integration
- Document indexing and retrieval
- Query engine with Axon backend
- Multi-collection document organization

Requirements:
    pip install llama-index-core llama-index-llms-openai llama-index-embeddings-openai

Run: python examples/27_llamaindex_rag.py
"""

import asyncio
import os

# Set OpenAI API key (or use environment variable)
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"

from axon import MemorySystem
from axon.core.templates import balanced

try:
    from llama_index.core import Document, VectorStoreIndex, StorageContext
    from llama_index.core.schema import TextNode
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding

    from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    print("ERROR: This example requires llama-index-core and related packages")
    print(
        "Install with: pip install llama-index-core llama-index-llms-openai llama-index-embeddings-openai"
    )
    exit(1)


async def demo_basic_rag():
    """Demonstrate basic RAG pipeline with Axon."""
    print("\n" + "=" * 80)
    print("BASIC RAG WITH AXON VECTOR STORE")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(balanced())

    # Create Axon vector store
    vectorstore = AxonLlamaIndexVectorStore(system, collection_name="knowledge_base")

    # Create storage context
    storage_context = StorageContext.from_defaults(vector_store=vectorstore)

    print("Created Axon-backed vector store")
    print("Collection: knowledge_base")
    print()

    # Create sample documents
    documents = [
        Document(
            text="Axon is a unified memory SDK for LLM applications with multi-tier storage.",
            metadata={"source": "axon_docs", "topic": "overview"},
        ),
        Document(
            text="The policy engine manages memory lifecycle across ephemeral, session, and persistent tiers.",
            metadata={"source": "axon_docs", "topic": "architecture"},
        ),
        Document(
            text="Axon supports multiple storage backends including InMemory, Redis, ChromaDB, Qdrant, and Pinecone.",
            metadata={"source": "axon_docs", "topic": "adapters"},
        ),
        Document(
            text="Memory compaction uses LLM summarization to reduce storage while preserving key information.",
            metadata={"source": "axon_docs", "topic": "compaction"},
        ),
    ]

    print(f"Indexing {len(documents)} documents...")

    # Create index
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    print(f"  [+] Indexed {len(documents)} documents into Axon")
    print()

    # Create query engine
    query_engine = index.as_query_engine(similarity_top_k=3)

    # Perform queries
    queries = [
        "What is Axon?",
        "How does memory lifecycle work?",
        "What storage backends are supported?",
    ]

    print("Running queries...")
    print()

    for query in queries:
        print(f"Query: {query}")
        response = query_engine.query(query)
        print(f"Response: {response}")
        print()

    print("[OK] RAG pipeline working with Axon vector store")
    print()


async def demo_multi_collection():
    """Demonstrate organizing documents across multiple collections."""
    print("\n" + "=" * 80)
    print("MULTI-COLLECTION DOCUMENT ORGANIZATION")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(balanced())

    # Create separate vector stores for different collections
    tech_store = AxonLlamaIndexVectorStore(system, collection_name="tech_docs")
    science_store = AxonLlamaIndexVectorStore(system, collection_name="science_docs")

    print("Created two collections: tech_docs and science_docs")
    print()

    # Tech documents
    tech_docs = [
        Document(
            text="Python is a high-level programming language known for readability.",
            metadata={"category": "tech"},
        ),
        Document(
            text="React is a JavaScript library for building user interfaces.",
            metadata={"category": "tech"},
        ),
    ]

    # Science documents
    science_docs = [
        Document(
            text="Photosynthesis is the process by which plants convert light into energy.",
            metadata={"category": "science"},
        ),
        Document(
            text="DNA contains genetic information in all living organisms.",
            metadata={"category": "science"},
        ),
    ]

    # Index documents into respective collections
    print("Indexing documents into separate collections...")

    tech_context = StorageContext.from_defaults(vector_store=tech_store)
    tech_index = VectorStoreIndex.from_documents(tech_docs, storage_context=tech_context)

    science_context = StorageContext.from_defaults(vector_store=science_store)
    science_index = VectorStoreIndex.from_documents(science_docs, storage_context=science_context)

    print(f"  [+] Indexed {len(tech_docs)} tech documents")
    print(f"  [+] Indexed {len(science_docs)} science documents")
    print()

    # Query each collection
    print("Querying tech collection:")
    tech_engine = tech_index.as_query_engine(similarity_top_k=2)
    tech_response = tech_engine.query("Tell me about programming")
    print(f"  Response: {tech_response}")
    print()

    print("Querying science collection:")
    science_engine = science_index.as_query_engine(similarity_top_k=2)
    science_response = science_engine.query("How do plants create energy?")
    print(f"  Response: {science_response}")
    print()

    print("[OK] Multi-collection organization working")
    print()


async def demo_incremental_indexing():
    """Demonstrate adding documents incrementally."""
    print("\n" + "=" * 80)
    print("INCREMENTAL DOCUMENT INDEXING")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(balanced())

    # Create vector store
    vectorstore = AxonLlamaIndexVectorStore(system, collection_name="incremental_docs")

    # Create storage context
    storage_context = StorageContext.from_defaults(vector_store=vectorstore)

    print("Starting with initial document set...")

    # Initial documents
    initial_docs = [
        Document(text="The Earth is the third planet from the Sun.", metadata={"batch": 1}),
    ]

    # Create index
    index = VectorStoreIndex.from_documents(initial_docs, storage_context=storage_context)

    print(f"  [+] Indexed {len(initial_docs)} initial documents")
    print()

    # Add more documents incrementally
    print("Adding more documents incrementally...")

    additional_docs = [
        Document(
            text="The Moon orbits the Earth approximately every 27 days.", metadata={"batch": 2}
        ),
        Document(text="Mars is known as the Red Planet.", metadata={"batch": 2}),
    ]

    for doc in additional_docs:
        index.insert(doc)
        print(f"  [+] Added: {doc.text[:50]}...")

    print()

    # Query the updated index
    query_engine = index.as_query_engine(similarity_top_k=3)
    response = query_engine.query("Tell me about planets and moons")

    print(f"Query: Tell me about planets and moons")
    print(f"Response: {response}")
    print()

    print("[OK] Incremental indexing working")
    print()


async def demo_with_custom_nodes():
    """Demonstrate using custom TextNodes directly."""
    print("\n" + "=" * 80)
    print("CUSTOM TEXTNODES WITH METADATA")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(balanced())

    # Create vector store
    vectorstore = AxonLlamaIndexVectorStore(system, collection_name="custom_nodes")

    print("Creating custom TextNodes with rich metadata...")

    # Create custom nodes
    nodes = [
        TextNode(
            text="Quantum computing uses quantum bits or qubits.",
            metadata={"author": "Dr. Smith", "date": "2025-01-01", "difficulty": "advanced"},
        ),
        TextNode(
            text="Classical computers use bits that are either 0 or 1.",
            metadata={"author": "Dr. Jones", "date": "2025-01-02", "difficulty": "beginner"},
        ),
    ]

    # Embed nodes (in real scenario, you'd use an embedding model)
    # For this demo, we'll add them through the index
    storage_context = StorageContext.from_defaults(vector_store=vectorstore)
    index = VectorStoreIndex(nodes=nodes, storage_context=storage_context)

    print(f"  [+] Created index with {len(nodes)} custom nodes")
    print()

    # Query
    query_engine = index.as_query_engine()
    response = query_engine.query("Explain computing basics")

    print(f"Query: Explain computing basics")
    print(f"Response: {response}")
    print()

    print("[OK] Custom nodes with metadata working")
    print()


async def main():
    """Run all LlamaIndex RAG demonstrations."""
    print("\n" + "=" * 80)
    print("LLAMAINDEX RAG WITH AXON VECTOR STORE")
    print("=" * 80)
    print()
    print("This example shows how to use Axon as a vector store backend for LlamaIndex RAG.")
    print("Axon provides multi-tier storage, semantic indexing, and document lifecycle management.")
    print()

    if not LLAMAINDEX_AVAILABLE:
        print("ERROR: LlamaIndex is not installed")
        print(
            "Install with: pip install llama-index-core llama-index-llms-openai llama-index-embeddings-openai"
        )
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print()
        print("Some demos may not work without embeddings...")
        print()

    # Run demos
    print("Note: Some demos may be simplified due to OpenAI API availability")
    print()

    await demo_basic_rag()
    await demo_multi_collection()
    await demo_incremental_indexing()
    await demo_with_custom_nodes()

    # Summary
    print("=" * 80)
    print("LLAMAINDEX INTEGRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  [+] AxonLlamaIndexVectorStore implements BasePydanticVectorStore")
    print("  [+] Seamless integration with LlamaIndex indexing and querying")
    print("  [+] Multi-collection organization for document categorization")
    print("  [+] Incremental indexing for growing knowledge bases")
    print("  [+] Rich metadata support for advanced filtering")
    print()
    print("Use Cases:")
    print("  - RAG applications with multi-tier document storage")
    print("  - Knowledge bases with automatic lifecycle management")
    print("  - Document search with policy-driven retention")
    print("  - Semantic search over large document collections")
    print()
    print("Next Steps:")
    print("  - Configure custom tier policies for document storage")
    print("  - Enable compaction for large document collections")
    print("  - Integrate with LlamaIndex agents and tools")
    print("  - Explore hybrid search capabilities")
    print()


if __name__ == "__main__":
    asyncio.run(main())
