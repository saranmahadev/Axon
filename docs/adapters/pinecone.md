# Pinecone Adapter

Fully managed serverless vector database for production without infrastructure management.

---

## Overview

The **Pinecone adapter** provides persistent vector storage using Pinecone, a fully managed serverless vector database. Perfect for production when you want performance without managing infrastructure.

**Key Features:**
- ✓ Fully managed service
- ✓ Serverless architecture
- ✓ Global deployment
- ✓ Auto-scaling
- ✓ High availability built-in
- ✓ No infrastructure management
- ✓ Production-ready out of the box

---

## Installation

```bash
# Install Pinecone client
pip install pinecone-client>=3.0.0

# Or with axon-sdk
pip install "axon-sdk[all]"

# Get API key from: https://app.pinecone.io
```

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy

config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="pinecone",
        compaction_threshold=20000
    )
)

memory = MemorySystem(config)

# Store with serverless scaling
await memory.store("Production knowledge", importance=0.8)
```

---

## Configuration

### API Key Setup

```python
from axon.adapters.pinecone import PineconeAdapter

# Basic configuration
adapter = PineconeAdapter(
    api_key="your-api-key",
    index_name="memories",
    environment="us-east1-gcp"  # or your preferred region
)
```

### Environment Variables

```bash
export PINECONE_API_KEY=your-api-key
export PINECONE_ENVIRONMENT=us-east1-gcp
export PINECONE_INDEX=memories
```

### Using with Templates

```python
from axon.core.templates import PINECONE_CONFIG

# PINECONE_CONFIG uses Pinecone for persistent tier
memory = MemorySystem(PINECONE_CONFIG)
```

---

## Features

### Serverless Architecture

No servers to manage:

```python
# Pinecone handles all infrastructure
# - Auto-scaling
# - Load balancing
# - High availability
# - Backups
# - Monitoring

# You just use it
results = await memory.recall(
    "query",
    k=50,
    tier="persistent"
)
```

### Global Deployment

Choose your region:

```python
# US East (GCP)
adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    environment="us-east1-gcp"
)

# EU West (AWS)
adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    environment="eu-west1-aws"
)

# Asia Pacific (GCP)
adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    environment="asia-southeast1-gcp"
)
```

### Metadata Filtering

Advanced filtering capabilities:

```python
from axon.models.filter import Filter

results = await memory.recall(
    "query",
    filter=Filter(
        tags=["verified"],
        min_importance=0.7,
        metadata={"category": "technical", "verified": True}
    ),
    k=20
)
```

### Namespaces

Multi-tenancy support:

```python
# Different namespaces for isolation
tenant1_adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    namespace="tenant_123"
)

tenant2_adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    namespace="tenant_456"
)
```

---

## Use Cases

### ✅ Perfect For

- **Persistent Tier**: Production knowledge base
- Startups and MVPs (fast time-to-market)
- Applications requiring global reach
- Teams without DevOps resources
- High-availability requirements
- Unpredictable scaling needs
- Cost-effective at small-medium scale

### ❌ Not Suitable For

- Cost-sensitive at massive scale (>10M vectors)
- On-premise requirements
- Full control over infrastructure
- Ephemeral/session tiers (use Redis)

---

## Examples

### Production Knowledge Base

```python
# Serverless knowledge base
for i in range(100000):
    await memory.store(
        f"Knowledge entry {i}: {content}",
        importance=0.8,
        tier="persistent",
        tags=["knowledge", category]
    )

# Global fast search
results = await memory.recall(
    "What is machine learning?",
    k=50,
    tier="persistent"
)
```

### Multi-Tenant SaaS

```python
from axon.adapters.pinecone import PineconeAdapter

# Tenant isolation with namespaces
class TenantMemory:
    def __init__(self, tenant_id: str):
        self.adapter = PineconeAdapter(
            api_key="key",
            index_name="saas_memories",
            namespace=f"tenant_{tenant_id}"
        )
        
        config = MemoryConfig(
            persistent=PersistentPolicy(adapter=self.adapter)
        )
        self.memory = MemorySystem(config)
    
    async def store(self, text: str, **kwargs):
        return await self.memory.store(text, **kwargs)
    
    async def recall(self, query: str, **kwargs):
        return await self.memory.recall(query, **kwargs)

