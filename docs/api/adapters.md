# Storage Adapters API

Complete API reference for storage adapter interface and implementations.

---

## Overview

Storage adapters provide the persistence layer for Axon's memory system. All adapters implement the `StorageAdapter` interface for consistent operations across different backends.

```python
from axon.adapters import InMemoryAdapter, RedisAdapter, ChromaAdapter

# Use different adapters
memory_adapter = InMemoryAdapter()
redis_adapter = RedisAdapter(url="redis://localhost:6379")
chroma_adapter = ChromaAdapter(host="localhost", port=8000)
```

---

## StorageAdapter (Base Class)

Abstract base class that all adapters must implement.

### Methods

#### `save`

```python
async def save(self, entry: MemoryEntry) -> str
```

Save a memory entry and return its ID.

**Parameters:**
- `entry` (`MemoryEntry`): Memory entry to save

**Returns:**
- `str`: Entry ID

**Raises:**
- `ValueError`: If entry is invalid

---

#### `query`

```python
async def query(
    self,
    vector: list[float],
    k: int = 5,
    filter: Filter | None = None
) -> list[MemoryEntry]
```

Query by vector similarity with optional metadata filtering.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vector` | `list[float]` | required | Query embedding vector |
| `k` | `int` | `5` | Number of results (top-k) |
| `filter` | `Filter \| None` | `None` | Optional metadata filter |

**Returns:**
- `list[MemoryEntry]`: Matching entries, ordered by similarity

**Raises:**
- `ValueError`: If vector is empty or k is invalid

---

#### `get`

```python
async def get(self, id: str) -> MemoryEntry
```

Retrieve a memory entry by ID.

**Parameters:**
- `id` (`str`): Entry identifier

**Returns:**
- `MemoryEntry`: Memory entry

**Raises:**
- `KeyError`: If entry not found

---

#### `delete`

```python
async def delete(self, id: str) -> bool
```

Delete a memory entry by ID.

**Parameters:**
- `id` (`str`): Entry identifier

**Returns:**
- `bool`: `True` if deleted, `False` if not found

**Raises:**
- `ValueError`: If id is invalid

---

#### `bulk_save`

```python
async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]
```

Save multiple entries efficiently in batch.

**Parameters:**
- `entries` (`list[MemoryEntry]`): List of entries to save

**Returns:**
- `list[str]`: List of entry IDs

---

#### `reindex`

```python
async def reindex(self) -> None
```

Rebuild index for vector stores (vector databases only).

---

## Transaction Support

Adapters may support distributed transactions with Two-Phase Commit (2PC).

#### `supports_transactions`

```python
async def supports_transactions(self) -> bool
```

Check if adapter supports transactions.

**Returns:**
- `bool`: `True` if transactions supported

---

#### `prepare_transaction`

```python
async def prepare_transaction(self, transaction_id: str) -> bool
```

Prepare phase of 2PC protocol.

**Parameters:**
- `transaction_id` (`str`): Transaction identifier

**Returns:**
- `bool`: `True` if prepared successfully

---

#### `commit_transaction`

```python
async def commit_transaction(self, transaction_id: str) -> bool
```

Commit phase of 2PC protocol.

**Parameters:**
- `transaction_id` (`str`): Transaction identifier

**Returns:**
- `bool`: `True` if committed successfully

---

#### `abort_transaction`

```python
async def abort_transaction(self, transaction_id: str) -> bool
```

Abort transaction and rollback changes.

**Parameters:**
- `transaction_id` (`str`): Transaction identifier

**Returns:**
- `bool`: `True` if aborted successfully

---

## InMemoryAdapter

In-memory storage adapter (ephemeral tier).

### Constructor

```python
class InMemoryAdapter(StorageAdapter):
    def __init__(self)
```

**Features:**
- Fastest performance (microseconds)
- No persistence (data lost on restart)
- No external dependencies
- Thread-safe with asyncio locks

**Example:**

```python
from axon.adapters import InMemoryAdapter

adapter = InMemoryAdapter()

# Save
entry = MemoryEntry(id="1", text="Data", embedding=[0.1, 0.2])
await adapter.save(entry)

# Query
results = await adapter.query([0.1, 0.2], k=5)

# Get
entry = await adapter.get("1")

# Delete
await adapter.delete("1")
```

---

## RedisAdapter

Redis-backed storage adapter (session tier).

### Constructor

```python
class RedisAdapter(StorageAdapter):
    def __init__(
        self,
        url: str = "redis://localhost:6379",
        password: str | None = None,
        db: int = 0,
        max_connections: int = 50,
        socket_timeout: int = 5
    )
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | `"redis://localhost:6379"` | Redis connection URL |
| `password` | `str \| None` | `None` | Redis password |
| `db` | `int` | `0` | Database number |
| `max_connections` | `int` | `50` | Connection pool size |
| `socket_timeout` | `int` | `5` | Socket timeout in seconds |

**Features:**
- Fast performance (milliseconds)
- Persistence with snapshots
- TTL support
- Distributed caching
- Transaction support with MULTI/EXEC

**Example:**

```python
from axon.adapters import RedisAdapter

adapter = RedisAdapter(
    url="redis://localhost:6379",
    password="secret",
    max_connections=50
)

# Save with TTL
entry = MemoryEntry(id="1", text="Session data", embedding=[0.1, 0.2])
await adapter.save(entry)

# Auto-expires after TTL
```

---

## ChromaAdapter

ChromaDB vector database adapter (persistent tier).

### Constructor

