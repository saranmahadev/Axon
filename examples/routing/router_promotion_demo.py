"""
Example: Automatic Memory Promotion and Demotion

This example demonstrates:
- How memories are automatically promoted based on access patterns
- PolicyEngine integration for promotion rules
- Scoring changes that trigger tier transitions
- Monitoring promotion/demotion statistics

Understanding automatic tier migration helps optimize memory systems
for frequently accessed vs. rarely used information.
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


def create_mock_registry():
    """Create mock adapter registry with simulated storage."""
    registry = Mock(spec=AdapterRegistry)

    # In-memory storage simulation
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
    registry._storage = storage

    return registry


def create_memory(entry_id: str, text: str, importance: float, access_count: int = 0):
    """Create a memory entry with access metadata."""
    return MemoryEntry(
        id=entry_id,
        text=text,
        metadata=MemoryMetadata(
            importance=importance,
            created_at=datetime.now(),
            access_count=access_count,
            last_accessed=datetime.now(),
        ),
    )


async def main():
    """Demonstrate automatic promotion and demotion."""

    print("=" * 70)
    print("AXON ROUTER - AUTOMATIC PROMOTION & DEMOTION EXAMPLE")
    print("=" * 70)

    # Initialize components
    config = create_mock_config()
    registry = create_mock_registry()

    # Create mock policy engine for demonstration
    policy_engine = Mock()
    policy_engine.get_promotion_path = Mock(return_value=None)
    policy_engine.get_demotion_path = Mock(return_value=None)
    policy_engine.check_overflow = Mock(return_value=(False, {"is_overflow": False}))

    router = Router(config=config, registry=registry, policy_engine=policy_engine)

    print("\n1. INITIAL STORAGE (Session Tier)")
    print("-" * 70)
    print("Store a memory with medium importance in session tier:\n")

    # Store memory with moderate importance
    memory = create_memory(
        "promo-1",
        "User prefers dark mode theme in editor",
        importance=0.5,  # Session tier (0.3 ≤ importance < 0.7)
        access_count=0,
    )

    initial_tier = await router.select_tier(memory)
    await router.route_store(memory)

    print("Memory ID:        promo-1")
    print(f"Text:             '{memory.text}'")
    print(f"Initial Tier:     {initial_tier}")
    print(f"Importance:       {memory.metadata.importance}")
    print(f"Access Count:     {memory.metadata.access_count}")

    print("\n2. SIMULATING FREQUENT ACCESS")
    print("-" * 70)
    print("Each recall increases access_count and may trigger promotion:\n")

    # Simulate multiple accesses
    for i in range(1, 6):
        # Recall the memory
        results = await router.route_recall("dark mode", k=1, tiers=["session"])

        if results:
            accessed_memory = results[0]

            # Update access metadata (normally done by Router internally)
            accessed_memory.metadata.access_count = i
            accessed_memory.metadata.last_accessed = datetime.now()

            # Recalculate importance based on access pattern (simplified for demo)
            # In production, Router uses ScoringEngine for this
            new_importance = min(0.95, accessed_memory.metadata.importance + (i * 0.1))
            accessed_memory.metadata.importance = new_importance

            # Check if promotion is needed
            new_tier = await router.select_tier(accessed_memory)

            print(f"Access #{i}:")
            print(f"  Access Count:   {accessed_memory.metadata.access_count}")
            print(f"  New Importance: {new_importance:.3f}")
            print(f"  Selected Tier:  {new_tier}")

            # If tier changed, demonstrate promotion
            if new_tier != initial_tier and i == 3:
                print(f"\n  🔼 PROMOTION TRIGGERED: {initial_tier} → {new_tier}")
                print("     Reason: Frequent access pattern detected")
                print("     Action: Moving memory to higher tier\n")

                # Perform promotion
                await router.route_store(accessed_memory, tier=new_tier)
                await router.route_forget(entry_id="promo-1", tier=initial_tier)
                initial_tier = new_tier

    print("\n3. CHECKING FINAL STATE")
    print("-" * 70)

    # Recall from all tiers to see where it ended up
    final_results = await router.route_recall("dark mode", k=1)

    if final_results:
        final_memory = final_results[0]
        final_tier = await router.select_tier(final_memory)
        print(f"Final Tier:       {final_tier}")
        print(f"Final Importance: {final_memory.metadata.importance:.3f}")
        print(f"Total Accesses:   {final_memory.metadata.access_count}")
        print("\n✓ Memory successfully promoted to higher tier")

    print("\n4. DEMOTION SCENARIO")
    print("-" * 70)
    print("Demonstrate demotion when memory becomes less relevant:\n")

    # Create a highly important memory
    important_memory = create_memory(
        "demote-1",
        "Temporary API key for testing: abc123xyz",
        importance=0.8,  # Persistent tier initially
        access_count=0,
    )

    current_tier = await router.select_tier(important_memory)
    await router.route_store(important_memory)

    print("Memory ID:        demote-1")
    print(f"Initial Tier:     {current_tier}")
    print(f"Initial Importance: {important_memory.metadata.importance}")

    # Simulate time passing and importance decay
    print("\nSimulating importance decay (e.g., API key expired):")

    for decay_step in range(1, 4):
        # Reduce importance (simulating decay or user marking as less important)
        important_memory.metadata.importance -= 0.25
        new_tier = await router.select_tier(important_memory)

        print(f"\nDecay Step {decay_step}:")
        print(f"  New Importance: {important_memory.metadata.importance:.3f}")
        print(f"  Selected Tier:  {new_tier}")

        if new_tier != current_tier:
            print(f"  🔽 DEMOTION TRIGGERED: {current_tier} → {new_tier}")
            print("     Reason: Importance decreased below threshold")
            print("     Action: Moving memory to lower tier")

            # Perform demotion
            await router.route_store(important_memory, tier=new_tier)
            await router.route_forget(entry_id="demote-1", tier=current_tier)
            current_tier = new_tier

    print("\n5. PROMOTION/DEMOTION STATISTICS")
    print("-" * 70)

    stats = router.get_tier_stats()

    print("\nTier Statistics:")
    for tier, tier_stats in stats.items():
        print(f"\n{tier.upper()}:")
        print(f"  Stores:     {tier_stats['stores']}")
        print(f"  Recalls:    {tier_stats['recalls']}")
        print(f"  Forgets:    {tier_stats['forgets']}")
        if tier_stats.get("promotions"):
            print(f"  Promotions: {tier_stats['promotions']}")
        if tier_stats.get("demotions"):
            print(f"  Demotions:  {tier_stats['demotions']}")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Frequent access increases importance and can trigger promotion")
    print("  • PolicyEngine evaluates tier transitions based on scoring")
    print("  • Promotion moves memories to more durable/expensive tiers")
    print("  • Demotion moves memories to cheaper/temporary tiers")
    print("  • Access patterns influence automatic tier selection")
    print("  • Monitor promotion/demotion stats to optimize tier policies")
    print("  • Importance thresholds determine tier boundaries:")
    print("    - Ephemeral:   importance < 0.3")
    print("    - Session:     0.3 ≤ importance < 0.7")
    print("    - Persistent:  importance ≥ 0.7")
    print()


if __name__ == "__main__":
    asyncio.run(main())
