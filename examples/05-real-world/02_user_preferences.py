"""
User Preferences Management

Manage user preferences with automatic persistence and recall.

Run: python 02_user_preferences.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.filter import Filter


async def main():
    print("=== User Preferences Management ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    user_id = "user_12345"

    print("1. Storing user preferences...")

    preferences = [
        ("theme", "dark"),
        ("language", "en"),
        ("timezone", "UTC-5"),
        ("notifications", "enabled"),
        ("font_size", "medium")
    ]

    for key, value in preferences:
        await memory.store(
            f"User preference: {key} = {value}",
            importance=0.9,  # High importance for preferences
            tier="persistent",
            tags=["preferences", key],
            metadata={"user_id": user_id, "pref_key": key}
        )

    print(f"  OK Stored {len(preferences)} preferences\n")

    # Recall specific preference
    print("2. Recalling specific preference (theme)...")
    results = await memory.recall(
        "theme preference",
        k=1,
        filter=Filter(user_id=user_id, tags=["theme"])
    )

    if results:
        print(f"  -> {results[0].text}\n")

    # Recall all preferences
    print("3. Recalling all user preferences...")
    all_prefs = await memory.recall(
        "",  # Empty query
        k=100,
        filter=Filter(user_id=user_id, tags=["preferences"])
    )

    print(f"  Found {len(all_prefs)} preferences:")
    for pref in all_prefs:
        print(f"    * {pref.text}")

    print()

    # Update preference
    print("4. Updating preference (theme = light)...")
    await memory.store(
        "User preference: theme = light",
        importance=0.9,
        tier="persistent",
        tags=["preferences", "theme"],
        metadata={"user_id": user_id, "pref_key": "theme"}
    )

    print("  OK Preference updated\n")

    print("=" * 50)
    print("* User preferences complete!")


if __name__ == "__main__":
    asyncio.run(main())
