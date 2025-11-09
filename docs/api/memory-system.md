# MemorySystem API

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
