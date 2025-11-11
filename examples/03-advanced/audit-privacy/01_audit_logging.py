"""
Audit Logging

Track all memory operations for compliance and observability.

Run: python 01_audit_logging.py
"""

import asyncio
from axon import MemorySystem
from axon.core import AuditLogger
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.audit import OperationType


async def main():
    print("=== Audit Logging ===\n")

    # Create audit logger
    audit_logger = AuditLogger(max_events=1000, enable_rotation=True)

    memory = MemorySystem(DEVELOPMENT_CONFIG, audit_logger=audit_logger)

    print("1. Performing operations (auto-logged)...")
    await memory.store("User logged in", importance=0.7)
    await memory.store("API key created", importance=0.9)
    await memory.recall("user", k=5)

    print("  OK Operations logged\n")

    # Export audit log
    print("2. Exporting audit log...")
    events = await memory.export_audit_log()

    print(f"  Total events: {len(events)}")
    for event in events[:3]:
        print(f"\n  Event: {event['operation']}")
        print(f"    Status: {event['status']}")
        print(f"    Duration: {event['duration_ms']:.2f}ms")
        if event.get('entry_ids'):
            print(f"    Entries: {len(event['entry_ids'])}")

    # Filter by operation
    print("\n3. Filter by operation type...")
    store_events = await memory.export_audit_log(operation=OperationType.STORE)
    print(f"  STORE operations: {len(store_events)}\n")

    print("=" * 50)
    print("* Audit logging complete!")


if __name__ == "__main__":
    asyncio.run(main())
