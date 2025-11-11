"""
Compaction Policies

Learn how to configure memory compaction to automatically summarize and
reduce the number of entries when tiers reach capacity thresholds.

Learn:
- Compaction threshold configuration
- Compaction strategies (count, importance, semantic, time, hybrid)
- When compaction triggers
- Compaction vs. eviction
- Best practices for long-term storage

Run:
    python 04_compaction_policies.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy


async def main():
    """Demonstrate compaction policy configuration."""
    print("=== Compaction Policies ===\n")

    # 1. Configure compaction policy
    print("1. Persistent Policy with Compaction")
    print("-" * 50)

    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None,
            compaction_threshold=100,  # Compact when > 100 entries
            compaction_strategy="importance"  # Strategy to use
        ),
        default_tier="persistent"
    )

    print(f"  Compaction threshold: 100 entries")
    print(f"  Compaction strategy: importance")
    print()

    memory = MemorySystem(config)

    # 2. Compaction strategies
    print("2. Available Compaction Strategies")
    print("-" * 50)
    print()

    strategies = [
        ("count", "Simple count-based compaction", "Legacy, groups by batch size"),
        ("importance", "Compact low-importance first", "Preserves high-value memories"),
        ("semantic", "Group by similarity", "Clusters related content"),
        ("time", "Compact old entries first", "Preserves recent activity"),
        ("hybrid", "Combined approach", "Balances multiple factors")
    ]

    for name, description, behavior in strategies:
        print(f"  {name}:")
        print(f"    Description: {description}")
        print(f"    Behavior: {behavior}")
        print()

    # 3. When compaction triggers
    print("3. Compaction Triggers")
    print("-" * 50)
    print()
    print("  Compaction occurs when:")
    print("    1. Entry count exceeds threshold")
    print("    2. manual await memory.compact() call")
    print()
    print("  Compaction process:")
    print("    1. Select entries to compact (based on strategy)")
    print("    2. Group entries into batches")
    print("    3. Summarize each group using LLM")
    print("    4. Replace originals with summaries")
    print("    5. Update provenance metadata")
    print()

    # 4. Compaction threshold examples
    print("4. Threshold Configuration Examples")
    print("-" * 50)
    print()

    # Small scale
    print("  Small Scale (< 1K entries):")
    small_config = PersistentPolicy(
        adapter_type="memory",
        compaction_threshold=500,
        compaction_strategy="count"
    )
    print(f"    Threshold: 500")
    print(f"    Strategy: count (simple)")
    print()

    # Medium scale
    print("  Medium Scale (1K-10K entries):")
    medium_config = PersistentPolicy(
        adapter_type="memory",
        compaction_threshold=5000,
        compaction_strategy="importance"
    )
    print(f"    Threshold: 5000")
    print(f"    Strategy: importance")
    print()

    # Large scale
    print("  Large Scale (10K+ entries):")
    large_config = PersistentPolicy(
        adapter_type="memory",
        compaction_threshold=50000,
        compaction_strategy="semantic"
    )
    print(f"    Threshold: 50000")
    print(f"    Strategy: semantic (clustering)")
    print()

    # 5. Compaction vs. Eviction
    print("5. Compaction vs. Eviction")
    print("-" * 50)
    print()

    print("  COMPACTION:")
    print("    * Summarizes groups of entries")
    print("    * Preserves information (condensed)")
    print("    * Reduces entry count")
    print("    * Uses LLM for summarization")
    print("    * Slower but preserves context")
    print("    * Best for: Knowledge bases, long-term storage")
    print()

    print("  EVICTION:")
    print("    * Deletes entries entirely")
    print("    * Information is lost")
    print("    * Fast operation")
    print("    * No LLM needed")
    print("    * Best for: Caches, temporary data")
    print()

    # 6. Strategy selection guide
    print("6. Strategy Selection Guide")
    print("-" * 50)
    print()

    use_cases = [
        ("User preferences", "importance", "Keep high-value preferences"),
        ("Knowledge base", "semantic", "Group related knowledge"),
        ("Chat history", "time", "Summarize old conversations"),
        ("Mixed content", "hybrid", "Balance all factors"),
        ("Simple/testing", "count", "No special logic needed")
    ]

    for use_case, strategy, reason in use_cases:
        print(f"  {use_case}:")
        print(f"    Strategy: {strategy}")
        print(f"    Reason: {reason}")
        print()

    # 7. Manual compaction
    print("7. Manual Compaction Trigger")
    print("-" * 50)
    print()
    print("  Trigger compaction manually:")
    print("    result = await memory.compact(tier='persistent')")
    print()
    print("  Dry run (preview):")
    print("    result = await memory.compact(dry_run=True)")
    print()
    print("  Override threshold:")
    print("    result = await memory.compact(threshold=1000)")
    print()
    print("  Specify strategy:")
    print("    result = await memory.compact(strategy='semantic')")
    print()

    # 8. Compaction results
    print("8. Compaction Results")
    print("-" * 50)
    print()
    print("  Returned dictionary contains:")
    print("    * entries_before: Count before compaction")
    print("    * entries_after: Count after compaction")
    print("    * summaries_created: Number of summaries")
    print("    * groups_compacted: Number of groups")
    print("    * reduction_ratio: Percentage reduction (0.0-1.0)")
    print("    * execution_time: Time taken (seconds)")
    print("    * strategy: Strategy used")
    print()

    # 9. Best practices
    print("9. Compaction Best Practices")
    print("-" * 50)
    print()
    print("  1. Set appropriate threshold:")
    print("     - Too low: Frequent compaction, high cost")
    print("     - Too high: Memory bloat")
    print("     - Rule of thumb: 5-10x expected normal size")
    print()
    print("  2. Choose strategy for your data:")
    print("     - Semantic: Best for knowledge/documents")
    print("     - Importance: Best for mixed priorities")
    print("     - Time: Best for time-series data")
    print()
    print("  3. Monitor compaction frequency:")
    print("     - Track via audit logs")
    print("     - Adjust threshold if too frequent")
    print()
    print("  4. Provide good embedder:")
    print("     - Semantic strategy needs quality embeddings")
    print("     - Use OpenAI or Voyage for production")
    print()
    print("  5. Consider compaction cost:")
    print("     - LLM API calls for summarization")
    print("     - Compute time for grouping")
    print("     - Balance cost vs. storage")
    print()

    print("=" * 50)
    print("* Successfully demonstrated compaction policies!")
    print("=" * 50)
    print("\nCompaction Summary:")
    print("  * Compaction summarizes groups of entries")
    print("  * Threshold determines when to trigger")
    print("  * Strategies: count, importance, semantic, time, hybrid")
    print("  * Preserves information (unlike eviction)")
    print("  * Best for persistent tier (long-term storage)")
    print("  * Monitor and tune threshold for your scale")


if __name__ == "__main__":
    asyncio.run(main())
