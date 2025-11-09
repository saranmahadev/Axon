"""
Example: Scoring and Policy Configuration

This example demonstrates:
- How ScoringEngine calculates promotion/demotion scores
- Understanding scoring factors (frequency, recency, velocity, decay)
- How scoring influences tier transitions
- Monitoring score explanations for debugging

Understanding scoring helps optimize memory tier management.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.core.policy_engine import PolicyEngine
from axon.core.router import Router
from axon.core.scoring import ScoringConfig, ScoringEngine
from axon.models.entry import MemoryEntry, MemoryMetadata


def create_config():
    """Create standard configuration."""
    config = Mock(spec=MemoryConfig)
    config.tiers = {
        "ephemeral": EphemeralPolicy(adapter_type="memory", max_entries=10, ttl_seconds=60),
        "session": SessionPolicy(adapter_type="memory", max_entries=50, ttl_seconds=3600),
        "persistent": PersistentPolicy(adapter_type="memory", max_entries=1000),
    }
    return config


def create_mock_registry():
    """Create mock registry with storage."""
    registry = Mock(spec=AdapterRegistry)
    storage = {"ephemeral": {}, "session": {}, "persistent": {}}

    async def get_adapter(tier: str):
        adapter = AsyncMock()

        async def save(entry):
            storage[tier][entry.id] = entry
            return entry.id

        async def query(query_text, k=5, filter_dict=None):
            results = list(storage[tier].values())
            return results[:k]

        async def delete(entry_id):
            if entry_id in storage[tier]:
                del storage[tier][entry_id]

        adapter.save = AsyncMock(side_effect=save)
        adapter.query = AsyncMock(side_effect=query)
        adapter.delete = AsyncMock(side_effect=delete)
        adapter.close = AsyncMock()

        return adapter

    registry.get_adapter = AsyncMock(side_effect=get_adapter)
    registry.get_all_tiers = Mock(return_value=["ephemeral", "session", "persistent"])
    registry._storage = storage

    return registry


def create_memory(
    entry_id: str, text: str, importance: float, access_count: int = 0, days_old: int = 0
) -> MemoryEntry:
    """Create a test memory entry."""
    last_accessed = datetime.now() - timedelta(days=days_old)

    return MemoryEntry(
        id=entry_id,
        text=text,
        metadata=MemoryMetadata(
            importance=importance,
            access_count=access_count,
            created_at=last_accessed,
            last_accessed=last_accessed,
        ),
    )


async def main():
    """Demonstrate scoring system."""

    print("=" * 70)
    print("AXON ROUTER - SCORING SYSTEM DEMONSTRATION")
    print("=" * 70)

    # Setup
    config = create_config()
    registry = create_mock_registry()
    policy_engine = Mock(spec=PolicyEngine)

    router = Router(config=config, registry=registry, policy_engine=policy_engine)

    print("\n1. DEFAULT SCORING CONFIGURATION")
    print("-" * 70)

    scoring_engine = ScoringEngine()

    print("ScoringEngine uses multiple factors:")
    print("  Promotion weights:")
    print(f"    • Frequency:     {scoring_engine.config.promotion_frequency_weight:.2f}")
    print(f"    • Recency:       {scoring_engine.config.promotion_recency_weight:.2f}")
    print(f"    • Velocity:      {scoring_engine.config.promotion_velocity_weight:.2f}")
    print(f"    • Importance:    {scoring_engine.config.promotion_importance_weight:.2f}")
    print("  Demotion weights:")
    print(f"    • Decay:         {scoring_engine.config.demotion_decay_weight:.2f}")
    print(f"    • Importance:    {scoring_engine.config.demotion_importance_weight:.2f}")
    print(f"    • Capacity:      {scoring_engine.config.demotion_capacity_weight:.2f}")
    print(f"    • Staleness:     {scoring_engine.config.demotion_staleness_weight:.2f}")
    print("  Thresholds:")
    print(f"    • Promotion:     {scoring_engine.config.promotion_threshold:.2f}")
    print(f"    • Demotion:      {scoring_engine.config.demotion_threshold:.2f}")

    print("\n2. PROMOTION SCORE CALCULATION")
    print("-" * 70)
    print("Promotion scores determine if memory should move to higher tier:\n")

    # Create test memories with different characteristics
    test_memories = [
        (
            "Old, rarely accessed",
            create_memory("test-1", "Old data", 0.4, access_count=1, days_old=30),
        ),
        (
            "Recent, frequently accessed",
            create_memory("test-2", "Hot data", 0.4, access_count=20, days_old=1),
        ),
        (
            "High importance, new",
            create_memory("test-3", "Important", 0.9, access_count=0, days_old=0),
        ),
        (
            "Medium, moderate access",
            create_memory("test-4", "Medium", 0.5, access_count=5, days_old=7),
        ),
    ]

    current_tier = "session"

    print(f"Evaluating promotion from {current_tier}:\n")

    for description, memory in test_memories:
        score, components = scoring_engine.calculate_promotion_score(
            entry=memory, current_tier=current_tier
        )

        days_old = (datetime.now() - memory.metadata.last_accessed).days
        should_promote = score >= scoring_engine.config.promotion_threshold

        print(f"  {description:30}")
        print(f"    Importance:   {memory.metadata.importance:.2f}")
        print(f"    Access count: {memory.metadata.access_count:2d}")
        print(f"    Age (days):   {days_old:2d}")
        print(f"    → Score:      {score:.3f} {'✓ PROMOTE' if should_promote else '✗ Keep'}")
        print()

    print("\n3. DEMOTION SCORE CALCULATION")
    print("-" * 70)
    print("Demotion scores determine if memory should move to lower tier:\n")

    current_tier = "persistent"

    print(f"Evaluating demotion from {current_tier}:\n")

    for description, memory in test_memories:
        score, components = scoring_engine.calculate_demotion_score(
            entry=memory, current_tier=current_tier
        )

        days_old = (datetime.now() - memory.metadata.last_accessed).days
        should_demote = score >= scoring_engine.config.demotion_threshold

        print(f"  {description:30}")
        print(f"    Importance:   {memory.metadata.importance:.2f}")
        print(f"    Access count: {memory.metadata.access_count:2d}")
        print(f"    Age (days):   {days_old:2d}")
        print(f"    → Score:      {score:.3f} {'✓ DEMOTE' if should_demote else '✗ Keep'}")
        print()

    print("\n4. SCORE EXPLANATION")
    print("-" * 70)
    print("Get detailed breakdown of scoring factors:\n")

    test_entry = create_memory(
        "explain-test", "Sample memory for explanation", importance=0.6, access_count=10, days_old=3
    )

    # Calculate promotion score
    promotion_score, components = scoring_engine.calculate_promotion_score(
        entry=test_entry, current_tier="session"
    )

    print("Promotion Score Breakdown:")
    print(f"  Final Score:          {promotion_score:.3f}")
    print(f"  Frequency Score:      {components['frequency']:.3f}")
    print(f"  Recency Score:        {components['recency']:.3f}")
    print(f"  Velocity Score:       {components['velocity']:.3f}")
    print(f"  Importance Score:     {components['importance']:.3f}")
    print(f"  Meets Threshold:      {components['should_promote']}")
    print(f"  Threshold:            {components['threshold']:.3f}")

    print("\n5. CUSTOM SCORING CONFIGURATION")
    print("-" * 70)
    print("Create ScoringEngine with custom weights:\n")

    # Create custom config emphasizing recency
    recency_focused_config = ScoringConfig(
        promotion_frequency_weight=0.1,  # Low weight on access count
        promotion_recency_weight=0.6,  # High weight on recency
        promotion_velocity_weight=0.1,  # Low weight on velocity
        promotion_importance_weight=0.2,  # Medium weight on base importance
    )

    recency_focused_engine = ScoringEngine(config=recency_focused_config)

    print("Recency-Focused Configuration:")
    print(f"  Frequency weight: {recency_focused_config.promotion_frequency_weight:.2f}")
    print(f"  Recency weight:   {recency_focused_config.promotion_recency_weight:.2f}")
    print(f"  Velocity weight:  {recency_focused_config.promotion_velocity_weight:.2f}")
    print(f"  Importance weight: {recency_focused_config.promotion_importance_weight:.2f}")

    print("\nCompare Default vs. Recency-Focused:\n")

    test_entry = create_memory(
        "compare",
        "Memory accessed recently but infrequently",
        importance=0.4,
        access_count=2,
        days_old=1,
    )

    default_score, _ = scoring_engine.calculate_promotion_score(test_entry, "session")
    recency_score, _ = recency_focused_engine.calculate_promotion_score(test_entry, "session")

    print(f"  Default scoring:         {default_score:.3f}")
    print(f"  Recency-focused scoring: {recency_score:.3f}")
    print(f"  Difference:              {recency_score - default_score:+.3f}")

    print("\n6. TIER SELECTION BASED ON IMPORTANCE")
    print("-" * 70)
    print("Router uses importance thresholds for initial tier selection:\n")

    importance_levels = [0.1, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85, 0.95]

    print("Importance → Selected Tier:")
    for importance in importance_levels:
        memory = create_memory(f"tier-{importance}", "Test", importance)
        tier = await router.select_tier(memory)
        print(f"  {importance:.2f} → {tier:12}  ", end="")

        if importance < 0.3:
            print("(ephemeral: importance < 0.3)")
        elif importance < 0.7:
            print("(session: 0.3 ≤ importance < 0.7)")
        else:
            print("(persistent: importance ≥ 0.7)")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)

    print("\nKey Takeaways:")
    print("  • ScoringEngine combines multiple factors:")
    print("    - Frequency: How often memory is accessed")
    print("    - Recency: How recently memory was accessed")
    print("    - Velocity: Rate of access increase")
    print("    - Importance: Base importance value")
    print()
    print("  • Promotion scores → move to higher (more durable) tier")
    print("  • Demotion scores → move to lower (cheaper) tier")
    print("  • Configurable weights allow optimization for use case")
    print()
    print("  • Use Cases:")
    print("    - High recency weight: Chatbots, sessions")
    print("    - High frequency weight: Knowledge bases")
    print("    - High importance weight: Document archives")
    print()
    print("  • Score explanations help debug tier transitions")
    print("  • Test different configurations before production")
    print()


if __name__ == "__main__":
    asyncio.run(main())
