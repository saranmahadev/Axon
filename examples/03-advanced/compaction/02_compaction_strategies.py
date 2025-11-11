"""
Compaction Strategies

Compare different compaction strategies: count, importance, semantic, time, hybrid.

Run: python 02_compaction_strategies.py
"""

import asyncio
import os
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed


async def main():
    print("=== Compaction Strategies ===\n")

    print("Available Strategies:\n")

    strategies = [
        ("count", "Groups entries by batch size", "Simple, fast"),
        ("importance", "Compacts low-importance first", "Preserves valuable data"),
        ("semantic", "Groups similar content", "Best for knowledge bases"),
        ("time", "Compacts oldest first", "Good for time-series"),
        ("hybrid", "Combines multiple factors", "Balanced approach")
    ]

    for name, desc, use in strategies:
        print(f"  {name.upper()}:")
        print(f"    * {desc}")
        print(f"    * Use case: {use}\n")

    # Demo with count strategy
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    for i in range(20):
        await memory.store(
            f"Memory {i+1} about Python concepts",
            importance=0.3 + (i * 0.02)
        )

    print("Compacting with 'importance' strategy...")
    result = await memory.compact(
        tier="persistent",
        strategy="importance",
        threshold=15
    )

    print(f"  OK Compacted {result['groups_compacted']} groups")
    print(f"  OK Reduction: {result['reduction_ratio']*100:.0f}%\n")

    print("=" * 50)
    print("* Strategy comparison complete!")


if __name__ == "__main__":
    asyncio.run(main())
