"""
Forget Operations - Removing Memories

Learn how to remove memories from the system by ID or through filtering.
Note: Direct forget() API is coming soon. This example shows current approaches.

Learn:
- Retrieving entry IDs for deletion
- Deleting specific entries
- Bulk deletion patterns
- Clearing memories by filter criteria

Run:
    python 03_forget_operations.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    """Demonstrate memory deletion operations."""
    print("=== Axon Forget Operations ===\n")

    # Create memory system and populate with sample data
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Setting up sample data...\n")

    # Store test memories with IDs we can track
    entry_ids = []

    # Temporary cache entries
    for i in range(3):
        entry_id = await memory.store(
            f"Temporary cache item {i+1}",
            importance=0.3,
            tags=["cache", "temporary"],
            tier="ephemeral"
        )
        entry_ids.append(("temp", entry_id))

    # User preferences
    pref_id = await memory.store(
        "User prefers dark mode",
        importance=0.7,
        tags=["preferences", "ui"],
        metadata={"user_id": "user_123"}
    )
    entry_ids.append(("pref", pref_id))

    # Old log entry
    log_id = await memory.store(
        "Login from 192.168.1.1 on 2025-01-01",
        importance=0.4,
        tags=["logs", "security"],
        tier="ephemeral"
    )
    entry_ids.append(("log", log_id))

    print(f"   OK Created {len(entry_ids)} test memories\n")

    # 2. Delete a single entry by ID
    print("2. Delete a specific entry by ID:")
    temp_entry_id = entry_ids[0][1]

    # Get the tier where this entry is stored
    adapter = await memory.registry.get_adapter("ephemeral")
    success = await adapter.delete(temp_entry_id)

    if success:
        print(f"   OK Deleted entry: {temp_entry_id}")
    else:
        print(f"   X Entry not found: {temp_entry_id}")
    print()

    # 3. Verify deletion
    print("3. Verify deletion:")
    try:
        entry = await adapter.get(temp_entry_id)
        print(f"   X Entry still exists: {entry.text}")
    except KeyError:
        print(f"   OK Entry successfully deleted (not found)")
    print()

    # 4. Delete multiple entries (bulk pattern)
    print("4. Bulk delete multiple entries:")

    # Get all temp cache entries
    results = await memory.recall("temporary cache", k=10, tiers=["ephemeral"])
    print(f"   Found {len(results)} cache entries to delete")

    deleted_count = 0
    for entry in results:
        success = await adapter.delete(entry.id)
        if success:
            deleted_count += 1

    print(f"   OK Deleted {deleted_count} entries\n")

    # 5. Conditional deletion based on filters
    print("5. Delete entries matching filter criteria:")

    # Find all log entries
    log_results = await memory.recall(
        "logs",
        k=100,
        filter=Filter(tags=["logs"]),
        tiers=["ephemeral"]
    )

    print(f"   Found {len(log_results)} log entries")

    for entry in log_results:
        await adapter.delete(entry.id)

    print(f"   OK Deleted all log entries\n")

    # 6. Safe deletion with verification
    print("6. Safe deletion with verification:")
    pref_id = entry_ids[3][1]  # User preference entry

    # First check if entry exists
    try:
        entry = await memory.recall("dark mode", k=1)
        if entry:
            target_id = entry[0].id
            print(f"   Found entry to delete: {entry[0].text}")

            # Determine which tier it's in
            found_tier = None
            for tier_name in ["ephemeral", "session", "persistent"]:
                adapter = await memory.registry.get_adapter(tier_name)
                try:
                    await adapter.get(target_id)
                    found_tier = tier_name
                    break
                except KeyError:
                    continue

            if found_tier:
                adapter = await memory.registry.get_adapter(found_tier)
                success = await adapter.delete(target_id)
                print(f"   OK Deleted from '{found_tier}' tier")
            else:
                print("   X Entry not found in any tier")
    except Exception as e:
        print(f"   X Error during deletion: {e}")

    print()

    # 7. Check remaining entries
    print("7. Verify remaining memories:")
    all_results = await memory.recall("", k=100)  # Empty query gets all
    print(f"   Remaining memories: {len(all_results)}")

    for entry in all_results:
        print(f"   - {entry.text[:50]}...")

    print("\n" + "=" * 50)
    print("* Successfully demonstrated forget operations!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * Use adapter.delete(id) to remove entries")
    print("  * Always verify entry exists before deletion")
    print("  * Use recall + filters to find entries to delete")
    print("  * Bulk deletion requires iteration over results")
    print("  * Check which tier contains the entry first")
    print("  * A high-level forget() API is planned for future releases")


if __name__ == "__main__":
    asyncio.run(main())
