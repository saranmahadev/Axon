"""
Custom Policy Configuration

Learn how to create custom policies for each tier to precisely control
memory behavior, TTL, capacity, overflow, and compaction settings.

Learn:
- Creating custom EphemeralPolicy
- Creating custom SessionPolicy
- Creating custom PersistentPolicy
- Combining policies in MemoryConfig
- Policy constraints and validation
- Policy templates vs custom policies

Run:
    python 01_custom_policies.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate custom policy configuration."""
    print("=== Custom Policy Configuration ===\n")

    # 1. Custom Ephemeral Policy
    print("1. Custom Ephemeral Policy")
    print("-" * 50)

    ephemeral_policy = EphemeralPolicy(
        adapter_type="memory",  # "redis" or "memory"
        ttl_seconds=30,  # 30 seconds (5s to 1hr allowed)
    )

    print(f"  Adapter: {ephemeral_policy.adapter_type}")
    print(f"  TTL: {ephemeral_policy.ttl_seconds}s")
    print(f"  Eviction: {ephemeral_policy.eviction_strategy}")
    print(f"  Vector search: {ephemeral_policy.enable_vector_search}")
    print()

    # 2. Custom Session Policy
    print("2. Custom Session Policy")
    print("-" * 50)

    session_policy = SessionPolicy(
        adapter_type="memory",  # redis, memory, chroma, qdrant, pinecone
        ttl_seconds=900,  # 15 minutes
        max_entries=500,  # Maximum 500 entries
        overflow_to_persistent=True,  # Overflow to persistent when full
        enable_vector_search=True  # Enable semantic search
    )

    print(f"  Adapter: {session_policy.adapter_type}")
    print(f"  TTL: {session_policy.ttl_seconds}s ({session_policy.ttl_seconds // 60} minutes)")
    print(f"  Max entries: {session_policy.max_entries}")
    print(f"  Overflow to persistent: {session_policy.overflow_to_persistent}")
    print(f"  Vector search: {session_policy.enable_vector_search}")
    print()

    # 3. Custom Persistent Policy
    print("3. Custom Persistent Policy")
    print("-" * 50)

    persistent_policy = PersistentPolicy(
        adapter_type="memory",  # chroma, qdrant, pinecone, memory
        ttl_seconds=None,  # No expiration
        compaction_threshold=5000,  # Compact when > 5000 entries
        compaction_strategy="importance",  # importance, semantic, count, hybrid
    )

    print(f"  Adapter: {persistent_policy.adapter_type}")
    print(f"  TTL: {persistent_policy.ttl_seconds} (permanent)")
    print(f"  Compaction threshold: {persistent_policy.compaction_threshold}")
    print(f"  Compaction strategy: {persistent_policy.compaction_strategy}")
    print()

    # 4. Create MemoryConfig with custom policies
    print("4. Combine policies in MemoryConfig")
    print("-" * 50)

    config = MemoryConfig(
        ephemeral=ephemeral_policy,
        session=session_policy,
        persistent=persistent_policy,
        default_tier="session",  # Default tier for auto-routing
        enable_promotion=True,  # Enable automatic tier promotion
        enable_demotion=False  # Disable demotion
    )

    print(f"  Tiers configured: {list(config.tiers.keys())}")
    print(f"  Default tier: {config.default_tier}")
    print(f"  Promotion enabled: {config.enable_promotion}")
    print(f"  Demotion enabled: {config.enable_demotion}")
    print()

    # 5. Create MemorySystem with custom config
    print("5. Create MemorySystem with custom config")
    print("-" * 50)

    memory = MemorySystem(config)

    print(f"  OK MemorySystem initialized")
    print(f"  Tiers available: {list(memory.config.tiers.keys())}")
    print()

    # 6. Test custom policies in action
    print("6. Test custom policies")
    print("-" * 50)

    # Store with auto-routing (uses default_tier)
    entry1 = await memory.store(
        "Test message: checking default tier routing",
        importance=0.5
    )
    print(f"  OK Auto-routed to default tier (session)")

    # Store to specific tier
    entry2 = await memory.store(
        "Temporary cache data",
        tier="ephemeral"
    )
    print(f"  OK Stored to ephemeral (30s TTL)")

    # Store to persistent
    entry3 = await memory.store(
        "Important knowledge: Python is dynamically typed",
        importance=0.9,
        tier="persistent"
    )
    print(f"  OK Stored to persistent (permanent)")
    print()

    # 7. Policy validation examples
    print("7. Policy Validation")
    print("-" * 50)
    print("Policies have built-in validation:")
    print()

    # Valid ephemeral TTL range
    print("  Ephemeral TTL constraints:")
    print("    OK Valid: 5s to 3600s (1 hour)")
    print("    X Invalid: < 5s or > 3600s")

    try:
        invalid = EphemeralPolicy(ttl_seconds=2)  # Too short
    except ValueError as e:
        print(f"    Error: {e}")

    print()

    # Session max_entries constraint
    print("  Session max_entries constraints:")
    print("    OK Valid: >= 10 entries")
    print("    X Invalid: < 10 entries")

    try:
        invalid = SessionPolicy(max_entries=5)  # Too small
    except ValueError as e:
        print(f"    Error: {e}")

    print()

    # 8. Use case examples
    print("8. Common Policy Configurations")
    print("-" * 50)
    print()

    # High-throughput caching
    print("  Use Case: High-Throughput Caching")
    cache_config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",
            ttl_seconds=60  # 1 minute
        ),
        persistent=PersistentPolicy(adapter_type="memory"),
        default_tier="ephemeral"
    )
    print("    Config: Ephemeral (60s TTL) + Persistent")
    print()

    # Long conversation history
    print("  Use Case: Long Conversation History")
    chat_config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=7200,  # 2 hours
            max_entries=2000,
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=10000
        ),
        default_tier="session"
    )
    print("    Config: Session (2hr, 2000 entries) + Overflow + Persistent")
    print()

    # Knowledge base only
    print("  Use Case: Knowledge Base (Persistent Only)")
    kb_config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=50000,
            compaction_strategy="semantic"
        ),
        default_tier="persistent"
    )
    print("    Config: Persistent only, semantic compaction at 50k entries")
    print()

    print("=" * 50)
    print("* Successfully demonstrated custom policies!")
    print("=" * 50)
    print("\nPolicy Summary:")
    print("  * EphemeralPolicy: Short-lived (5s-1hr), redis/memory")
    print("  * SessionPolicy: Medium-term (>=60s), any adapter")
    print("  * PersistentPolicy: Long-term (no TTL), vector DBs")
    print("  * Policies enforce constraints via validation")
    print("  * Combine in MemoryConfig to build custom systems")
    print("  * Choose policies based on use case requirements")


if __name__ == "__main__":
    asyncio.run(main())
