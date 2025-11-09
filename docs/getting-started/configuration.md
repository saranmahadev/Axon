# Configuration

Learn how to configure Axon for your specific use case.

## Configuration Overview

Axon uses a hierarchical configuration system based on `MemoryConfig` and tier-specific `Policy` objects.

```python
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

config = MemoryConfig(
    tiers={
        "ephemeral": EphemeralPolicy(ttl_minutes=5, max_items=1000),
        "session": SessionPolicy(ttl_minutes=60, summarize_after=50),
        "persistent": PersistentPolicy(backend="qdrant", embedder="openai")
    }
)
```

## Tier Policies

### Ephemeral Policy

Short-lived, high-volume data with TTL expiration.

```python
from axon.core.policies import EphemeralPolicy

ephemeral = EphemeralPolicy(
    ttl_minutes=10,        # Expire after 10 minutes
    max_items=5000,        # Capacity limit
    eviction_policy="lru"  # Least recently used
)
```

### Session Policy

Session-scoped memory with automatic summarization.

```python
from axon.core.policies import SessionPolicy

session = SessionPolicy(
    ttl_minutes=120,         # 2 hour sessions
    max_items=200,           # Max items per session
    summarize_after=100,     # Trigger summarization at 100 items
    promote_threshold=0.8,   # Promote important memories
    demote_threshold=0.2     # Demote low-importance
)
```

### Persistent Policy

Long-term semantic storage.

```python
from axon.core.policies import PersistentPolicy

persistent = PersistentPolicy(
    backend="qdrant",                    # Storage adapter
    embedder="openai",                   # Embedding model
    promote_threshold=0.7,               # Auto-promote from session
    max_items=100000,                    # Capacity limit
    compaction_strategy="hybrid"         # Compaction approach
)
```

## Storage Backends

### In-Memory

```python
from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry

registry = AdapterRegistry()
registry.register("ephemeral", InMemoryAdapter())
```

### Redis

```python
from axon.adapters import RedisAdapter

redis_adapter = RedisAdapter(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    ttl_seconds=300
)
```

### ChromaDB

```python
from axon.adapters import ChromaAdapter

chroma_adapter = ChromaAdapter(
    collection_name="my_memories",
    persist_directory="./chroma_db"
)
```

### Qdrant

```python
from axon.adapters import QdrantAdapter

qdrant_adapter = QdrantAdapter(
    collection_name="memories",
    host="localhost",
    port=6333,
    vector_size=1536  # Match embedder dimensions
)
```

### Pinecone

```python
import os
from axon.adapters import PineconeAdapter

os.environ["PINECONE_API_KEY"] = "..."
os.environ["PINECONE_ENVIRONMENT"] = "us-east-1-aws"

pinecone_adapter = PineconeAdapter(
    index_name="axon-memories",
    vector_size=1536
)
```

## Embedders

### OpenAI

```python
from axon.embedders import OpenAIEmbedder

embedder = OpenAIEmbedder(
    model="text-embedding-3-small",  # or text-embedding-3-large
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### Voyage AI

```python
from axon.embedders import VoyageAIEmbedder

embedder = VoyageAIEmbedder(
    model="voyage-2",
    api_key=os.getenv("VOYAGE_API_KEY")
)
```

### Sentence Transformers

```python
from axon.embedders import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder(
    model_name="all-MiniLM-L6-v2"  # Fast local model
)
```

## Using Templates

Pre-configured templates for common scenarios.

### Development

```python
from axon.core.templates import DEVELOPMENT_CONFIG
system = MemorySystem(config=DEVELOPMENT_CONFIG)
```

### Production

```python
from axon.core.templates import balanced
config = balanced()
system = MemorySystem(config=config)
```

## Environment Variables

```bash
# Logging
AXON_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
AXON_STRUCTURED_LOGGING=true

# API Keys
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east-1-aws
VOYAGE_API_KEY=...
```

## Complete Example

```python
import os
from dotenv import load_dotenv
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy
from axon.adapters import RedisAdapter, ChromaAdapter, QdrantAdapter
from axon.embedders import OpenAIEmbedder
from axon.core import AuditLogger
from axon.core.adapter_registry import AdapterRegistry

load_dotenv()

# Setup adapters
registry = AdapterRegistry()
registry.register("ephemeral", RedisAdapter(host="localhost", ttl_seconds=300))
registry.register("session", ChromaAdapter(collection_name="sessions"))
registry.register("persistent", QdrantAdapter(collection_name="memories"))

# Configure policies
config = MemoryConfig(
    tiers={
        "ephemeral": EphemeralPolicy(ttl_minutes=5, max_items=10000),
        "session": SessionPolicy(ttl_minutes=60, summarize_after=50),
        "persistent": PersistentPolicy(backend="qdrant", embedder="openai")
    }
)

# Setup audit logging
audit_logger = AuditLogger(max_events=10000, enable_rotation=True)

# Create embedder
embedder = OpenAIEmbedder(model="text-embedding-3-small")

# Create system
system = MemorySystem(
    config=config,
    registry=registry,
    embedder=embedder,
    audit_logger=audit_logger,
    enable_pii_detection=True
)
```
