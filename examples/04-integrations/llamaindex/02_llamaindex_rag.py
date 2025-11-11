"""
LlamaIndex RAG Application

Build a RAG application using Axon with LlamaIndex.

Run: python 02_llamaindex_rag.py
"""

import asyncio


async def main():
    print("=== LlamaIndex RAG with Axon ===\n")

    print("Complete RAG application example:\n")

    print("""
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from axon.core.templates import STANDARD_CONFIG
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Load documents
documents = SimpleDirectoryReader('data/').load_data()

# Create Axon-backed index
vector_store = AxonLlamaIndexVectorStore(config=STANDARD_CONFIG)
index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# Query engine with Axon
query_engine = index.as_query_engine(
    similarity_top_k=5,
    response_mode="compact"
)

# Query
response = query_engine.query("Explain memory tiers")
print(response)
    """)

    print("\nBenefits:")
    print("  * Multi-tier storage (ephemeral/session/persistent)")
    print("  * Automatic tier management")
    print("  * Built-in compaction")
    print("  * Observability and audit logs\n")

    print("=" * 50)
    print("* LlamaIndex RAG complete!")


if __name__ == "__main__":
    asyncio.run(main())
