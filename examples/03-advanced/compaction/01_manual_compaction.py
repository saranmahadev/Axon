"""
Manual Compaction

Learn how to manually trigger memory compaction to summarize and reduce
entry counts when needed.

Run: python 01_manual_compaction.py
"""

import asyncio
import os
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed


async def main():
    print("=== Manual Compaction ===\n")

    # Configure with compaction
    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=100,  # Minimum threshold
            compaction_strategy="count"
        ),
        default_tier="persistent"
    )

    memory = MemorySystem(config)

    # Store many entries
    print("1. Storing 60 entries...")
    for i in range(60):
        await memory.store(
            f"Entry {i+1}: Information about Python programming",
            importance=0.5,
            tags=["python"]
        )
    print("  OK Stored 60 entries\n")

    # Manual compaction
    print("2. Triggering manual compaction...")
    result = await memory.compact(tier="persistent")

    print(f"  Entries before: {result['entries_before']}")
    print(f"  Entries after: {result['entries_after']}")
    print(f"  Summaries created: {result['summaries_created']}")
    print(f"  Reduction: {result['reduction_ratio']*100:.1f}%")
    print(f"  Time: {result['execution_time']:.2f}s\n")

    # Dry run
    print("3. Dry run (preview without executing)...")
    dry_result = await memory.compact(tier="persistent", dry_run=True)
    print(f"  Would compact: {dry_result['groups_compacted']} groups\n")

    print("=" * 50)
    print("* Manual compaction complete!")


if __name__ == "__main__":
    asyncio.run(main())
