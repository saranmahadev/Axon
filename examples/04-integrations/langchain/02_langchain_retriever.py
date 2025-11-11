"""
LangChain Retriever

Use Axon as a retriever for LangChain RAG applications.

Run: python 02_langchain_retriever.py
"""

import asyncio


async def main():
    print("=== LangChain Retriever ===\n")

    print("Axon can be used as a LangChain retriever:\n")

    print("Example code:")
    print("""
from axon.integrations.langchain import AxonRetriever
from axon.core.templates import DEVELOPMENT_CONFIG

# Create retriever
retriever = AxonRetriever(config=DEVELOPMENT_CONFIG)

# Use with LangChain
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(),
    retriever=retriever,
    return_source_documents=True
)

# Query
result = qa_chain("What are the key features?")
    """)

    print("\nFeatures:")
    print("  * Semantic search via vector similarity")
    print("  * Metadata filtering")
    print("  * Multi-tier search")
    print("  * Compatible with all LangChain chains\n")

    print("=" * 50)
    print("* LangChain retriever complete!")


if __name__ == "__main__":
    asyncio.run(main())
