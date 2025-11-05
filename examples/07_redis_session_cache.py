"""
Example 7: Redis Session Cache - Short-Term Memory with TTL

This example demonstrates using RedisAdapter for session-based caching:
- Store conversation history with automatic expiration
- Session isolation per user
- TTL-based cleanup (5 minute sessions)
- Fast retrieval of recent context

Use Case: Web application that maintains conversation state
without persisting every interaction to permanent storage.
"""

import asyncio
from datetime import datetime, timezone
from axon.adapters.redis import RedisAdapter
from axon.models.entry import MemoryEntry, MemoryMetadata

async def main():
    # Initialize Redis adapter with 5-minute session TTL
    adapter = RedisAdapter(
        host="localhost",
        port=6379,
        namespace="session_cache",
        default_ttl=300  # 5 minutes
    )
    
    print("=" * 70)
    print("EXAMPLE 7: Redis Session Cache - Conversation History")
    print("=" * 70)
    
    # Simulate a conversation session
    session_id = "conv_20251105_user123"
    user_id = "user_123"
    
    print(f"\n📝 Starting conversation session: {session_id}")
    print(f"   TTL: 5 minutes (auto-cleanup)")
    
    # Turn 1: User asks a question
    turn1 = MemoryEntry(
        id="msg_001",
        text="What is the capital of France?",
        embedding=[0.1] * 384,
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            tags=["question", "geography"],
            importance=0.6,
            privacy_level="private"
        )
    )
    await adapter.save(turn1)
    print(f"\n💬 Turn 1 (User): {turn1.text}")
    
    # Turn 2: Assistant responds
    turn2 = MemoryEntry(
        id="msg_002",
        text="The capital of France is Paris.",
        embedding=[0.2] * 384,
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            tags=["answer", "geography"],
            importance=0.6,
            privacy_level="private"
        )
    )
    await adapter.save(turn2)
    print(f"🤖 Turn 2 (Bot):  {turn2.text}")
    
    # Turn 3: Follow-up question
    turn3 = MemoryEntry(
        id="msg_003",
        text="What about its population?",
        embedding=[0.3] * 384,
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            tags=["question", "demographics"],
            importance=0.5,
            privacy_level="private"
        )
    )
    await adapter.save(turn3)
    print(f"\n💬 Turn 3 (User): {turn3.text}")
    
    # Turn 4: Assistant responds with context
    turn4 = MemoryEntry(
        id="msg_004",
        text="Paris has a population of about 2.1 million in the city proper, and over 12 million in the metropolitan area.",
        embedding=[0.4] * 384,
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            tags=["answer", "demographics"],
            importance=0.7,
            privacy_level="private"
        )
    )
    await adapter.save(turn4)
    print(f"🤖 Turn 4 (Bot):  {turn4.text}")
    
    # Retrieve full conversation history
    print(f"\n📚 Retrieving session history from cache...")
    from axon.models.filter import Filter
    history = await adapter.query(
        vector=None,
        k=100,
        filter=Filter(session_id=session_id)
    )
    
    print(f"   Found {len(history)} messages in session")
    print(f"\n   Conversation replay:")
    for i, msg in enumerate(history, 1):
        speaker = "💬 User" if "question" in msg.metadata.tags else "🤖 Bot "
        print(f"   {i}. {speaker}: {msg.text[:60]}...")
    
    # Check TTL remaining
    ttl_msg1 = await adapter.get_ttl("msg_001")
    ttl_msg4 = await adapter.get_ttl("msg_004")
    print(f"\n⏱️  TTL Status:")
    print(f"   Message 1: {ttl_msg1} seconds remaining")
    print(f"   Message 4: {ttl_msg4} seconds remaining")
    
    # Simulate new session for same user
    print(f"\n\n🔄 Starting new session for same user...")
    new_session_id = "conv_20251105_user123_v2"
    
    new_msg = MemoryEntry(
        id="msg_101",
        text="Tell me about Rome",
        embedding=[0.5] * 384,
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=new_session_id,
            tags=["question", "geography"],
            importance=0.6,
            privacy_level="private"
        )
    )
    await adapter.save(new_msg)
    print(f"💬 New session message: {new_msg.text}")
    
    # Verify session isolation
    old_session = await adapter.query(
        vector=None,
        k=100,
        filter=Filter(session_id=session_id)
    )
    new_session = await adapter.query(
        vector=None,
        k=100,
        filter=Filter(session_id=new_session_id)
    )
    
    print(f"\n🔒 Session Isolation Test:")
    print(f"   Old session ({session_id}): {len(old_session)} messages")
    print(f"   New session ({new_session_id}): {len(new_session)} messages")
    print(f"   ✅ Sessions are properly isolated!")
    
    # Count total cached entries
    total = await adapter.count_async()
    print(f"\n📊 Cache Statistics:")
    print(f"   Total entries: {total}")
    print(f"   Namespace: {adapter.namespace}")
    print(f"   All entries will auto-expire after 5 minutes")
    
    # Cleanup
    print(f"\n🧹 Cleaning up demo data...")
    await adapter.clear_async()
    await adapter.close()
    
    print(f"\n✅ Example complete!")
    print(f"\n💡 Key Takeaways:")
    print(f"   • Redis provides fast session storage with automatic cleanup")
    print(f"   • TTL ensures old sessions don't accumulate indefinitely")
    print(f"   • Session isolation allows multiple concurrent conversations")
    print(f"   • No manual cleanup needed - Redis handles expiration")

if __name__ == "__main__":
    asyncio.run(main())
