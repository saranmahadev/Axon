"""
Chatbot with Conversation Memory

Complete chatbot example with multi-tier conversation memory.

Run: python 01_conversation_memory.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy


async def main():
    print("=== Chatbot Conversation Memory ===\n")

    # Chatbot-optimized configuration
    config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=3600,  # 1 hour conversation
            max_entries=100,
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            compaction_threshold=500
        ),
        default_tier="session"
    )

    memory = MemorySystem(config)

    print("Chatbot Configuration:")
    print("  * Session: 1hr TTL, 100 messages")
    print("  * Auto-overflow to persistent")
    print("  * Compaction at 500 entries\n")

    # Simulate conversation
    user_id = "user_123"
    session_id = "chat_abc"

    messages = [
        ("user", "Hi, my name is Alice"),
        ("assistant", "Hello Alice! How can I help you?"),
        ("user", "I'm learning Python"),
        ("assistant", "Great! Python is a versatile language."),
        ("user", "What's my name?"),
        ("assistant", "Your name is Alice."),
    ]

    print("Simulating conversation...")
    for role, content in messages:
        await memory.store(
            f"{role}: {content}",
            tier="session",
            metadata={"user_id": user_id, "session_id": session_id, "role": role},
            tags=["conversation"]
        )

    print(f"  OK Stored {len(messages)} messages\n")

    # Recall context
    print("Recalling conversation context...")
    context = await memory.recall(
        "Alice Python",
        k=5,
        tiers=["session", "persistent"]
    )

    print(f"  Retrieved {len(context)} relevant messages:")
    for entry in context[:3]:
        print(f"    - {entry.text}")

    print()

    print("=" * 50)
    print("* Chatbot memory complete!")


if __name__ == "__main__":
    asyncio.run(main())
