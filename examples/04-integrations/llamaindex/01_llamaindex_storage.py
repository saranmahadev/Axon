"""
LlamaIndex Storage Integration

Use Axon as storage backend for LlamaIndex applications.

Run: python 01_llamaindex_storage.py

Requirements: pip install llama-index
"""

import asyncio


async def main():
    print("=== LlamaIndex Storage Integration ===\n")

    print("Axon provides LlamaIndex vector store integration:\n")

    print("Example code:")
    print("""
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from axon.core.templates import DEVELOPMENT_CONFIG
from llama_index.core import VectorStoreIndex, Document

# Create Axon vector store
vector_store = AxonLlamaIndexVectorStore(config=DEVELOPMENT_CONFIG)

# Create documents
documents = [
    Document(text="Axon is a memory SDK"),
    Document(text="It supports multiple tiers")
]

# Build index
index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is Axon?")
    """)

    print("\nFeatures:")
    print("  * Full LlamaIndex compatibility")
    print("  * Multi-tier storage")
    print("  * Automatic persistence")
    print("  * Metadata support\n")

    print("=" * 50)
    print("* LlamaIndex integration complete!")


if __name__ == "__main__":
    asyncio.run(main())
