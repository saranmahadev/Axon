# InMemory Adapter

Fast in-memory storage adapter for development, testing, and ephemeral workloads.

---

## Overview

The **InMemory adapter** stores memories in RAM using Python dictionaries with numpy-based vector similarity search. Perfect for development, testing, and situations where persistence isn't required.

**Key Features:**
- ✓ Zero setup - no external dependencies
- ✓ Fast operations (<1ms latency)
- ✓ Vector similarity search with numpy
- ✓ Metadata filtering
- ✗ No persistence (data lost on restart)
- ✗ Single-process only

---

## Installation

```bash
# Included with axon-sdk (no extra dependencies)
pip install axon-sdk
```

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

# Configure all tiers with InMemory
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="memory"),
    session=SessionPolicy(adapter_type="memory"),
    persistent=PersistentPolicy(adapter_type="memory")
)

memory = MemorySystem(config)

# Store and recall
await memory.store("Test data", importance=0.5)
results = await memory.recall("test", k=5)
```

---

## Configuration

### Default Configuration

```python
from axon.adapters.memory import InMemoryAdapter

adapter = InMemoryAdapter()
# No configuration needed - ready to use
```

### Using with Config Templates

```python
from axon.core.templates import DEVELOPMENT_CONFIG

# DEVELOPMENT_CONFIG uses InMemory for all tiers
memory = MemorySystem(DEVELOPMENT_CONFIG)
```

---

## Features

### Vector Similarity Search

Uses numpy for cosine similarity:

```python
# Automatic vector search
results = await memory.recall(
    "Find similar memories",
    k=10,
    tier="persistent"
)

# Results sorted by similarity score
for result in results:
    print(f"{result.text} (similarity: {result.similarity:.2f})")
```

### Metadata Filtering

Filter by tags, importance, date range:

```python
from axon.models.filter import Filter

results = await memory.recall(
    "query",
    filter=Filter(
        tags=["important"],
        min_importance=0.7,
        max_age_seconds=86400  # Last 24 hours
    )
)
```

---

## Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| **save()** | <1ms | >10,000 ops/sec |
| **query()** | <1ms | >5,000 ops/sec |
| **get()** | <1ms | >50,000 ops/sec |
| **delete()** | <1ms | >20,000 ops/sec |

**Note:** Performance depends on dataset size and vector dimensions.

---

## Use Cases

### ✅ Good For

- Local development and debugging
- Unit testing and CI/CD pipelines
- Prototyping and experimentation
- Ephemeral workloads that don't need persistence
- Single-process applications

### ❌ Not Good For

- Production deployments (no persistence)
- Multi-process applications (no shared state)
- Large datasets (memory constraints)
- Distributed systems
- Data that must survive restarts

---

## Examples

### Development Environment

```python
# Perfect for local development
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="memory", ttl_seconds=60),
    session=SessionPolicy(adapter_type="memory", ttl_seconds=600),
    persistent=PersistentPolicy(adapter_type="memory")
)

memory = MemorySystem(config)

# All operations work exactly like production
await memory.store("Development data", importance=0.8)
results = await memory.recall("development", k=5)
```

### Unit Testing

```python
import pytest
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

@pytest.fixture
def memory():
    """Provide clean memory system for each test."""
    return MemorySystem(DEVELOPMENT_CONFIG)

@pytest.mark.asyncio
async def test_store_and_recall(memory):
    # Store test data
    entry_id = await memory.store("Test memory", importance=0.5)
    assert entry_id is not None
    
    # Recall test data
    results = await memory.recall("test", k=1)
    assert len(results) == 1
    assert "test" in results[0].text.lower()
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install axon-sdk pytest pytest-asyncio
      - name: Run tests
        run: pytest
        # InMemory adapter - no external services needed!
```

---

## Limitations

### No Persistence

Data is lost when process exits:

```python
# Store data
await memory.store("Important data", importance=0.9)

# Restart application
# Data is gone ❌
```

**Solution:** Use ChromaDB, Qdrant, or Pinecone for persistence.

### Single Process Only

Cannot share data between processes:

```python
# Process 1
await memory.store("Data from process 1")

# Process 2
results = await memory.recall("data")
# Returns [] - different memory space ❌
```

**Solution:** Use Redis for distributed cache.

### Memory Constraints

Limited by available RAM:

```python
# Storing 1M entries with 1536-dim embeddings
# ~6GB RAM required (rough estimate)
```

**Solution:** Use disk-based storage for large datasets.

---

## Best Practices

### 1. Use for Development/Testing Only

```python
# ✓ Good: Development
if env == "development":
    config = DEVELOPMENT_CONFIG  # InMemory
else:
    config = PRODUCTION_CONFIG    # Redis + Qdrant

# ✗ Bad: Production
config = DEVELOPMENT_CONFIG  # Don't use InMemory in production!
```

### 2. Clean Up in Tests

```python
@pytest.fixture
def memory():
    mem = MemorySystem(DEVELOPMENT_CONFIG)
    yield mem
    # Cleanup happens automatically (garbage collected)
```

### 3. Monitor Memory Usage

```python
import sys

# Check memory usage
adapter_size = sys.getsizeof(adapter._storage)
print(f"Adapter memory: {adapter_size / 1024 / 1024:.2f} MB")
```

---

## Comparison with Other Adapters

| Feature | InMemory | Redis | ChromaDB |
|---------|----------|-------|----------|
| **Setup** | None | Redis server | None (embedded) |
| **Persistence** | ✗ | Optional | ✓ |
| **Distributed** | ✗ | ✓ | ✗ |
| **Vector Search** | ✓ (numpy) | ✗ | ✓ |
| **Latency** | <1ms | 1-5ms | 5-20ms |
| **Best For** | Dev/Test | Cache | Local persistence |

---

## Troubleshooting

### High Memory Usage

```python
# Check number of entries
stats = await memory.get_tier_stats("persistent")
print(f"Entries: {stats['entry_count']}")

# Clear old entries
await memory.forget(filter=Filter(max_age_seconds=3600))
```

### Slow Queries

```python
# Reduce result count
results = await memory.recall("query", k=5)  # Instead of k=100

# Or limit by filters
results = await memory.recall(
    "query",
    filter=Filter(tags=["specific"]),  # Reduces search space
    k=10
)
```

---

## Migration

### From InMemory to ChromaDB

```python
# Export from InMemory
entries = await memory.export(tier="persistent")

# Create ChromaDB config
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="chroma")
)
memory_new = MemorySystem(config)

# Import to ChromaDB
await memory_new.import_data(entries, tier="persistent")
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-database-sync:{ .lg .middle } **Redis Adapter**

    ---

    Add distributed caching with Redis.

    [:octicons-arrow-right-24: Redis Guide](redis.md)

-   :material-database:{ .lg .middle } **ChromaDB Adapter**

    ---

    Add persistence with embedded ChromaDB.

    [:octicons-arrow-right-24: ChromaDB Guide](chromadb.md)

-   :material-test-tube:{ .lg .middle } **Testing Guide**

    ---

    Best practices for testing with InMemory.

    [:octicons-arrow-right-24: Testing](../contributing/testing.md)

</div>
