"""
Document Q&A RAG System

Build a document Q&A system with semantic retrieval.

Run: python 01_document_qa.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy


async def main():
    print("=== Document Q&A RAG System ===\n")

    # RAG-optimized configuration
    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=10000,
            compaction_strategy="semantic"
        ),
        default_tier="persistent"
    )

    memory = MemorySystem(config)

    print("1. Ingesting documents...")

    documents = [
        "Python is a high-level programming language known for readability",
        "Python supports multiple programming paradigms including OOP",
        "Python has a large ecosystem of libraries and frameworks",
        "FastAPI is a modern web framework for building APIs with Python",
        "Django is a batteries-included web framework for Python",
        "Machine learning libraries like TensorFlow and PyTorch use Python",
    ]

    for i, doc in enumerate(documents):
        await memory.store(
            doc,
            importance=0.9,
            tags=["documentation", "python"],
            metadata={"doc_id": f"doc_{i+1}"}
        )

    print(f"  OK Ingested {len(documents)} documents\n")

    # Query
    print("2. Querying knowledge base...")

    queries = [
        "What is Python?",
        "What web frameworks are available?",
        "Machine learning with Python"
    ]

    for query in queries:
        print(f"\n  Q: {query}")
        results = await memory.recall(query, k=2)

        if results:
            print(f"  A: {results[0].text}")

    print("\n" + "=" * 50)
    print("* Document Q&A complete!")


if __name__ == "__main__":
    asyncio.run(main())
