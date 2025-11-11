"""
Understanding Configuration

Learn how to configure your Axon memory system with different templates
and understand what each configuration does.

Learn:
- Available configuration templates
- What each template is optimized for
- How to choose the right configuration

Run:
    python 02_understanding_config.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import (
    DEVELOPMENT_CONFIG,
    LIGHTWEIGHT_CONFIG,
    STANDARD_CONFIG,
    PRODUCTION_CONFIG,
)


async def main():
    """Explore different configuration templates."""
    print("=== Understanding Axon Configuration ===\n")

    # 1. Development Config - Best for testing and development
    print("1. DEVELOPMENT_CONFIG")
    print("   Purpose: Fast, in-memory storage for development")
    print("   Best for: Testing, prototyping, local development")
    dev_system = MemorySystem(DEVELOPMENT_CONFIG)
    await dev_system.store("Development test memory")
    print("   OK Created with development config\n")

    # 2. Lightweight Config - Minimal dependencies
    print("2. LIGHTWEIGHT_CONFIG")
    print("   Purpose: Redis only, no vector databases needed")
    print("   Best for: Small deployments, minimal setup")
    # Note: Requires Redis running for actual use
    print("   (Requires Redis server to run)\n")

    # 3. Standard Config - Balanced setup
    print("3. STANDARD_CONFIG")
    print("   Purpose: Redis cache + ChromaDB vectors")
    print("   Best for: Most applications, balanced performance")
    # Note: Requires Redis and ChromaDB
    print("   (Requires Redis and ChromaDB)\n")

    # 4. Production Config - Enterprise ready
    print("4. PRODUCTION_CONFIG")
    print("   Purpose: Redis cache + Pinecone vectors")
    print("   Best for: High-scale production deployments")
    # Note: Requires Redis and Pinecone
    print("   (Requires Redis and Pinecone API key)\n")

    print("Tip: Start with DEVELOPMENT_CONFIG for learning,")
    print("     then upgrade to STANDARD or PRODUCTION for production.")


if __name__ == "__main__":
    asyncio.run(main())
