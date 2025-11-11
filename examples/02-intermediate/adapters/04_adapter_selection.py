"""
Adapter Selection Guide

Learn how to choose the right adapter for each tier based on your
requirements, scale, and deployment model.

Learn:
- Decision framework for adapter selection
- Tier-specific recommendations
- Performance vs. feature trade-offs
- Migration strategies
- Real-world configurations

Run:
    python 04_adapter_selection.py
"""

import asyncio


def main():
    """Guide for selecting the right adapters."""
    print("=== Adapter Selection Guide ===\n")

    # 1. Decision framework
    print("1. Adapter Selection Framework")
    print("-" * 50)
    print()
    print("  Key Questions:")
    print("    1. What's your deployment model?")
    print("       (Local, self-hosted, cloud)")
    print()
    print("    2. What's your scale?")
    print("       (< 10K, 10K-1M, > 1M entries)")
    print()
    print("    3. Do you need vector search?")
    print("       (Semantic similarity)")
    print()
    print("    4. Do you need persistence?")
    print("       (Survive restarts)")
    print()
    print("    5. Multi-process/multi-server?")
    print("       (Horizontal scaling)")
    print()

    # 2. Tier-specific recommendations
    print("2. Recommended Adapters by Tier")
    print("-" * 50)
    print()

    print("  EPHEMERAL TIER (Seconds to minutes):")
    print("    Development:")
    print("      OK InMemory - Fast, no setup")
    print()
    print("    Production:")
    print("      OK Redis - Fast, multi-process, TTL")
    print("      Alternative: InMemory (single-process apps)")
    print()

    print("  SESSION TIER (Minutes to hours):")
    print("    Development:")
    print("      OK InMemory - Fast, simple")
    print()
    print("    Production:")
    print("      OK Redis - Multi-process, TTL, fast")
    print("      Alternative: ChromaDB (if vector search needed)")
    print()

    print("  PERSISTENT TIER (Long-term):")
    print("    Development:")
    print("      OK ChromaDB - Easy setup, local files")
    print("      OK InMemory - Quick prototyping")
    print()
    print("    Production:")
    print("      OK Qdrant - Self-hosted, high performance")
    print("      OK Pinecone - Cloud-native, managed")
    print("      Alternative: ChromaDB (small scale)")
    print()

    # 3. Common configurations
    print("3. Common Configuration Patterns")
    print("-" * 50)
    print()

    configs = [
        ("Development", "memory", "memory", "memory", "Fast, no deps"),
        ("Testing/CI", "memory", "memory", "chroma", "Isolated, fast"),
        ("Small Prod", "redis", "redis", "chroma", "Simple, low cost"),
        ("Standard Prod", "redis", "redis", "qdrant", "Balanced, scalable"),
        ("Enterprise", "redis", "redis", "pinecone", "Managed, HA"),
        ("Cost-Optimized", "memory", "redis", "qdrant", "Minimize costs"),
        ("Max Performance", "redis", "redis", "qdrant", "Speed priority"),
    ]

    print(f"  {'Scenario':<15} {'Ephemeral':<10} {'Session':<10} {'Persistent':<10} {'Notes':<15}")
    print("  " + "-" * 70)
    for scenario, eph, sess, pers, notes in configs:
        print(f"  {scenario:<15} {eph:<10} {sess:<10} {pers:<10} {notes:<15}")

    print()

    # 4. Feature matrix
    print("4. Adapter Feature Matrix")
    print("-" * 50)
    print()

    features_matrix = [
        ("Feature", "InMemory", "Redis", "Chroma", "Qdrant", "Pinecone"),
        ("Vector Search", "OK", "X", "OK", "OK", "OK"),
        ("Persistence", "X", "Optional", "OK", "OK", "OK"),
        ("Multi-Process", "X", "OK", "Limited", "OK", "OK"),
        ("TTL Support", "OK", "OK", "X", "OK", "X"),
        ("Setup", "None", "Server", "Embedded", "Server", "Cloud"),
        ("Cost", "Free", "Server", "Free", "Server", "Usage"),
        ("Latency", "Lowest", "Very Low", "Low", "Low", "Medium"),
        ("Scalability", "Low", "Medium", "Medium", "High", "Very High"),
    ]

    for row in features_matrix:
        if row[0] == "Feature":
            print(f"  {row[0]:<15} {row[1]:<10} {row[2]:<10} {row[3]:<10} {row[4]:<10} {row[5]:<10}")
            print("  " + "-" * 75)
        else:
            print(f"  {row[0]:<15} {row[1]:<10} {row[2]:<10} {row[3]:<10} {row[4]:<10} {row[5]:<10}")

    print()

    # 5. Scale-based recommendations
    print("5. Recommendations by Scale")
    print("-" * 50)
    print()

    print("  Small Scale (< 10K entries):")
    print("    Ephemeral: InMemory or Redis")
    print("    Session: InMemory or Redis")
    print("    Persistent: ChromaDB")
    print("    Why: Minimal ops overhead, low cost")
    print()

    print("  Medium Scale (10K-1M entries):")
    print("    Ephemeral: Redis")
    print("    Session: Redis")
    print("    Persistent: Qdrant or ChromaDB")
    print("    Why: Balance performance and cost")
    print()

    print("  Large Scale (> 1M entries):")
    print("    Ephemeral: Redis (with clustering)")
    print("    Session: Redis (with clustering)")
    print("    Persistent: Qdrant or Pinecone")
    print("    Why: Proven at scale, high performance")
    print()

    # 6. Migration strategies
    print("6. Migration Strategies")
    print("-" * 50)
    print()

    print("  Path 1: Gradual Migration")
    print("    1. Start: All InMemory")
    print("    2. Add Redis for ephemeral/session")
    print("    3. Add ChromaDB for persistent")
    print("    4. Upgrade to Qdrant/Pinecone")
    print()

    print("  Path 2: Production-Ready from Start")
    print("    1. Development: InMemory + ChromaDB")
    print("    2. Staging: Redis + Qdrant")
    print("    3. Production: Redis + Qdrant/Pinecone")
    print()

    print("  Migration steps:")
    print("    a. Update MemoryConfig with new adapter")
    print("    b. Export from old: data = await memory.export()")
    print("    c. Import to new: await memory.import_from(data)")
    print("    d. Verify data integrity")
    print("    e. Switch traffic")
    print()

    # 7. Cost analysis
    print("7. Cost Considerations")
    print("-" * 50)
    print()

    print("  InMemory:")
    print("    Cost: Free (application memory)")
    print("    Trade-off: No persistence, single-process")
    print()

    print("  Redis:")
    print("    Cost: Server (EC2, DigitalOcean, etc.)")
    print("    Typical: $10-100/month (depends on memory)")
    print("    Trade-off: Need to manage server")
    print()

    print("  ChromaDB:")
    print("    Cost: Storage only")
    print("    Typical: < $5/month (small scale)")
    print("    Trade-off: Limited scalability")
    print()

    print("  Qdrant:")
    print("    Cost: Server or cloud")
    print("    Typical: $50-500/month")
    print("    Trade-off: Self-hosted = more ops work")
    print()

    print("  Pinecone:")
    print("    Cost: Usage-based (vectors + queries)")
    print("    Typical: $70+/month (includes free tier)")
    print("    Trade-off: Can get expensive at scale")
    print()

    # 8. Decision tree
    print("8. Quick Decision Tree")
    print("-" * 50)
    print()
    print("  Need persistence?")
    print("    NO -> InMemory")
    print("    YES |")
    print()
    print("  Need multi-process?")
    print("    NO -> InMemory or ChromaDB")
    print("    YES |")
    print()
    print("  Need vector search?")
    print("    NO -> Redis")
    print("    YES |")
    print()
    print("  Prefer managed service?")
    print("    YES -> Pinecone")
    print("    NO |")
    print()
    print("  Want open source?")
    print("    YES -> Qdrant or ChromaDB")
    print()

    # 9. Best practices
    print("9. Best Practices")
    print("-" * 50)
    print()
    print("  1. Match adapter to tier purpose:")
    print("     - Ephemeral: Speed matters (Redis/InMemory)")
    print("     - Session: Balance (Redis)")
    print("     - Persistent: Durability (Qdrant/Pinecone)")
    print()
    print("  2. Plan for growth:")
    print("     - Start simple (InMemory/ChromaDB)")
    print("     - Upgrade proactively before hitting limits")
    print("     - Test migration path early")
    print()
    print("  3. Monitor and measure:")
    print("     - Track query latency")
    print("     - Monitor storage growth")
    print("     - Watch costs")
    print()
    print("  4. Keep config flexible:")
    print("     - Use environment variables")
    print("     - Make adapters swappable")
    print("     - Test with multiple adapters")
    print()

    print("=" * 50)
    print("* Adapter Selection Guide Complete!")
    print("=" * 50)
    print("\nQuick Recommendations:")
    print("  * Starting out? -> All InMemory")
    print("  * Small app? -> Redis + ChromaDB")
    print("  * Production? -> Redis + Qdrant")
    print("  * Enterprise? -> Redis + Pinecone")
    print("  * Cost-sensitive? -> InMemory + Qdrant")


if __name__ == "__main__":
    main()
