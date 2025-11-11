# Basic Examples

Get started with Axon through simple, practical examples from the `examples/01-basics/` directory.

---

## Overview

These basic examples introduce fundamental Axon concepts through hands-on code. Perfect for beginners getting started with memory systems.

**Examples Covered:**
- Getting Started (3 examples)
- Basic Operations (4 examples)
- Working with Data (3 examples)

**What You'll Learn:**
- Creating a MemorySystem
- Store, recall, and forget operations
- Memory lifecycle management
- Metadata and filtering
- Export/import functionality

**Prerequisites:**
- Python 3.10+
- Axon SDK installed (`pip install axon-sdk`)

**Location:** `examples/01-basics/`

---

## Getting Started

### 01_hello_world.py

**Your first memory with Axon** - The simplest possible example.

**File:** `examples/01-basics/getting-started/01_hello_world.py`

**What it demonstrates:**
- Creating a MemorySystem
- Storing your first memory
- Recalling stored memories

**Code highlights:**

```python
import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

async def main():
    # Create memory system
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    
    # Store a memory
    entry_id = await memory.store("Hello, Axon! This is my first memory.")
    
    # Recall the memory
    results = await memory.recall("hello", k=1)
    
    if results:
        print(f"Content: {results[0].text}")
        print(f"ID: {results[0].id}")

asyncio.run(main())
```

**Run it:**
```bash
cd examples/01-basics/getting-started
python 01_hello_world.py
```

**Expected output:**
```
=== Axon Hello World ===

1. Creating memory system...
   ✓ Memory system created

2. Storing a memory...
   ✓ Memory stored with ID: 550e8400-e29b-41d4-a716-446655440000

3. Recalling memories about 'hello'...
   ✓ Found 1 result(s)

✓ Success! You've stored and recalled your first memory with Axon.
```

---

### 02_understanding_config.py

**Configuration basics** - Learn how memory system configuration works.

**File:** `examples/01-basics/getting-started/02_understanding_config.py`

**What it demonstrates:**
- Memory tier configuration
- Adapter selection
- TTL and capacity settings
- Default tier selection

---

### 03_installation_setup.py

**Installation verification** - Verify your Axon installation.

**File:** `examples/01-basics/getting-started/03_installation_setup.py`

**What it demonstrates:**
- Dependency checking
- Configuration validation
- Example data operations

---

## Basic Operations

### 01_store_operations.py

**Comprehensive store operations** - Learn different ways to store memories.

**File:** `examples/01-basics/basic-operations/01_store_operations.py`

**What it demonstrates:**
- Basic store with text only
- Store with importance scores (0.0-1.0)
- Store with tags for categorization
- Store with metadata (user/session context)
- Explicit tier selection

**Key operations:**

```python
# Basic store
entry_id = await memory.store("The user's favorite color is blue.")

# With importance
entry_id = await memory.store(
    "Critical API key: sk-abc123xyz",
    importance=0.95
)

# With tags
entry_id = await memory.store(
    "User prefers dark mode",
    importance=0.7,
    tags=["preferences", "ui", "settings"]
)

# With metadata
entry_id = await memory.store(
    "User completed onboarding",
    metadata={
        "user_id": "user_12345",
        "session_id": "session_abc",
        "source": "onboarding_flow"
    },
    tags=["milestone", "onboarding"]
)

# Explicit tier
entry_id = await memory.store(
    "Temporary cache data",
    tier="ephemeral"
)
```

---

### 02_recall_operations.py

**Semantic search and retrieval** - Master recall operations.

**File:** `examples/01-basics/basic-operations/02_recall_operations.py`

**What it demonstrates:**
- Basic recall by query
- Top-K results
- Filtering by metadata
- Filtering by tags
- Filtering by importance range
- Filtering by time range
- Multi-tier recall

**Key operations:**

```python
from axon.models.filter import Filter

# Basic recall
results = await memory.recall("user preferences", k=5)

# Filter by tags
results = await memory.recall(
    "api",
    filter=Filter(tags=["security"])
)

# Filter by importance
results = await memory.recall(
    "important data",
    filter=Filter(importance_range=(0.8, 1.0))
)

# Filter by metadata
results = await memory.recall(
    "user data",
    filter=Filter(metadata={"user_id": "user_123"})
)
```

---

### 03_forget_operations.py

**Delete memories** - Remove entries from memory.

**File:** `examples/01-basics/basic-operations/03_forget_operations.py`

**What it demonstrates:**
- Forget by entry ID
- Forget by filter (bulk delete)
- Forget from specific tier
- Safety checks before deletion

**Key operations:**

