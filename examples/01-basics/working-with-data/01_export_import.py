"""
Export & Import Operations

Learn how to export memories for backup, migration, or archival purposes,
and how to import them back into a memory system.

Learn:
- Exporting all memories to JSON
- Exporting specific tiers
- Filtered exports
- Importing from backups
- Tier remapping during import
- Conflict resolution strategies

Run:
    python 01_export_import.py
"""

import asyncio
import json
from pathlib import Path
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    """Demonstrate export and import operations."""
    print("=== Axon Export & Import Operations ===\n")

    # Create memory system and populate with sample data
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Setting up sample data...")
    print("-" * 50)

    # Create diverse sample memories
    sample_data = [
        ("User prefers dark mode", 0.8, ["preferences", "ui"], "user_123", "persistent"),
        ("API key for OpenAI", 0.95, ["credentials"], "user_123", "persistent"),
        ("Recent search query: async patterns", 0.3, ["cache"], "user_123", "ephemeral"),
        ("User timezone: UTC-5", 0.7, ["preferences"], "user_123", "session"),
        ("Completed Python tutorial", 0.6, ["achievements"], "user_123", "persistent"),
        ("Login from 192.168.1.1", 0.4, ["logs"], "user_456", "ephemeral"),
    ]

    for content, importance, tags, user_id, tier in sample_data:
        await memory.store(
            content,
            importance=importance,
            tags=tags,
            metadata={"user_id": user_id},
            tier=tier
        )

    print(f"OK Created {len(sample_data)} sample memories\n")

    # 2. Export all memories
    print("2. Export all memories")
    print("-" * 50)

    export_data = await memory.export()

    print(f"OK Export completed:")
    print(f"  Version: {export_data['version']}")
    print(f"  Exported at: {export_data['exported_at']}")
    print(f"  Total entries: {export_data['statistics']['total_entries']}")
    print(f"  Tiers: {', '.join(export_data['config']['tiers'])}")
    print(f"\n  Breakdown by tier:")
    for tier, count in export_data['statistics']['by_tier'].items():
        print(f"    {tier}: {count} entries")
    print()

    # 3. Export specific tier
    print("3. Export specific tier (persistent only)")
    print("-" * 50)

    persistent_export = await memory.export(tier="persistent")

    print(f"OK Persistent tier export:")
    print(f"  Total entries: {persistent_export['statistics']['total_entries']}")
    print(f"  Entries:")
    for entry in persistent_export['entries']:
        print(f"    - {entry['text'][:50]}...")
    print()

    # 4. Export with filters
    print("4. Export with filters (user_123 only)")
    print("-" * 50)

    filtered_export = await memory.export(
        filter=Filter(user_id="user_123")
    )

    print(f"OK Filtered export:")
    print(f"  Total entries: {filtered_export['statistics']['total_entries']}")
    print(f"  All entries belong to user_123")
    print()

    # 5. Export without embeddings (smaller file size)
    print("5. Export without embeddings")
    print("-" * 50)

    compact_export = await memory.export(include_embeddings=False)

    print(f"OK Compact export (no embeddings):")
    print(f"  Total entries: {compact_export['statistics']['total_entries']}")
    print(f"  Includes embeddings: {compact_export['statistics']['include_embeddings']}")
    print(f"  Note: Smaller file size, faster serialization")
    print()

    # 6. Save export to file
    print("6. Save export to JSON file")
    print("-" * 50)

    backup_path = Path("memory_backup.json")

    with open(backup_path, "w") as f:
        json.dump(export_data, f, indent=2)

    file_size = backup_path.stat().st_size / 1024  # KB

    print(f"OK Saved to: {backup_path}")
    print(f"  File size: {file_size:.2f} KB")
    print()

    # 7. Create new memory system for import demonstration
    print("7. Import into new memory system")
    print("-" * 50)

    memory2 = MemorySystem(DEVELOPMENT_CONFIG)

    # Load from file
    with open(backup_path, "r") as f:
        loaded_data = json.load(f)

    import_stats = await memory2.import_from(loaded_data)

    print(f"OK Import completed:")
    print(f"  Imported: {import_stats['imported']} entries")
    print(f"  Skipped: {import_stats['skipped']} entries")
    print(f"  Errors: {import_stats['errors']} entries")
    print(f"\n  Breakdown by tier:")
    for tier, count in import_stats['by_tier'].items():
        print(f"    {tier}: {count} entries")
    print()

    # 8. Verify import
    print("8. Verify imported data")
    print("-" * 50)

    results = await memory2.recall("user preferences", k=5)

    print(f"OK Retrieved {len(results)} memories from imported system:")
    for entry in results:
        print(f"  - {entry.text[:50]}...")
    print()

    # 9. Import with tier remapping
    print("9. Import with tier remapping")
    print("-" * 50)

    memory3 = MemorySystem(DEVELOPMENT_CONFIG)

    # Remap ephemeral -> session tier
    import_stats = await memory3.import_from(
        loaded_data,
        tier_mapping={"ephemeral": "session"}
    )

    print(f"OK Import with remapping (ephemeral -> session):")
    print(f"  Imported: {import_stats['imported']} entries")
    print(f"  Breakdown by target tier:")
    for tier, count in import_stats['by_tier'].items():
        print(f"    {tier}: {count} entries")
    print()

    # 10. Import with overwrite
    print("10. Import with overwrite (duplicate handling)")
    print("-" * 50)

    # Import again without overwrite (should skip duplicates)
    import_stats_no_overwrite = await memory2.import_from(
        loaded_data,
        overwrite=False
    )

    print(f"OK Import without overwrite:")
    print(f"  Imported: {import_stats_no_overwrite['imported']}")
    print(f"  Skipped: {import_stats_no_overwrite['skipped']} (duplicates)")

    # Import with overwrite
    import_stats_overwrite = await memory2.import_from(
        loaded_data,
        overwrite=True
    )

    print(f"\nOK Import with overwrite:")
    print(f"  Imported: {import_stats_overwrite['imported']}")
    print(f"  Skipped: {import_stats_overwrite['skipped']}")
    print()

    # Cleanup
    backup_path.unlink()
    print(f"OK Cleaned up backup file\n")

    print("=" * 50)
    print("* Successfully demonstrated export & import!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * export() creates JSON-serializable backups")
    print("  * Filter exports by tier, user, tags, etc.")
    print("  * Exclude embeddings for smaller file sizes")
    print("  * import_from() restores from backups")
    print("  * Tier remapping allows flexible restoration")
    print("  * Overwrite controls duplicate handling")
    print("  * Use for: backups, migrations, testing, archival")


if __name__ == "__main__":
    asyncio.run(main())
