"""
Vector Database Adapters

Learn about vector database adapters (ChromaDB, Qdrant, Pinecone) for
semantic search and persistent storage with embeddings.

Learn:
- Vector DB capabilities and features
- ChromaDB for local development
- Qdrant for self-hosted production
- Pinecone for cloud-native deployments
- When to use each adapter

Run:
    python 03_vector_adapters.py

Note: This example uses InMemory for demonstration. See individual
adapter examples for ChromaDB, Qdrant, and Pinecone setup.
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy


async def main():
    """Demonstrate vector database adapter concepts."""
    print("=== Vector Database Adapters ===\n")

    # 1. Vector adapter overview
    print("1. Vector Database Adapters")
    print("-" * 50)
    print()
    print("  Axon supports three vector databases:")
    print()
    print("  [Package] ChromaDB:")
    print("     * Local-first, embedded database")
    print("     * Easy setup, no server required")
    print("     * Good for: Development, small deployments")
    print()
    print("  [Rocket] Qdrant:")
    print("     * Self-hosted or cloud")
    print("     * High performance, production-ready")
    print("     * Good for: Production, self-hosted")
    print()
    print("  [Cloud]  Pinecone:")
    print("     * Fully managed cloud service")
    print("     * Serverless, auto-scaling")
    print("     * Good for: Cloud-native, enterprise")
    print()

    # 2. Configuration examples
    print("2. Configuration Examples")
    print("-" * 50)
    print()

    # ChromaDB configuration
    print("  ChromaDB Configuration:")
    print("    persistent=PersistentPolicy(")
    print("        adapter_type='chroma',")
    print("        collection_name='my_memories',")
    print("        persist_directory='./chroma_db'")
    print("    )")
    print()

    # Qdrant configuration
    print("  Qdrant Configuration:")
    print("    persistent=PersistentPolicy(")
    print("        adapter_type='qdrant',")
    print("        collection_name='memories',")
    print("        url='http://localhost:6333'")
    print("    )")
    print()

    # Pinecone configuration
    print("  Pinecone Configuration:")
    print("    persistent=PersistentPolicy(")
    print("        adapter_type='pinecone',")
    print("        index_name='axon-memories',")
    print("        api_key=os.getenv('PINECONE_API_KEY')")
    print("    )")
    print()

    # 3. Feature comparison
    print("3. Feature Comparison")
    print("-" * 50)
    print()

    features = [
        ("Setup Complexity", "Low", "Medium", "Low"),
        ("Deployment", "Local", "Self-hosted", "Cloud"),
        ("Scalability", "Small-Medium", "Large", "Very Large"),
        ("Cost", "Free", "Server costs", "Pay-per-use"),
        ("Vector Search", "Yes", "Yes", "Yes"),
        ("Metadata Filtering", "Yes", "Yes", "Yes"),
        ("Persistence", "Local files", "Disk/S3", "Managed"),
        ("Multi-tenancy", "Limited", "Yes", "Yes"),
        ("Performance", "Good", "Excellent", "Excellent"),
    ]

    print(f"  {'Feature':<20} {'ChromaDB':<15} {'Qdrant':<15} {'Pinecone':<15}")
    print("  " + "-" * 65)
    for feature, chroma, qdrant, pinecone in features:
        print(f"  {feature:<20} {chroma:<15} {qdrant:<15} {pinecone:<15}")

    print()

    # 4. Use case recommendations
    print("4. Use Case Recommendations")
    print("-" * 50)
    print()

    use_cases = [
        ("Local Development", "ChromaDB", "Easy setup, no config"),
        ("CI/CD Testing", "ChromaDB", "Embedded, fast tests"),
        ("Self-Hosted Prod", "Qdrant", "Full control, performance"),
        ("Cloud Native", "Pinecone", "Managed, auto-scaling"),
        ("Hybrid Cloud", "Qdrant", "On-prem + cloud flexible"),
        ("Enterprise Scale", "Pinecone", "Battle-tested at scale"),
        ("Cost-Sensitive", "Qdrant", "No usage-based pricing"),
        ("Rapid Prototyping", "ChromaDB", "Fastest to start"),
    ]

    for use_case, recommended, reason in use_cases:
        print(f"  {use_case}:")
        print(f"    -> {recommended}")
        print(f"    Why: {reason}")
        print()

    # 5. Semantic search demo (using InMemory)
    print("5. Semantic Search Capabilities")
    print("-" * 50)

    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="memory",  # Using InMemory for demo
            ttl_seconds=None
        ),
        default_tier="persistent"
    )

    memory = MemorySystem(config)

    # Store semantically related content
    await memory.store("Python is a high-level programming language", importance=0.8)
    await memory.store("JavaScript is used for web development", importance=0.7)
    await memory.store("Machine learning models require training data", importance=0.9)
    await memory.store("Python is popular for data science and AI", importance=0.9)

    print("  OK Stored 4 diverse memories")
    print()

    # Semantic search
    results = await memory.recall("programming languages", k=2)
    print("  Query: 'programming languages'")
    print(f"  Results ({len(results)}):")
    for i, entry in enumerate(results, 1):
        print(f"    {i}. {entry.text}")

    print()

    # 6. Migration path
    print("6. Migration Strategy")
    print("-" * 50)
    print()
    print("  Recommended progression:")
    print()
    print("  1. Development:")
    print("     Start with: ChromaDB (or InMemory)")
    print("     Why: Easy setup, fast iteration")
    print()
    print("  2. Staging:")
    print("     Move to: Qdrant (Docker)")
    print("     Why: Production-like environment")
    print()
    print("  3. Production:")
    print("     Choose:")
    print("       * Qdrant: Self-hosted, full control")
    print("       * Pinecone: Managed, less ops overhead")
    print()
    print("  Migration steps:")
    print("    a. Export from current adapter:")
    print("       data = await memory.export()")
    print()
    print("    b. Update config to new adapter")
    print()
    print("    c. Import to new adapter:")
    print("       await memory.import_from(data)")
    print()

    # 7. Performance considerations
    print("7. Performance Considerations")
    print("-" * 50)
    print()
    print("  Query latency (typical):")
    print("    ChromaDB (local): 10-50ms")
    print("    Qdrant (same region): 20-100ms")
    print("    Pinecone (cloud): 50-200ms")
    print()
    print("  Factors affecting performance:")
    print("    * Collection size")
    print("    * Embedding dimensions")
    print("    * Filter complexity")
    print("    * Network latency")
    print("    * Index configuration")
    print()

    # 8. Best practices
    print("8. Best Practices")
    print("-" * 50)
    print()
    print("  1. Choose the right adapter:")
    print("     - Development: ChromaDB")
    print("     - Production: Qdrant or Pinecone")
    print("     - Hybrid: Qdrant (flexibility)")
    print()
    print("  2. Embedder selection:")
    print("     - ChromaDB: OpenAI, Sentence Transformers")
    print("     - Qdrant: Any embedder")
    print("     - Pinecone: Match index dimensions")
    print()
    print("  3. Index configuration:")
    print("     - Set appropriate dimensions")
    print("     - Choose distance metric (cosine recommended)")
    print("     - Configure quantization for performance")
    print()
    print("  4. Cost optimization:")
    print("     - Pinecone: Right-size index, use gRPC")
    print("     - Qdrant: Optimize instance size")
    print("     - All: Use compaction to reduce entries")
    print()

    print("=" * 50)
    print("* Successfully demonstrated vector adapters!")
    print("=" * 50)
    print("\nVector Adapter Summary:")
    print("  * Three options: ChromaDB, Qdrant, Pinecone")
    print("  * ChromaDB: Easy local development")
    print("  * Qdrant: Self-hosted production")
    print("  * Pinecone: Managed cloud service")
    print("  * All support semantic search + metadata filtering")
    print("  * Choose based on deployment model and scale")


if __name__ == "__main__":
    asyncio.run(main())