```python
class ChromaAdapter(StorageAdapter):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "memories",
        distance_metric: str = "cosine"
    )
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | `"localhost"` | ChromaDB host |
| `port` | `int` | `8000` | ChromaDB port |
| `collection_name` | `str` | `"memories"` | Collection name |
| `distance_metric` | `str` | `"cosine"` | Distance metric ("cosine", "l2", "ip") |

**Features:**
- Optimized for semantic search
- Persistent storage
- Efficient vector similarity
- Metadata filtering
- Local or server deployment

**Example:**

```python
from axon.adapters import ChromaAdapter

adapter = ChromaAdapter(
    host="localhost",
    port=8000,
    collection_name="memories",
    distance_metric="cosine"
)

# Save
entry = MemoryEntry(
    id="1",
    text="User prefers dark mode",
    embedding=[0.1, 0.2, ...],  # 1536 dimensions
    metadata={"category": "preference"}
)
await adapter.save(entry)

# Query with filter
from axon.models.filter import Filter

results = await adapter.query(
    vector=[0.1, 0.2, ...],
    k=10,
    filter=Filter(metadata={"category": "preference"})
)
```

---

## QdrantAdapter

Qdrant vector database adapter (persistent tier).

### Constructor

```python
class QdrantAdapter(StorageAdapter):
    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        collection_name: str = "memories",
        distance: str = "Cosine",
        vector_size: int = 1536,
        timeout: int = 60,
        prefer_grpc: bool = True
    )
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | `"http://localhost:6333"` | Qdrant server URL |
| `api_key` | `str \| None` | `None` | API key for authentication |
| `collection_name` | `str` | `"memories"` | Collection name |
| `distance` | `str` | `"Cosine"` | Distance metric |
| `vector_size` | `int` | `1536` | Embedding dimension |
| `timeout` | `int` | `60` | Request timeout |
| `prefer_grpc` | `bool` | `True` | Use gRPC for better performance |

**Features:**
- High-performance vector search
- Horizontal scalability
- Advanced filtering
- Payload indexing
- gRPC support

**Example:**

```python
from axon.adapters import QdrantAdapter

adapter = QdrantAdapter(
    url="http://localhost:6333",
    api_key="your-api-key",
    collection_name="memories",
    prefer_grpc=True,
    timeout=60
)

# Save
entry = MemoryEntry(id="1", text="Data", embedding=[...])
await adapter.save(entry)

# Query
results = await adapter.query(vector=[...], k=10)
```

---

## PineconeAdapter

Pinecone vector database adapter (persistent tier).

### Constructor

```python
class PineconeAdapter(StorageAdapter):
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str = "memories",
        dimension: int = 1536,
        metric: str = "cosine"
    )
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | required | Pinecone API key |
| `environment` | `str` | required | Pinecone environment |
| `index_name` | `str` | `"memories"` | Index name |
| `dimension` | `int` | `1536` | Vector dimension |
| `metric` | `str` | `"cosine"` | Distance metric |

**Features:**
- Fully managed service
- Auto-scaling
- Global deployment
- Low latency
- Enterprise features

**Example:**

```python
from axon.adapters import PineconeAdapter

adapter = PineconeAdapter(
    api_key="your-api-key",
    environment="us-west1-gcp",
    index_name="memories",
    dimension=1536
)

# Save
entry = MemoryEntry(id="1", text="Data", embedding=[...])
await adapter.save(entry)

# Query
results = await adapter.query(vector=[...], k=10)
```

---

## Adapter Registry

Manages adapter instances and lazy initialization.

### Constructor

```python
class AdapterRegistry:
    def __init__(self)
```

### Methods

#### `register`

```python
def register(
    self,
    tier: str,
    adapter_type: str,
    adapter_config: dict | Policy
) -> None
```

Register an adapter for a tier.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tier` | `str` | Tier name |
| `adapter_type` | `str` | Adapter type ("redis", "chroma", etc.) |
| `adapter_config` | `dict \| Policy` | Adapter configuration |

**Example:**

```python
from axon.core.adapter_registry import AdapterRegistry

registry = AdapterRegistry()

registry.register(
    tier="session",
    adapter_type="redis",
    adapter_config={
        "url": "redis://localhost:6379",
        "password": "secret"
    }
)
```

---

#### `get_adapter`

```python
async def get_adapter(self, tier: str) -> StorageAdapter
```

Get adapter instance for tier (lazy initialization).

**Parameters:**
- `tier` (`str`): Tier name

**Returns:**
- `StorageAdapter`: Adapter instance

**Raises:**
- `KeyError`: If tier not registered

---

## Performance Comparison

| Adapter | Latency | Throughput | Persistence | Scalability |
|---------|---------|------------|-------------|-------------|
| **InMemory** | 0.1-1ms | 50K+ ops/sec | None | Single node |
| **Redis** | 5-20ms | 10K+ ops/sec | Snapshots | Cluster |
| **ChromaDB** | 20-100ms | 5K+ ops/sec | Persistent | Server |
| **Qdrant** | 20-100ms | 5K+ ops/sec | Persistent | Cluster |
| **Pinecone** | 50-150ms | 2K-5K ops/sec | Persistent | Global |

---

## Next Steps

<div class="grid cards" markdown>

-   :material-database-cog:{ .lg .middle } **Adapter Guides**

    ---

    Detailed adapter documentation.

    [:octicons-arrow-right-24: Adapter Guides](../adapters/overview.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Configure adapters in policies.

    [:octicons-arrow-right-24: Configuration API](config.md)

-   :material-wrench:{ .lg .middle } **Custom Adapters**

    ---

    Build your own adapter.

    [:octicons-arrow-right-24: Custom Adapters](../adapters/custom.md)

</div>
