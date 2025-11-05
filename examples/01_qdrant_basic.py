"""Basic Qdrant Adapter Example.

This example demonstrates the fundamental usage of the Qdrant adapter
for storing and retrieving memory entries.

Prerequisites:
    - Qdrant running at localhost:6333
    - OpenAI API key in .env file

Run:
    python examples/01_qdrant_basic.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.axon.adapters import QdrantAdapter
from src.axon.embedders import OpenAIEmbedder
from src.axon.models import MemoryEntry, MemoryMetadata, ProvenanceEvent


async def main():
    """Demonstrate basic Qdrant operations."""
    
    print("🚀 AxonML - Qdrant Basic Example\n")
    print("=" * 60)
    
    # Load environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Please create a .env file with your OpenAI API key")
        return
    
    # 1. Initialize embedder and adapter
    print("\n1️⃣  Initializing OpenAI embedder and Qdrant adapter...")
    embedder = OpenAIEmbedder(api_key=api_key, model="text-embedding-3-small")
    storage = QdrantAdapter(
        url="http://localhost:6333",
        collection_name="basic_example"
    )
    
    # 2. Create sample memories
    print("\n2️⃣  Creating sample memories...")
    memories = [
        "Python is a high-level programming language",
        "Machine learning requires lots of data",
        "Vector databases enable semantic search",
        "Qdrant is a fast vector search engine",
        "AI agents need memory to maintain context"
    ]
    
    # 3. Embed and store memories
    print("\n3️⃣  Embedding and storing memories...")
    entries = []
    for i, text in enumerate(memories):
        # Generate embedding
        embedding = await embedder.embed(text)
        
        # Create memory entry
        entry = MemoryEntry(
            text=text,
            embedding=embedding,
            metadata=MemoryMetadata(
                source="app",
                tags=["example", f"fact_{i}"],
                importance=0.5 + (i * 0.1),
                provenance=[
                    ProvenanceEvent(
                        action="store",
                        by="basic_example",
                        metadata={"index": str(i)}
                    )
                ]
            )
        )
        entries.append(entry)
        print(f"   ✓ Stored: {text[:50]}...")
    
    # Batch save
    await storage.bulk_save(entries)
    print(f"\n   📦 Saved {len(entries)} memories to Qdrant")
    
    # 4. Query similar memories
    print("\n4️⃣  Querying similar memories...")
    query = "What is a vector database?"
    query_embedding = await embedder.embed(query)
    
    print(f"\n   🔍 Query: '{query}'")
    results = await storage.query(query_embedding, limit=3)
    
    print(f"\n   📊 Top {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n   {i}. {result.text}")
        print(f"      Importance: {result.metadata.importance:.2f}")
        print(f"      Tags: {', '.join(result.metadata.tags)}")
    
    # 5. Retrieve specific memory
    print("\n5️⃣  Retrieving specific memory by ID...")
    first_id = entries[0].id
    retrieved = await storage.get(first_id)
    if retrieved:
        print(f"   ✓ Found: {retrieved.text}")
        print(f"   ✓ Created: {retrieved.metadata.created_at}")
    
    # 6. Count total memories
    print("\n6️⃣  Counting total memories...")
    total = await storage.count_async()
    print(f"   📈 Total memories in collection: {total}")
    
    # 7. Delete a memory
    print("\n7️⃣  Deleting a memory...")
    deleted = await storage.delete(entries[-1].id)
    if deleted:
        print(f"   🗑️  Deleted: {entries[-1].text}")
        new_total = await storage.count_async()
        print(f"   📉 New total: {new_total}")
    
    # 8. Cleanup (optional - comment out to keep data)
    print("\n8️⃣  Cleanup...")
    print("   💡 To clear the collection, uncomment the line below")
    # await storage.clear_async()
    
    print("\n" + "=" * 60)
    print("✅ Example completed successfully!")
    print("\n💡 Next steps:")
    print("   - Try modifying the memories")
    print("   - Experiment with different queries")
    print("   - Add metadata filters")
    print("   - Check the Qdrant dashboard at http://localhost:6333/dashboard")


if __name__ == "__main__":
    asyncio.run(main())
