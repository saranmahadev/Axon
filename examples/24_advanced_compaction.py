"""
Advanced Compaction Strategies Example

This example demonstrates Axon's advanced compaction strategies:
- Semantic compaction: Group similar entries by embedding similarity
- Importance-based compaction: Compact low-importance entries first
- Time-based compaction: Compact old entries
- Hybrid strategies: Combine multiple strategies with weights
- Custom strategy instances: Fine-tune compaction parameters

Features demonstrated:
- All 5 compaction strategies (semantic, importance, time, hybrid, count)
- Strategy selection and configuration
- Dry-run mode for testing
- Compaction metrics and reporting
- Custom strategy parameters

Run: python examples/24_advanced_compaction.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from axon.adapters import InMemoryAdapter
from axon.core import MemorySystem
from axon.core.adapter_registry import AdapterRegistry
from axon.core.compaction_strategies import (
    HybridCompactionStrategy,
    ImportanceCompactionStrategy,
    SemanticCompactionStrategy,
    TimeBasedCompactionStrategy,
    get_strategy,
)
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy
from axon.embedders import EmbeddingCache
from axon.models import MemoryEntry, MemoryMetadata


class SimpleEmbedder:
    """Simple embedder for demonstration (no API calls needed)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate simple embeddings based on text hash."""
        embeddings = []
        for text in texts:
            # Create a simple embedding based on text length and hash
            base_val = hash(text) % 100 / 100.0
            embedding = [base_val + i * 0.01 for i in range(128)]
            embeddings.append(embedding)
        return embeddings

    def signature(self) -> str:
        """Return embedder signature."""
        return "simple-embedder:v1"


async def create_test_data(system: MemorySystem, count: int = 120):
    """Create test entries with varying importance and age."""
    print(f"Creating {count} test entries...")

    entries_created = 0
    now = datetime.now(timezone.utc)

    # Create entries with different characteristics
    for i in range(count):
        # Vary importance (0.0 to 1.0)
        importance = (i % 10) / 10.0

        # Vary age (0 to 100 days old)
        age_days = (i % 20) * 5
        created_at = now - timedelta(days=age_days)

        # Create different types of content
        if i % 3 == 0:
            text = f"Important task {i}: Complete project milestone"
        elif i % 3 == 1:
            text = f"Meeting note {i}: Discussed team updates"
        else:
            text = f"Reminder {i}: Follow up on action items"

        # Store entry
        await system.store(
            text=text,
            tier="persistent",
            metadata=MemoryMetadata(
                importance=importance, created_at=created_at, tags=[f"category_{i % 5}"]
            ),
        )
        entries_created += 1

    print(f"✓ Created {entries_created} entries")
    return entries_created


async def demo_semantic_compaction(system: MemorySystem):
    """Demonstrate semantic similarity-based compaction."""
    print("\n" + "=" * 80)
    print("SEMANTIC COMPACTION STRATEGY")
    print("=" * 80)
    print()
    print("Groups semantically similar entries together for coherent summaries.")
    print()

    # Dry run first to see what would happen
    print("[Dry Run]")
    result = await system.compact(tier="persistent", strategy="semantic", dry_run=True)

    print(f"  Current entries: {result['entries_before']}")
    print(f"  After compaction: {result['entries_after']}")
    print(f"  Groups created: {result['groups_compacted']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print()


async def demo_importance_compaction(system: MemorySystem):
    """Demonstrate importance-based compaction."""
    print("\n" + "=" * 80)
    print("IMPORTANCE-BASED COMPACTION STRATEGY")
    print("=" * 80)
    print()
    print("Compacts low-importance entries first, preserving critical information.")
    print()

    # Dry run with custom threshold
    print("[Dry Run with importance_threshold=0.5]")
    strategy = ImportanceCompactionStrategy(importance_threshold=0.5)
    result = await system.compact(tier="persistent", strategy=strategy, dry_run=True)

    print(f"  Current entries: {result['entries_before']}")
    print(f"  After compaction: {result['entries_after']}")
    print(f"  Groups created: {result['groups_compacted']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print()


async def demo_time_based_compaction(system: MemorySystem):
    """Demonstrate time-based compaction."""
    print("\n" + "=" * 80)
    print("TIME-BASED COMPACTION STRATEGY")
    print("=" * 80)
    print()
    print("Compacts entries older than a threshold, keeping recent ones intact.")
    print()

    # Dry run with 30-day threshold
    print("[Dry Run with age_threshold_days=30]")
    strategy = TimeBasedCompactionStrategy(age_threshold_days=30)
    result = await system.compact(tier="persistent", strategy=strategy, dry_run=True)

    print(f"  Current entries: {result['entries_before']}")
    print(f"  After compaction: {result['entries_after']}")
    print(f"  Groups created: {result['groups_compacted']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print()


async def demo_hybrid_compaction(system: MemorySystem):
    """Demonstrate hybrid multi-strategy compaction."""
    print("\n" + "=" * 80)
    print("HYBRID COMPACTION STRATEGY")
    print("=" * 80)
    print()
    print("Combines multiple strategies with configurable weights.")
    print()

    # Combine importance (60%) and time (40%) strategies
    print("[Dry Run: 60% importance + 40% time]")
    strategies = [
        ImportanceCompactionStrategy(importance_threshold=0.5),
        TimeBasedCompactionStrategy(age_threshold_days=45),
    ]
    hybrid = HybridCompactionStrategy(strategies, weights=[0.6, 0.4])

    result = await system.compact(tier="persistent", strategy=hybrid, dry_run=True)

    print(f"  Strategy: {result['strategy']}")
    print(f"  Current entries: {result['entries_before']}")
    print(f"  After compaction: {result['entries_after']}")
    print(f"  Groups created: {result['groups_compacted']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print()


async def demo_count_compaction(system: MemorySystem):
    """Demonstrate legacy count-based compaction."""
    print("\n" + "=" * 80)
    print("COUNT-BASED COMPACTION STRATEGY (Legacy)")
    print("=" * 80)
    print()
    print("Original compaction strategy for backward compatibility.")
    print()

    # Dry run with count strategy
    print("[Dry Run]")
    result = await system.compact(
        tier="persistent", strategy="count", threshold=100, dry_run=True
    )

    print(f"  Current entries: {result['entries_before']}")
    print(f"  After compaction: {result['entries_after']}")
    print(f"  Groups created: {result['groups_compacted']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print()


async def demo_custom_semantic_parameters(system: MemorySystem):
    """Demonstrate custom semantic compaction parameters."""
    print("\n" + "=" * 80)
    print("CUSTOM SEMANTIC COMPACTION PARAMETERS")
    print("=" * 80)
    print()
    print("Fine-tune semantic clustering with custom similarity threshold.")
    print()

    # High similarity threshold (0.95) for very tight clusters
    print("[High Similarity (0.95) - Strict Clustering]")
    strategy_high = SemanticCompactionStrategy(similarity_threshold=0.95, min_cluster_size=3)
    result_high = await system.compact(tier="persistent", strategy=strategy_high, dry_run=True)

    print(f"  Groups created: {result_high['groups_compacted']}")
    print(f"  Reduction: {result_high['reduction_ratio']*100:.1f}%")
    print()

    # Low similarity threshold (0.7) for looser clusters
    print("[Low Similarity (0.7) - Loose Clustering]")
    strategy_low = SemanticCompactionStrategy(similarity_threshold=0.7, min_cluster_size=2)
    result_low = await system.compact(tier="persistent", strategy=strategy_low, dry_run=True)

    print(f"  Groups created: {result_low['groups_compacted']}")
    print(f"  Reduction: {result_low['reduction_ratio']*100:.1f}%")
    print()


async def demo_strategy_comparison(system: MemorySystem):
    """Compare all strategies side-by-side."""
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON")
    print("=" * 80)
    print()
    print("Compare compaction efficiency across all strategies:")
    print()

    strategies_to_test = [
        ("count", get_strategy("count")),
        ("semantic", get_strategy("semantic")),
        ("importance", ImportanceCompactionStrategy(importance_threshold=0.6)),
        ("time", TimeBasedCompactionStrategy(age_threshold_days=40)),
    ]

    results = []
    for name, strategy in strategies_to_test:
        result = await system.compact(
            tier="persistent", strategy=strategy, threshold=100, dry_run=True
        )
        results.append(
            {
                "name": name,
                "groups": result["groups_compacted"],
                "reduction": result["reduction_ratio"] * 100,
                "entries_after": result["entries_after"],
            }
        )

    # Print comparison table
    print(f"{'Strategy':<15} {'Groups':<10} {'Reduction':<12} {'Final Count':<12}")
    print("-" * 55)
    for r in results:
        print(
            f"{r['name']:<15} {r['groups']:<10} {r['reduction']:<11.1f}% {r['entries_after']:<12}"
        )
    print()


async def main():
    """Run all compaction strategy demonstrations."""
    print("\n" + "=" * 80)
    print("AXON ADVANCED COMPACTION STRATEGIES")
    print("=" * 80)
    print()

    # Setup memory system
    print("Setting up memory system...")
    registry = AdapterRegistry()
    registry.register("persistent", adapter_type="memory", adapter_instance=InMemoryAdapter())

    embedder = SimpleEmbedder()
    cache = EmbeddingCache()

    config = MemoryConfig(
        tiers={
            "persistent": PersistentPolicy(
                backend="memory", embedder="simple", compaction_threshold=100
            )
        }
    )

    system = MemorySystem(config, registry=registry, embedder=embedder, embedding_cache=cache)

    # Create test data
    entry_count = await create_test_data(system, count=120)

    # Demonstrate each strategy
    await demo_semantic_compaction(system)
    await demo_importance_compaction(system)
    await demo_time_based_compaction(system)
    await demo_hybrid_compaction(system)
    await demo_count_compaction(system)
    await demo_custom_semantic_parameters(system)
    await demo_strategy_comparison(system)

    # Summary
    print("=" * 80)
    print("ADVANCED COMPACTION EXAMPLES COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  [+] Semantic: Groups similar content for coherent summaries")
    print("  [+] Importance: Preserves critical information, compacts low-value entries")
    print("  [+] Time-based: Removes old entries while keeping recent ones")
    print("  [+] Hybrid: Combines strategies with configurable weights")
    print("  [+] Count: Legacy strategy for backward compatibility")
    print()
    print("Strategy Selection Guide:")
    print("  - Use semantic for knowledge bases with related content")
    print("  - Use importance for critical data preservation")
    print("  - Use time-based for temporal data (logs, events)")
    print("  - Use hybrid when multiple factors matter")
    print("  - Use count for simple threshold-based compaction")
    print()
    print("Next Steps:")
    print("  - Try different strategy parameters")
    print("  - Test with real embedders (OpenAI, Voyage)")
    print("  - Integrate with actual summarization LLMs")
    print("  - Monitor compaction metrics in production")
    print()


if __name__ == "__main__":
    asyncio.run(main())
