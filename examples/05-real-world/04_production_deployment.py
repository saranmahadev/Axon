"""
Production Deployment Guide

Best practices for deploying Axon in production.

Run: python 04_production_deployment.py
"""

import asyncio


async def main():
    print("=== Production Deployment Guide ===\n")

    print("1. PRODUCTION CONFIGURATION")
    print("-" * 50)
    print("""
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="redis",
        ttl_seconds=60
    ),
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800,
        max_entries=2000,
        overflow_to_persistent=True
    ),
    persistent=PersistentPolicy(
        adapter_type="qdrant",  # or "pinecone"
        compaction_threshold=50000,
        compaction_strategy="semantic"
    ),
    enable_promotion=True,
    enable_demotion=True
)
    """)

    print("\n2. INFRASTRUCTURE REQUIREMENTS")
    print("-" * 50)
    print("  Redis:")
    print("    * 4GB+ RAM")
    print("    * Enable persistence (AOF + RDB)")
    print("    * Set maxmemory-policy=volatile-lru")
    print()
    print("  Qdrant:")
    print("    * 8GB+ RAM")
    print("    * SSD storage")
    print("    * Proper indexing configuration")
    print()
    print("  Application:")
    print("    * 2GB+ RAM per instance")
    print("    * Multiple instances for HA")
    print()

    print("3. MONITORING")
    print("-" * 50)
    print("  Key Metrics:")
    print("    * Query latency (p50, p95, p99)")
    print("    * Storage usage per tier")
    print("    * Compaction frequency")
    print("    * Cache hit rate")
    print("    * Error rate")
    print()
    print("  Tools:")
    print("    * Prometheus + Grafana")
    print("    * DataDog APM")
    print("    * Custom audit logs")
    print()

    print("4. SECURITY")
    print("-" * 50)
    print("  * Enable authentication on Redis/Qdrant")
    print("  * Use TLS for network traffic")
    print("  * Enable PII detection")
    print("  * Configure audit logging")
    print("  * Encrypt sensitive data at rest")
    print("  * Regular security audits")
    print()

    print("5. SCALING")
    print("-" * 50)
    print("  Horizontal:")
    print("    * Load balancer across app instances")
    print("    * Redis Cluster for high throughput")
    print("    * Qdrant sharding for large datasets")
    print()
    print("  Vertical:")
    print("    * Scale Redis memory")
    print("    * Scale vector DB resources")
    print("    * Optimize query patterns")
    print()

    print("6. BACKUP & RECOVERY")
    print("-" * 50)
    print("  * Daily exports: await memory.export()")
    print("  * Store in S3/Cloud Storage")
    print("  * Test recovery procedures")
    print("  * Document restore process")
    print("  * Monitor backup success")
    print()

    print("7. COST OPTIMIZATION")
    print("-" * 50)
    print("  * Set appropriate compaction thresholds")
    print("  * Use Redis for cache tiers (cheaper)")
    print("  * Self-host Qdrant vs. managed Pinecone")
    print("  * Monitor and optimize embedding costs")
    print("  * Right-size infrastructure")
    print()

    print("=" * 50)
    print("* Production deployment guide complete!")


if __name__ == "__main__":
    asyncio.run(main())
