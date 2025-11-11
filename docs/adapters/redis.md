# Redis Adapter

High-performance distributed cache adapter with TTL support for ephemeral and session tiers.

---

## Overview

The **Redis adapter** provides fast, distributed in-memory storage with automatic TTL-based expiration. Perfect for ephemeral caching, session management, and rate limiting.

**Key Features:**
- ✓ Sub-millisecond latency (1-5ms)
- ✓ TTL-based automatic expiration
- ✓ Distributed across multiple processes/servers
- ✓ Connection pooling for performance
- ✓ Namespace isolation for multi-tenancy
- ✗ No vector similarity search
- ✗ Not suitable for long-term storage

---

## Installation

```bash
# Install Redis client
pip install redis>=5.0.0

# Or with axon-sdk
pip install "axon-sdk[all]"

# Start Redis server (Docker)
docker run -d -p 6379:6379 redis:latest
```

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy

config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="redis",
        ttl_seconds=60  # 1 minute
    ),
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800,  # 30 minutes
        max_entries=1000
    )
)

memory = MemorySystem(config)

# Store with automatic expiration
await memory.store("Temporary data", importance=0.2, tier="ephemeral")

# Auto-expires after 60 seconds
```

---

## Configuration

### Basic Configuration

```python
from axon.adapters.redis import RedisAdapter

# Default (localhost)
adapter = RedisAdapter()

# Custom settings
adapter = RedisAdapter(
    host="redis.example.com",
    port=6379,
    password="secret",
    db=0,
    namespace="app_v1",
    default_ttl=3600,
    max_connections=10
)
```

### Environment Variables

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your-password
```

### Connection Pooling

```python
# Recommended for production
adapter = RedisAdapter(
    max_connections=20,  # Connection pool size
    decode_responses=True
)
```

---

## Features

### TTL-Based Expiration

Automatic cleanup after TTL expires:

```python
# Store with 60-second TTL
await memory.store(
    "Rate limit: user_123",
    importance=0.1,
    tier="ephemeral"  # 60s TTL configured
)

# Wait 61 seconds
await asyncio.sleep(61)

# Automatically deleted
results = await memory.recall("rate limit", tier="ephemeral")
assert len(results) == 0
```

### Namespace Isolation

Multi-tenancy support:

```python
# Different namespaces for different users
user1_adapter = RedisAdapter(namespace="user_123")
user2_adapter = RedisAdapter(namespace="user_456")

# Data isolated by namespace
```

### Distributed Access

Share data across processes/servers:

```python
# Process 1
await memory.store("Shared data", tier="session")

# Process 2 (different machine)
results = await memory.recall("shared", tier="session")
# Returns results ✓
```

---

## Use Cases

### ✅ Perfect For

- **Ephemeral Tier**: Short-lived cache (5s-1hr)
- **Session Tier**: User sessions (minutes-hours)
- Rate limiting and throttling
- Temporary feature flags
- API request de-duplication
- Recent activity tracking
- Distributed locking

### ❌ Not Suitable For

- **Persistent Tier**: Long-term storage
- Vector similarity search
- Semantic search requirements
- Knowledge bases
- Data requiring backup/disaster recovery

---

## Examples

### Rate Limiting

```python
async def check_rate_limit(user_id: str) -> bool:
    key = f"rate_limit:{user_id}"
    
    # Count requests in last minute
    results = await memory.recall(key, tier="ephemeral")
    
    if len(results) >= 100:  # Max 100 requests/minute
        return False
    
    # Track request
    await memory.store(
        f"Request at {datetime.now()}",
        importance=0.1,
        tier="ephemeral",
        tags=[key]
    )
    
    return True
```

### Session Management

```python
# Store session data
session_id = "sess_abc123"

await memory.store(
    f"User logged in: {user_id}",
    importance=0.4,
    tier="session",
    tags=[session_id, user_id]
)

# Retrieve session
results = await memory.recall(
    "session",
    tier="session",
    filter=Filter(tags=[session_id])
)

# Auto-expires after TTL (e.g., 30 minutes)
```

### Cache Warming

```python
# Pre-populate cache
for item in frequently_accessed_items:
    await memory.store(
        item.content,
        importance=0.2,
        tier="ephemeral",
        tags=["cache", item.id]
    )

# Fast retrieval (< 5ms)
results = await memory.recall("query", tier="ephemeral")
```

---

## Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| **save()** | 1-5ms | >1,000 ops/sec |
| **get()** | 1-3ms | >5,000 ops/sec |
| **delete()** | 1-3ms | >2,000 ops/sec |

**Note:** Latency depends on network and Redis configuration.

---

## Best Practices

### 1. Use for Ephemeral/Session Tiers Only

```python
# ✓ Good
ephemeral=EphemeralPolicy(adapter_type="redis")
session=SessionPolicy(adapter_type="redis")

# ✗ Bad
persistent=PersistentPolicy(adapter_type="redis")  # No vector search!
```

### 2. Set Appropriate TTLs

```python
# ✓ Good TTLs
ephemeral: 30-300 seconds
session: 600-3600 seconds

# ✗ Bad TTLs
ephemeral: 86400 seconds  # Use session instead
```

### 3. Use Connection Pooling

```python
# ✓ Good
adapter = RedisAdapter(max_connections=20)

# ✗ Bad (bottleneck)
adapter = RedisAdapter(max_connections=1)
```

### 4. Monitor Memory Usage

```bash
# Redis CLI
redis-cli INFO memory

# Check used memory
redis-cli INFO | grep used_memory_human
```

---

## Production Deployment

### Redis Configuration

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict least recently used
tcp-keepalive 300
timeout 0
```

### High Availability

```python
# Redis Sentinel for HA
from redis.sentinel import Sentinel

sentinel = Sentinel([
    ('sentinel1', 26379),
    ('sentinel2', 26379),
    ('sentinel3', 26379)
], socket_timeout=0.1)

# Get master
master = sentinel.master_for('mymaster', socket_timeout=0.1)
```

### Redis Cluster

```python
# Redis Cluster for horizontal scaling
from redis.cluster import RedisCluster

rc = RedisCluster(host='localhost', port=7000)
```

---

## Troubleshooting

### Connection Refused

```python
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
# Expected: PONG
```

### Out of Memory

```bash
# Check memory usage
redis-cli INFO memory

# Increase maxmemory in redis.conf
maxmemory 4gb

# Or enable eviction policy
maxmemory-policy allkeys-lru
```

### Slow Operations

```python
# Enable slow log
redis-cli CONFIG SET slowlog-log-slower-than 10000  # 10ms

# Check slow log
redis-cli SLOWLOG GET 10
```

---

## Migration

### From InMemory to Redis

```python
# No data migration needed
# Just change adapter type in config
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="redis")  # Was "memory"
)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-database:{ .lg .middle } **ChromaDB Adapter**

    ---

    Add persistent vector search.

    [:octicons-arrow-right-24: ChromaDB Guide](chromadb.md)

-   :material-rocket-launch:{ .lg .middle } **Qdrant Adapter**

    ---

    High-performance production vector search.

    [:octicons-arrow-right-24: Qdrant Guide](qdrant.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Configure Redis for production.

    [:octicons-arrow-right-24: Production Guide](../deployment/production.md)

</div>
