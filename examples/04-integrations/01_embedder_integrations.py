"""
Embedder Integrations

Use different embedders with Axon (OpenAI, Voyage, HuggingFace, etc.).

Run: python 01_embedder_integrations.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    print("=== Embedder Integrations ===\n")

    print("Supported Embedders:\n")

    print("1. OpenAI Embeddings")
    print("   from axon.embedders import OpenAIEmbedder")
    print("   embedder = OpenAIEmbedder(model='text-embedding-3-large')\n")

    print("2. Voyage AI")
    print("   from axon.embedders import VoyageAIEmbedder")
    print("   embedder = VoyageAIEmbedder(model='voyage-2')\n")

    print("3. Sentence Transformers (local)")
    print("   from axon.embedders import SentenceTransformerEmbedder")
    print("   embedder = SentenceTransformerEmbedder()")
    print("   # No API key needed!\n")

    print("4. HuggingFace")
    print("   from axon.embedders import HuggingFaceEmbedder")
    print("   embedder = HuggingFaceEmbedder(model='...')\n")

    print("Usage with MemorySystem:")
    print("  memory = MemorySystem(config, embedder=embedder)\n")

    print("=" * 50)
    print("* Embedder integrations complete!")


if __name__ == "__main__":
    asyncio.run(main())
