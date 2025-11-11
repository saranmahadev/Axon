"""
Provenance Tracking

Track memory lineage through compaction and transformations.

Run: python 03_provenance_tracking.py
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
    print("=== Provenance Tracking ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    # Store original entries
    print("1. Storing original entries...")
    ids = []
    for i in range(5):
        entry_id = await memory.store(
            f"Original fact {i+1} about machine learning",
            importance=0.6
        )
        ids.append(entry_id)
    print(f"  OK Stored {len(ids)} entries\n")

    # Compact (creates summaries)
    print("2. Compacting (creates summaries)...")
    await memory.compact(tier="persistent", threshold=3)
    print("  OK Compaction complete\n")

    # Find summaries
    print("3. Checking provenance...")
    all_entries = await memory.recall("", k=100)

    for entry in all_entries:
        if entry.metadata.provenance:
            print(f"  Entry: {entry.id[:8]}...")
            print(f"    Type: {entry.type}")
            for prov in entry.metadata.provenance:
                print(f"    Action: {prov.action}")
                print(f"    By: {prov.by}")
                if "summarized_ids" in prov.metadata:
                    print(f"    Sources: {prov.metadata['summarized_ids'][:50]}...")
            print()

    print("=" * 50)
    print("* Provenance tracking complete!")


if __name__ == "__main__":
    asyncio.run(main())
