# Performance Optimization

Optimize Axon memory systems for maximum throughput and minimal latency.

---

## Overview

This guide covers performance optimization strategies for Axon-based applications, including benchmarking, profiling, and tuning recommendations.

**Key Topics:**
- ✓ Performance benchmarks
- ✓ Bottleneck identification
- ✓ Optimization strategies
- ✓ Caching patterns
- ✓ Query optimization
- ✓ Resource tuning

---

## Benchmarks

### Typical Performance

| Operation | InMemory | Redis | ChromaDB | Qdrant | Pinecone |
|-----------|----------|-------|----------|---------|----------|
| **store()** | 0.1-1ms | 5-20ms | 10-50ms | 20-100ms | 50-150ms |
| **recall()** | 1-10ms | 10-50ms | 20-100ms | 20-100ms | 50-200ms |
| **get()** | 0.1ms | 2-10ms | 5-20ms | 10-50ms | 20-100ms |
| **delete()** | 0.1ms | 2-10ms | 5-20ms | 10-50ms | 20-100ms |

*Note: Latencies include embedding generation (~50-200ms for OpenAI)*

### Throughput

| Adapter | Reads/sec | Writes/sec | Scale |
|---------|-----------|------------|-------|
| **InMemory** | 50,000+ | 50,000+ | Single node |
| **Redis** | 10,000+ | 5,000+ | Distributed |
| **ChromaDB** | 1,000+ | 500+ | Single node |
| **Qdrant** | 5,000+ | 2,000+ | Distributed |
| **Pinecone** | 2,000+ | 1,000+ | Serverless |

---

## Bottleneck Identification

### Profiling

```python
import time
import logging
from axon import MemorySystem

logger = logging.getLogger(__name__)

async def profile_operation(operation_name: str, func, *args, **kwargs):
    """Profile an async operation."""
    start = time.time()
    result = await func(*args, **kwargs)
    duration = (time.time() - start) * 1000
    
    logger.info(f"{operation_name}: {duration:.2f}ms")
    return result

# Profile store operation
memory = MemorySystem(config)
await profile_operation("store", memory.store, "Test data", importance=0.8)

# Profile recall operation
await profile_operation("recall", memory.recall, "query", k=10)
```

### Common Bottlenecks

1. **Embedding Generation** (50-200ms)
   - OpenAI API call latency
   - Solution: Batch embeddings, use local models

2. **Network Latency** (10-100ms)
   - Redis/Qdrant round trips
   - Solution: Connection pooling, request batching

3. **Vector Search** (10-100ms)
   - Large dataset similarity search
   - Solution: Indexes, filtering, limit k

4. **Serialization** (1-10ms)
   - JSON encoding/decoding
   - Solution: MessagePack, Protocol Buffers

---

## Optimization Strategies

### 1. Batch Operations

```python
# ❌ Slow: Individual operations
for text in texts:
    await memory.store(text)  # N round trips

# ✓ Fast: Batch operations
await memory.bulk_store(texts)  # 1 round trip
```

### 2. Connection Pooling

```python
# ✓ Reuse connections
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://localhost:6379",
            "max_connections": 50,  # Connection pool
            "socket_timeout": 5,
            "socket_connect_timeout": 5
        }
    )
)
```

### 3. Query Optimization

```python
# ❌ Slow: Large result set
results = await memory.recall(query, k=1000)  # Too many results

# ✓ Fast: Limit results
results = await memory.recall(query, k=10)  # Just what you need

# ✓ Fast: Add filters
results = await memory.recall(
    query,
    k=10,
    filter=Filter(tags=["specific"])  # Reduce search space
)
```

### 4. Caching

```python
from functools import lru_cache
import hashlib

# Cache embeddings
@lru_cache(maxsize=10000)
def get_cached_embedding(text: str):
    """Cache embeddings for frequently used text."""
    # Generate embedding once, reuse many times
    return embedder.embed(text)

# Use in store operations
embedding = get_cached_embedding(text)
await memory.store(text, embedding=embedding)
```

### 5. Async Operations

