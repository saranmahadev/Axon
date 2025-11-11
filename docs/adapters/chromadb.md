# ChromaDB Adapter

Embedded vector database adapter for persistent storage with semantic search capabilities.

---

## Overview

The **ChromaDB adapter** provides persistent vector storage using an embedded SQLite-backed database. Perfect for local development, prototyping, and small to medium-scale applications.

**Key Features:**
- ✓ Embedded (no separate server required)
- ✓ Persistent storage to disk
- ✓ Vector similarity search
- ✓ Metadata filtering
- ✓ Easy local development
- ✗ Single-machine only (no distributed)
- ✗ Limited to ~1M vectors

---

## Installation

```bash
# Install ChromaDB
pip install chromadb>=0.4.0

# Or with axon-sdk
pip install "axon-sdk[all]"
```

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy

config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="chroma",
        compaction_threshold=10000
    )
)

memory = MemorySystem(config)

# Store with persistence
await memory.store("Important knowledge", importance=0.8)

# Data persists across restarts ✓
```

---

## Configuration

### Basic Configuration

```python
from axon.adapters.chroma import ChromaAdapter

# Default (./chroma_db directory)
adapter = ChromaAdapter()

# Custom settings
adapter = ChromaAdapter(
    collection_name="my_memories",
    persist_directory="/path/to/chroma_db"
)
```

### Using with Templates

```python
from axon.core.templates import STANDARD_CONFIG

# STANDARD_CONFIG uses ChromaDB for persistent tier
memory = MemorySystem(STANDARD_CONFIG)
```

---

## Features

### Persistent Storage

Data survives application restarts:

```python
# Store data
await memory.store("User prefers dark mode", importance=0.8)

# Restart application
# Data still available ✓

results = await memory.recall("dark mode preference")
assert len(results) > 0
```

### Vector Similarity Search

Semantic search with cosine similarity:

```python
# Store knowledge base
facts = [
    "Python is a programming language",
    "FastAPI is a web framework",
    "NumPy is for numerical computing"
]

for fact in facts:
    await memory.store(fact, importance=0.8)

# Semantic query
results = await memory.recall("What is Python?", k=3)
# Returns relevant facts sorted by similarity
```

### Metadata Filtering

Filter by tags, importance, dates:

```python
from axon.models.filter import Filter

results = await memory.recall(
    "query",
    filter=Filter(
        tags=["knowledge", "verified"],
        min_importance=0.7,
        max_age_seconds=2592000  # Last 30 days
    )
)
```

---

## Use Cases

### ✅ Perfect For

- **Persistent Tier**: Long-term knowledge base
- Local development with persistence
- Prototypes and MVPs
- Small to medium datasets (<1M vectors)
- Embedded applications
- Desktop applications
- Single-user applications

### ❌ Not Suitable For

- Large-scale production (>1M vectors)
- Distributed deployments
- Multi-server architectures
- High-concurrency workloads
- Ephemeral or session tiers (use Redis)

---

## Examples

### Knowledge Base

```python
# Build persistent knowledge base
documents = [
    {"text": "Python type hints improve code quality", "tags": ["python", "typing"]},
    {"text": "Async/await enables concurrent programming", "tags": ["python", "async"]},
    {"text": "Pydantic validates data at runtime", "tags": ["python", "validation"]}
]

for doc in documents:
    await memory.store(
        doc["text"],
        importance=0.8,
        tier="persistent",
        tags=doc["tags"]
    )

# Query knowledge base
results = await memory.recall("How to validate data in Python?", k=5)
```

### User Preferences

```python
# Store user preferences permanently
preferences = [
    "User prefers dark theme",
    "User timezone is America/New_York",
    "User language is English"
]

for pref in preferences:
    await memory.store(
        pref,
        importance=0.9,
        tier="persistent",
        tags=["preference", user_id]
    )

# Retrieve all preferences
prefs = await memory.recall(
    "user preferences",
    filter=Filter(tags=["preference", user_id])
)
```

### Conversation History Archive

```python
# Archive important conversations
important_conversations = await memory.recall(
    "conversation",
    tier="session",
    filter=Filter(min_importance=0.7)
)

