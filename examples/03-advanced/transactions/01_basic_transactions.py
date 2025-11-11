"""
Basic Transactions

Learn two-phase commit (2PC) transactions for atomic multi-tier operations.

Run: python 01_basic_transactions.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    print("=== Basic Transactions ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Transaction with automatic commit...")
    try:
        async with memory.transaction() as txn:
            await memory.store("Entry 1", tier="ephemeral")
            await memory.store("Entry 2", tier="session")
            await memory.store("Entry 3", tier="persistent")
        print("  OK Transaction committed\n")
    except Exception as e:
        print(f"  X Transaction rolled back: {e}\n")

    print("2. Transaction with error (rollback)...")
    try:
        async with memory.transaction() as txn:
            await memory.store("Entry A", tier="ephemeral")
            raise ValueError("Simulated error")
            await memory.store("Entry B", tier="session")
    except ValueError:
        print("  OK Transaction rolled back successfully\n")

    results = await memory.recall("", k=100)
    print(f"3. Final state: {len(results)} entries stored")
    print("   (Only entries from first transaction)\n")

    print("=" * 50)
    print("* Transactions complete!")


if __name__ == "__main__":
    asyncio.run(main())