```python
import asyncio

# ❌ Slow: Sequential
for text in texts:
    await memory.store(text)

# ✓ Fast: Concurrent
tasks = [memory.store(text) for text in texts]
await asyncio.gather(*tasks)
```

---

## Adapter-Specific Tuning

### InMemory Adapter

```python
# Already optimized - no tuning needed
# Use for: Development, testing, ephemeral tier
```

### Redis Adapter

```python
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://localhost:6379",
            
            # Connection pool
            "max_connections": 50,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            
            # Pipeline operations
            "decode_responses": True,
            
            # Namespace for isolation
            "namespace": "axon:session"
        }
    )
)

# Enable persistence
# redis.conf:
# appendonly yes
# appendfsync everysec  # Balance performance + durability
```

### Qdrant Adapter

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        adapter_config={
            "url": "http://localhost:6333",
            "collection_name": "memories",
            
            # Increase timeout for large queries
            "timeout": 60,
            
            # Use async client
            "prefer_grpc": True  # Faster than HTTP
        }
    )
)

# Qdrant configuration (config.yaml):
# storage:
#   on_disk_payload: false  # Keep in RAM for speed
# service:
#   max_request_size_mb: 100
```

### Pinecone Adapter

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="pinecone",
        adapter_config={
            "api_key": "your-key",
            "index_name": "memories",
            "environment": "us-east1-gcp",
            
            # Use namespaces for isolation
            "namespace": "production"
        }
    )
)

# Pinecone automatically handles:
# - Auto-scaling
# - Load balancing
# - Replication
```

---

## Embedding Optimization

### Use Local Embedders

```python
# ❌ Slow: OpenAI API (200ms per embedding)
from axon.embedders.openai import OpenAIEmbedder

embedder = OpenAIEmbedder()
# Each embedding: 200ms network latency

# ✓ Fast: Local sentence-transformers (10ms per embedding)
from axon.embedders.sentence_transformer import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder(
    model_name="all-MiniLM-L6-v2"  # Fast, local
)
# Each embedding: 10ms on CPU, 1ms on GPU
```

### Batch Embeddings

```python
# ❌ Slow: Individual embeddings
for text in texts:
    embedding = await embedder.embed(text)  # N API calls

# ✓ Fast: Batch embeddings
embeddings = await embedder.embed_batch(texts)  # 1 API call
```

### Cache Embeddings

```python
import hashlib
import json
from pathlib import Path

class EmbeddingCache:
    """Cache embeddings to disk."""
    
    def __init__(self, cache_dir: str = ".embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_key(self, text: str) -> str:
        """Generate cache key."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def get_embedding(self, text: str, embedder):
        """Get embedding from cache or generate."""
        key = self._get_key(text)
        cache_file = self.cache_dir / f"{key}.json"
        
        # Check cache
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        
        # Generate and cache
        embedding = await embedder.embed(text)
        with open(cache_file, 'w') as f:
            json.dump(embedding, f)
        
        return embedding

# Use cache
cache = EmbeddingCache()
embedding = await cache.get_embedding(text, embedder)
```

---

## Memory Management

### Set Compaction Thresholds

```python
# Balance memory usage vs performance
config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        compaction_threshold=1000,  # Compact at 1K entries
        compaction_batch_size=100
    ),
    session=SessionPolicy(
        compaction_threshold=10000,  # Compact at 10K
        compaction_batch_size=500
    ),
    persistent=PersistentPolicy(
        compaction_threshold=100000,  # Compact at 100K
        compaction_batch_size=1000
    )
)
```

### Monitor Memory Usage

```python
import psutil
import logging

logger = logging.getLogger(__name__)

def log_memory_usage():
    """Log current memory usage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    
    logger.info(f"Memory usage: {mem_info.rss / 1024 / 1024:.2f} MB")

# Monitor periodically
import schedule

schedule.every(5).minutes.do(log_memory_usage)
```

---

## Query Optimization

### Use Filters

