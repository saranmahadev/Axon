"""
Performance Benchmarking

Measure and optimize memory system performance.

Run: python 01_benchmarking.py
"""

import asyncio
import time
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    print("=== Performance Benchmarking ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    # Benchmark store operations
    print("1. Store Performance...")
    start = time.time()
    for i in range(1000):
        await memory.store(f"Entry {i}", importance=0.5)
    store_time = time.time() - start

    print(f"  1000 stores: {store_time:.3f}s")
    print(f"  Average: {store_time/1000*1000:.2f}ms per store")
    print(f"  Throughput: {1000/store_time:.0f} ops/sec\n")

    # Benchmark recall operations
    print("2. Recall Performance...")
    start = time.time()
    for i in range(100):
        await memory.recall("entry", k=10)
    recall_time = time.time() - start

    print(f"  100 recalls: {recall_time:.3f}s")
    print(f"  Average: {recall_time/100*1000:.2f}ms per recall")
    print(f"  Throughput: {100/recall_time:.0f} ops/sec\n")

    # Memory usage
    print("3. Memory Statistics...")
    stats = memory.get_statistics()
    print(f"  Total stores: {stats['total_operations']['stores']}")
    print(f"  Total recalls: {stats['total_operations']['recalls']}")
    print(f"  Trace events: {stats['trace_events']}\n")

    print("=" * 50)
    print("* Benchmarking complete!")


if __name__ == "__main__":
    asyncio.run(main())