```python
# Forget by ID
success = await memory.forget("entry-uuid")

# Forget by filter
from axon.models.filter import Filter

count = await memory.forget(
    Filter(tags=["temporary", "cache"])
)

# Forget from specific tier
success = await memory.forget("entry-uuid", tier="ephemeral")
```

---

### 04_memory_lifecycle.py

**Complete memory lifecycle** - From creation to deletion.

**File:** `examples/01-basics/basic-operations/04_memory_lifecycle.py`

**What it demonstrates:**
- Create memories
- Read/retrieve memories
- Update memories
- Delete memories
- Track access patterns
- Importance decay over time

---

## Working with Data

### 01_export_import.py

**Export and import memories** - Backup and restore your data.

**File:** `examples/01-basics/working-with-data/01_export_import.py`

**What it demonstrates:**
- Export all memories to JSON
- Export specific tier
- Export with filters
- Import memories from backup
- Handle export/import errors

**Key operations:**

```python
# Export all memories
data = await memory.export(include_embeddings=False)

# Save to file
import json
with open("memories_backup.json", "w") as f:
    json.dump(data, f, indent=2)

# Import from file
with open("memories_backup.json", "r") as f:
    data = json.load(f)

count = await memory.import_data(data)
print(f"Imported {count} memories")
```

---

### 02_tier_sync.py

**Synchronize across tiers** - Keep tiers in sync.

**File:** `examples/01-basics/working-with-data/02_tier_sync.py`

**What it demonstrates:**
- Copy entries between tiers
- Sync important memories to persistent
- Promote frequently accessed entries
- Tier migration strategies

---

### 03_metadata_filtering.py

**Advanced filtering** - Master metadata-based queries.

**File:** `examples/01-basics/working-with-data/03_metadata_filtering.py`

**What it demonstrates:**
- Filter by single metadata field
- Filter by multiple fields (AND logic)
- Combine metadata and tag filters
- Time-based filtering
- Importance range filtering
- Complex filter combinations

**Key operations:**

```python
from axon.models.filter import Filter
from datetime import datetime, timedelta

# Filter by metadata
results = await memory.recall(
    "query",
    filter=Filter(metadata={"category": "finance", "user_id": "user_123"})
)

# Filter by tags
results = await memory.recall(
    "query",
    filter=Filter(tags=["important", "reviewed"])
)

# Filter by importance range
results = await memory.recall(
    "query",
    filter=Filter(importance_range=(0.7, 1.0))
)

# Filter by time range
results = await memory.recall(
    "query",
    filter=Filter(
        time_range=(
            datetime.now() - timedelta(days=7),
            datetime.now()
        )
    )
)

# Combine filters
results = await memory.recall(
    "query",
    filter=Filter(
        metadata={"category": "finance"},
        tags=["important"],
        importance_range=(0.8, 1.0),
        time_range=(datetime.now() - timedelta(days=30), datetime.now())
    )
)
```

---

## Summary

The basic examples cover fundamental Axon operations:

**Getting Started:**
- Hello World - First memory operations
- Understanding Configuration - Memory system setup
- Installation Setup - Verify your installation

**Basic Operations:**
- Store Operations - Various ways to save memories
- Recall Operations - Semantic search and filtering
- Forget Operations - Delete memories safely
- Memory Lifecycle - Complete CRUD operations

**Working with Data:**
- Export/Import - Backup and restore
- Tier Sync - Synchronize across tiers
- Metadata Filtering - Advanced queries

**Key Takeaways:**
- ✓ MemorySystem is your main interface
- ✓ Use importance scores (0.0-1.0) for prioritization
- ✓ Tags and metadata enable powerful filtering
- ✓ Tiers provide speed vs. durability trade-offs
- ✓ Export/import enables backup and migration

**Run All Basic Examples:**

```bash
cd examples/01-basics

# Getting started
python getting-started/01_hello_world.py
python getting-started/02_understanding_config.py
python getting-started/03_installation_setup.py

# Basic operations
python basic-operations/01_store_operations.py
python basic-operations/02_recall_operations.py
python basic-operations/03_forget_operations.py
python basic-operations/04_memory_lifecycle.py

# Working with data
python working-with-data/01_export_import.py
python working-with-data/02_tier_sync.py
python working-with-data/03_metadata_filtering.py
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-layers-triple:{ .lg .middle } **Intermediate Examples**

    ---

    Learn about adapters and policies.

    [:octicons-arrow-right-24: Intermediate Examples](intermediate.md)

-   :material-book-open-variant:{ .lg .middle } **Core Concepts**

    ---

    Understand memory system architecture.

    [:octicons-arrow-right-24: Core Concepts](../concepts/overview.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation.

    [:octicons-arrow-right-24: API Reference](../api/memory-system.md)

</div>
