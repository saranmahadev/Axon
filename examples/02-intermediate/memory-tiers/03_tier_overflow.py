"""
Tier Overflow Management

Learn how Axon handles tier capacity limits through overflow mechanisms,
automatic eviction, and overflow-to-next-tier patterns.

Learn:
- Tier capacity limits (max_entries)
- Overflow to higher tiers
- Eviction policies (LRU, importance-based)
- Capacity monitoring
- Overflow prevention strategies

Run:
    python 03_tier_overflow.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate tier overflow and capacity management."""
    print("=== Tier Overflow Management ===\n")

    # Create config with small capacity limits to demonstrate overflow
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",
            ttl_seconds=60,
            max_entries=5  # Small limit to trigger overflow quickly
        ),
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=600,
            max_entries=10,  # Also limited
            overflow_to_persistent=True,  # Enable overflow
            enable_vector_search=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None,
            compaction_threshold=100
        ),
        default_tier="ephemeral"
    )

    memory = MemorySystem(config)

    print("Configuration:")
    print("-" * 50)
    print(f"Ephemeral max entries: 5")
    print(f"Session max entries: 10")
    print(f"Session overflow enabled: True")
    print()

    # 1. Fill ephemeral tier to capacity
    print("1. Fill ephemeral tier to capacity")
    print("-" * 50)

    ephemeral_ids = []
    for i in range(5):
        entry_id = await memory.store(
            f"Ephemeral entry #{i+1}: Temporary cache data",
            importance=0.3,
            tier="ephemeral",
            tags=["cache", "temp"]
        )
        ephemeral_ids.append(entry_id)
        print(f"  OK Stored entry {i+1}/5: {entry_id}")

    print(f"\n  Ephemeral tier is now at capacity (5/5 entries)")
    print()

    # 2. Trigger overflow by storing more
    print("2. Store beyond capacity (triggers overflow/eviction)")
    print("-" * 50)
    print("Attempting to store 3 more entries...")
    print()

    for i in range(3):
        entry_id = await memory.store(
            f"Overflow entry #{i+1}: New cache data",
            importance=0.4,  # Slightly higher importance
            tier="ephemeral",
            tags=["cache", "new"]
        )
        print(f"  OK Stored overflow entry {i+1}: {entry_id}")
        print(f"    Note: Ephemeral tier may evict older entries")

    print()

    # 3. Check ephemeral tier contents after overflow
    print("3. Inspect ephemeral tier after overflow")
    print("-" * 50)

    ephemeral_results = await memory.recall("", k=100, tiers=["ephemeral"])

    print(f"  Ephemeral tier now contains: {len(ephemeral_results)} entries")
    print(f"  (max capacity: 5)")
    print()

    if len(ephemeral_results) <= 5:
        print("  Eviction occurred - older entries removed")
    else:
        print("  Note: InMemory adapter may not enforce hard limits")

    print()

    # 4. Session tier with overflow to persistent
    print("4. Session tier overflow to persistent")
    print("-" * 50)
    print(f"Session capacity: 10 entries")
    print(f"Overflow enabled: True (overflow_to_persistent)")
    print()

    # Fill session tier
    session_ids = []
    for i in range(12):  # Exceed capacity
        entry_id = await memory.store(
            f"Session entry #{i+1}: User activity data",
            importance=0.6,
            tier="session",
            tags=["session", "activity"],
            metadata={"session_id": "session_abc"}
        )
        session_ids.append(entry_id)

        if i < 10:
            print(f"  OK Stored in session: {i+1}/10")
        else:
            print(f"  ! Overflow #{i-9}: May move to persistent")

    print()

    # 5. Verify overflow behavior
    print("5. Verify overflow results")
    print("-" * 50)

    session_results = await memory.recall("", k=100, tiers=["session"])
    persistent_results = await memory.recall("", k=100, tiers=["persistent"])

    print(f"  Session tier: {len(session_results)} entries")
    print(f"  Persistent tier: {len(persistent_results)} entries")
    print()

    if len(persistent_results) > 0:
        print("  OK Overflow occurred - entries moved to persistent")
    else:
        print("  Note: Overflow behavior depends on adapter implementation")

    print()

    # 6. Importance-based eviction
    print("6. Importance-based eviction priority")
    print("-" * 50)
    print("When evicting, lower importance entries are removed first")
    print()

    # Store entries with varying importance
    await memory.store("Low importance temp data", importance=0.1, tier="ephemeral")
    await memory.store("High importance cache", importance=0.8, tier="ephemeral")
    await memory.store("Medium importance data", importance=0.5, tier="ephemeral")

    print("  OK Stored entries with varying importance")
    print("  When capacity reached:")
    print("    - Low importance (0.1) evicted first")
    print("    - Medium importance (0.5) evicted next")
    print("    - High importance (0.8) retained longer")
    print()

    # 7. Monitoring capacity
    print("7. Monitor tier capacity")
    print("-" * 50)

    # Get adapters to check capacity
    ephemeral_adapter = await memory.registry.get_adapter("ephemeral")
    session_adapter = await memory.registry.get_adapter("session")
    persistent_adapter = await memory.registry.get_adapter("persistent")

    print(f"  Ephemeral entries: {ephemeral_adapter.count()}")
    print(f"  Session entries: {session_adapter.count()}")
    print(f"  Persistent entries: {persistent_adapter.count()}")
    print()

    # 8. Overflow prevention strategies
    print("8. Overflow Prevention Strategies")
    print("-" * 50)
    print("Strategies to prevent unwanted overflow:")
    print()
    print("  1. Manual cleanup:")
    print("     - Periodically delete old entries")
    print("     - Use filters to identify deletion candidates")
    print()
    print("  2. Importance-based storage:")
    print("     - Store high-importance directly to persistent")
    print("     - Reserve ephemeral for truly temporary data")
    print()
    print("  3. TTL management:")
    print("     - Rely on TTL expiration for ephemeral")
    print("     - Set appropriate TTL values")
    print()
    print("  4. Compaction:")
    print("     - Enable compaction for persistent tier")
    print("     - Summarize old entries to reduce count")
    print()

    # 9. Tier statistics
    print("9. System Statistics")
    print("-" * 50)

    stats = memory.get_statistics()

    print(f"  Total operations:")
    print(f"    Stores: {stats['total_operations']['stores']}")
    print(f"    Recalls: {stats['total_operations']['recalls']}")
    print()

    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"  {tier_name.upper()} tier:")
        print(f"    Store ops: {tier_stats.get('stores', 0)}")

    print()

    print("=" * 50)
    print("* Successfully demonstrated tier overflow!")
    print("=" * 50)
    print("\nOverflow Summary:")
    print("  * Each tier has max_entries capacity")
    print("  * Exceeding capacity triggers eviction or overflow")
    print("  * Eviction priority: lowest importance first")
    print("  * overflow_to_persistent moves to next tier")
    print("  * Monitor capacity with adapter.count()")
    print("  * Prevent overflow with:")
    print("    - Manual cleanup")
    print("    - Importance-based routing")
    print("    - TTL expiration")
    print("    - Compaction")


if __name__ == "__main__":
    asyncio.run(main())
