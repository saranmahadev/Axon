"""
Transaction Isolation Levels

Configure isolation levels for transaction consistency.

Run: python 02_isolation_levels.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.core.transaction import IsolationLevel


async def main():
    print("=== Transaction Isolation Levels ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("Available Isolation Levels:\n")
    print("  READ_COMMITTED (default):")
    print("    * Prevents dirty reads")
    print("    * Standard for most use cases\n")

    print("  SERIALIZABLE:")
    print("    * Strictest isolation")
    print("    * Prevents all anomalies\n")

    # Use specific isolation level
    print("1. Transaction with READ_COMMITTED...")
    async with memory.transaction(isolation_level=IsolationLevel.READ_COMMITTED):
        await memory.store("Data 1", tier="persistent")
        await memory.store("Data 2", tier="persistent")

    print("  OK Transaction committed\n")

    print("2. Transaction with SERIALIZABLE...")
    async with memory.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
        await memory.store("Critical data", importance=0.9, tier="persistent")

    print("  OK Transaction committed\n")

    results = await memory.recall("", k=100)
    print(f"Final state: {len(results)} entries\n")

    print("=" * 50)
    print("* Isolation levels complete!")


if __name__ == "__main__":
    asyncio.run(main())
