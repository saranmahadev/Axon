"""
Session State Management

Manage user session state with automatic expiration.

Run: python 03_session_management.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy
from axon.models.filter import Filter


async def main():
    print("=== Session State Management ===\n")

    # Session-optimized config
    config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=1800,  # 30 minutes
            max_entries=50
        ),
        persistent=PersistentPolicy(
            adapter_type="memory"
        ),
        default_tier="session"
    )

    memory = MemorySystem(config)

    session_id = "sess_abc123"
    user_id = "user_456"

    print("1. Tracking session activities...")

    activities = [
        "User viewed homepage",
        "User added item to cart: Product A",
        "User viewed product details: Product B",
        "User updated cart quantity",
        "User proceeded to checkout"
    ]

    for activity in activities:
        await memory.store(
            activity,
            tier="session",
            tags=["activity"],
            metadata={"session_id": session_id, "user_id": user_id}
        )

    print(f"  OK Tracked {len(activities)} activities\n")

    # Recall session history
    print("2. Retrieving session history...")
    history = await memory.recall(
        "",
        k=100,
        filter=Filter(session_id=session_id)
    )

    print(f"  Session activities ({len(history)}):")
    for entry in history:
        print(f"    * {entry.text}")

    print()

    # Session analytics
    print("3. Session analytics...")
    cart_activities = await memory.recall(
        "cart",
        k=100,
        filter=Filter(session_id=session_id)
    )

    print(f"  Cart-related activities: {len(cart_activities)}")
    print(f"  Session expires in: 30 minutes")
    print(f"  Entries auto-deleted after expiration\n")

    print("=" * 50)
    print("* Session management complete!")


if __name__ == "__main__":
    asyncio.run(main())
