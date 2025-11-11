"""
InMemory Adapter

Learn how to use the InMemory adapter for development, testing, and
small-scale deployments without external dependencies.

Learn:
- InMemory adapter features and limitations
- Configuration and initialization
- Performance characteristics
- Use cases and best practices
- When to use vs. external adapters

Run:
    python 01_inmemory_adapter.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate InMemory adapter usage."""
    print("=== InMemory Adapter ===\n")

    # 1. InMemory adapter configuration
    print("1. Configure InMemory Adapter")
    print("-" * 50)

    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",  # InMemory adapter
            ttl_seconds=60
        ),
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=600,
            max_entries=100,
            enable_vector_search=True
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None,
            compaction_threshold=1000
        ),
        default_tier="session"
    )

    print("  OK All tiers using InMemory adapter")
    print("  OK No external dependencies required")
    print()

    memory = MemorySystem(config)

    # 2. InMemory adapter features
    print("2. InMemory Adapter Features")
    print("-" * 50)
    print()
    print("  Capabilities:")
    print("    OK Store and retrieve memories")
    print("    OK Semantic search (cosine similarity)")
    print("    OK Metadata filtering")
    print("    OK TTL-based expiration")
    print("    OK Bulk operations")
    print()
    print("  Limitations:")
    print("    X Data lost on restart (not persistent)")
    print("    X Single-process only (no clustering)")
    print("    X Memory-bound capacity")
    print("    X No disk persistence")
    print()

    # 3. Store and retrieve
    print("3. Basic Operations")
    print("-" * 50)

    # Store memories
    for i in range(5):
        await memory.store(
            f"Memory #{i+1}: Python is a versatile programming language",
            importance=0.5 + (i * 0.1),
            tags=["python", "programming"]
        )

    print(f"  OK Stored 5 memories")

    # Retrieve with semantic search
    results = await memory.recall("Python programming", k=3)
    print(f"  OK Retrieved {len(results)} results via semantic search")

    for i, entry in enumerate(results, 1):
        print(f"    {i}. {entry.text[:50]}...")
        print(f"       Importance: {entry.metadata.importance}")

    print()

    # 4. Performance characteristics
    print("4. Performance Characteristics")
    print("-" * 50)
    print()
    print("  Speed:")
    print("    * Very fast (in-memory)")
    print("    * No network latency")
    print("    * Direct Python object access")
    print()
    print("  Scalability:")
    print("    * Limited by available RAM")
    print("    * Typical: 10K-100K entries")
    print("    * Vector operations scale O(n)")
    print()
    print("  Throughput:")
    print("    * High read/write throughput")
    print("    * No serialization overhead")
    print("    * Limited by CPU for vector ops")
    print()

    # 5. Use cases
    print("5. Use Cases")
    print("-" * 50)
    print()

    use_cases = [
        ("Development", "Fast iteration, no setup", "OK Recommended"),
        ("Testing/CI", "No external services needed", "OK Recommended"),
        ("Prototyping", "Quick validation of ideas", "OK Recommended"),
        ("Small deployments", "< 10K entries, single server", "OK Viable"),
        ("Production", "High scale, multi-process", "X Not recommended"),
        ("Multi-tenant", "Shared infrastructure", "X Use Redis/Vector DBs"),
    ]

    for use_case, description, recommendation in use_cases:
        print(f"  {use_case}:")
        print(f"    {description}")
        print(f"    {recommendation}")
        print()

    # 6. Data persistence (or lack thereof)
    print("6. Data Persistence")
    print("-" * 50)
    print()
    print("  InMemory adapter does NOT persist data to disk.")
    print()
    print("  On restart:")
    print("    * All data is lost")
    print("    * No recovery possible")
    print()
    print("  Workarounds:")
    print("    1. Use export() before shutdown:")
    print("       data = await memory.export()")
    print("       save_to_file(data, 'backup.json')")
    print()
    print("    2. Use import_from() on startup:")
    print("       data = load_from_file('backup.json')")
    print("       await memory.import_from(data)")
    print()
    print("    3. Switch to persistent adapter:")
    print("       - ChromaDB for local persistence")
    print("       - Qdrant for production")
    print("       - Pinecone for cloud-native")
    print()

    # 7. Configuration comparison
    print("7. InMemory vs. External Adapters")
    print("-" * 50)
    print()

    print("  InMemory:")
    print("    Setup: None required")
    print("    Dependencies: None")
    print("    Persistence: No")
    print("    Multi-process: No")
    print("    Speed: Fastest")
    print("    Cost: Free")
    print()

    print("  Redis:")
    print("    Setup: Redis server")
    print("    Dependencies: redis-py")
    print("    Persistence: Optional")
    print("    Multi-process: Yes")
    print("    Speed: Very fast")
    print("    Cost: Server + RAM")
    print()

    print("  ChromaDB:")
    print("    Setup: Local or server")
    print("    Dependencies: chromadb")
    print("    Persistence: Yes (local files)")
    print("    Multi-process: With server mode")
    print("    Speed: Fast")
    print("    Cost: Storage")
    print()

    print("  Qdrant:")
    print("    Setup: Docker or cloud")
    print("    Dependencies: qdrant-client")
    print("    Persistence: Yes")
    print("    Multi-process: Yes")
    print("    Speed: Very fast")
    print("    Cost: Server/cloud")
    print()

    # 8. Best practices
    print("8. Best Practices")
    print("-" * 50)
    print()
    print("  1. Development workflow:")
    print("     - Start with InMemory for rapid development")
    print("     - Switch to real adapter before production")
    print()
    print("  2. Testing:")
    print("     - Use InMemory for unit tests (fast, isolated)")
    print("     - Use real adapters for integration tests")
    print()
    print("  3. Capacity planning:")
    print("     - Monitor memory usage")
    print("     - Set realistic compaction thresholds")
    print("     - Consider export/import for backup")
    print()
    print("  4. Migration path:")
    print("     - Design code to be adapter-agnostic")
    print("     - Use MemoryConfig for easy switching")
    print("     - Test with both InMemory and target adapter")
    print()

    # 9. Verify functionality
    print("9. Verify All Features Work")
    print("-" * 50)

    # Export
    export_data = await memory.export()
    print(f"  OK Export: {export_data['statistics']['total_entries']} entries")

    # Filter
    from axon.models.filter import Filter
    filtered = await memory.recall("", k=100, filter=Filter(tags=["python"]))
    print(f"  OK Filtering: {len(filtered)} entries with 'python' tag")

    # Stats
    stats = memory.get_statistics()
    print(f"  OK Statistics: {stats['total_operations']['stores']} total stores")

    print()

    print("=" * 50)
    print("* Successfully demonstrated InMemory adapter!")
    print("=" * 50)
    print("\nInMemory Summary:")
    print("  * Zero setup, no dependencies")
    print("  * Perfect for development and testing")
    print("  * Fast in-memory operations")
    print("  * No data persistence (lost on restart)")
    print("  * Limited to single process")
    print("  * Switch to external adapters for production")


if __name__ == "__main__":
    asyncio.run(main())
