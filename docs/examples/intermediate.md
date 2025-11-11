# Intermediate Examples

Explore advanced memory management with adapters, tiers, and policies from `examples/02-intermediate/`.

---

## Overview

These intermediate examples demonstrate adapter configuration, multi-tier memory management, and policy customization.

**Examples Covered:**
- Adapters (4 examples)
- Memory Tiers (4 examples)
- Policies (4 examples)

**What You'll Learn:**
- Storage adapter configuration
- Tier promotion and demotion
- Policy customization
- Multi-tier queries
- TTL and overflow management

**Prerequisites:**
- Completed basic examples
- Redis server (for adapter examples)
- Understanding of memory tiers

**Location:** `examples/02-intermediate/`

---

## Adapters

### 01_inmemory_adapter.py

**In-memory storage** - Fast, ephemeral storage for temporary data.

**File:** `examples/02-intermediate/adapters/01_inmemory_adapter.py`

**What it demonstrates:**
- InMemoryAdapter configuration
- Fastest performance (microseconds)
- No persistence
- Use cases: caching, temporary calculations
- Thread-safety with asyncio

**Key configuration:**

```python
from axon.core.policies import EphemeralPolicy

config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="memory",  # In-memory adapter
        ttl_seconds=60,
        max_entries=100
    ),
    persistent=PersistentPolicy(adapter_type="memory")
)
```

---

### 02_redis_adapter.py

**Redis for session storage** - High-performance distributed caching.

**File:** `examples/02-intermediate/adapters/02_redis_adapter.py`

**What it demonstrates:**
- Redis adapter configuration
- Connection setup
- TTL and eviction policies
- Multi-process support
- Production use cases

**Key configuration:**

```python
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://localhost:6379",
            "password": "your-password",
            "db": 0,
            "max_connections": 50
        },
        ttl_seconds=600,
        max_entries=1000
    ),
    persistent=PersistentPolicy(adapter_type="memory")
)
```

**Requirements:**
- Redis server running on localhost:6379
- `pip install redis`

---

### 03_vector_adapters.py

**Vector databases** - ChromaDB, Qdrant, Pinecone for semantic search.

**File:** `examples/02-intermediate/adapters/03_vector_adapters.py`

**What it demonstrates:**
- ChromaDB configuration
- Qdrant configuration
- Pinecone configuration
- Vector similarity search
- Metadata filtering

**ChromaDB:**

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="chroma",
        adapter_config={
            "host": "localhost",
            "port": 8000,
            "collection_name": "memories"
        }
    )
)
```

**Qdrant:**

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        adapter_config={
            "url": "http://localhost:6333",
            "collection_name": "memories",
            "prefer_grpc": True
        }
    )
)
```

**Pinecone:**

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="pinecone",
        adapter_config={
            "api_key": "your-api-key",
            "environment": "us-west1-gcp",
            "index_name": "memories"
        }
    )
)
```

---

### 04_adapter_selection.py

**Choose the right adapter** - Decision framework for adapter selection.

**File:** `examples/02-intermediate/adapters/04_adapter_selection.py`

**What it demonstrates:**
- Adapter comparison
- Performance benchmarks
- Use case matching
- Cost vs. performance trade-offs

| Adapter | Speed | Persistence | Cost | Best For |
|---------|-------|-------------|------|----------|
| InMemory | Fastest | None | Free | Ephemeral, testing |
| Redis | Fast | Snapshots | Low | Sessions, caching |
| ChromaDB | Medium | Full | Free | Self-hosted semantic search |
| Qdrant | Fast | Full | Medium | Production semantic search |
| Pinecone | Medium | Full | High | Managed, global scale |

---

## Memory Tiers

### 01_understanding_tiers.py

**Multi-tier architecture** - Learn how tiers work together.

**File:** `examples/02-intermediate/memory-tiers/01_understanding_tiers.py`

**What it demonstrates:**
- Three-tier architecture (ephemeral, session, persistent)
- Automatic tier selection by importance
- Tier characteristics and trade-offs
- When to use each tier

**Tier selection logic:**

```python
# importance >= 0.7 → persistent
await memory.store("Critical data", importance=0.9)

# 0.3 <= importance < 0.7 → session  
await memory.store("Session data", importance=0.5)

