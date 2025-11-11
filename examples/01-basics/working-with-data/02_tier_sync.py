"""
Tier Synchronization

Learn how to synchronize memories between different tiers for promotion,
archival, replication, and tier rebalancing operations.

Learn:
- Copying memories between tiers
- Moving memories (copy + delete)
- Filtered synchronization
- Conflict resolution strategies
- Tier promotion patterns
- Archival workflows

Run:
    python 02_tier_sync.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    """Demonstrate tier synchronization operations."""
    print("=== Axon Tier Synchronization ===\n")

    # Create memory system and populate with sample data
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Setting up sample data across tiers...")
    print("-" * 50)

    # Session tier: temporary but important data
    session_data = [
        ("User working on project: FastAPI migration", 0.75, ["session", "project"]),
        ("Current task: API endpoint refactoring", 0.70, ["session", "task"]),
        ("Important note: Check database indexes", 0.85, ["session", "reminder"]),
        ("Draft message: Need to schedule team meeting", 0.65, ["session", "draft"]),
    ]

    for content, importance, tags in session_data:
        await memory.store(
            content,
            importance=importance,
            tags=tags,
            tier="session"
        )

    # Ephemeral tier: cache and temporary data
    ephemeral_data = [
        ("Recent search: Python async best practices", 0.3, ["cache", "search"]),
        ("Autocomplete suggestion: asyncio.gather", 0.2, ["cache", "autocomplete"]),
        ("Old log entry from yesterday", 0.1, ["logs", "old"]),
    ]

    for content, importance, tags in ephemeral_data:
        await memory.store(
            content,
            importance=importance,
            tags=tags,
            tier="ephemeral"
        )

    print(f"OK Created session memories: {len(session_data)}")
    print(f"OK Created ephemeral memories: {len(ephemeral_data)}\n")

    # 2. Copy important session data to persistent
    print("2. Promote important session memories to persistent")
    print("-" * 50)

    stats = await memory.sync(
        source_tier="session",
        target_tier="persistent",
        filter=Filter(min_importance=0.8),  # Only high-importance
        delete_source=False  # Copy, don't move
    )

    print(f"OK Promotion completed:")
    print(f"  Synced: {stats['synced']} entries")
    print(f"  Skipped: {stats['skipped']} entries")
    print(f"  Deleted: {stats['deleted']} entries")
    print(f"  Conflicts: {stats['conflicts']} entries")
    print()

    # 3. Move old ephemeral data to session (tier upgrade)
    print("3. Move ephemeral cache to session tier")
    print("-" * 50)

    stats = await memory.sync(
        source_tier="ephemeral",
        target_tier="session",
        filter=Filter(tags=["cache"]),
        delete_source=True,  # Move operation
        conflict_resolution="source"  # Always use source
    )

    print(f"OK Move operation completed:")
    print(f"  Synced: {stats['synced']} entries")
    print(f"  Deleted from source: {stats['deleted']} entries")
    print()

    # 4. Verify tier contents
    print("4. Verify tier contents after sync")
    print("-" * 50)

    # Check session tier
    session_results = await memory.recall("", k=100, tiers=["session"])
    print(f"OK Session tier: {len(session_results)} entries")
    for entry in session_results:
        print(f"  - {entry.text[:50]}... (importance: {entry.metadata.importance})")

    print()

    # Check persistent tier
    persistent_results = await memory.recall("", k=100, tiers=["persistent"])
    print(f"OK Persistent tier: {len(persistent_results)} entries")
    for entry in persistent_results:
        print(f"  - {entry.text[:50]}... (importance: {entry.metadata.importance})")

    print()

    # 5. Sync with conflict resolution
    print("5. Sync with conflict resolution (newer wins)")
    print("-" * 50)

    # Store duplicate entry in session tier
    await memory.store(
        "User working on project: FastAPI migration",  # Duplicate
        importance=0.80,  # Higher importance
        tags=["session", "project", "active"],
        tier="session"
    )

    stats = await memory.sync(
        source_tier="session",
        target_tier="persistent",
        conflict_resolution="newer"  # Keep newer entry
    )

    print(f"OK Sync with conflict resolution:")
    print(f"  Synced: {stats['synced']} entries")
    print(f"  Conflicts resolved: {stats['conflicts']} entries")
    print(f"  Strategy: Keep newer entry based on last_accessed_at")
    print()

    # 6. Filtered sync by tag
    print("6. Filtered sync by specific tags")
    print("-" * 50)

    # Store tagged memories
    await memory.store(
        "Production deployment scheduled for Friday",
        importance=0.9,
        tags=["important", "deployment"],
        tier="session"
    )

    await memory.store(
        "Remember to update staging environment",
        importance=0.85,
        tags=["important", "reminder"],
        tier="session"
    )

    stats = await memory.sync(
        source_tier="session",
        target_tier="persistent",
        filter=Filter(tags=["important"]),
        delete_source=False
    )

    print(f"OK Synced 'important' tagged entries:")
    print(f"  Synced: {stats['synced']} entries")
    print()

    # 7. Copy operation (replicate across tiers)
    print("7. Replicate critical data across tiers")
    print("-" * 50)

    # Ensure critical data exists in both session and persistent
    stats = await memory.sync(
        source_tier="persistent",
        target_tier="session",
        filter=Filter(min_importance=0.9),
        delete_source=False,  # Copy only
        conflict_resolution="target"  # Keep target if exists
    )

    print(f"OK Replication completed:")
    print(f"  Synced: {stats['synced']} entries")
    print(f"  Skipped (already exists): {stats['skipped']} entries")
    print(f"  Note: Critical data now in both tiers")
    print()

    # 8. Archival pattern (move old data down a tier)
    print("8. Archival: Move old persistent to session")
    print("-" * 50)

    # In real scenario, would use date filters
    stats = await memory.sync(
        source_tier="persistent",
        target_tier="session",
        filter=Filter(max_importance=0.7),  # Lower importance items
        delete_source=True,  # Move to free up persistent tier
        conflict_resolution="source"
    )

    print(f"OK Archival completed:")
    print(f"  Moved: {stats['synced']} entries")
    print(f"  Deleted from persistent: {stats['deleted']} entries")
    print(f"  Purpose: Free up high-value persistent storage")
    print()

    # 9. Final tier statistics
    print("9. Final tier statistics")
    print("-" * 50)

    system_stats = memory.get_statistics()

    print(f"OK System-wide stats:")
    for tier_name, tier_stats in system_stats['tier_stats'].items():
        print(f"\n  {tier_name.upper()} tier:")
        print(f"    Stores: {tier_stats.get('stores', 0)}")
        print(f"    Recalls: {tier_stats.get('recalls', 0)}")

    print()

    print("=" * 50)
    print("* Successfully demonstrated tier synchronization!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * sync() copies or moves memories between tiers")
    print("  * Use filters to selectively sync data")
    print("  * delete_source=True makes it a move operation")
    print("  * Conflict resolution: 'newer', 'source', 'target'")
    print("  * Common patterns:")
    print("    - Promote important session -> persistent")
    print("    - Archive old persistent -> session/ephemeral")
    print("    - Replicate critical data across tiers")
    print("    - Tier rebalancing based on importance")


if __name__ == "__main__":
    asyncio.run(main())
