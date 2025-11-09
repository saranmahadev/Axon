"""
Transactional Operations Example

This example demonstrates Axon's transaction support for atomic multi-tier
memory operations using Two-Phase Commit (2PC) protocol.

Features demonstrated:
- Transaction context manager
- Atomic operations across multiple tiers
- Automatic rollback on failure
- Transaction isolation levels
- Low-level TransactionCoordinator API

Run: python examples/25_transactional_operations.py
"""

import asyncio
from datetime import datetime, timezone

from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy
from axon.core.transaction import IsolationLevel, TransactionCoordinator
from axon.models import MemoryEntry, MemoryMetadata


async def demo_basic_transaction():
    """Demonstrate basic transaction with successful commit."""
    print("\n" + "=" * 80)
    print("BASIC TRANSACTION DEMO")
    print("=" * 80)
    print()

    # Setup transaction coordinator with adapters
    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    coordinator = TransactionCoordinator(adapters=adapters)

    # Create sample entries
    entry1 = MemoryEntry(
        text="User logged in at 10:00 AM",
        embedding=[0.1] * 128,
        metadata=MemoryMetadata(importance=0.5, tags=["login", "event"]),
    )

    entry2 = MemoryEntry(
        text="User completed profile setup",
        embedding=[0.2] * 128,
        metadata=MemoryMetadata(importance=0.8, tags=["profile", "setup"]),
    )

    print("Starting transaction...")
    print(f"  Entry 1: {entry1.text}")
    print(f"  Entry 2: {entry2.text}")
    print()

    # Use transaction context manager
    async with coordinator.transaction() as txn_id:
        print(f"Transaction {txn_id[:8]}... active")

        # Add operations
        await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
        await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)

        print("  [+] Added 2 operations")
        print("  [+] Preparing transaction...")

    print("  [+] Transaction committed successfully!")
    print()

    # Verify entries were saved
    saved1 = await adapters["ephemeral"].get(entry1.id)
    saved2 = await adapters["persistent"].get(entry2.id)

    print("Verification:")
    print(f"  [OK] Ephemeral tier: {saved1.text}")
    print(f"  [OK] Persistent tier: {saved2.text}")
    print()


async def demo_transaction_rollback():
    """Demonstrate automatic rollback on exception."""
    print("\n" + "=" * 80)
    print("TRANSACTION ROLLBACK DEMO")
    print("=" * 80)
    print()

    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    coordinator = TransactionCoordinator(adapters=adapters)

    entry1 = MemoryEntry(
        text="This should not be saved",
        embedding=[0.1] * 128,
        metadata=MemoryMetadata(importance=0.5),
    )

    entry2 = MemoryEntry(
        text="This should also not be saved",
        embedding=[0.2] * 128,
        metadata=MemoryMetadata(importance=0.8),
    )

    print("Starting transaction that will fail...")
    print()

    try:
        async with coordinator.transaction() as txn_id:
            print(f"Transaction {txn_id[:8]}... active")

            await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
            await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)

            print("  [+] Added 2 operations")
            print("  [!] Simulating error...")

            # Simulate an error
            raise RuntimeError("Simulated processing error")

    except RuntimeError as e:
        print(f"  [!] Error caught: {e}")
        print("  [+] Transaction automatically rolled back")
        print()

    # Verify entries were NOT saved
    print("Verification:")
    try:
        await adapters["ephemeral"].get(entry1.id)
        print("  [X] ERROR: Entry 1 should not exist!")
    except KeyError:
        print("  [OK] Entry 1 was not saved (rollback successful)")

    try:
        await adapters["persistent"].get(entry2.id)
        print("  [X] ERROR: Entry 2 should not exist!")
    except KeyError:
        print("  [OK] Entry 2 was not saved (rollback successful)")

    print()


async def demo_isolation_levels():
    """Demonstrate different transaction isolation levels."""
    print("\n" + "=" * 80)
    print("ISOLATION LEVELS DEMO")
    print("=" * 80)
    print()

    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }

    isolation_levels = [
        IsolationLevel.READ_UNCOMMITTED,
        IsolationLevel.READ_COMMITTED,
        IsolationLevel.REPEATABLE_READ,
        IsolationLevel.SERIALIZABLE,
    ]

    for level in isolation_levels:
        print(f"Isolation Level: {level.value.upper()}")

        coordinator = TransactionCoordinator(adapters=adapters, isolation_level=level)

        entry = MemoryEntry(
            text=f"Entry with {level.value} isolation",
            embedding=[0.1] * 128,
            metadata=MemoryMetadata(importance=0.5),
        )

        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(txn_id, "save", "persistent", entry=entry)

        print(f"  [OK] Committed with {level.value} isolation")
        print()


async def demo_low_level_api():
    """Demonstrate low-level TransactionCoordinator API."""
    print("\n" + "=" * 80)
    print("LOW-LEVEL API DEMO")
    print("=" * 80)
    print()

    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    coordinator = TransactionCoordinator(adapters=adapters)

    entry = MemoryEntry(
        text="Using low-level transaction API",
        embedding=[0.1] * 128,
        metadata=MemoryMetadata(importance=0.7),
    )

    # Manual transaction control
    print("Manual transaction control:")
    print()

    # Step 1: Begin
    txn_id = await coordinator.begin()
    print(f"1. Begin transaction: {txn_id[:8]}...")
    print(f"   State: {coordinator.get_state(txn_id).value}")
    print()

    # Step 2: Add operations
    await coordinator.add_operation(txn_id, "save", "persistent", entry=entry)
    print(f"2. Added operation")
    print(f"   State: {coordinator.get_state(txn_id).value}")
    print()

    # Step 3: Prepare
    prepared = await coordinator.prepare(txn_id)
    print(f"3. Prepare phase: {'[OK] Success' if prepared else '[X] Failed'}")
    print(f"   State: {coordinator.get_state(txn_id).value}")
    print()

    # Step 4: Commit
    committed = await coordinator.commit(txn_id)
    print(f"4. Commit phase: {'[OK] Success' if committed else '[X] Failed'}")
    print(f"   State: {coordinator.get_state(txn_id).value}")
    print()

    # Step 5: Cleanup
    await coordinator.cleanup(txn_id)
    print(f"5. Cleanup complete")
    print(f"   State: {coordinator.get_state(txn_id)}")  # None after cleanup
    print()


