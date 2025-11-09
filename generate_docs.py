"""
Script to generate complete AxonML documentation structure.
Run this to populate all docs/ directories with content.
"""

import os
from pathlib import Path

DOCS_ROOT = Path("docs")

# Documentation content templates
DOCS_CONTENT = {
    "getting-started/configuration.md": """# Configuration

Learn how to configure AxonML for your specific use case.

## Configuration Overview

AxonML uses a hierarchical configuration system based on `MemoryConfig` and tier-specific `Policy` objects.

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
""",

    "concepts/overview.md": """# Core Concepts

Understanding AxonML's architecture and design principles.

## Architecture

AxonML is built on four core pillars:

1. **Multi-Tier Storage**: Automatic routing across ephemeral, session, and persistent tiers
2. **Policy-Driven Lifecycle**: Configurable policies for TTL, capacity, promotion, and demotion
3. **Semantic Recall**: Vector-based similarity search with metadata filtering
4. **Production Features**: Audit logging, PII detection, transactions, and observability

## Memory Flow

```mermaid
sequenceDiagram
    participant App as Your App
    participant MS as MemorySystem
    participant Router as Router
    participant PE as PolicyEngine
    participant Adapter as StorageAdapter

    App->>MS: store(text, importance=0.8)
    MS->>PE: calculate_score(entry)
    PE->>MS: importance_score
    MS->>Router: route_to_tier(entry, score)
    Router->>Adapter: save(entry)
    Adapter-->>Router: entry_id
    Router-->>MS: entry_id
    MS-->>App: entry_id
```

## Key Components

### MemorySystem

The main API for all memory operations.

**Methods:**
- `store()` - Save a memory
- `recall()` - Search memories semantically
- `forget()` - Delete memories
- `compact()` - Summarize and compress
- `export()` - Export all memories
- `import_data()` - Import memories

### Router

Intelligently routes operations across tiers based on:
- Importance scores
- Access patterns
- Capacity constraints
- Explicit tier hints

### PolicyEngine

Orchestrates lifecycle decisions:
- Promotion eligibility
- Demotion triggers
- Eviction policies
- Compaction scheduling

### ScoringEngine

Calculates importance scores using:
- Access frequency
- Recency
- Base importance
- Session continuity

## Memory Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Ephemeral: importance < 0.3
    [*] --> Session: 0.3 ≤ importance < 0.7
    [*] --> Persistent: importance ≥ 0.7

    Ephemeral --> Expired: TTL reached
    Ephemeral --> Session: Promoted (access pattern)

    Session --> Ephemeral: Demoted (low score)
    Session --> Persistent: Promoted (high score)
    Session --> Summarized: Compaction triggered

    Persistent --> Archived: Long-term storage

    Expired --> [*]
    Summarized --> Persistent
    Archived --> [*]
```

## Design Principles

### 1. Async-First

All operations are async for high performance:

```python
# Correct
await system.store("memory")

# Wrong
system.store("memory")  # Returns coroutine, doesn't execute
```

### 2. Fail-Fast

Invalid inputs raise exceptions immediately:

```python
# Raises ValueError
await system.store("", importance=0.8)  # Empty content

await system.recall("query", k=0)  # Invalid k
```

### 3. Explicit > Implicit

Always prefer explicit configuration:

```python
# Explicit tier
await system.store("data", tier="persistent")

# Explicit importance
await system.store("data", importance=0.8)
```

### 4. Composability

Components can be mixed and matched:

```python
# Custom adapter + policy
registry.register("custom", MyAdapter())
config.tiers["custom"] = MyPolicy()
```

## Next Steps

- [Memory Tiers](tiers.md) - Deep dive into tier architecture
- [Policies](policies.md) - Learn about policy configuration
- [Routing](routing.md) - Understand tier selection logic
""",

    "api/memory-system.md": """# MemorySystem API

Complete API reference for the `MemorySystem` class.

## Class: MemorySystem

Main entry point for all memory operations.

```python
from axon import MemorySystem
from axon.core.templates import balanced

system = MemorySystem(config=balanced())
```

### Constructor

```python
def __init__(
    self,
    config: MemoryConfig,
    registry: Optional[AdapterRegistry] = None,
    embedder: Optional[Embedder] = None,
    audit_logger: Optional[AuditLogger] = None,
    enable_pii_detection: bool = True
)
```

**Parameters:**

- **config** (`MemoryConfig`): Configuration with tier policies
- **registry** (`AdapterRegistry`, optional): Custom adapter registry
- **embedder** (`Embedder`, optional): Embedding model for semantic search
- **audit_logger** (`AuditLogger`, optional): Enable audit logging
- **enable_pii_detection** (`bool`, default=True): Enable PII detection

**Example:**

```python
from axon import MemorySystem
from axon.core import AuditLogger
from axon.embedders import OpenAIEmbedder
from axon.core.templates import balanced

audit_logger = AuditLogger()
embedder = OpenAIEmbedder()

system = MemorySystem(
    config=balanced(),
    embedder=embedder,
    audit_logger=audit_logger,
    enable_pii_detection=True
)
```

---

## Methods

### store()

Store a memory with automatic tier routing.

```python
async def store(
    self,
    text: str,
    importance: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    tier: Optional[str] = None
) -> str
```

**Parameters:**

- **text** (`str`): Memory content (required, non-empty)
- **importance** (`float`, optional): Importance score 0.0-1.0
- **metadata** (`dict`, optional): Additional metadata
- **tags** (`list[str]`, optional): Tags for categorization
- **tier** (`str`, optional): Explicit tier override

**Returns:** `str` - Entry ID

**Raises:** `ValueError` if text is empty

**Example:**

```python
entry_id = await system.store(
    "User prefers dark mode",
    importance=0.8,
    metadata={"user_id": "user_123"},
    tags=["preference", "ui"]
)
```

---

### recall()

Semantic search across all tiers.

```python
async def recall(
    self,
    query: str,
    k: int = 10,
    filter: Optional[Filter] = None,
    filter_dict: Optional[Dict[str, Any]] = None,
    tier: Optional[str] = None
) -> List[MemoryEntry]
```

**Parameters:**

- **query** (`str`): Search query
- **k** (`int`, default=10): Number of results
- **filter** (`Filter`, optional): Filter object
- **filter_dict** (`dict`, optional): Filter as dictionary
- **tier** (`str`, optional): Search specific tier only

**Returns:** `List[MemoryEntry]` - Ranked results

**Example:**

```python
from axon.models import Filter

results = await system.recall(
    "user preferences",
    k=5,
    filter=Filter(tags=["preference"])
)

for entry in results:
    print(f"{entry.text} (score: {entry.metadata.importance})")
```

---

### forget()

Delete memories by ID or filter.

```python
async def forget(
    self,
    entry_id_or_filter: Union[str, Filter, Dict[str, Any]]
) -> int
```

**Parameters:**

- **entry_id_or_filter**: Entry ID, Filter object, or filter dict

**Returns:** `int` - Number of entries deleted

**Example:**

```python
# Forget by ID
await system.forget("entry_123")

# Forget by filter
from axon.models import Filter

count = await system.forget(Filter(tags=["temporary"]))
print(f"Deleted {count} entries")
```

---

### compact()

Compact and summarize memories.

```python
async def compact(
    self,
    tier: str = "session",
    strategy: str = "count",
    threshold: Optional[int] = None,
    dry_run: bool = False,
    summarizer: Optional[Summarizer] = None
) -> CompactionResult
```

**Parameters:**

- **tier** (`str`, default="session"): Tier to compact
- **strategy** (`str`, default="count"): Strategy (count, semantic, importance, time, hybrid)
- **threshold** (`int`, optional): Strategy-specific threshold
- **dry_run** (`bool`, default=False): Preview without executing
- **summarizer** (`Summarizer`, optional): Custom summarizer

**Returns:** `CompactionResult` - Result with summaries

**Example:**

```python
# Dry run to preview
result = await system.compact(
    tier="session",
    strategy="count",
    threshold=50,
    dry_run=True
)

print(f"Would compact {len(result.entries_to_compact)} entries")
print(f"Into {result.num_summaries} summaries")

# Execute compaction
result = await system.compact(tier="session", strategy="hybrid")
```

---

### export()

Export all memories to JSON-serializable format.

```python
async def export(
    self,
    include_embeddings: bool = True,
    filter: Optional[Filter] = None
) -> Dict[str, List[Dict[str, Any]]]
```

**Parameters:**

- **include_embeddings** (`bool`, default=True): Include embedding vectors
- **filter** (`Filter`, optional): Export only matching entries

**Returns:** `Dict[str, List[Dict]]` - Memories by tier

**Example:**

```python
# Export all
data = await system.export(include_embeddings=False)

# Export to file
import json
with open("memories.json", "w") as f:
    json.dump(data, f, indent=2)
```

---

### import_data()

Import memories from exported data.

```python
async def import_data(
    self,
    data: Dict[str, List[Dict[str, Any]]],
    overwrite: bool = False
) -> int
```

**Parameters:**

- **data** (`dict`): Exported data from `export()`
- **overwrite** (`bool`, default=False): Overwrite existing entries

**Returns:** `int` - Number of imported entries

**Example:**

```python
import json

with open("memories.json", "r") as f:
    data = json.load(f)

count = await system.import_data(data)
print(f"Imported {count} memories")
```

---

### export_audit_log()

Export audit log events.

```python
async def export_audit_log(
    self,
    operation: Optional[OperationType] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    status: Optional[EventStatus] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- **operation** (`OperationType`, optional): Filter by operation
- **user_id** (`str`, optional): Filter by user
- **session_id** (`str`, optional): Filter by session
- **status** (`EventStatus`, optional): Filter by status
- **start_time** (`datetime`, optional): Start of time range
- **end_time** (`datetime`, optional): End of time range

**Returns:** `List[Dict]` - Audit events

**Raises:** `RuntimeError` if no audit logger configured

**Example:**

```python
from axon.models.audit import OperationType

# Export all events
events = await system.export_audit_log()

# Export only STORE operations
store_events = await system.export_audit_log(
    operation=OperationType.STORE
)
```

---

## Properties

### config

Get the current configuration.

```python
@property
def config(self) -> MemoryConfig
```

---

## Complete Example

```python
import asyncio
from axon import MemorySystem
from axon.core.templates import balanced
from axon.core import AuditLogger
from axon.models import Filter

async def main():
    # Setup
    audit_logger = AuditLogger()
    system = MemorySystem(
        config=balanced(),
        audit_logger=audit_logger
    )

    # Store
    entry_id = await system.store(
        "Important meeting notes",
        importance=0.9,
        tags=["meeting", "notes"]
    )

    # Recall
    results = await system.recall(
        "meeting",
        k=5,
        filter=Filter(tags=["notes"])
    )

    # Compact
    result = await system.compact(
        tier="session",
        strategy="hybrid"
    )

    # Export
    data = await system.export()

    # Audit
    events = await system.export_audit_log()
    print(f"Logged {len(events)} events")

asyncio.run(main())
```
""",
}


def create_docs():
    """Generate all documentation files."""
    for file_path, content in DOCS_CONTENT.items():
        full_path = DOCS_ROOT / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Created: {full_path}")

    print(f"\n✅ Generated {len(DOCS_CONTENT)} documentation files!")


if __name__ == "__main__":
    create_docs()
