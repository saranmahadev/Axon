"""
Understanding Memory Tiers

Learn about the three-tier architecture in Axon: ephemeral, session, and
persistent tiers. Understand when and how to use each tier effectively.

Learn:
- Ephemeral tier: short-lived, high-throughput cache
- Session tier: medium-term, session-scoped storage
- Persistent tier: long-term, durable semantic storage
- Automatic tier selection based on importance
- Explicit tier specification
- Tier characteristics and trade-offs

Run:
    python 01_understanding_tiers.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    """Demonstrate the three-tier memory architecture."""
    print("=== Understanding Memory Tiers ===\n")

    # Create memory system with all three tiers
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("Memory System Configuration:")
    print("-" * 50)
    print(f"Tiers available: {list(memory.config.tiers.keys())}")
    print(f"Default tier: {memory.config.default_tier}")
    print()

    # 1. EPHEMERAL TIER - Temporary, high-speed cache
    print("1. EPHEMERAL TIER - Temporary Cache")
    print("-" * 50)
    print("Characteristics:")
    print("  * Short TTL (seconds to minutes)")
    print("  * High throughput, minimal latency")
    print("  * Auto-expires after TTL")
    print("  * Best for: caching, temporary data, rate limiting")
    print()

    # Store in ephemeral tier
    ephemeral_entries = []
    for i in range(3):
        entry_id = await memory.store(
            f"Recent search query: Python tutorial part {i+1}",
            importance=0.2,  # Low importance
            tier="ephemeral",  # Explicit tier
            tags=["cache", "search"]
        )
        ephemeral_entries.append(entry_id)
        print(f"  OK Stored ephemeral: {entry_id}")

    print()

    # 2. SESSION TIER - Medium-term, session-scoped
    print("2. SESSION TIER - Session Storage")
    print("-" * 50)
    print("Characteristics:")
    print("  * Medium TTL (minutes to hours)")
    print("  * Session-scoped context")
    print("  * Can overflow to persistent")
    print("  * Best for: conversation history, user sessions, drafts")
    print()

    # Store in session tier
    session_entries = []
    for i in range(3):
        entry_id = await memory.store(
            f"User working on task: Write documentation section {i+1}",
            importance=0.5,  # Medium importance
            tier="session",  # Explicit tier
            tags=["session", "task"],
            metadata={"session_id": "session_abc123"}
        )
        session_entries.append(entry_id)
        print(f"  OK Stored session: {entry_id}")

    print()

    # 3. PERSISTENT TIER - Long-term, durable storage
    print("3. PERSISTENT TIER - Long-term Storage")
    print("-" * 50)
    print("Characteristics:")
    print("  * No TTL (permanent until deleted)")
    print("  * Vector search enabled")
    print("  * Supports compaction and summarization")
    print("  * Best for: user preferences, knowledge base, facts")
    print()

    # Store in persistent tier
    persistent_entries = []
    for i in range(3):
        entry_id = await memory.store(
            f"User preference: Always use {['dark mode', 'monospace font', 'auto-save'][i]}",
            importance=0.8,  # High importance
            tier="persistent",  # Explicit tier
            tags=["preferences", "permanent"]
        )
        persistent_entries.append(entry_id)
        print(f"  OK Stored persistent: {entry_id}")

    print()

    # 4. Automatic tier selection based on importance
    print("4. AUTOMATIC TIER SELECTION")
    print("-" * 50)
    print("When tier is not specified, Axon automatically selects based on importance:")
    print()

    test_cases = [
        ("Temporary debug log message", 0.1, "ephemeral"),
        ("User's current draft message", 0.5, "session"),
        ("Critical API credentials", 0.95, "persistent"),
    ]

    for content, importance, expected_tier in test_cases:
        entry_id = await memory.store(content, importance=importance)
        print(f"  Importance {importance} -> {expected_tier} tier")
        print(f"    Content: {content[:40]}...")

    print()

    # 5. Querying specific tiers
    print("5. QUERYING SPECIFIC TIERS")
    print("-" * 50)

    # Query ephemeral only
    ephemeral_results = await memory.recall("search", k=10, tiers=["ephemeral"])
    print(f"  Ephemeral tier: {len(ephemeral_results)} entries")
    for entry in ephemeral_results:
        print(f"    - {entry.text[:50]}...")

    print()

    # Query session only
    session_results = await memory.recall("task", k=10, tiers=["session"])
    print(f"  Session tier: {len(session_results)} entries")
    for entry in session_results:
        print(f"    - {entry.text[:50]}...")

    print()

    # Query persistent only
    persistent_results = await memory.recall("preference", k=10, tiers=["persistent"])
    print(f"  Persistent tier: {len(persistent_results)} entries")
    for entry in persistent_results:
        print(f"    - {entry.text[:50]}...")

    print()

    # 6. Multi-tier search (default behavior)
    print("6. MULTI-TIER SEARCH")
    print("-" * 50)
    print("Default behavior: searches ALL tiers and merges results")
    print()

    all_results = await memory.recall("user", k=10)
    print(f"  Found {len(all_results)} total results across all tiers")

    # Group by tier (if we had tier info in metadata)
    print()

    # 7. Tier statistics
    print("7. TIER STATISTICS")
    print("-" * 50)

    stats = memory.get_statistics()

    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"\n  {tier_name.upper()} tier:")
        print(f"    Store operations: {tier_stats.get('stores', 0)}")
        print(f"    Recall operations: {tier_stats.get('recalls', 0)}")

    print()

    # 8. Tier configuration details
    print("8. TIER CONFIGURATION DETAILS")
    print("-" * 50)

    for tier_name, policy in memory.config.tiers.items():
        print(f"\n  {tier_name.upper()}:")
        print(f"    Adapter: {policy.adapter_type}")
        print(f"    TTL: {policy.ttl_seconds}s" if policy.ttl_seconds else "    TTL: None (permanent)")
        if hasattr(policy, 'max_entries'):
            print(f"    Max entries: {policy.max_entries}")
        if hasattr(policy, 'compaction_threshold'):
            print(f"    Compaction threshold: {policy.compaction_threshold}")

    print()

    print("=" * 50)
    print("* Successfully demonstrated memory tiers!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * Ephemeral: Fast cache for temporary data")
    print("  * Session: Medium-term session-scoped storage")
    print("  * Persistent: Long-term durable semantic storage")
    print("  * Automatic tier selection based on importance")
    print("  * Explicit tier control with tier= parameter")
    print("  * Query specific tiers or search across all")
    print("  * Each tier has different TTL and characteristics")


if __name__ == "__main__":
    asyncio.run(main())
