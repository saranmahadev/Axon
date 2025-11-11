# Qdrant Adapter

High-performance vector search engine adapter for production-scale persistent storage.

---

## Overview

The **Qdrant adapter** provides persistent vector storage using Qdrant, a high-performance vector search engine. Perfect for production deployments requiring fast, scalable semantic search.

**Key Features:**
- ✓ High-performance vector search
- ✓ Horizontal scaling support
- ✓ Local and cloud deployment
- ✓ Advanced filtering capabilities
- ✓ Persistent storage
- ✓ Production-ready
- ✓ Cost-effective (self-hosted)

---

## Installation

```bash
# Install Qdrant client
pip install qdrant-client>=1.6.0

# Or with axon-sdk
pip install "axon-sdk[all]"

# Start Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant:latest
```

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy

config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        compaction_threshold=20000
    )
)

memory = MemorySystem(config)

# Store with high-performance search
await memory.store("Production knowledge", importance=0.8)
```

---

## Configuration

### Local Instance

```python
from axon.adapters.qdrant import QdrantAdapter

# Local Qdrant
adapter = QdrantAdapter(
    url="http://localhost:6333",
    collection_name="memories"
)
```

### Qdrant Cloud

```python
# Qdrant Cloud (managed)
adapter = QdrantAdapter(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key",
    collection_name="memories"
)
```

### Environment Variables

```bash
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-api-key
```

### Using with Templates

```python
from axon.core.templates import QDRANT_CONFIG

# QDRANT_CONFIG uses Qdrant for persistent tier
memory = MemorySystem(QDRANT_CONFIG)
```

---

## Features

### High-Performance Search

Optimized for large-scale vector search:

```python
# Fast semantic search on millions of vectors
results = await memory.recall(
    "Find relevant information",
    k=100,  # Can retrieve many results efficiently
    tier="persistent"
)

# Typical latency: 10-50ms even with 10M+ vectors
```

### Advanced Filtering

Powerful metadata filtering:

```python
from axon.models.filter import Filter

results = await memory.recall(
    "query",
    filter=Filter(
        tags=["verified", "important"],
        min_importance=0.7,
        max_age_seconds=2592000,  # 30 days
        metadata={"category": "technical"}
    ),
    k=20
)
```

### Horizontal Scaling

Scale across multiple nodes:

```python
# Qdrant supports distributed deployment
# Collections can be sharded across nodes
# Automatic replication for high availability
```

---

## Use Cases

### ✅ Perfect For

- **Persistent Tier**: Production knowledge base
- Large-scale deployments (>1M vectors)
- High-performance vector search
- Self-hosted infrastructure
- Cost-sensitive production workloads
- Multi-tenant applications
- RAG (Retrieval-Augmented Generation)

### ❌ Not Suitable For

- Embedded applications (use ChromaDB)
- Ephemeral/session tiers (use Redis)
- Fully managed preference (use Pinecone)

---

## Examples

### Production Knowledge Base

```python
# Large-scale knowledge base
for i in range(100000):
    await memory.store(
        f"Knowledge entry {i}: {content}",
        importance=0.8,
        tier="persistent",
        tags=["knowledge", category]
    )

# Fast semantic search
results = await memory.recall(
    "What is machine learning?",
    k=50,
    tier="persistent"
)
```

### Multi-Tenant System

```python
# Use namespaces for isolation
tenant1_adapter = QdrantAdapter(
    url="http://qdrant:6333",
    collection_name="tenant_123"
)

tenant2_adapter = QdrantAdapter(
    url="http://qdrant:6333",
    collection_name="tenant_456"
)

# Or use metadata for filtering
await memory.store(
    "Tenant-specific data",
    importance=0.8,
    metadata={"tenant_id": "123"}
)

# Query with tenant filter
results = await memory.recall(
    "query",
    filter=Filter(metadata={"tenant_id": "123"})
)
```

### RAG Application

```python
# Build RAG system with Qdrant
async def answer_question(question: str) -> str:
    # Retrieve relevant context
    context = await memory.recall(
        question,
        k=5,
        tier="persistent"
    )
    
    # Build prompt
    context_text = "\n".join([c.text for c in context])
    prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
    
    # Generate answer with LLM
    answer = await llm.generate(prompt)
    return answer
