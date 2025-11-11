"""
Multi-Tier Queries

Learn how to perform advanced queries across multiple tiers, understand
result merging, deduplication, and tier-aware search strategies.

Learn:
- Querying across all tiers
- Selective multi-tier queries
- Result merging and ranking
- Deduplication strategies
- Tier-specific vs. global search
- Performance considerations

Run:
    python 04_multi_tier_queries.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    """Demonstrate multi-tier query patterns."""
    print("=== Multi-Tier Queries ===\n")

    # Create memory system
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Setting up data across multiple tiers...")
    print("-" * 50)

    # Store overlapping data across tiers
    # Ephemeral: Recent activity
    for i in range(3):
        await memory.store(
            f"Recent search: Python best practices #{i+1}",
            importance=0.3,
            tier="ephemeral",
            tags=["search", "python", "recent"]
        )

    # Session: Current work
    for i in range(3):
        await memory.store(
            f"Working on: Python async patterns tutorial section {i+1}",
            importance=0.6,
            tier="session",
            tags=["work", "python", "async"],
            metadata={"session_id": "session_123"}
        )

    # Persistent: Stored knowledge
    for i in range(3):
        await memory.store(
            f"Python core concept: {['OOP', 'Functional', 'Asyncio'][i]}",
            importance=0.9,
            tier="persistent",
            tags=["knowledge", "python", "concepts"]
        )

    print("  OK Stored 3 entries in ephemeral tier")
    print("  OK Stored 3 entries in session tier")
    print("  OK Stored 3 entries in persistent tier")
    print()

    # 2. Query all tiers (default behavior)
    print("2. Query all tiers (default behavior)")
    print("-" * 50)

    results = await memory.recall("Python", k=10)

    print(f"  Query: 'Python'")
    print(f"  Results: {len(results)} entries from all tiers")
    print()

    # Try to identify tier for each result (we'd need tier tracking)
    for i, entry in enumerate(results, 1):
        print(f"  {i}. {entry.text[:50]}...")
        print(f"     Importance: {entry.metadata.importance}")
        print(f"     Tags: {', '.join(entry.metadata.tags[:2])}")

    print()

    # 3. Query specific tier
    print("3. Query specific tier only")
    print("-" * 50)

    # Query each tier individually
    ephemeral_results = await memory.recall("Python", k=10, tiers=["ephemeral"])
    session_results = await memory.recall("Python", k=10, tiers=["session"])
    persistent_results = await memory.recall("Python", k=10, tiers=["persistent"])

    print(f"  Ephemeral tier: {len(ephemeral_results)} results")
    for entry in ephemeral_results:
        print(f"    - {entry.text[:45]}...")

    print(f"\n  Session tier: {len(session_results)} results")
    for entry in session_results:
        print(f"    - {entry.text[:45]}...")

    print(f"\n  Persistent tier: {len(persistent_results)} results")
    for entry in persistent_results:
        print(f"    - {entry.text[:45]}...")

    print()

    # 4. Multi-tier selective query
    print("4. Query specific subset of tiers")
    print("-" * 50)

    # Query only session + persistent (skip ephemeral)
    results = await memory.recall(
        "Python patterns",
        k=10,
        tiers=["session", "persistent"]
    )

    print(f"  Query: 'Python patterns' in session + persistent")
    print(f"  Results: {len(results)} entries")
    for entry in results:
        print(f"    - {entry.text[:50]}...")

    print()

    # 5. Multi-tier query with filters
    print("5. Multi-tier query with filters")
    print("-" * 50)

    results = await memory.recall(
        "Python",
        k=10,
        tiers=["session", "persistent"],
        filter=Filter(min_importance=0.6)
    )

    print(f"  Query: 'Python' with importance >= 0.6")
    print(f"  Tiers: session + persistent")
    print(f"  Results: {len(results)} entries")
    for entry in results:
        print(f"    - {entry.text[:45]}... (imp: {entry.metadata.importance})")

    print()

    # 6. Result ranking across tiers
    print("6. Result ranking and merging")
    print("-" * 50)

    results = await memory.recall("Python", k=10)

    print(f"  Results are ranked by relevance across all tiers:")
    for i, entry in enumerate(results, 1):
        print(f"  {i}. Importance: {entry.metadata.importance}")
        print(f"     Text: {entry.text[:50]}...")

    print()
    print("  Note: Router merges and ranks results from all tiers")
    print("  Higher importance generally ranks higher")
    print()

    # 7. Deduplication behavior
    print("7. Deduplication across tiers")
    print("-" * 50)

    # Store same content in multiple tiers
    content = "Important: Python requires strict indentation"

    id1 = await memory.store(content, importance=0.5, tier="session")
    id2 = await memory.store(content, importance=0.9, tier="persistent")

    print(f"  Stored identical content in 2 tiers:")
    print(f"    Session tier: {id1}")
    print(f"    Persistent tier: {id2}")
    print()

    results = await memory.recall("Python indentation", k=10)

    print(f"  Query results: {len(results)} entries")
    print(f"  Note: Both entries returned (different IDs)")
    print(f"  Deduplication is NOT automatic across tiers")
    print()

    # 8. Performance considerations
    print("8. Performance considerations")
    print("-" * 50)
    print("Query strategy trade-offs:")
    print()
    print("  All tiers (default):")
    print("    + Comprehensive results")
    print("    - Slower (searches all tiers)")
    print("    - More compute/network")
    print()
    print("  Single tier:")
    print("    + Fastest queries")
    print("    + Least resource usage")
    print("    - Limited scope")
    print()
    print("  Multi-tier selective:")
    print("    + Balance speed and coverage")
    print("    + Skip irrelevant tiers")
    print("    - Requires tier knowledge")
    print()

    # 9. Tier-aware search patterns
    print("9. Tier-aware search patterns")
    print("-" * 50)
    print("Common query patterns:")
    print()

    # Pattern 1: Recent + Long-term
    print("  Pattern 1: Recent activity + Long-term knowledge")
    results = await memory.recall(
        "Python",
        k=10,
        tiers=["ephemeral", "persistent"]  # Skip session
    )
    print(f"    Results: {len(results)} entries")

    # Pattern 2: Session-only
    print("\n  Pattern 2: Current session only")
    results = await memory.recall(
        "working",
        k=10,
        tiers=["session"],
        filter=Filter(session_id="session_123")
    )
    print(f"    Results: {len(results)} entries")

    # Pattern 3: Important + Persistent
    print("\n  Pattern 3: Important persistent knowledge")
    results = await memory.recall(
        "concepts",
        k=10,
        tiers=["persistent"],
        filter=Filter(min_importance=0.8)
    )
    print(f"    Results: {len(results)} entries")

    print()

    # 10. Statistics by tier
    print("10. Query statistics by tier")
    print("-" * 50)

    stats = memory.get_statistics()

    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"\n  {tier_name.upper()} tier:")
        print(f"    Total recalls: {tier_stats.get('recalls', 0)}")

    print()

    print("=" * 50)
    print("* Successfully demonstrated multi-tier queries!")
    print("=" * 50)
    print("\nQuery Strategy Summary:")
    print("  * Default: Searches all tiers, merges results")
    print("  * Specific tier: tiers=['tier_name']")
    print("  * Multi-tier subset: tiers=['tier1', 'tier2']")
    print("  * Results ranked by relevance + importance")
    print("  * No automatic deduplication across tiers")
    print("  * Choose strategy based on:")
    print("    - Query scope requirements")
    print("    - Performance needs")
    print("    - Data location knowledge")


if __name__ == "__main__":
    asyncio.run(main())
