"""
Custom Embedder Implementation

Create a custom embedder for Axon.

Run: python 02_custom_embedder.py
"""

import asyncio
try:
    import numpy as np
except ImportError:
    print('numpy not installed, using random'); import random as np
from axon import MemorySystem
from axon.embedders.base import Embedder
from axon.core.templates import DEVELOPMENT_CONFIG


class CustomEmbedder(Embedder):
    """Custom embedder example - uses random vectors for demo."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text (random for demo purposes)."""
        return np.random.rand(self.dimensions).tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (random for demo purposes)."""
        return [np.random.rand(self.dimensions).tolist() for _ in texts]

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self.dimensions

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return f"custom-embedder-{self.dimensions}d"

    def signature(self) -> str:
        """Return embedder signature for caching."""
        return f"custom-embedder:v1:{self.dimensions}"


async def main():
    print("=== Custom Embedder ===\n")

    # Create custom embedder
    embedder = CustomEmbedder(dimensions=384)

    # Use with MemorySystem
    memory = MemorySystem(DEVELOPMENT_CONFIG, embedder=embedder)

    print("1. Storing with custom embedder...")
    await memory.store("Test entry with custom embeddings")
    print("  OK Entry stored with custom embeddings\n")

    print("2. Embedder signature:")
    print(f"  {embedder.signature()}\n")

    print("Custom Embedder Implementation:")
    print("  * Inherit from axon.embedders.base.Embedder")
    print("  * Implement embed() method")
    print("  * Implement signature() method")
    print("  * Use any embedding model/API\n")

    print("=" * 50)
    print("* Custom embedder complete!")


if __name__ == "__main__":
    asyncio.run(main())
