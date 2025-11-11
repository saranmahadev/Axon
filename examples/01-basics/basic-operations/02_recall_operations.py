"""
Recall Operations - Comprehensive Guide

Learn different ways to retrieve memories using semantic search, filters,
importance thresholds, and multi-tier queries.

Learn:
- Basic semantic recall
- Filtering by tags, user, session
- Setting result limits (k parameter)
- Importance-based filtering
- Multi-tier search
- Working with recall results

Run:
    python 02_recall_operations.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    """Demonstrate various recall operations."""
    print("=== Axon Recall Operations ===\n")

    # Create memory system and populate with sample data
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    print("1. Setting up sample data...\n")

    # Store diverse memories for demonstration
    sample_data = [
        ("User prefers dark mode", 0.8, ["preferences", "ui"], "user_123"),
        ("API key for OpenAI: sk-test123", 0.95, ["credentials", "api"], "user_123"),
        ("User's favorite color is blue", 0.6, ["preferences", "personal"], "user_123"),
        ("Completed Python tutorial", 0.7, ["achievements", "learning"], "user_123"),
        ("Recent search: machine learning", 0.4, ["search", "temporary"], "user_456"),
        ("Account created on 2025-01-15", 0.9, ["account", "metadata"], "user_123"),
        ("User timezone: UTC-5", 0.7, ["preferences", "timezone"], "user_123"),
        ("Failed login attempt from 192.168.1.1", 0.5, ["security", "logs"], "user_456"),
    ]

    for content, importance, tags, user_id in sample_data:
        await memory.store(
            content,
            importance=importance,
            tags=tags,
            metadata={"user_id": user_id}
        )

    print("   OK Stored 8 sample memories\n")

    # 2. Basic semantic recall
    print("2. Basic semantic recall (query: 'user settings'):")
    results = await memory.recall("user settings", k=3)
    print(f"   Found {len(results)} results:")
    for i, entry in enumerate(results, 1):
        print(f"   {i}. {entry.text[:50]}... (importance: {entry.metadata.importance})")
    print()

    # 3. Recall with limit (k parameter)
    print("3. Recall with different limits:")
    results_top1 = await memory.recall("preferences", k=1)
    results_top5 = await memory.recall("preferences", k=5)
    print(f"   k=1: {len(results_top1)} result(s)")
    print(f"   k=5: {len(results_top5)} result(s)")
    print()

    # 4. Recall with tag filter
    print("4. Recall with tag filter (tags=['preferences']):")
    results = await memory.recall(
        "user",
        k=10,
        filter=Filter(tags=["preferences"])
    )
    print(f"   Found {len(results)} results with 'preferences' tag:")
    for entry in results:
        print(f"   - {entry.text[:40]}... Tags: {entry.metadata.tags}")
    print()

    # 5. Recall with user_id filter
    print("5. Recall filtered by user_id:")
    results = await memory.recall(
        "user",
        k=10,
        filter=Filter(user_id="user_123")
    )
    print(f"   Found {len(results)} results for user_123")
    print()

    # 6. Recall with importance threshold
    print("6. Recall with importance threshold (min_importance=0.8):")
    results = await memory.recall(
        "user",
        k=10,
        min_importance=0.8
    )
    print(f"   Found {len(results)} high-importance results:")
    for entry in results:
        print(f"   - {entry.text[:50]}... (importance: {entry.metadata.importance})")
    print()

    # 7. Recall with multiple filters combined
    print("7. Recall with combined filters:")
    results = await memory.recall(
        "user preferences",
        k=10,
        filter=Filter(
            user_id="user_123",
            tags=["preferences"],
            min_importance=0.6
        )
    )
    print(f"   Found {len(results)} results matching all criteria:")
    for entry in results:
        print(f"   - {entry.text[:45]}...")
    print()

    # 8. Recall from specific tier
    print("8. Recall from specific tier (persistent only):")
    results = await memory.recall(
        "user",
        k=10,
        tiers=["persistent"]
    )
    print(f"   Found {len(results)} results from persistent tier")
    print()

    # 9. Recall with importance range
    print("9. Recall with importance range (0.6-0.8):")
    results = await memory.recall(
        "user",
        k=10,
        filter=Filter(min_importance=0.6, max_importance=0.8)
    )
    print(f"   Found {len(results)} results in importance range:")
    for entry in results:
        print(f"   - {entry.text[:50]}... (importance: {entry.metadata.importance})")
    print()

    # 10. Working with recall results
    print("10. Working with recall results:")
    results = await memory.recall("preferences", k=3)

    if results:
        first_result = results[0]
        print(f"   Entry ID: {first_result.id}")
        print(f"   Type: {first_result.type}")
        print(f"   Text: {first_result.text}")
        print(f"   Importance: {first_result.metadata.importance}")
        print(f"   Tags: {first_result.metadata.tags}")
        print(f"   User ID: {first_result.metadata.user_id}")
        print(f"   Created: {first_result.metadata.created_at}")
    print()

    print("=" * 50)
    print("* Successfully demonstrated all recall operations!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * Recall uses semantic search (not exact keyword matching)")
    print("  * k parameter limits number of results returned")
    print("  * Filters allow precise targeting (tags, user, importance)")
    print("  * Multiple filters can be combined (AND logic)")
    print("  * Results are MemoryEntry objects with rich metadata")
    print("  * Empty query returns all entries (up to k limit)")


if __name__ == "__main__":
    asyncio.run(main())