# Usage
tenant_123 = TenantMemory("123")
await tenant_123.store("Tenant-specific data")
```

### RAG Application

```python
# Serverless RAG with Pinecone
async def build_rag_system(documents: list[str]):
    # Ingest documents
    for doc in documents:
        await memory.store(
            doc,
            importance=0.8,
            tier="persistent"
        )
    
    # Query function
    async def answer(question: str) -> str:
        # Retrieve context (serverless, auto-scaled)
        context = await memory.recall(
            question,
            k=5,
            tier="persistent"
        )
        
        # Generate answer
        context_text = "\n".join([c.text for c in context])
        return await llm.generate(
            f"Context:\n{context_text}\n\nQuestion: {question}"
        )
    
    return answer
```

---

## Performance

| Operation | Latency | Throughput | Scale |
|-----------|---------|------------|-------|
| **save()** | 20-150ms | 200-1000 ops/sec | Unlimited |
| **query()** | 20-100ms | 100-500 ops/sec | Unlimited |
| **get()** | 20-100ms | 200-1000 ops/sec | Unlimited |
| **delete()** | 20-100ms | 200-1000 ops/sec | Unlimited |

**Note:** Latency includes network overhead. Auto-scales to handle traffic spikes.

---

## Production Deployment

### Application Setup

```python
# app.py - Production configuration
import os
from axon import MemorySystem
from axon.core.templates import PINECONE_CONFIG

# Load API key from environment
os.environ['PINECONE_API_KEY'] = os.getenv('PINECONE_API_KEY')

# Initialize memory system
memory = MemorySystem(PINECONE_CONFIG)

# Use in your application
@app.route('/store', methods=['POST'])
async def store_memory():
    text = request.json['text']
    await memory.store(text, importance=0.8)
    return {'status': 'success'}

@app.route('/recall', methods=['POST'])
async def recall_memories():
    query = request.json['query']
    results = await memory.recall(query, k=10)
    return {'results': [r.dict() for r in results]}
```

### Environment Configuration

```bash
# .env file
PINECONE_API_KEY=your-production-api-key
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX=prod-memories

# Load in application
from dotenv import load_dotenv
load_dotenv()
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PINECONE_API_KEY=${PINECONE_API_KEY}

CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_ENVIRONMENT=us-east1-gcp
      - PINECONE_INDEX=memories
    ports:
      - "8000:8000"
```

---

## Best Practices

### 1. Use for Persistent Tier

```python
# ✓ Good: Managed persistent storage
persistent=PersistentPolicy(adapter_type="pinecone")

# ✗ Bad: Expensive for ephemeral (use Redis)
ephemeral=EphemeralPolicy(adapter_type="pinecone")
```

### 2. Optimize Batch Operations

```python
# Batch upserts for better throughput
entries = [
    MemoryEntry(text=f"Entry {i}", ...)
    for i in range(100)
]

# Pinecone batches internally, but still batch on your end
for batch in chunks(entries, 100):
    for entry in batch:
        await adapter.save(entry)
```

### 3. Use Namespaces for Isolation

```python
# Multi-tenant isolation
tenant_adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    namespace=f"tenant_{tenant_id}"  # Isolated namespace
)
```

### 4. Monitor Usage

```python
# Check index stats
from pinecone import Pinecone

pc = Pinecone(api_key="key")
index = pc.Index("memories")
stats = index.describe_index_stats()

print(f"Total vectors: {stats.total_vector_count}")
print(f"Namespaces: {stats.namespaces}")
```

---

## Troubleshooting

### API Key Issues

```python
# Test connection
from pinecone import Pinecone

pc = Pinecone(api_key="your-key")
print(pc.list_indexes())  # Should list indexes

# If fails, check:
# 1. API key is correct
# 2. API key has permissions
# 3. Network allows outbound HTTPS
```

### Index Not Found

```python
# Create index if needed
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="key")