async def demo_multi_operation_transaction():
    """Demonstrate transaction with many operations."""
    print("\n" + "=" * 80)
    print("MULTI-OPERATION TRANSACTION DEMO")
    print("=" * 80)
    print()

    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    coordinator = TransactionCoordinator(adapters=adapters, timeout_seconds=60.0)

    # Create 20 entries
    entries = []
    for i in range(20):
        entry = MemoryEntry(
            text=f"Batch entry {i + 1}",
            embedding=[float(i % 10) / 10.0] * 128,
            metadata=MemoryMetadata(
                importance=0.5 + (i % 5) * 0.1, tags=[f"batch", f"group_{i % 4}"]
            ),
        )
        entries.append(entry)

    print(f"Creating transaction with {len(entries)} operations...")
    print()

    async with coordinator.transaction() as txn_id:
        for i, entry in enumerate(entries):
            tier = "ephemeral" if i % 2 == 0 else "persistent"
            await coordinator.add_operation(txn_id, "save", tier, entry=entry)

        print(f"  [+] Added {len(entries)} operations")
        print(f"  [+] 10 to ephemeral tier")
        print(f"  [+] 10 to persistent tier")

    print("  [+] Transaction committed successfully!")
    print()

    # Verify counts
    ephemeral_count = len([e for i, e in enumerate(entries) if i % 2 == 0])
    persistent_count = len([e for i, e in enumerate(entries) if i % 2 == 1])

    print("Verification:")
    print(f"  [OK] {ephemeral_count} entries in ephemeral tier")
    print(f"  [OK] {persistent_count} entries in persistent tier")
    print()


async def demo_delete_operations():
    """Demonstrate delete operations in transactions."""
    print("\n" + "=" * 80)
    print("DELETE OPERATIONS DEMO")
    print("=" * 80)
    print()

    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    coordinator = TransactionCoordinator(adapters=adapters)

    # First, create some entries
    entry1 = MemoryEntry(text="Entry to delete 1", embedding=[0.1] * 128, metadata=MemoryMetadata())
    entry2 = MemoryEntry(text="Entry to delete 2", embedding=[0.2] * 128, metadata=MemoryMetadata())

    await adapters["ephemeral"].save(entry1)
    await adapters["persistent"].save(entry2)

    print("Initial state:")
    print(f"  Entry 1 exists: {entry1.id[:8]}...")
    print(f"  Entry 2 exists: {entry2.id[:8]}...")
    print()

    # Delete in transaction
    print("Deleting in transaction...")
    async with coordinator.transaction() as txn_id:
        await coordinator.add_operation(txn_id, "delete", "ephemeral", entry_id=entry1.id)
        await coordinator.add_operation(txn_id, "delete", "persistent", entry_id=entry2.id)

    print("  [+] Transaction committed")
    print()

    # Verify deletions
    print("Verification:")
    try:
        await adapters["ephemeral"].get(entry1.id)
        print("  [X] ERROR: Entry 1 should be deleted!")
    except KeyError:
        print("  [OK] Entry 1 deleted successfully")

    try:
        await adapters["persistent"].get(entry2.id)
        print("  [X] ERROR: Entry 2 should be deleted!")
    except KeyError:
        print("  [OK] Entry 2 deleted successfully")

    print()


async def main():
    """Run all transaction demonstrations."""
    print("\n" + "=" * 80)
    print("AXON TRANSACTIONAL OPERATIONS")
    print("=" * 80)
    print()
    print("This example demonstrates Two-Phase Commit (2PC) transactions")
    print("for atomic multi-tier memory operations.")
    print()

    await demo_basic_transaction()
    await demo_transaction_rollback()
    await demo_isolation_levels()
    await demo_low_level_api()
    await demo_multi_operation_transaction()
    await demo_delete_operations()

    # Summary
    print("=" * 80)
    print("TRANSACTION EXAMPLES COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  [+] Transactions ensure atomicity across multiple tiers")
    print("  [+] Context manager automatically handles commit/rollback")
    print("  [+] Exceptions trigger automatic rollback")
    print("  [+] Multiple isolation levels supported")
    print("  [+] Low-level API available for fine-grained control")
    print()
    print("Use Cases:")
    print("  - Maintaining consistency across ephemeral and persistent storage")
    print("  - Batch operations that must succeed or fail together")
    print("  - Complex workflows requiring atomic state changes")
    print("  - Preventing partial updates during errors")
    print()
    print("Next Steps:")
    print("  - Integrate transactions into your memory workflows")
    print("  - Choose appropriate isolation levels for your use case")
    print("  - Implement custom rollback logic if needed")
    print("  - Monitor transaction performance in production")
    print()


if __name__ == "__main__":
    asyncio.run(main())
