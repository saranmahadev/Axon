"""
Advanced Metadata Filtering

Learn how to use powerful filtering capabilities to query memories by user,
session, tags, importance, date ranges, privacy levels, and custom metadata.

Learn:
- Filter by user_id and session_id
- Tag-based filtering (AND logic)
- Importance range filtering
- Date range queries
- Privacy level filtering
- Custom metadata filters
- Combining multiple filters

Run:
    python 03_metadata_filtering.py
"""

import asyncio
from datetime import datetime, timedelta
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter, DateRange
from axon.models.base import PrivacyLevel


async def main():
    """Demonstrate advanced metadata filtering."""
    print("=== Axon Metadata Filtering ===\n")

    # Create memory system and populate with diverse data
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Setting up diverse sample data...")
    print("-" * 50)

    # Create memories with various metadata combinations
    now = datetime.now()

    sample_data = [
        # User 123 - Session A
        ("User prefers dark mode", 0.8, ["preferences", "ui"], "user_123", "session_a", "internal"),
        ("API key: sk-test123", 0.95, ["credentials", "api"], "user_123", "session_a", "restricted"),
        ("Favorite color is blue", 0.6, ["preferences", "personal"], "user_123", "session_a", "public"),

        # User 123 - Session B
        ("Completed Python tutorial", 0.7, ["achievements", "learning"], "user_123", "session_b", "public"),
        ("Working on FastAPI project", 0.75, ["project", "work"], "user_123", "session_b", "internal"),

        # User 456 - Session C
        ("Recent search: machine learning", 0.4, ["search", "temporary"], "user_456", "session_c", "public"),
        ("Failed login attempt", 0.5, ["security", "logs"], "user_456", "session_c", "internal"),
        ("User timezone: UTC-8", 0.7, ["preferences", "timezone"], "user_456", "session_c", "public"),

        # System entries
        ("System maintenance scheduled", 0.9, ["system", "important"], None, None, "internal"),
        ("Database backup completed", 0.6, ["system", "logs"], None, None, "internal"),
    ]

    for content, importance, tags, user_id, session_id, privacy in sample_data:
        metadata = {}
        if user_id:
            metadata["user_id"] = user_id
        if session_id:
            metadata["session_id"] = session_id
        if privacy:
            metadata["privacy_level"] = privacy

        await memory.store(
            content,
            importance=importance,
            tags=tags,
            metadata=metadata
        )

    print(f"OK Created {len(sample_data)} diverse memories\n")

    # 2. Filter by user_id
    print("2. Filter by user_id")
    print("-" * 50)

    results = await memory.recall(
        "",  # Empty query gets all
        k=100,
        filter=Filter(user_id="user_123")
    )

    print(f"OK Found {len(results)} memories for user_123:")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # 3. Filter by session_id
    print("3. Filter by session_id")
    print("-" * 50)

    results = await memory.recall(
        "",
        k=100,
        filter=Filter(session_id="session_a")
    )

    print(f"OK Found {len(results)} memories for session_a:")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # 4. Filter by tags (AND logic - must have ALL tags)
    print("4. Filter by tags (AND logic)")
    print("-" * 50)

    results = await memory.recall(
        "",
        k=100,
        filter=Filter(tags=["preferences"])
    )

    print(f"OK Found {len(results)} memories with 'preferences' tag:")
    for entry in results:
        print(f"  - {entry.text[:40]}... Tags: {entry.metadata.tags}")
    print()

    # Multiple tags (must have both)
    results = await memory.recall(
        "",
        k=100,
        filter=Filter(tags=["preferences", "ui"])
    )

    print(f"OK Found {len(results)} memories with both 'preferences' AND 'ui' tags:")
    for entry in results:
        print(f"  - {entry.text[:40]}... Tags: {entry.metadata.tags}")
    print()

    # 5. Filter by importance range
    print("5. Filter by importance range")
    print("-" * 50)

    # High importance only
    results = await memory.recall(
        "",
        k=100,
        filter=Filter(min_importance=0.8)
    )

    print(f"OK High importance (>=0.8): {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:40]}... (importance: {entry.metadata.importance})")
    print()

    # Medium importance range
    results = await memory.recall(
        "",
        k=100,
        filter=Filter(min_importance=0.5, max_importance=0.7)
    )

    print(f"OK Medium importance (0.5-0.7): {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:40]}... (importance: {entry.metadata.importance})")
    print()

    # 6. Filter by privacy level
    print("6. Filter by privacy level")
    print("-" * 50)

    # Public memories only
    results = await memory.recall(
        "",
        k=100,
        filter=Filter(privacy_level="public")
    )

    print(f"OK Public memories: {len(results)} entries")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # Restricted/sensitive data
    results = await memory.recall(
        "",
        k=100,
        filter=Filter(privacy_level="restricted")
    )

    print(f"OK Restricted memories: {len(results)} entries")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # 7. Combine multiple filters
    print("7. Combine multiple filters (AND logic)")
    print("-" * 50)

    results = await memory.recall(
        "",
        k=100,
        filter=Filter(
            user_id="user_123",
            tags=["preferences"],
            min_importance=0.6
        )
    )

    print(f"OK Complex filter (user_123 + preferences + importance>=0.6):")
    print(f"  Found: {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:40]}...")
        print(f"    User: {entry.metadata.user_id}")
        print(f"    Tags: {entry.metadata.tags}")
        print(f"    Importance: {entry.metadata.importance}")
    print()

    # 8. Session + user combination
    print("8. Filter by user AND session")
    print("-" * 50)

    results = await memory.recall(
        "",
        k=100,
        filter=Filter(
            user_id="user_123",
            session_id="session_a"
        )
    )

    print(f"OK User 123's session A: {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # 9. Tag + privacy combination
    print("9. Filter by tags AND privacy level")
    print("-" * 50)

    results = await memory.recall(
        "",
        k=100,
        filter=Filter(
            tags=["system"],
            privacy_level="internal"
        )
    )

    print(f"OK Internal system entries: {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:45]}...")
    print()

    # 10. Complex multi-criteria filter
    print("10. Complex multi-criteria filter")
    print("-" * 50)

    results = await memory.recall(
        "user preferences",  # Semantic query
        k=10,
        filter=Filter(
            user_id="user_123",
            tags=["preferences"],
            min_importance=0.5,
            privacy_level="public"
        )
    )

    print(f"OK Semantic query + complex filter:")
    print(f"  Query: 'user preferences'")
    print(f"  Filters: user_123, preferences tag, importance>=0.5, public")
    print(f"  Found: {len(results)} memories")
    for entry in results:
        print(f"  - {entry.text[:40]}...")
    print()

    # 11. Filter semantics demonstration
    print("11. Understanding filter behavior")
    print("-" * 50)

    # No filters - get everything
    all_results = await memory.recall("", k=100)
    print(f"OK No filter: {len(all_results)} total memories")

    # Single filter
    user_results = await memory.recall("", k=100, filter=Filter(user_id="user_123"))
    print(f"OK User filter only: {len(user_results)} memories")

    # Multiple filters (AND)
    combined = await memory.recall(
        "",
        k=100,
        filter=Filter(user_id="user_123", tags=["preferences"])
    )
    print(f"OK User + tag filter (AND): {len(combined)} memories")
    print(f"  Note: Filters use AND logic (all conditions must match)")
    print()

    print("=" * 50)
    print("* Successfully demonstrated metadata filtering!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * Filters support: user, session, tags, importance, privacy")
    print("  * Multiple filters use AND logic (all must match)")
    print("  * Tags filter requires ALL specified tags")
    print("  * Importance filters support min/max ranges")
    print("  * Privacy levels: public, internal, sensitive, restricted")
    print("  * Combine filters with semantic queries")
    print("  * Empty query ('') with filters returns all matching entries")


if __name__ == "__main__":
    asyncio.run(main())
