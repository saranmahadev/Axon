"""
Audit Logging Example

This example demonstrates how to use the audit logging system to track
all operations on the memory system for compliance and observability.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from axon import MemorySystem
from axon.core import AuditLogger, MemoryConfig
from axon.core.policies import PersistentPolicy, SessionPolicy
from axon.models.audit import EventStatus, OperationType


async def main():
    print("=" * 70)
    print("Axon Audit Logging Example")
    print("=" * 70)
    print()

    # Step 1: Create an audit logger with configuration
    print("1. Setting up audit logger...")
    audit_logger = AuditLogger(
        max_events=10000,  # Keep up to 10,000 events in memory
        enable_rotation=True,  # Auto-rotate when full
    )
    print(f"   Audit logger created (max_events=10000)")
    print()

    # Step 2: Create MemorySystem with audit logging enabled
    print("2. Creating MemorySystem with audit logging...")
    config = MemoryConfig(
        session=SessionPolicy(adapter_type="in_memory", collection_name="session"),
        persistent=PersistentPolicy(
            adapter_type="in_memory", collection_name="persistent"
        ),
    )
    system = MemorySystem(config=config, audit_logger=audit_logger)
    print("   MemorySystem created with audit logger attached")
    print()

    # Step 3: Perform various operations (all will be audited)
    print("3. Performing operations (all will be audited)...")
    print()

    # Store operations
    print("   Storing entries...")
    id1 = await system.store(
        "User prefers dark mode",
        importance=0.8,
        tags=["preferences", "ui"],
        metadata={"user_id": "user_123", "session_id": "session_456"},
    )
    print(f"   ✓ Stored entry {id1[:8]}... with user_id=user_123")

    id2 = await system.store(
        "User's email: user@example.com",
        importance=0.9,
        tags=["contact", "pii"],
        metadata={"user_id": "user_123", "session_id": "session_456"},
    )
    print(f"   ✓ Stored entry {id2[:8]}... with PII tag")

    id3 = await system.store(
        "API key: abc123xyz",
        importance=1.0,
        tags=["credentials"],
        metadata={"user_id": "user_123", "session_id": "session_456"},
    )
    print(f"   ✓ Stored entry {id3[:8]}... (credentials)")
    print()

    # Recall operation
    print("   Recalling entries...")
    results = await system.recall("user preferences", k=5)
    print(f"   ✓ Recalled {len(results)} entries matching 'user preferences'")
    print()

    # Export operation
    print("   Exporting data...")
    export_data = await system.export(tier="persistent")
    print(
        f"   ✓ Exported {export_data['statistics']['total_entries']} entries from persistent tier"
    )
    print()

    # Simulate a failed operation
    print("   Attempting invalid operation (will fail)...")
    try:
        await system.store("", importance=0.5)  # Empty content - should fail
    except ValueError as e:
        print(f"   ✗ Operation failed (expected): {e}")
    print()

    # Step 4: Query the audit log
    print("4. Querying audit log...")
    print()

    # Get all events
    all_events = await audit_logger.get_events()
    print(f"   Total events logged: {len(all_events)}")
    print()

    # Get STORE events only
    store_events = await audit_logger.get_events(operation=OperationType.STORE)
    print(f"   STORE operations: {len(store_events)}")
    for event in store_events:
        status_symbol = "✓" if event.status == EventStatus.SUCCESS else "✗"
        print(
            f"     {status_symbol} {event.timestamp.strftime('%H:%M:%S')} - "
            f"Importance: {event.metadata.get('importance', 'N/A')} - "
            f"Status: {event.status.value}"
        )
    print()

    # Get events for specific user
    user_events = await audit_logger.get_events(user_id="user_123")
    print(f"   Events for user_123: {len(user_events)}")
    print()

    # Get events for specific session
    session_events = await audit_logger.get_events(session_id="session_456")
    print(f"   Events for session_456: {len(session_events)}")
    print()

    # Get failed events
    failed_events = await audit_logger.get_events(status=EventStatus.FAILURE)
    print(f"   Failed operations: {len(failed_events)}")
    if failed_events:
        for event in failed_events:
            print(f"     ✗ {event.operation.value}: {event.error_message}")
    print()

    # Step 5: Export audit log to JSON
    print("5. Exporting audit log to file...")
    audit_file = Path("audit_log_export.json")
    count = await audit_logger.export_to_json(audit_file)
    print(f"   ✓ Exported {count} audit events to {audit_file}")
    print()

    # Step 6: Use MemorySystem's export_audit_log method
    print("6. Using MemorySystem.export_audit_log()...")
    audit_events = await system.export_audit_log()
    print(f"   Retrieved {len(audit_events)} events from MemorySystem")
    print()

    # Filter by operation type
    recall_events = await system.export_audit_log(operation=OperationType.RECALL)
    print(f"   RECALL operations: {len(recall_events)}")
    print()

    # Filter by time range
    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_events = await system.export_audit_log(start_time=recent_cutoff)
    print(f"   Events in last 5 minutes: {len(recent_events)}")
    print()

    # Step 7: Display detailed event information
    print("7. Detailed audit event example...")
    print()
    if all_events:
        event = all_events[0]  # Most recent event
        print(f"   Event ID: {event.event_id}")
        print(f"   Timestamp: {event.timestamp.isoformat()}")
        print(f"   Operation: {event.operation.value}")
        print(f"   User ID: {event.user_id}")
        print(f"   Session ID: {event.session_id}")
        print(f"   Entry IDs: {event.entry_ids}")
        print(f"   Status: {event.status.value}")
        print(f"   Duration: {event.duration_ms:.2f}ms")
        print(f"   Metadata: {json.dumps(event.metadata, indent=4)}")
    print()

    # Step 8: Get audit logger statistics
    print("8. Audit logger statistics...")
    stats = audit_logger.get_stats()
    print(f"   Events in memory: {stats['events_in_memory']}")
    print(f"   Total events logged: {stats['total_events_logged']}")
    print(f"   Max events: {stats['max_events']}")
    print(f"   Rotation enabled: {stats['rotation_enabled']}")
    print(f"   Auto-export enabled: {stats['auto_export_enabled']}")
    print()

    # Step 9: Demonstrate provenance tracking
    print("9. Provenance tracking...")
    print()

    # Get provenance chain for an entry
    if results:
        entry = results[0]
        print(f"   Getting provenance chain for entry {entry.id[:8]}...")
        chain = await system.get_provenance_chain(entry.id)
        print(f"   Provenance chain length: {len(chain)}")
        for i, ancestor in enumerate(chain):
            print(
                f"     {i+1}. {ancestor.id[:8]}... - {ancestor.type} - "
                f"Created: {ancestor.metadata.created_at.strftime('%H:%M:%S')}"
            )
    print()

    # Step 10: Cleanup
    print("10. Cleanup...")
    if audit_file.exists():
        audit_file.unlink()
        print(f"   ✓ Removed {audit_file}")
    await system.close()
    print("   ✓ Closed MemorySystem")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total operations performed: {stats['total_events_logged']}")
    print(
        f"Successful operations: {len([e for e in all_events if e.status == EventStatus.SUCCESS])}"
    )
    print(
        f"Failed operations: {len([e for e in all_events if e.status == EventStatus.FAILURE])}"
    )
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Audit logger configuration and setup")
    print("  ✓ Automatic operation logging (store, recall, export)")
    print("  ✓ User and session tracking")
    print("  ✓ Success and failure event logging")
    print("  ✓ Querying audit log with filters")
    print("  ✓ Exporting audit log to JSON")
    print("  ✓ Performance metrics (duration tracking)")
    print("  ✓ Provenance chain tracking")
    print()


if __name__ == "__main__":
    asyncio.run(main())
