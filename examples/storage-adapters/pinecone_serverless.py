"""Pinecone Serverless Multi-User Application Example

This example demonstrates:
- Multi-user memory isolation with namespaces
- Session-based memory management
- Privacy levels (public vs private memories)
- Real-world conversation tracking
- Efficient bulk operations
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.axon.adapters import PineconeAdapter
from src.axon.models import Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent

# Load environment variables
load_dotenv()


class ConversationMemoryManager:
    """Manages conversation memories for multiple users in Pinecone."""

    def __init__(self, api_key: str, index_name: str = "axon-conversations"):
        self.api_key = api_key
        self.index_name = index_name

    def get_user_adapter(self, user_id: str) -> PineconeAdapter:
        """Get a Pinecone adapter for a specific user's namespace."""
        return PineconeAdapter(
            api_key=self.api_key,
            index_name=self.index_name,
            namespace=f"user_{user_id}",
            cloud="aws",
            region="us-east-1",
        )

    async def store_conversation_turn(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        embedding: list[float],
        privacy_level: str = "private",
        importance: float = 0.5,
    ):
        """Store a conversation turn (user message + assistant response)."""
        adapter = self.get_user_adapter(user_id)

        # Combine user message and assistant response into one memory
        combined_text = f"User: {user_message}\nAssistant: {assistant_response}"

        entry = MemoryEntry(
            id=str(uuid4()),
            text=combined_text,
            embedding=embedding,
            metadata=MemoryMetadata(
                source="app",
                user_id=user_id,
                session_id=session_id,
                privacy_level=privacy_level,
                tags=["conversation", "chat"],
                importance=importance,
                provenance=[
                    ProvenanceEvent(
                        action="store",
                        by="conversation_manager",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
            ),
        )

        await adapter.save(entry)
        return entry.id

    async def get_session_history(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> list[MemoryEntry]:
        """Retrieve conversation history for a specific session."""
        adapter = self.get_user_adapter(user_id)

        # Use a dummy query vector (in production, use actual embeddings)
        dummy_query = [0.1] * 384

        # Filter by session
        session_filter = Filter(session_id=session_id)

        results = await adapter.query(embedding=dummy_query, filter=session_filter, limit=limit)

        return results

    async def get_user_stats(self, user_id: str) -> dict:
        """Get statistics for a user's memories."""
        adapter = self.get_user_adapter(user_id)

        total_count = await adapter.count_async()
        all_ids = await adapter.list_ids_async()

        return {
            "user_id": user_id,
            "total_memories": total_count,
            "memory_ids": all_ids[:5],  # First 5 IDs
            "has_more": total_count > 5,
        }

    async def cleanup_old_sessions(self, user_id: str, days_old: int = 30):
        """Delete memories from sessions older than specified days."""
        adapter = self.get_user_adapter(user_id)

        # Get all memories
        all_ids = await adapter.list_ids_async()
        deleted_count = 0

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        for memory_id in all_ids:
            memory = await adapter.get(memory_id)
            if memory and memory.metadata.created_at < cutoff_date:
                await adapter.delete(memory_id)
                deleted_count += 1

        return deleted_count


async def main():
    """Demonstrate multi-user conversation memory management."""

    print("🚀 Initializing Multi-User Conversation System with Pinecone\n")

    manager = ConversationMemoryManager(api_key=os.getenv("PINECONE_API_KEY"))

    # Simple embedding function for demo
    def create_embedding(text: str) -> list[float]:
        return [hash(text + str(i)) % 1000 / 1000.0 for i in range(384)]

    # Simulate conversations for different users
    print("💬 Simulating conversations for multiple users...\n")

    # User 1: Alice - asking about Python
    print("👤 User: alice_001")
    print("   Session: morning_session")

    alice_turns = [
        ("What is Python?", "Python is a high-level programming language known for readability."),
        (
            "How do I install packages?",
            "You can use pip to install packages: pip install package_name",
        ),
        ("What are virtual environments?", "Virtual environments isolate project dependencies."),
    ]

    for i, (user_msg, assistant_msg) in enumerate(alice_turns, 1):
        memory_id = await manager.store_conversation_turn(
            user_id="alice_001",
            session_id="morning_session",
            user_message=user_msg,
            assistant_response=assistant_msg,
            embedding=create_embedding(user_msg + assistant_msg),
            privacy_level="private",
            importance=0.7 + (i * 0.1),
        )
        print(f"   ✓ Stored turn {i}: {memory_id[:16]}...")

    print()

    # User 2: Bob - asking about machine learning
    print("👤 User: bob_002")
    print("   Session: afternoon_session")

    bob_turns = [
        ("What is machine learning?", "Machine learning is a subset of AI that learns from data."),
        (
            "What's the difference between supervised and unsupervised learning?",
            "Supervised learning uses labeled data, unsupervised finds patterns in unlabeled data.",
        ),
    ]

    for i, (user_msg, assistant_msg) in enumerate(bob_turns, 1):
        memory_id = await manager.store_conversation_turn(
            user_id="bob_002",
            session_id="afternoon_session",
            user_message=user_msg,
            assistant_response=assistant_msg,
            embedding=create_embedding(user_msg + assistant_msg),
            privacy_level="public",
            importance=0.85,
        )
        print(f"   ✓ Stored turn {i}: {memory_id[:16]}...")

    print()

    # Wait for indexing
    await asyncio.sleep(2)

    # Retrieve Alice's session history
    print("📜 Retrieving Alice's morning session history...")
    alice_history = await manager.get_session_history(
        user_id="alice_001", session_id="morning_session", limit=10
    )

    print(f"   Found {len(alice_history)} conversation turns:\n")
    for i, memory in enumerate(alice_history, 1):
        lines = memory.text.split("\n")
        print(f"   Turn {i}:")
        for line in lines:
            print(f"      {line}")
        print(f"      Importance: {memory.metadata.importance}")
        print()

    # Get user statistics
    print("📊 User Statistics:\n")

    alice_stats = await manager.get_user_stats("alice_001")
    print("   Alice (alice_001):")
    print(f"      Total memories: {alice_stats['total_memories']}")
    print(f"      Sample IDs: {alice_stats['memory_ids']}\n")

    bob_stats = await manager.get_user_stats("bob_002")
    print("   Bob (bob_002):")
    print(f"      Total memories: {bob_stats['total_memories']}")
    print(f"      Sample IDs: {bob_stats['memory_ids']}\n")

    # Demonstrate namespace isolation
    print("🔒 Demonstrating namespace isolation...")
    print("   Alice's adapter can only see Alice's memories")
    print("   Bob's adapter can only see Bob's memories\n")

    alice_adapter = manager.get_user_adapter("alice_001")
    alice_count = await alice_adapter.count_async()
    print(f"   Alice's namespace: {alice_count} memories")

    bob_adapter = manager.get_user_adapter("bob_002")
    bob_count = await bob_adapter.count_async()
    print(f"   Bob's namespace: {bob_count} memories\n")

    # Cleanup demo
    print("🧹 Cleanup demonstration...")
    print("   (In production, you'd run this periodically)\n")

    # Clear Alice's memories
    await alice_adapter.clear_async()
    print("   ✓ Cleared Alice's namespace")

    # Clear Bob's memories
    await bob_adapter.clear_async()
    print("   ✓ Cleared Bob's namespace")

    print("\n✨ Multi-user demo complete!")
    print("\n💡 Key Takeaways:")
    print("   • Each user has isolated namespace for privacy")
    print("   • Session-based filtering enables conversation tracking")
    print("   • Privacy levels control data sharing")
    print("   • Serverless Pinecone scales automatically")


if __name__ == "__main__":
    asyncio.run(main())
