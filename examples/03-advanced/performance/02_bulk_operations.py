"""
Bulk Operations

Optimize performance with bulk store and query operations.

Run: python 02_bulk_operations.py
"""

import asyncio
import time
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    print("=== Bulk Operations ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    # Bulk store
    print("1. Bulk Store Performance...")

    entries_data = [(f"Bulk entry {i}", 0.5, ["bulk"]) for i in range(100)]

    start = time.time()
    for content, importance, tags in entries_data:
        await memory.store(content, importance=importance, tags=tags)
    bulk_time = time.time() - start

    print(f"  100 entries: {bulk_time:.3f}s")
    print(f"  Throughput: {100/bulk_time:.0f} entries/sec\n")

    # Bulk recall
    print("2. Bulk Recall...")
    start = time.time()
    results = await memory.recall("bulk", k=100)
    recall_time = time.time() - start

    print(f"  Retrieved {len(results)} entries in {recall_time:.3f}s\n")

    # Export/Import (bulk transfer)
    print("3. Bulk Export/Import...")
    start = time.time()
    data = await memory.export()
    export_time = time.time() - start

    print(f"  Export: {export_time:.3f}s")
    print(f"  Entries: {data['statistics']['total_entries']}\n")

    print("=" * 50)
    print("* Bulk operations complete!")


if __name__ == "__main__":
    asyncio.run(main())
