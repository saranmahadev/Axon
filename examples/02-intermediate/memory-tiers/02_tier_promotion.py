"""
Tier Promotion - Automatic Memory Upgrading

Learn how memories are automatically promoted to higher tiers based on
access patterns, importance scores, and usage frequency.

Learn:
- Access-based promotion logic
- Importance score thresholds
- Promotion scoring algorithm
- Manual promotion via sync()
- Promotion triggers and conditions
- Monitoring promotion events

Run:
    python 02_tier_promotion.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate tier promotion mechanisms."""
    print("=== Tier Promotion Mechanics ===\n")

    # Create config with promotion enabled
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",
            ttl_seconds=60,
            max_entries=50
        ),
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=600,
            max_entries=100,
            overflow_to_persistent=True,
            enable_vector_search=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None,
            compaction_threshold=1000
        ),
        enable_promotion=True,  # Enable automatic promotion
        default_tier="ephemeral"
    )

    memory = MemorySystem(config)

    print("Configuration:")
    print("-" * 50)
    print(f"Promotion enabled: {config.enable_promotion}")
    print(f"Default tier: {config.default_tier}")
    print()

    # 1. Store memories in ephemeral tier
    print("1. Store memories in ephemeral tier")
    print("-" * 50)

    entry_ids = []
    for i in range(5):
        entry_id = await memory.store(
            f"Important fact #{i+1}: Python is a dynamic language",
            importance=0.6,  # Medium importance
            tier="ephemeral",
            tags=["facts", "python"]
        )
        entry_ids.append(entry_id)
        print(f"  OK Stored in ephemeral: {entry_id}")

    print()

    # 2. Access patterns trigger promotion
    print("2. Frequent access triggers promotion consideration")
    print("-" * 50)
    print("Accessing the same memory multiple times...")
    print()

    # Access one memory repeatedly
    target_query = "Important fact #1"

    for access_num in range(5):
        results = await memory.recall(target_query, k=1, tiers=["ephemeral"])
        if results:
            entry = results[0]
            print(f"  Access {access_num + 1}:")
            print(f"    Access count: {entry.metadata.access_count}")
            print(f"    Importance: {entry.metadata.importance}")

    print()
    print("  Note: High access count increases promotion score")
    print()

    # 3. Promotion scoring factors
    print("3. Promotion Scoring Factors")
    print("-" * 50)
    print("Factors that influence promotion:")
    print("  1. Access frequency (number of recalls)")
    print("  2. Recency of access (recent = higher score)")
    print("  3. Base importance score (0.0-1.0)")
    print("  4. Session continuity (same session = higher score)")
    print()
    print("Formula: score = weighted sum of above factors")
    print("When score exceeds threshold -> promote to next tier")
    print()

    # 4. Manual promotion via sync
    print("4. Manual promotion via sync()")
    print("-" * 50)

    # Promote high-importance ephemeral to session
    from axon.models.filter import Filter

    stats = await memory.sync(
        source_tier="ephemeral",
        target_tier="session",
        filter=Filter(min_importance=0.5),
        delete_source=False  # Keep in ephemeral too
    )

    print(f"  Manual promotion results:")
    print(f"    Promoted: {stats['synced']} entries")
    print(f"    From: ephemeral -> session")
    print()

    # 5. Verify promotion
    print("5. Verify promotion results")
    print("-" * 50)

    session_results = await memory.recall("Important fact", k=10, tiers=["session"])
    ephemeral_results = await memory.recall("Important fact", k=10, tiers=["ephemeral"])

    print(f"  Session tier now has: {len(session_results)} entries")
    print(f"  Ephemeral tier still has: {len(ephemeral_results)} entries")
    print()

    # 6. Importance-based automatic selection
    print("6. Importance-based automatic tier selection")
    print("-" * 50)
    print("Storing with different importance scores...")
    print()

    test_cases = [
        ("Low importance note", 0.2, "ephemeral"),
        ("Medium importance task", 0.5, "session"),
        ("High importance credential", 0.9, "persistent"),
    ]

    for content, importance, expected in test_cases:
        await memory.store(content, importance=importance)
        print(f"  Importance {importance} -> likely stored in {expected}")

    print()

    # 7. Session continuity promotes retention
    print("7. Session continuity")
    print("-" * 50)

    session_id = "user_session_abc123"

    # Store multiple related memories in same session
    for i in range(3):
        await memory.store(
            f"Step {i+1}: User completed onboarding task",
            importance=0.6,
            tier="session",
            metadata={"session_id": session_id},
            tags=["onboarding", "session"]
        )

    print(f"  OK Stored 3 memories in session '{session_id}'")
    print(f"  Session continuity increases promotion likelihood")
    print()

    # 8. Monitoring promotion candidates
    print("8. Identifying promotion candidates")
    print("-" * 50)

    # Query ephemeral tier for high-value entries
    candidates = await memory.recall(
        "",
        k=100,
        tiers=["ephemeral"],
        filter=Filter(min_importance=0.5)
    )

    print(f"  Found {len(candidates)} promotion candidates in ephemeral:")
    for entry in candidates[:5]:  # Show first 5
        print(f"    - {entry.text[:40]}...")
        print(f"      Importance: {entry.metadata.importance}")
        print(f"      Access count: {entry.metadata.access_count}")

    print()

    # 9. Tier statistics after promotion
    print("9. System statistics")
    print("-" * 50)

    stats = memory.get_statistics()

    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"\n  {tier_name.upper()} tier:")
        print(f"    Stores: {tier_stats.get('stores', 0)}")
        print(f"    Recalls: {tier_stats.get('recalls', 0)}")

    print()

    print("=" * 50)
    print("* Successfully demonstrated tier promotion!")
    print("=" * 50)
    print("\nPromotion Summary:")
    print("  * Automatic promotion based on:")
    print("    - Access frequency")
    print("    - Recency of access")
    print("    - Base importance")
    print("    - Session continuity")
    print("  * Manual promotion via sync()")
    print("  * Promotion tiers: ephemeral -> session -> persistent")
    print("  * Monitor candidates via filters")
    print("  * Configure thresholds in ScoringEngine")


if __name__ == "__main__":
    asyncio.run(main())
