"""
Example: Basic Router Usage

This example demonstrates the fundamental operations of the Router:
- Storing memories in appropriate tiers
- Recalling memories with semantic search
- Forgetting memories when no longer needed
- Monitoring tier statistics

The Router automatically selects the appropriate tier (ephemeral, session,
persistent) based on memory importance and configured policies.
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
    """Create a mock configuration for the Router."""
    config = Mock(spec=MemoryConfig)
    config.tiers = {
        "ephemeral": EphemeralPolicy(
            adapter_type="memory", max_entries=10, ttl_seconds=60  # 1 minute TTL
        ),
        "session": SessionPolicy(
            adapter_type="memory", max_entries=50, ttl_seconds=3600  # 1 hour TTL
        ),
        "persistent": PersistentPolicy(adapter_type="memory", max_entries=1000),
    }
    return config


def create_mock_registry():
    """Create a mock adapter registry with simulated storage."""
    registry = Mock(spec=AdapterRegistry)

    # Simulated storage for each tier
    storage = {"ephemeral": {}, "session": {}, "persistent": {}}

    async def mock_get_adapter(tier):
        adapter = AsyncMock()

        # Mock save operation
        async def save(entry):
            storage[tier][entry.id] = entry
            print(f"  ✓ Saved to {tier}: '{entry.text[:50]}...'")
            return entry.id

        adapter.save = AsyncMock(side_effect=save)

        # Mock query operation
        async def query(query_text, k=5, filter=None):
            results = []
            for entry in storage[tier].values():
                if query_text.lower() in entry.text.lower():
                    results.append(entry)
            return results[:k]

        adapter.query = AsyncMock(side_effect=query)

        # Mock delete operation
        async def delete(entry_id=None, filter=None):
            if entry_id and entry_id in storage[tier]:
                del storage[tier][entry_id]
                print(f"  ✓ Deleted from {tier}: {entry_id}")
                return 1
            return 0

        adapter.delete = AsyncMock(side_effect=delete)

        return adapter

    registry.get_adapter = AsyncMock(side_effect=mock_get_adapter)
    registry.get_all_tiers = Mock(return_value=["ephemeral", "session", "persistent"])

    return registry


def create_memory(entry_id: str, text: str, importance: float, tags: list = None):
    """Helper to create a memory entry."""
    return MemoryEntry(
        id=entry_id,
        text=text,
        metadata=MemoryMetadata(importance=importance, tags=tags or [], created_at=datetime.now()),
    )


async def main():
    """Main example demonstrating basic Router operations."""

    print("=" * 70)
    print("AXON ROUTER - BASIC USAGE EXAMPLE")
    print("=" * 70)

    # Initialize Router
    config = create_mock_config()
    registry = create_mock_registry()
    router = Router(config=config, registry=registry)

    print("\n1. STORING MEMORIES")
    print("-" * 70)
    print("The Router automatically selects tiers based on importance:\n")

    # Store memories with different importance levels
    memories = [
        create_memory(
            "mem-1",
            "User mentioned they like pizza for dinner",
            importance=0.9,  # High importance → persistent tier
            tags=["food", "preferences"],
        ),
        create_memory(
            "mem-2",
            "Current weather is sunny and 72°F",
            importance=0.1,  # Low importance → ephemeral tier
            tags=["weather", "temporary"],
        ),
        create_memory(
            "mem-3",
            "User is working on a Python project about machine learning",
            importance=0.6,  # Medium importance → session tier
            tags=["projects", "context"],
        ),
    ]

    for memory in memories:
        print(f"Storing (importance={memory.metadata.importance}):")
        await router.route_store(memory)

    print("\n2. RECALLING MEMORIES")
    print("-" * 70)
    print("Search across all tiers for relevant memories:\n")

    # Query for memories
    query = "user preferences"
    print(f"Query: '{query}'")
    results = await router.route_recall(query, k=5)

    print(f"\nFound {len(results)} result(s):")
    for i, result in enumerate(results, 1):
        print(f"  {i}. [{result.id}] {result.text}")
        print(f"     Importance: {result.metadata.importance}")
        print(f"     Tags: {', '.join(result.metadata.tags)}")

    print("\n3. TIER STATISTICS")
    print("-" * 70)
    print("Monitor operations across tiers:\n")

    stats = router.get_tier_stats()
    for tier, tier_stats in stats.items():
        print(f"{tier.upper()} Tier:")
        print(f"  Stores:  {tier_stats['stores']}")
        print(f"  Recalls: {tier_stats['recalls']}")
        print(f"  Forgets: {tier_stats['forgets']}")

    print("\n4. FORGETTING MEMORIES")
    print("-" * 70)
    print("Remove memories that are no longer needed:\n")

    # Forget the temporary weather memory
    print("Forgetting temporary weather data...")
    deleted = await router.route_forget(entry_id="mem-2")
    print(f"  ✓ Deleted {deleted} entry/entries")

    # Verify it's gone
    print("\nVerifying deletion...")
    results_after = await router.route_recall("weather", k=5)
    print(f"  Weather-related memories found: {len(results_after)}")

    print("\n5. EXPLICIT TIER SELECTION")
    print("-" * 70)
    print("Override automatic tier selection when needed:\n")

    # Store a low-importance memory in persistent tier explicitly
    important_note = create_memory(
        "mem-4",
        "User's birthday is December 25th",
        importance=0.3,  # Would normally go to ephemeral
        tags=["personal", "important"],
    )

    print("Storing low-importance memory explicitly in persistent tier:")
    await router.route_store(important_note, tier="persistent")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Router automatically routes memories based on importance")
    print("  • Importance ≥0.7 → persistent, ≥0.3 → session, <0.3 → ephemeral")
    print("  • Recall searches across all tiers by default")
    print("  • Statistics help monitor memory system usage")
    print("  • Explicit tier selection available when needed")
    print()


if __name__ == "__main__":
    asyncio.run(main())