# Move to persistent storage
for conv in important_conversations:
    await memory.store(
        conv.text,
        importance=conv.metadata.importance,
        tier="persistent",
        tags=["archived", "conversation"]
    )
```

---

## Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| **save()** | 5-30ms | 100-500 ops/sec |
| **query()** | 10-50ms | 50-200 ops/sec |
| **get()** | 5-20ms | 200-500 ops/sec |
| **delete()** | 5-20ms | 100-300 ops/sec |

**Note:** Performance depends on dataset size and hardware (SSD recommended).

---

## Best Practices

### 1. Use for Persistent Tier Only

```python
# ✓ Good
persistent=PersistentPolicy(adapter_type="chroma")

# ✗ Bad (use Redis instead)
ephemeral=EphemeralPolicy(adapter_type="chroma")
session=SessionPolicy(adapter_type="chroma")
```

### 2. Use SSD for Storage

```python
# ✓ Good: SSD path
adapter = ChromaAdapter(persist_directory="/mnt/ssd/chroma_db")

# ⚠️ Slower: HDD path
adapter = ChromaAdapter(persist_directory="/mnt/hdd/chroma_db")
```

### 3. Regular Backups

```bash
# Backup ChromaDB data
tar -czf chroma_backup.tar.gz ./chroma_db/

# Restore
tar -xzf chroma_backup.tar.gz
```

### 4. Monitor Disk Usage

```python
import os

def get_db_size(path="./chroma_db"):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total += os.path.getsize(filepath)
    return total / (1024 * 1024)  # MB

print(f"ChromaDB size: {get_db_size():.2f} MB")
```

---

## Production Deployment

### Directory Structure

```
/app
├── chroma_db/           # Persistent data
│   ├── chroma.sqlite3   # SQLite database
│   └── index/           # Vector indices
└── your_app.py
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Create volume for ChromaDB data
VOLUME ["/app/chroma_db"]

CMD ["python", "app.py"]
```

```bash
# Run with volume
docker run -v ./chroma_db:/app/chroma_db my-app
```

---

## Troubleshooting

### Collection Not Found

```python
# Reset database (development only!)
adapter.client.reset()  # Deletes all data!

# Or check collection name
collections = adapter.client.list_collections()
print(f"Collections: {[c.name for c in collections]}")
```

### Slow Queries

```python
# Reduce result count
results = await memory.recall("query", k=5)  # Instead of k=100

# Add specific filters
results = await memory.recall(
    "query",
    filter=Filter(tags=["specific"]),
    k=10
)
```

### Disk Space Issues

```python
# Check database size
import os
db_size = os.path.getsize("./chroma_db/chroma.sqlite3")
print(f"Database: {db_size / 1024 / 1024:.2f} MB")

# Compact if needed
await memory.compact(tier="persistent", strategy="importance")
```

---

## Migration

### From InMemory to ChromaDB

```python
# Export from InMemory
entries = await old_memory.export(tier="persistent")

# Create ChromaDB config
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="chroma")
)
new_memory = MemorySystem(config)

# Import to ChromaDB
await new_memory.import_data(entries, tier="persistent")
```

### To Qdrant (for scaling)

```python
# Export from ChromaDB
entries = await memory.export(tier="persistent")

# Import to Qdrant
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="qdrant")
)
qdrant_memory = MemorySystem(config)
await qdrant_memory.import_data(entries, tier="persistent")
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Qdrant Adapter**

    ---

    Scale to production with Qdrant.

    [:octicons-arrow-right-24: Qdrant Guide](qdrant.md)

-   :material-cloud:{ .lg .middle } **Pinecone Adapter**

    ---

    Managed cloud alternative.

    [:octicons-arrow-right-24: Pinecone Guide](pinecone.md)

-   :material-backup-restore:{ .lg .middle } **Backup Guide**

    ---

    Backup and disaster recovery.

    [:octicons-arrow-right-24: Backup Guide](../deployment/production.md#backup)

</div>
