"""
Overflow Policies

Learn how to configure overflow behavior when tiers reach capacity,
including overflow-to-persistent and eviction strategies.

Learn:
- overflow_to_persistent setting
- Capacity management
- Eviction strategies
- Overflow triggers
- Preventing data loss

Run:
    python 03_overflow_policies.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate overflow policy configuration."""
    print("=== Overflow Policies ===\n")

    # 1. Session policy with overflow enabled
    print("1. Configure overflow-to-persistent")
    print("-" * 50)

    config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=600,
            max_entries=10,  # Minimum capacity for demonstration
            overflow_to_persistent=True,  # Enable overflow
            enable_vector_search=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None
        ),
        default_tier="session"
    )

    print(f"  Session max_entries: 10")
    print(f"  Overflow to persistent: True")
    print()

    memory = MemorySystem(config)

    # 2. Fill session to capacity
    print("2. Fill session tier to capacity")
    print("-" * 50)

    for i in range(10):
        entry_id = await memory.store(
            f"Session entry {i+1}: User activity",
            tier="session",
            importance=0.6,
            tags=["session"]
        )
        print(f"  OK Entry {i+1}/10 stored")

    print("\n  Session tier at capacity (10/10)")
    print()

    # 3. Trigger overflow
    print("3. Store beyond capacity (triggers overflow)")
    print("-" * 50)

    for i in range(3):
        entry_id = await memory.store(
            f"Overflow entry {i+1}: Additional data",
            tier="session",
            importance=0.7,
            tags=["session", "overflow"]
        )
        print(f"  OK Overflow entry {i+1} stored")

    print()

    # 4. Check distribution
    print("4. Verify tier distribution")
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

    # 5. Overflow vs. Eviction
    print("5. Overflow vs. Eviction Strategies")
    print("-" * 50)
    print()

    print("  WITH overflow_to_persistent=True:")
    print("    * Entries move to persistent tier")
    print("    * No data loss")
    print("    * Persistent tier must have capacity")
    print("    * Good for: Important session data")
    print()

    print("  WITHOUT overflow (eviction only):")
    print("    * Oldest/lowest importance entries deleted")
    print("    * Potential data loss")
    print("    * Keeps tier within bounds")
    print("    * Good for: Truly temporary data")
    print()

    # 6. Overflow configuration examples
    print("6. Overflow Configuration Patterns")
    print("-" * 50)
    print()

    # Chatbot with overflow
    print("  Pattern 1: Chatbot with Overflow")
    chatbot_config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=3600,  # 1 hour
            max_entries=100,
            overflow_to_persistent=True  # Save important context
        ),
        persistent=PersistentPolicy(adapter_type="memory"),
        default_tier="session"
    )
    print("    Session: 100 entries, 1hr TTL, overflow enabled")
    print("    Use: Long conversations with context preservation")
    print()

    # Cache without overflow
    print("  Pattern 2: Pure Cache (No Overflow)")
    cache_config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=300,  # 5 minutes
            max_entries=1000,
            overflow_to_persistent=False  # Just evict
        ),
        persistent=PersistentPolicy(adapter_type="memory"),
        default_tier="session"
    )
    print("    Session: 1000 entries, 5min TTL, no overflow")
    print("    Use: High-throughput caching")
    print()

    # 7. Monitoring overflow
    print("7. Monitor Overflow Events")
    print("-" * 50)

    stats = memory.get_statistics()

    print(f"\n  Total operations:")
    print(f"    Stores: {stats['total_operations']['stores']}")
    print(f"    Recalls: {stats['total_operations']['recalls']}")
    print()

    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"  {tier_name.upper()} tier:")
        print(f"    Stores: {tier_stats.get('stores', 0)}")

    print()

    # 8. Best practices
    print("8. Overflow Best Practices")
    print("-" * 50)
    print()
    print("  1. Set realistic max_entries:")
    print("     - Consider memory limits")
    print("     - Account for peak usage")
    print()
    print("  2. Enable overflow for important data:")
    print("     - Conversation history")
    print("     - User state")
    print("     - Work in progress")
    print()
    print("  3. Disable overflow for temporary data:")
    print("     - Caches")
    print("     - Rate limit tokens")
    print("     - Temporary flags")
    print()
    print("  4. Monitor persistent tier capacity:")
    print("     - Overflow can fill persistent quickly")
    print("     - Enable compaction on persistent")
    print()

    print("=" * 50)
    print("* Successfully demonstrated overflow policies!")
    print("=" * 50)
    print("\nOverflow Summary:")
    print("  * overflow_to_persistent moves entries to next tier")
    print("  * Prevents data loss when session fills up")
    print("  * Alternative: Eviction (delete oldest/lowest priority)")
    print("  * Enable for important session data")
    print("  * Disable for pure caching scenarios")
    print("  * Monitor both session and persistent capacity")


if __name__ == "__main__":
    asyncio.run(main())
