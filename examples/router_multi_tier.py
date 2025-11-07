"""
Example: Multi-Tier Querying and Memory Lifecycle

This example demonstrates:
- Querying specific tiers vs. all tiers
- Memory lifecycle across different tiers
- How tier selection affects recall performance
- Managing memories as they transition between tiers

Understanding multi-tier architecture helps optimize memory retrieval
and storage costs in production systems.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.core.router import Router
from axon.models.entry import MemoryEntry, MemoryMetadata


def create_mock_config():
    """Create configuration with all three tiers."""
    config = Mock(spec=MemoryConfig)
    config.tiers = {
        "ephemeral": EphemeralPolicy(adapter_type="memory", max_entries=10, ttl_seconds=60),
        "session": SessionPolicy(adapter_type="memory", max_entries=50, ttl_seconds=3600),
        "persistent": PersistentPolicy(adapter_type="memory", max_entries=1000),
    }
    return config


def create_mock_registry_with_storage():
    """Create registry with visible storage tracking."""
    registry = Mock(spec=AdapterRegistry)

    # Shared storage for demonstration
    storage = {"ephemeral": {}, "session": {}, "persistent": {}}

    async def mock_get_adapter(tier):
        adapter = AsyncMock()

        async def save(entry):
            storage[tier][entry.id] = entry
            return entry.id

        adapter.save = AsyncMock(side_effect=save)

        async def query(query_text, k=5, filter=None):
            results = []
            for entry in storage[tier].values():
                if not query_text or query_text.lower() in entry.text.lower():
                    results.append(entry)
            return results[:k]

        adapter.query = AsyncMock(side_effect=query)

        async def delete(entry_id=None, filter=None):
            if entry_id and entry_id in storage[tier]:
                del storage[tier][entry_id]
                return 1
            return 0

        adapter.delete = AsyncMock(side_effect=delete)

        return adapter

    registry.get_adapter = AsyncMock(side_effect=mock_get_adapter)
    registry.get_all_tiers = Mock(return_value=["ephemeral", "session", "persistent"])
    registry._storage = storage  # Expose for demonstration

    return registry


def create_memory(entry_id: str, text: str, importance: float):
    """Create a memory entry."""
    return MemoryEntry(
        id=entry_id,
        text=text,
        metadata=MemoryMetadata(importance=importance, created_at=datetime.now()),
    )


async def main():
    """Demonstrate multi-tier querying and memory lifecycle."""

    print("=" * 70)
    print("AXON ROUTER - MULTI-TIER QUERYING EXAMPLE")
    print("=" * 70)

    # Initialize Router
    config = create_mock_config()
    registry = create_mock_registry_with_storage()
    router = Router(config=config, registry=registry)

    print("\n1. POPULATING DIFFERENT TIERS")
    print("-" * 70)

    # Store memories in different tiers based on importance
    memories = [
        # Ephemeral tier (importance < 0.3)
        ("temp-1", "Temporary calculation result: 42", 0.1),
        ("temp-2", "Current cursor position: line 25", 0.15),
        # Session tier (0.3 ≤ importance < 0.7)
        ("session-1", "User is debugging authentication module", 0.5),
        ("session-2", "Current conversation about async programming", 0.4),
        ("session-3", "Working directory: /home/user/projects", 0.35),
        # Persistent tier (importance ≥ 0.7)
        ("persist-1", "User's preferred programming language: Python", 0.9),
        ("persist-2", "Project goals: Build ML-powered chatbot", 0.85),
        ("persist-3", "User expertise: Senior developer, 10+ years", 0.95),
    ]

    for entry_id, text, importance in memories:
        memory = create_memory(entry_id, text, importance)
        tier = await router.select_tier(memory)
        await router.route_store(memory)
        print(f"  {tier:12} ← [{entry_id}] (importance: {importance})")

    print(f"\nTotal memories stored: {len(memories)}")

    # Show tier distribution
    print("\nTier Distribution:")
    for tier, storage in registry._storage.items():
        print(f"  {tier:12}: {len(storage)} memories")

    print("\n2. QUERYING ALL TIERS (DEFAULT)")
    print("-" * 70)
    print("By default, recall searches across all tiers:\n")

    query = "user"
    print(f"Query: '{query}'")
    all_results = await router.route_recall(query, k=10)

    print(f"\nFound {len(all_results)} result(s) across all tiers:")
    for result in all_results:
        print(f"  • [{result.id}] {result.text[:50]}...")

    print("\n3. QUERYING SPECIFIC TIERS")
    print("-" * 70)
    print("Query only specific tiers for targeted retrieval:\n")

    # Query only persistent tier
    print("A. Querying PERSISTENT tier only:")
    persistent_results = await router.route_recall("user", k=10, tiers=["persistent"])
    print(f"   Found {len(persistent_results)} result(s)")
    for result in persistent_results:
        print(f"   • [{result.id}] {result.text[:50]}...")

    # Query session tier only
    print("\nB. Querying SESSION tier only:")
    session_results = await router.route_recall("current", k=10, tiers=["session"])
    print(f"   Found {len(session_results)} result(s)")
    for result in session_results:
        print(f"   • [{result.id}] {result.text[:50]}...")

    # Query multiple specific tiers
    print("\nC. Querying SESSION + PERSISTENT tiers:")
    multi_tier_results = await router.route_recall(
        "", k=10, tiers=["session", "persistent"]  # Empty query returns all
    )
    print(f"   Found {len(multi_tier_results)} result(s)")

    print("\n4. MEMORY LIFECYCLE DEMONSTRATION")
    print("-" * 70)
    print("Memories can be moved between tiers as needed:\n")

    print("Scenario: Temporary data becomes important\n")

    # Initially store as ephemeral
    temp_memory = create_memory(
        "lifecycle-1", "Code snippet: async def process_data()", importance=0.2
    )

    print("1. Store as ephemeral (low importance):")
    await router.route_store(temp_memory)
    print("   Tier: ephemeral")

    # Later, realize it's important - store in persistent
    print("\n2. User finds it useful - promote to persistent:")
    temp_memory.metadata.importance = 0.9  # Update importance
    await router.route_store(temp_memory, tier="persistent")
    print("   Tier: persistent (explicit)")

    # Clean up from ephemeral
    print("\n3. Clean up from ephemeral tier:")
    await router.route_forget(entry_id="lifecycle-1", tier="ephemeral")
    print("   Removed from ephemeral")

    print("\n5. TIER-SPECIFIC FORGETTING")
    print("-" * 70)
    print("Remove memories from specific tiers:\n")

    print("Clearing ephemeral tier (temporary data):")
    for entry_id in list(registry._storage["ephemeral"].keys()):
        await router.route_forget(entry_id=entry_id, tier="ephemeral")
        print(f"  ✓ Removed {entry_id}")

    print(f"\nEphemeral tier now has: {len(registry._storage['ephemeral'])} memories")

    print("\n6. STATISTICS AFTER OPERATIONS")
    print("-" * 70)

    stats = router.get_tier_stats()
    for tier, tier_stats in stats.items():
        print(f"\n{tier.upper()}:")
        print(f"  Stores:  {tier_stats['stores']}")
        print(f"  Recalls: {tier_stats['recalls']}")
        print(f"  Forgets: {tier_stats['forgets']}")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • All-tier queries provide comprehensive results")
    print("  • Specific-tier queries optimize for performance/cost")
    print("  • Memories can be moved between tiers as importance changes")
    print("  • Tier-specific forget operations enable targeted cleanup")
    print("  • Use session tier for conversation context")
    print("  • Use persistent tier for long-term knowledge")
    print("  • Use ephemeral tier for temporary computations")
    print()


if __name__ == "__main__":
    asyncio.run(main())
