"""
Knowledge Base Management

Build a knowledge management system with semantic search and compaction.

Run: python 01_knowledge_management.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy


async def main():
    print("=== Knowledge Base Management ===\n")

    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=100,
            compaction_strategy="semantic"
        ),
        default_tier="persistent"
    )

    memory = MemorySystem(config)

    print("1. Building knowledge base...")

    knowledge_items = [
        ("Axon supports multi-tier memory architecture", ["architecture"], 0.9),
        ("Three tiers: ephemeral, session, persistent", ["architecture"], 0.9),
        ("Redis is recommended for caching tiers", ["best-practices"], 0.8),
        ("ChromaDB works well for development", ["best-practices"], 0.7),
        ("Compaction reduces entry count via summarization", ["features"], 0.8),
        ("Automatic PII detection is built-in", ["features", "security"], 0.9),
    ]

    for content, tags, importance in knowledge_items:
        await memory.store(content, importance=importance, tags=tags)

    print(f"  OK Added {len(knowledge_items)} knowledge items\n")

    # Search
    print("2. Searching knowledge base...")

    searches = [
        ("architecture", ["architecture"]),
        ("best practices", ["best-practices"]),
        ("security features", ["security"])
    ]

    for query, expected_tags in searches:
        results = await memory.recall(query, k=3)
        print(f"\n  Query: '{query}'")
        print(f"  Results: {len(results)}")
        if results:
            print(f"    -> {results[0].text}")

    # Export knowledge
    print("\n3. Exporting knowledge base...")
    data = await memory.export()
    print(f"  OK Exported {data['statistics']['total_entries']} entries\n")

    print("=" * 50)
    print("* Knowledge management complete!")


if __name__ == "__main__":
    asyncio.run(main())