# importance < 0.3 → ephemeral
await memory.store("Temporary data", importance=0.2)
```

---

### 02_tier_promotion.py

**Automatic promotion** - Elevate important memories to higher tiers.

**File:** `examples/02-intermediate/memory-tiers/02_tier_promotion.py`

**What it demonstrates:**
- Access pattern tracking
- Automatic promotion based on:
  - High importance (>= 0.7)
  - High access frequency (>= 5 accesses)
  - Recent access patterns
- Manual promotion
- Promotion strategies

**Enable promotion:**

```python
config = MemoryConfig(
    ephemeral=EphemeralPolicy(...),
    session=SessionPolicy(...),
    persistent=PersistentPolicy(...),
    enable_promotion=True  # Auto-promote important memories
)
```

**Promotion criteria:**
- Entry accessed 5+ times → promote
- Importance >= 0.7 → promote
- Recent access (< 1 hour) → promote

---

### 03_tier_overflow.py

**Handle capacity limits** - Manage tier overflow gracefully.

**File:** `examples/02-intermediate/memory-tiers/03_tier_overflow.py`

**What it demonstrates:**
- Max entries configuration
- Overflow strategies
- Eviction policies (LRU, FIFO, TTL, importance)
- Overflow to next tier

**Overflow configuration:**

```python
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        max_entries=1000,  # Limit capacity
        eviction_strategy="lru",  # Least recently used
        overflow_to_persistent=True  # Move to persistent on overflow
    ),
    persistent=PersistentPolicy(...)
)
```

---

### 04_multi_tier_queries.py

**Query across tiers** - Search multiple tiers efficiently.

**File:** `examples/02-intermediate/memory-tiers/04_multi_tier_queries.py`

**What it demonstrates:**
- Query all tiers simultaneously
- Query specific tier
- Merge and rank results
- Performance optimization

**Multi-tier recall:**

```python
# Query all tiers
results = await memory.recall("query", k=10)

# Query specific tier
results = await memory.recall("query", tier="session")

# Query multiple tiers
results = await memory.recall("query", tiers=["session", "persistent"])
```

---

## Policies

### 01_custom_policies.py

**Create custom policies** - Tailor tier behavior to your needs.

**File:** `examples/02-intermediate/policies/01_custom_policies.py`

**What it demonstrates:**
- Custom policy creation
- Override default behavior
- Custom eviction strategies
- Application-specific policies

---

### 02_ttl_management.py

**Time-to-live policies** - Automatic expiration and cleanup.

**File:** `examples/02-intermediate/policies/02_ttl_management.py`

**What it demonstrates:**
- TTL configuration
- Automatic expiration
- TTL extension
- TTL monitoring

**TTL configuration:**

```python
config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        ttl_seconds=60  # 1 minute
    ),
    session=SessionPolicy(
        ttl_seconds=600  # 10 minutes
    ),
    persistent=PersistentPolicy(
        ttl_seconds=None  # Never expires
    )
)
```

---

### 03_overflow_policies.py

**Overflow management** - Handle tier capacity intelligently.

**File:** `examples/02-intermediate/policies/03_overflow_policies.py`

**What it demonstrates:**
- Overflow detection
- Overflow strategies
- Tier migration on overflow
- Capacity planning

---

### 04_compaction_policies.py

**Memory compaction** - Summarize and compress old memories.

**File:** `examples/02-intermediate/policies/04_compaction_policies.py`

**What it demonstrates:**
- Compaction triggers
- Compaction strategies
- Memory summarization
- Performance impact

**Compaction configuration:**

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_threshold=10000,  # Trigger at 10K entries
        compaction_strategy="semantic"  # Cluster similar entries
    )
)
```

---

## Summary

Intermediate examples demonstrate:

**Adapters:**
- InMemory for speed
- Redis for sessions
- Vector DBs for semantic search
- Choosing the right adapter

**Memory Tiers:**
- Multi-tier architecture
- Automatic promotion
- Overflow handling
- Multi-tier queries

**Policies:**
- Custom policy creation
- TTL management
- Overflow strategies
- Compaction policies

**Run All Intermediate Examples:**

```bash
cd examples/02-intermediate

# Adapters
python adapters/01_inmemory_adapter.py
python adapters/02_redis_adapter.py
python adapters/03_vector_adapters.py
python adapters/04_adapter_selection.py

# Memory tiers
python memory-tiers/01_understanding_tiers.py
python memory-tiers/02_tier_promotion.py
python memory-tiers/03_tier_overflow.py
python memory-tiers/04_multi_tier_queries.py

# Policies
python policies/01_custom_policies.py
python policies/02_ttl_management.py
python policies/03_overflow_policies.py
python policies/04_compaction_policies.py
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-shield-lock:{ .lg .middle } **Advanced Examples**

    ---

    Audit, privacy, transactions, and performance.

    [:octicons-arrow-right-24: Advanced Examples](advanced.md)

-   :material-puzzle:{ .lg .middle } **Integration Examples**

    ---

    LangChain and LlamaIndex integrations.

    [:octicons-arrow-right-24: Integration Examples](integrations.md)

-   :material-application:{ .lg .middle } **Real-World Examples**

    ---

    Complete applications and use cases.

    [:octicons-arrow-right-24: Real-World Examples](real-world.md)

</div>
