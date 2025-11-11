"""
Store Operations - Comprehensive Guide

Learn different ways to store memories with various metadata, importance
scores, tags, and explicit tier selection.

Learn:
- Basic store operations
- Storing with metadata and tags
- Setting importance scores
- Explicit tier selection
- User and session context

Run:
    python 01_store_operations.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    """Demonstrate various store operations."""
    print("=== Axon Store Operations ===\n")

    # Create memory system
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    print("Memory system initialized\n")

    # 1. Basic store (minimal)
    print("1. Basic store with text only:")
    entry_id1 = await memory.store("The user's favorite color is blue.")
    print(f"   OK Stored entry: {entry_id1}")
    print(f"   Default importance: 0.5\n")

    # 2. Store with importance score
    print("2. Store with explicit importance:")
    entry_id2 = await memory.store(
        "Critical API key: sk-abc123xyz",
        importance=0.95  # Very important
    )
    print(f"   OK Stored entry: {entry_id2}")
    print(f"   Importance: 0.95 (high priority)\n")

    # 3. Store with tags for categorization
    print("3. Store with tags:")
    entry_id3 = await memory.store(
        "User prefers dark mode in settings",
        importance=0.7,
        tags=["preferences", "ui", "settings"]
    )
    print(f"   OK Stored entry: {entry_id3}")
    print(f"   Tags: preferences, ui, settings\n")

    # 4. Store with metadata (user/session context)
    print("4. Store with user and session context:")
    entry_id4 = await memory.store(
        "User completed onboarding tutorial",
        importance=0.6,
        metadata={
            "user_id": "user_12345",
            "session_id": "session_abc",
            "source": "onboarding_flow"
        },
        tags=["milestone", "onboarding"]
    )
    print(f"   OK Stored entry: {entry_id4}")
    print(f"   User: user_12345, Session: session_abc\n")

    # 5. Store with explicit tier selection
    print("5. Store with explicit tier (ephemeral):")
    entry_id5 = await memory.store(
        "Temporary cache: recent search query",
        tier="ephemeral",  # Force to ephemeral tier
        tags=["cache", "temporary"]
    )
    print(f"   OK Stored entry: {entry_id5}")
    print(f"   Tier: ephemeral (short-lived)\n")

    # 6. Store with explicit tier (persistent)
    print("6. Store with explicit tier (persistent):")
    entry_id6 = await memory.store(
        "User's account creation date: 2025-01-15",
        importance=0.9,
        tier="persistent",  # Force to persistent tier
        tags=["account", "metadata"]
    )
    print(f"   OK Stored entry: {entry_id6}")
    print(f"   Tier: persistent (long-term storage)\n")

    # 7. Batch store multiple memories
    print("7. Batch store multiple related memories:")
    user_preferences = [
        ("Language preference: English", ["preferences", "language"]),
        ("Timezone: UTC-5", ["preferences", "timezone"]),
        ("Newsletter opt-in: True", ["preferences", "notifications"])
    ]

    for content, tags in user_preferences:
        entry_id = await memory.store(
            content,
            importance=0.7,
            metadata={"user_id": "user_12345", "category": "preferences"},
            tags=tags
        )
        print(f"   OK Stored: {content[:40]}...")

    print("\n" + "=" * 50)
    print("* Successfully demonstrated all store operations!")
    print("=" * 50)
    print("\nKey Takeaways:")
    print("  * Default importance is 0.5")
    print("  * Higher importance (0.8-1.0) promotes to better tiers")
    print("  * Tags help with categorization and filtering")
    print("  * Metadata adds context (user_id, session_id, source)")
    print("  * Explicit tier selection overrides automatic routing")


if __name__ == "__main__":
    asyncio.run(main())
