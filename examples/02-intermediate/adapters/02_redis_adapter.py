"""
Redis Adapter

Learn how to use Redis adapter for high-performance caching, session
storage, and multi-process deployments.

Learn:
- Redis adapter configuration
- Connection setup
- TTL and eviction policies
- Multi-process support
- Use cases and best practices

Run:
    python 02_redis_adapter.py

Requirements:
    - Redis server running (localhost:6379)
    - pip install redis
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate Redis adapter usage."""
    print("=== Redis Adapter ===\n")

    # 1. Redis adapter configuration
    print("1. Configure Redis Adapter")
    print("-" * 50)

    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",  # Redis for ephemeral
            ttl_seconds=60
        ),
        session=SessionPolicy(
            adapter_type="redis",  # Redis for session
            ttl_seconds=600,
            max_entries=1000,
            enable_vector_search=False  # Redis doesn't support vector search
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",  # Use vector DB for persistent
            ttl_seconds=None
        ),
        default_tier="session"
    )

    print("  Configuration:")
    print("    Ephemeral: Redis (60s TTL)")
    print("    Session: Redis (10min TTL, 1000 entries)")
    print("    Persistent: InMemory (for demo)")
    print()

    try:
        memory = MemorySystem(config)
        print("  OK Connected to Redis successfully")
    except Exception as e:
        print(f"  X Redis connection failed: {e}")
        print("\n  Please ensure Redis is running:")
        print("    Docker: docker run -d -p 6379:6379 redis")
        print("    Local: redis-server")
        return

    print()

    # 2. Redis adapter features
    print("2. Redis Adapter Features")
    print("-" * 50)
    print()
    print("  Capabilities:")
    print("    OK High-performance key-value storage")
    print("    OK Automatic TTL expiration")
    print("    OK Multi-process/multi-server support")
    print("    OK Optional persistence (RDB/AOF)")
    print("    OK Pub/sub for real-time updates")
    print()
    print("  Limitations:")
    print("    X No native vector search")
    print("    X Memory-only (unless persistence enabled)")
    print("    X Text-based filtering only")
    print()

    # 3. Store with TTL
    print("3. Store with Automatic TTL")
    print("-" * 50)

    # Store in ephemeral (60s TTL)
    ephemeral_id = await memory.store(
        "Temporary auth token: abc123xyz",
        tier="ephemeral",
        tags=["auth", "temporary"]
    )
    print(f"  OK Stored in ephemeral tier (expires in 60s)")
    print(f"    Entry ID: {ephemeral_id}")

    # Store in session (600s TTL)
    session_id = await memory.store(
        "User active on checkout page",
        tier="session",
        tags=["session", "activity"],
        metadata={"session_id": "sess_abc123"}
    )
    print(f"  OK Stored in session tier (expires in 10min)")
    print(f"    Entry ID: {session_id}")

    print()

    # 4. Multi-process support
    print("4. Multi-Process Support")
    print("-" * 50)
    print()
    print("  Redis enables:")
    print("    * Multiple app instances sharing same cache")
    print("    * Horizontal scaling")
    print("    * Load balancer compatibility")
    print("    * Distributed session storage")
    print()
    print("  Example architecture:")
    print("    +---------+  +---------+  +---------+")
    print("    | App #1  |  | App #2  |  | App #3  |")
    print("    +----+----+  +----+----+  +----+----+")
    print("         |            |            |")
    print("         +------------+------------+")
    print("                      |")
    print("                +-----+-----+")
    print("                |   Redis   |")
    print("                +-----------+")
    print()

    # 5. Use cases
    print("5. Common Use Cases")
    print("-" * 50)
    print()

    use_cases = [
        ("Session Cache", "User sessions, shopping carts", "ephemeral/session"),
        ("Rate Limiting", "API throttling, abuse prevention", "ephemeral"),
        ("Temporary Tokens", "OTP, auth codes, reset tokens", "ephemeral"),
        ("Recent Activity", "User actions, notifications", "session"),
        ("Distributed Cache", "Multi-server deployments", "ephemeral/session"),
    ]

    for name, description, tiers in use_cases:
        print(f"  {name}:")
        print(f"    Use: {description}")
        print(f"    Tiers: {tiers}")
        print()

    # 6. Redis configuration options
    print("6. Redis Configuration")
    print("-" * 50)
    print()
    print("  Connection:")
    print("    host: 'localhost' (default)")
    print("    port: 6379 (default)")
    print("    db: 0 (default)")
    print("    password: optional")
    print()
    print("  Persistence options:")
    print("    RDB: Periodic snapshots")
    print("    AOF: Append-only file (every write)")
    print("    Both: Maximum durability")
    print("    None: In-memory only (fastest)")
    print()
    print("  Memory management:")
    print("    maxmemory: Set memory limit")
    print("    maxmemory-policy: Eviction strategy")
    print("      - volatile-lru: Evict least recently used (with TTL)")
    print("      - allkeys-lru: Evict any least recently used")
    print("      - volatile-ttl: Evict shortest TTL first")
    print()

    # 7. Performance testing
    print("7. Performance Testing")
    print("-" * 50)

    import time

    # Measure store performance
    start = time.time()
    for i in range(50):
        await memory.store(
            f"Perf test entry #{i}",
            tier="session",
            tags=["perf"]
        )
    store_time = time.time() - start

    print(f"  Store 50 entries: {store_time:.3f}s")
    print(f"  Average: {store_time/50*1000:.2f}ms per entry")

    # Measure recall performance
    start = time.time()
    for i in range(20):
        await memory.recall("perf test", k=10, tiers=["session"])
    recall_time = time.time() - start

    print(f"  Recall 20 times: {recall_time:.3f}s")
    print(f"  Average: {recall_time/20*1000:.2f}ms per query")

    print()

    # 8. Redis vs. alternatives
    print("8. Redis vs. Alternatives")
    print("-" * 50)
    print()

    print("  Redis:")
    print("    OK Very fast (in-memory)")
    print("    OK Multi-process support")
    print("    OK Battle-tested, mature")
    print("    OK Rich ecosystem")
    print("    X No vector search")
    print()

    print("  InMemory:")
    print("    OK Fastest (no serialization)")
    print("    OK Zero setup")
    print("    X Single process only")
    print("    X No persistence")
    print()

    print("  ChromaDB/Qdrant:")
    print("    OK Vector search support")
    print("    OK Persistent storage")
    print("    ~ Slower for simple key-value")
    print("    ~ More resource-intensive")
    print()

    # 9. Best practices
    print("9. Best Practices")
    print("-" * 50)
    print()
    print("  1. Tier assignment:")
    print("     - Ephemeral/Session: Redis")
    print("     - Persistent: Vector DB (Chroma/Qdrant)")
    print()
    print("  2. TTL management:")
    print("     - Set appropriate TTLs")
    print("     - Use volatile-lru eviction")
    print("     - Monitor memory usage")
    print()
    print("  3. Connection pooling:")
    print("     - Reuse connections")
    print("     - Configure pool size")
    print("     - Handle reconnections")
    print()
    print("  4. Security:")
    print("     - Enable authentication")
    print("     - Use TLS for network traffic")
    print("     - Restrict network access")
    print()
    print("  5. Monitoring:")
    print("     - Track memory usage")
    print("     - Monitor eviction rate")
    print("     - Watch for slow queries")
    print()

    print("=" * 50)
    print("* Successfully demonstrated Redis adapter!")
    print("=" * 50)
    print("\nRedis Summary:")
    print("  * High-performance key-value storage")
    print("  * Perfect for ephemeral and session tiers")
    print("  * Multi-process/multi-server support")
    print("  * Automatic TTL expiration")
    print("  * No vector search (use with vector DB for persistent)")
    print("  * Production-ready for caching and sessions")


if __name__ == "__main__":
    asyncio.run(main())