```

---

## Performance

| Operation | Latency | Throughput | Scale |
|-----------|---------|------------|-------|
| **save()** | 10-100ms | 500-2000 ops/sec | Millions |
| **query()** | 10-50ms | 200-1000 ops/sec | Millions |
| **get()** | 5-20ms | 1000-5000 ops/sec | Millions |
| **delete()** | 10-50ms | 500-2000 ops/sec | Millions |

**Note:** Performance scales with hardware and cluster configuration.

---

## Production Deployment

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
  
  app:
    build: .
    depends_on:
      - qdrant
    environment:
      - QDRANT_URL=http://qdrant:6333
      - QDRANT_API_KEY=${QDRANT_API_KEY}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  serviceName: qdrant
  replicas: 3
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        volumeMounts:
        - name: storage
          mountPath: /qdrant/storage
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
```

### Qdrant Cloud

```python
# Managed Qdrant Cloud (easiest production option)
adapter = QdrantAdapter(
    url="https://abc123.us-east-1.aws.cloud.qdrant.io",
    api_key="your-cloud-api-key",
    collection_name="memories"
)

# Features:
# - Automatic scaling
# - High availability
# - Monitoring included
# - No infrastructure management
```

---

## Best Practices

### 1. Use for Persistent Tier

```python
# ✓ Good: High-performance persistent storage
persistent=PersistentPolicy(adapter_type="qdrant")

# ✗ Bad: Overkill for ephemeral (use Redis)
ephemeral=EphemeralPolicy(adapter_type="qdrant")
```

### 2. Optimize Collection Settings

```python
# Configure for performance
adapter = QdrantAdapter(
    url="http://qdrant:6333",
    collection_name="memories",
    timeout=60  # Longer timeout for large queries
)
```

### 3. Use Batch Operations

```python
# Batch inserts for better performance
entries = [
    MemoryEntry(text=f"Entry {i}", ...)
    for i in range(1000)
]

# Use bulk_save (if implemented)
for entry in entries:
    await adapter.save(entry)
```

### 4. Monitor Performance

```bash
# Qdrant metrics endpoint
curl http://localhost:6333/metrics

# Check collection info
curl http://localhost:6333/collections/memories
```

---

## Troubleshooting

### Connection Issues

```python
# Test connection
import aiohttp

async def test_connection():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:6333') as resp:
            print(f"Status: {resp.status}")

# Check Qdrant logs
docker logs qdrant-container
```

### Slow Queries

```python
# Add more specific filters
results = await memory.recall(
    "query",
    filter=Filter(tags=["specific"]),  # Reduces search space
    k=10  # Fewer results
)

# Or increase Qdrant resources
# - More CPU cores
# - More RAM
# - SSD storage
```

### Collection Issues

```python
# List collections
collections = await adapter.client.get_collections()
print([c.name for c in collections.collections])

# Recreate collection (development only!)
await adapter.client.delete_collection(collection_name)
```

---

## Migration

### From ChromaDB to Qdrant

```python
# Export from ChromaDB
chroma_memory = MemorySystem(STANDARD_CONFIG)  # Uses ChromaDB
entries = await chroma_memory.export(tier="persistent")

# Import to Qdrant
qdrant_config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="qdrant")
)
qdrant_memory = MemorySystem(qdrant_config)
await qdrant_memory.import_data(entries, tier="persistent")
```

---

## Cost Optimization

### Self-Hosted vs Cloud

| Deployment | Monthly Cost | Management | Scaling |
|------------|--------------|------------|---------|
| **Self-Hosted** | $50-500 | Manual | Manual |
| **Qdrant Cloud** | $200-2000 | Automated | Auto |

### Self-Hosted Setup

```bash
# Digital Ocean Droplet (8GB RAM, 4 vCPUs)
# ~$48/month

# Install Qdrant
docker run -d \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Cost for 10M vectors: ~$50-100/month (storage + compute)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-cloud:{ .lg .middle } **Pinecone Adapter**

    ---

    Fully managed alternative to Qdrant.

    [:octicons-arrow-right-24: Pinecone Guide](pinecone.md)

-   :material-chart-line:{ .lg .middle } **Performance Tuning**

    ---

    Optimize Qdrant for your workload.

    [:octicons-arrow-right-24: Performance Guide](../deployment/performance.md)

-   :material-server:{ .lg .middle } **Production Deployment**

    ---

    Deploy Qdrant in production.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
