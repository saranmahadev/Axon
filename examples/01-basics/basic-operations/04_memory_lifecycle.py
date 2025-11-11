"""
Memory Lifecycle - Complete CRUD Operations

Demonstrates the complete lifecycle of a memory: Create, Read, Update (metadata),
and Delete. This ties together all basic operations into a real-world scenario.

Learn:
- Full CRUD lifecycle
- Tracking memory through its lifetime
- Access patterns and metadata updates
- Memory statistics and observability

Run:
    python 04_memory_lifecycle.py
"""

import asyncio
from datetime import datetime
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    """Demonstrate complete memory lifecycle."""
    print("=== Axon Memory Lifecycle ===\n")

    # Create memory system
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    # Phase 1: CREATE
    print("Phase 1: CREATE - Storing a new memory")
    print("-" * 50)

    user_id = "user_12345"
    session_id = "session_abc123"

    entry_id = await memory.store(
        "User's preferred programming language is Python",
        importance=0.7,
        tags=["preferences", "programming"],
        metadata={
            "user_id": user_id,
            "session_id": session_id,
            "source": "user_profile"
        }
    )

    print(f"OK Memory created with ID: {entry_id}")
    print(f"  Content: 'User's preferred programming language is Python'")
    print(f"  Importance: 0.7")
    print(f"  Tags: preferences, programming")
    print()

    # Phase 2: READ - Retrieve and inspect
    print("Phase 2: READ - Retrieving the memory")
    print("-" * 50)

    results = await memory.recall("programming language", k=1)

    if results:
        entry = results[0]
        print(f"OK Memory retrieved successfully")
        print(f"  ID: {entry.id}")
        print(f"  Text: {entry.text}")
        print(f"  Type: {entry.type}")
        print(f"  Importance: {entry.metadata.importance}")
        print(f"  Tags: {', '.join(entry.metadata.tags)}")
        print(f"  User ID: {entry.metadata.user_id}")
        print(f"  Session ID: {entry.metadata.session_id}")
        print(f"  Created: {entry.metadata.created_at}")
        print(f"  Access count: {entry.metadata.access_count}")
    else:
        print("X Memory not found!")

    print()

    # Phase 3: UPDATE (via re-storage with same ID concept)
    # Note: Current implementation doesn't support direct updates,
    # but we can demonstrate updating importance through re-storage
    print("Phase 3: UPDATE - Modifying memory attributes")
    print("-" * 50)

    # Store updated version with higher importance
    updated_id = await memory.store(
        "User's preferred programming language is Python. Actively learning async patterns.",
        importance=0.85,  # Increased importance
        tags=["preferences", "programming", "learning"],  # Added tag
        metadata={
            "user_id": user_id,
            "session_id": session_id,
            "source": "user_profile",
            "updated_at": datetime.now().isoformat()
        }
    )

    print(f"OK Memory updated (new entry created)")
    print(f"  New ID: {updated_id}")
    print(f"  Updated importance: 0.85 (was 0.7)")
    print(f"  New tag added: 'learning'")
    print(f"  Content expanded with more context")
    print()

    # Phase 4: RETRIEVE AGAIN - Show access tracking
    print("Phase 4: MULTIPLE RECALLS - Access pattern tracking")
    print("-" * 50)

    for i in range(3):
        results = await memory.recall("Python programming", k=1)
        if results:
            print(f"  Recall #{i+1}: {results[0].text[:50]}...")

    print(f"\nOK Memory accessed multiple times")
    print(f"  Note: Access count and last_accessed are automatically tracked")
    print()

    # Phase 5: STATISTICS - System observability
    print("Phase 5: STATISTICS - Memory system insights")
    print("-" * 50)

    stats = memory.get_statistics()

    print(f"OK System statistics:")
    print(f"  Total store operations: {stats['total_operations']['stores']}")
    print(f"  Total recall operations: {stats['total_operations']['recalls']}")
    print(f"  Total forget operations: {stats['total_operations']['forgets']}")
    print(f"  Trace events: {stats['trace_events']}")
    print()

    # Show per-tier stats
    print(f"  Per-tier breakdown:")
    for tier_name, tier_stats in stats['tier_stats'].items():
        print(f"    {tier_name}:")
        print(f"      Stores: {tier_stats.get('stores', 0)}")
        print(f"      Recalls: {tier_stats.get('recalls', 0)}")
    print()

    # Phase 6: TRACE EVENTS - Operation history
    print("Phase 6: TRACE EVENTS - Operation history")
    print("-" * 50)

    # Get recent store events
    store_events = memory.get_trace_events(operation="store", limit=3)

    print(f"OK Recent store operations:")
    for event in store_events:
        print(f"  - {event.operation} at {event.timestamp}")
        print(f"    Entry ID: {event.entry_id}")
        print(f"    Duration: {event.duration_ms:.2f}ms")
        print(f"    Success: {event.success}")

    print()

    # Get recent recall events
    recall_events = memory.get_trace_events(operation="recall", limit=3)

    print(f"OK Recent recall operations:")
    for event in recall_events:
        print(f"  - {event.operation} at {event.timestamp}")
        print(f"    Query: '{event.query}'")
        print(f"    Results: {event.result_count}")
        print(f"    Duration: {event.duration_ms:.2f}ms")

    print()

    # Phase 7: DELETE - Cleanup
    print("Phase 7: DELETE - Removing the memory")
    print("-" * 50)

    # Find and delete the original entry
    results = await memory.recall("Python programming", k=2)

    deleted_count = 0
    for entry in results:
        # Determine which tier
        for tier_name in ["ephemeral", "session", "persistent"]:
            adapter = await memory.registry.get_adapter(tier_name)
            try:
                await adapter.get(entry.id)
                success = await adapter.delete(entry.id)
                if success:
                    print(f"  OK Deleted entry {entry.id} from {tier_name} tier")
                    deleted_count += 1
                break
            except KeyError:
                continue

    print(f"\nOK Deleted {deleted_count} memory entries")
    print()

    # Phase 8: VERIFY DELETION
    print("Phase 8: VERIFY - Confirm deletion")
    print("-" * 50)

    results = await memory.recall("Python programming", k=10)

    if not results:
        print("OK All memories successfully deleted")
        print("  No results found for 'Python programming' query")
    else:
        print(f"! Found {len(results)} remaining entries")

    print()

    print("=" * 50)
    print("* Complete memory lifecycle demonstrated!")
    print("=" * 50)
    print("\nLifecycle Summary:")
    print("  1. CREATE   - Store with metadata and tags")
    print("  2. READ     - Retrieve and inspect details")
    print("  3. UPDATE   - Modify importance and content")
    print("  4. TRACK    - Access patterns automatically recorded")
    print("  5. OBSERVE  - Statistics and trace events")
    print("  6. DELETE   - Remove when no longer needed")
    print("  7. VERIFY   - Confirm operations succeeded")


if __name__ == "__main__":
    asyncio.run(main())