```python
# ❌ Slow: Search all entries
results = await memory.recall(query, k=10)  # Searches millions

# ✓ Fast: Filter first
results = await memory.recall(
    query,
    k=10,
    filter=Filter(
        tags=["category:tech"],  # Narrow search space
        min_importance=0.7       # Only important entries
    )
)
```

### Limit Result Count

```python
# ❌ Slow: Too many results
results = await memory.recall(query, k=1000)  # Process 1000 results

# ✓ Fast: Reasonable limit
results = await memory.recall(query, k=10)  # Process 10 results
```

### Use Appropriate Tier

```python
# ❌ Slow: Search persistent for recent data
results = await memory.recall(query, tier="persistent")

# ✓ Fast: Search ephemeral for recent
results = await memory.recall(query, tier="ephemeral")
```

---

## Load Testing

### Benchmark Script

```python
import asyncio
import time
from axon import MemorySystem

async def benchmark_store(memory, n: int = 1000):
    """Benchmark store operations."""
    start = time.time()
    
    tasks = [
        memory.store(f"Test entry {i}", importance=0.5)
        for i in range(n)
    ]
    
    await asyncio.gather(*tasks)
    
    duration = time.time() - start
    ops_per_sec = n / duration
    
    print(f"Store: {n} ops in {duration:.2f}s = {ops_per_sec:.0f} ops/sec")

async def benchmark_recall(memory, n: int = 1000):
    """Benchmark recall operations."""
    start = time.time()
    
    tasks = [
        memory.recall(f"query {i}", k=10)
        for i in range(n)
    ]
    
    await asyncio.gather(*tasks)
    
    duration = time.time() - start
    ops_per_sec = n / duration
    
    print(f"Recall: {n} ops in {duration:.2f}s = {ops_per_sec:.0f} ops/sec")

# Run benchmarks
memory = MemorySystem(config)
await benchmark_store(memory, 1000)
await benchmark_recall(memory, 1000)
```

### Stress Testing

```python
import asyncio
import time

async def stress_test(memory, duration_seconds: int = 60):
    """Stress test for duration."""
    start = time.time()
    operations = 0
    errors = 0
    
    async def worker():
        nonlocal operations, errors
        while time.time() - start < duration_seconds:
            try:
                await memory.store(f"Test {operations}", importance=0.5)
                operations += 1
            except Exception as e:
                errors += 1
                print(f"Error: {e}")
    
    # Run 10 concurrent workers
    await asyncio.gather(*[worker() for _ in range(10)])
    
    duration = time.time() - start
    print(f"Stress test: {operations} ops in {duration:.2f}s")
    print(f"Throughput: {operations / duration:.0f} ops/sec")
    print(f"Errors: {errors}")

# Run stress test
await stress_test(memory, duration_seconds=60)
```

---

## Best Practices

### 1. Use Appropriate Adapters

```python
# ✓ Good: Match adapter to use case
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="memory"),  # Fast
    session=SessionPolicy(adapter_type="redis"),       # Distributed
    persistent=PersistentPolicy(adapter_type="qdrant")  # Scalable
)

# ✗ Bad: Wrong adapter
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="pinecone")  # Overkill!
)
```

### 2. Enable Connection Pooling

```python
# ✓ Good: Connection pool
adapter_config={"max_connections": 50}

# ✗ Bad: No pooling
adapter_config={}  # 1 connection per request
```

### 3. Monitor Performance

```python
# ✓ Good: Track metrics
from axon.core.logging_config import log_performance

@log_performance
async def store_with_monitoring(memory, text):
    return await memory.store(text)

# ✗ Bad: No monitoring
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-monitor:{ .lg .middle } **Monitoring**

    ---

    Set up performance monitoring.

    [:octicons-arrow-right-24: Monitoring Guide](monitoring.md)

-   :material-rocket-launch:{ .lg .middle } **Production**

    ---

    Deploy with optimizations.

    [:octicons-arrow-right-24: Production Guide](production.md)

-   :material-database:{ .lg .middle } **Adapters**

    ---

    Compare adapter performance.

    [:octicons-arrow-right-24: Adapters Guide](../adapters/overview.md)

</div>