# Check if exists
indexes = pc.list_indexes()
if "memories" not in [i.name for i in indexes]:
    # Create index
    pc.create_index(
        name="memories",
        dimension=1536,  # Match your embedding model
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
```

### Slow Queries

```python
# Add more specific filters
results = await memory.recall(
    "query",
    filter=Filter(
        tags=["specific"],  # Reduces search space
        metadata={"category": "narrow"}
    ),
    k=10  # Fewer results
)

# Or use namespaces for partitioning
adapter = PineconeAdapter(
    api_key="key",
    index_name="memories",
    namespace="specific_partition"
)
```

---

## Migration

### From Qdrant to Pinecone

```python
# Export from Qdrant
qdrant_memory = MemorySystem(QDRANT_CONFIG)
entries = await qdrant_memory.export(tier="persistent")

# Import to Pinecone
pinecone_config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="pinecone")
)
pinecone_memory = MemorySystem(pinecone_config)
await pinecone_memory.import_data(entries, tier="persistent")
```

### From ChromaDB to Pinecone

```python
# Export from ChromaDB
chroma_memory = MemorySystem(STANDARD_CONFIG)
entries = await chroma_memory.export(tier="persistent")

# Import to Pinecone (with batching)
pinecone_memory = MemorySystem(PINECONE_CONFIG)

for batch in chunks(entries, 100):
    await pinecone_memory.import_data(batch, tier="persistent")
    print(f"Imported {len(batch)} entries")
```

---

## Cost Analysis

### Pricing Model (as of 2024)

| Plan | Monthly Cost | Included | Per Vector/Month |
|------|--------------|----------|------------------|
| **Starter** | $0 | 100K vectors | Free |
| **Standard** | $70 | 100K vectors | $0.0012 |
| **Enterprise** | Custom | Custom | Discounted |

### Cost Optimization

```python
# Estimate costs
def estimate_pinecone_cost(num_vectors: int) -> float:
    """Estimate monthly Pinecone cost."""
    if num_vectors <= 100000:
        return 0  # Free tier
    
    # Standard tier
    base_cost = 70  # First 100K included
    extra_vectors = num_vectors - 100000
    extra_cost = extra_vectors * 0.0012
    
    return base_cost + extra_cost

# Examples
print(f"1M vectors: ${estimate_pinecone_cost(1_000_000)}/month")
# Output: $1,150/month

print(f"10M vectors: ${estimate_pinecone_cost(10_000_000)}/month")
# Output: $11,950/month
```

### Cost vs Qdrant

| Scale | Pinecone | Qdrant (Self-Hosted) | Winner |
|-------|----------|----------------------|--------|
| **100K vectors** | $0 | $50 | Pinecone |
| **1M vectors** | $1,150 | $100 | Qdrant |
| **10M vectors** | $11,950 | $500 | Qdrant |

**Recommendation:**
- **< 1M vectors:** Pinecone (simplicity + free tier)
- **> 1M vectors:** Consider Qdrant (cost-effective at scale)

---

## Comparison

### Pinecone vs Other Adapters

| Feature | Pinecone | Qdrant | ChromaDB | Redis |
|---------|----------|--------|----------|-------|
| **Management** | Fully managed | Self-hosted | Embedded | Self/Managed |
| **Setup Time** | < 5 min | 30+ min | < 1 min | 10-30 min |
| **Scaling** | Auto | Manual | Single node | Manual |
| **Cost (1M)** | $1,150/mo | $100/mo | Free | $50/mo |
| **Global** | Yes | Manual | No | Yes |
| **Best For** | Startups | Large scale | Development | Caching |

---

## Next Steps

<div class="grid cards" markdown>

-   :material-hammer-wrench:{ .lg .middle } **Custom Adapter**

    ---

    Build your own storage adapter.

    [:octicons-arrow-right-24: Custom Adapter Guide](custom.md)

-   :material-speedometer:{ .lg .middle } **Performance Comparison**

    ---

    Compare all adapter performance.

    [:octicons-arrow-right-24: Performance Guide](../deployment/performance.md)

-   :material-rocket-launch:{ .lg .middle } **Production Deployment**

    ---

    Deploy to production with best practices.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
