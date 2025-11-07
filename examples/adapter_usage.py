"""Example demonstrating storage adapter usage.

This example shows how to use the InMemoryAdapter for basic CRUD operations
and vector similarity search with the Axon memory system.
"""

import asyncio

from axon import Filter, InMemoryAdapter, MemoryEntry


async def main():
    """Demonstrate adapter usage with async/await."""
    print("=" * 60)
    print("Axon Storage Adapter Example")
    print("=" * 60)

    # Create an in-memory adapter
    adapter = InMemoryAdapter()
    print(f"\n✅ Created InMemoryAdapter (count: {adapter.count()})")

    # 1. Save individual entries
    print("\n--- Saving Entries ---")

    entry1 = MemoryEntry(
        text="User loves Python programming and machine learning",
        type="note",
        embedding=[0.8, 0.6, 0.1, 0.2, 0.1],
        metadata={"user_id": "u123", "topic": "programming", "priority": "high"},
    )

    entry2 = MemoryEntry(
        text="User prefers sci-fi movies, especially Dune",
        type="note",
        embedding=[0.1, 0.2, 0.9, 0.7, 0.3],
        metadata={"user_id": "u123", "topic": "movies", "priority": "medium"},
    )

    entry3 = MemoryEntry(
        text="User mentioned interest in deep learning frameworks",
        type="note",
        embedding=[0.7, 0.5, 0.2, 0.3, 0.1],
        metadata={"user_id": "u123", "topic": "programming", "priority": "high"},
    )

    id1 = await adapter.save(entry1)
    id2 = await adapter.save(entry2)
    id3 = await adapter.save(entry3)

    print(f"Saved entry 1: {id1[:8]}... | {entry1.text[:50]}")
    print(f"Saved entry 2: {id2[:8]}... | {entry2.text[:50]}")
    print(f"Saved entry 3: {id3[:8]}... | {entry3.text[:50]}")
    print(f"Total entries: {adapter.count()}")

    # 2. Retrieve by ID
    print("\n--- Retrieving by ID ---")
    retrieved = await adapter.get(id1)
    print(f"Retrieved: {retrieved.text}")
    print(f"User ID: {retrieved.metadata.user_id}")
    print(f"Topic: {retrieved.metadata.topic}")
    print(f"Priority: {retrieved.metadata.priority}")

    # 3. Vector similarity search
    print("\n--- Vector Similarity Search ---")
    # Query with vector similar to programming-related entries
    query_vector = [0.75, 0.55, 0.15, 0.25, 0.1]
    results = await adapter.query(vector=query_vector, k=2)

    print(f"Query vector: {query_vector}")
    print(f"\nTop {len(results)} similar entries:")
    for i, entry in enumerate(results, 1):
        print(f"  {i}. {entry.text[:60]}...")
        print(f"     Topic: {entry.metadata.topic}")

    # 4. Filtered search
    print("\n--- Filtered Search ---")
    # Only search programming-related entries
    filter_programming = Filter(custom={"topic": "programming"})
    filtered_results = await adapter.query(vector=query_vector, k=10, filter=filter_programming)

    print("Filter: topic='programming'")
    print(f"Found {len(filtered_results)} matches:")
    for entry in filtered_results:
        print(f"  - {entry.text[:60]}...")

    # 5. Bulk save
    print("\n--- Bulk Save ---")
    new_entries = [
        MemoryEntry(
            text=f"Bulk entry {i}: Some information",
            type="note",
            embedding=[0.1 * i, 0.2, 0.3, 0.4, 0.5],
            metadata={"batch": "demo"},
        )
        for i in range(3)
    ]

    bulk_ids = await adapter.bulk_save(new_entries)
    print(f"Bulk saved {len(bulk_ids)} entries")
    print(f"Total entries now: {adapter.count()}")

    # 6. Delete entry
    print("\n--- Deleting Entry ---")
    deleted = await adapter.delete(id2)
    print(f"Deleted entry {id2[:8]}...: {deleted}")
    print(f"Remaining entries: {adapter.count()}")

    # Try to get deleted entry (should raise KeyError)
    try:
        await adapter.get(id2)
    except KeyError:
        print("✅ Confirmed: Deleted entry not found")

    # 7. List all IDs
    print("\n--- List All IDs ---")
    all_ids = adapter.list_ids()
    print(f"All entry IDs ({len(all_ids)} total):")
    for entry_id in all_ids[:5]:  # Show first 5
        print(f"  - {entry_id[:8]}...")
    if len(all_ids) > 5:
        print(f"  ... and {len(all_ids) - 5} more")

    # 8. Clear storage
    print("\n--- Clearing Storage ---")
    adapter.clear()
    print(f"Cleared all entries. Count: {adapter.count()}")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


def sync_example():
    """Demonstrate synchronous API usage."""
    print("\n" + "=" * 60)
    print("Synchronous API Example")
    print("=" * 60)

    adapter = InMemoryAdapter()

    # Using sync wrappers
    entry = MemoryEntry(
        text="Synchronous save example",
        type="note",
        embedding=[0.5, 0.5, 0.5, 0.5, 0.5],
    )

    entry_id = adapter.save_sync(entry)
    print(f"\n✅ Saved (sync): {entry_id[:8]}...")

    retrieved = adapter.get_sync(entry_id)
    print(f"✅ Retrieved (sync): {retrieved.text}")

    results = adapter.query_sync(vector=[0.5, 0.5, 0.5, 0.5, 0.5], k=1)
    print(f"✅ Query (sync): Found {len(results)} results")

    deleted = adapter.delete_sync(entry_id)
    print(f"✅ Deleted (sync): {deleted}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run async example
    asyncio.run(main())

    # Run sync example
    sync_example()
