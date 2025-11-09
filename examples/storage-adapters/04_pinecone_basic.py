"""Basic Pinecone Adapter Usage Example

This example demonstrates:
- Connecting to Pinecone cloud service
- Storing and retrieving memory entries
- Vector similarity search
- Metadata filtering
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.axon.adapters import PineconeAdapter
from src.axon.models import Filter, MemoryEntry, MemoryMetadata

# Load environment variables
load_dotenv()


async def main():
    """Demonstrate basic Pinecone operations."""

    # Initialize Pinecone adapter
    print("🚀 Connecting to Pinecone...")
    adapter = PineconeAdapter(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name="axon-demo",
        namespace="basic_demo",
        cloud="aws",
        region="us-east-1",
    )

    print("✅ Connected to Pinecone serverless index\n")

    # Create some sample embeddings (in real use, these would come from an embedder)
    # Using simple embeddings for demonstration
    def create_simple_embedding(text: str, dimension: int = 384) -> list[float]:
        """Create a simple deterministic embedding from text."""
        return [hash(text + str(i)) % 1000 / 1000.0 for i in range(dimension)]

    # 1. Store memories with different metadata
    print("📝 Storing memories...")

    memories = [
        MemoryEntry(
            id="memory-1",
            text="Python is a high-level programming language known for its simplicity.",
            embedding=create_simple_embedding("Python programming"),
            metadata=MemoryMetadata(
                source="app",
                user_id="user_123",
                session_id="session_abc",
                privacy_level="public",
                tags=["programming", "python", "education"],
                importance=0.9,
            ),
        ),
        MemoryEntry(
            id="memory-2",
            text="JavaScript is widely used for web development and runs in browsers.",
            embedding=create_simple_embedding("JavaScript web"),
            metadata=MemoryMetadata(
                source="app",
                user_id="user_123",
                session_id="session_abc",
                privacy_level="public",
                tags=["programming", "javascript", "web"],
                importance=0.8,
            ),
        ),
        MemoryEntry(
            id="memory-3",
            text="Machine learning is a subset of AI focused on data-driven predictions.",
            embedding=create_simple_embedding("Machine learning AI"),
            metadata=MemoryMetadata(
                source="app",
                user_id="user_456",
                session_id="session_xyz",
                privacy_level="private",
                tags=["ai", "machine-learning", "data-science"],
                importance=0.95,
            ),
        ),
    ]

    # Bulk save for efficiency
    await adapter.bulk_save(memories)
    print(f"✅ Stored {len(memories)} memories\n")

    # Wait for indexing
    await asyncio.sleep(1.5)

    # 2. Retrieve specific memory by ID
    print("🔍 Retrieving memory by ID...")
    retrieved = await adapter.get("memory-1")
    if retrieved:
        print(f"   Text: {retrieved.text[:60]}...")
        print(f"   Tags: {retrieved.metadata.tags}")
        print(f"   User: {retrieved.metadata.user_id}\n")

    # 3. Vector similarity search
    print("🎯 Searching for programming-related memories...")
    query_embedding = create_simple_embedding("programming languages")
    results = await adapter.query(query_embedding, limit=2)

    print(f"   Found {len(results)} similar memories:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result.text[:60]}...")
        print(f"      Tags: {result.metadata.tags}\n")

    # 4. Filter by user
    print("🔍 Filtering memories by user_id='user_123'...")
    user_filter = Filter(user_id="user_123")
    user_results = await adapter.query(query_embedding, filter=user_filter, limit=10)

    print(f"   Found {len(user_results)} memories for user_123:")
    for result in user_results:
        print(f"   - {result.text[:60]}...\n")

    # 5. Filter by tags
    print("🏷️  Filtering memories with tag 'programming'...")
    tag_filter = Filter(tags=["programming"])
    tag_results = await adapter.query(query_embedding, filter=tag_filter, limit=10)

    print(f"   Found {len(tag_results)} memories with 'programming' tag:")
    for result in tag_results:
        print(f"   - {result.text[:60]}...")
        print(f"     Tags: {result.metadata.tags}\n")

    # 6. Filter by importance
    print("⭐ Filtering high-importance memories (>= 0.85)...")
    importance_filter = Filter(min_importance=0.85)
    important_results = await adapter.query(query_embedding, filter=importance_filter, limit=10)

    print(f"   Found {len(important_results)} high-importance memories:")
    for result in important_results:
        print(f"   - {result.text[:60]}...")
        print(f"     Importance: {result.metadata.importance}\n")

    # 7. Count and list operations
    print("📊 Namespace statistics...")
    count = await adapter.count_async()
    print(f"   Total memories: {count}")

    ids = await adapter.list_ids_async()
    print(f"   Memory IDs: {ids}\n")

    # 8. Delete a memory
    print("🗑️  Deleting memory-2...")
    deleted = await adapter.delete("memory-2")
    print(f"   Deleted: {deleted}")

    new_count = await adapter.count_async()
    print(f"   Remaining memories: {new_count}\n")

    # 9. Cleanup
    print("🧹 Cleaning up namespace...")
    await adapter.clear_async()
    final_count = await adapter.count_async()
    print(f"   Final count: {final_count}")

    print("\n✨ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
