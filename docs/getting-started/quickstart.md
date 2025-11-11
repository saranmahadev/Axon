# Quick Start

Get started with Axon in under 5 minutes! This guide walks you through the essentials of building your first memory-enabled application.

---

## Prerequisites

Before starting, make sure you have:

- Python 3.10 or higher installed
- Axon SDK installed (`pip install axon-sdk`)

---

## Hello World

Let's create your first memory system and store your first memory.

### Complete Example

```python
"""Your first Axon application."""
import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    """Store and recall your first memory."""
    print("=== Axon Hello World ===\n")
    
    # Step 1: Create memory system
    print("1. Creating memory system...")
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    print("   OK Memory system created\n")
    
    # Step 2: Store a memory
    print("2. Storing a memory...")
    entry_id = await memory.store("Hello, Axon! This is my first memory.")
    print(f"   OK Memory stored with ID: {entry_id}\n")
    
    # Step 3: Recall the memory
    print("3. Recalling memories about 'hello'...")
    results = await memory.recall("hello", k=1)
    print(f"   OK Found {len(results)} result(s)\n")
    
    # Step 4: Display the result
    if results:
        print("4. Retrieved memory:")
        print(f"   Content: {results[0].text}")
        print(f"   ID: {results[0].id}")
    
    print("\n* Success! You've stored and recalled your first memory with Axon.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
=== Axon Hello World ===

1. Creating memory system...
   OK Memory system created

2. Storing a memory...
   OK Memory stored with ID: a1b2c3d4-5678-90ab-cdef-1234567890ab

3. Recalling memories about 'hello'...
   OK Found 1 result(s)

4. Retrieved memory:
   Content: Hello, Axon! This is my first memory.
   ID: a1b2c3d4-5678-90ab-cdef-1234567890ab

* Success! You've stored and recalled your first memory with Axon.
```

!!! info "Why async?"
    Axon uses async/await for all I/O operations to ensure high performance and scalability. All memory operations must be awaited.

---

## Core Operations

### Storing Memories

Axon provides flexible ways to store memories with metadata, importance scores, and tags.

#### Basic Store

```python
# Simple text storage
entry_id = await memory.store("The user's favorite color is blue.")
```

#### Store with Importance

Importance scores (0.0 to 1.0) determine which tier stores the memory:

```python
# High importance → Persistent tier (long-term storage)
await memory.store(
    "User's email: user@example.com",
    importance=0.9
)

# Medium importance → Session tier (session-scoped)
await memory.store(
    "User viewed product page",
    importance=0.5
)

# Low importance → Ephemeral tier (short-lived cache)
await memory.store(
    "Temporary calculation result: 42",
    importance=0.2
)
```

#### Store with Tags

Tags help categorize and filter memories:

```python
await memory.store(
    "User prefers dark mode in settings",
    importance=0.7,
    tags=["preferences", "ui", "settings"]
)
```

#### Store with Metadata

Add structured metadata for context:

```python
await memory.store(
    "User completed onboarding tutorial",
    importance=0.6,
    metadata={
        "user_id": "user_12345",
        "session_id": "session_abc",
        "source": "onboarding_flow"
    },
    tags=["milestone", "onboarding"]
)
```

#### Explicit Tier Selection

Force storage to a specific tier:

```python
# Store in ephemeral tier (ignores importance score)
await memory.store(
    "Temporary cache: recent search query",
    tier="ephemeral",
    tags=["cache", "temporary"]
)

# Store in persistent tier
await memory.store(
    "Critical data that must persist",
    tier="persistent"
)
```

### Recalling Memories

Retrieve memories using semantic search, filtering, and multi-tier queries.

#### Basic Recall

```python
# Find top 5 most relevant memories
results = await memory.recall("user preferences", k=5)

for entry in results:
    print(f"Text: {entry.text}")
    print(f"Importance: {entry.importance}")
    print(f"Tags: {entry.tags}")
    print("---")
```

#### Recall from Specific Tiers

```python
# Search only in persistent tier
results = await memory.recall(
    "user email",
    k=10,
    tiers=["persistent"]
)

# Search across multiple tiers
results = await memory.recall(
    "recent activity",
    k=10,
    tiers=["ephemeral", "session"]
)
```

#### Recall with Filters

Filter by tags or metadata:

```python
from axon.models import Filter

# Filter by tags
filter_obj = Filter(tags=["preferences", "ui"])
results = await memory.recall("settings", k=10, filter=filter_obj)

# Filter by metadata
filter_obj = Filter(metadata={"user_id": "user_12345"})
results = await memory.recall("user data", k=10, filter=filter_obj)
```

### Forgetting Memories

Remove memories you no longer need:

```python
# Forget a specific memory by ID
await memory.forget(entry_id)
```

---

## Configuration Templates

Axon provides pre-configured templates for different use cases.

### Available Templates

```python
from axon.core.templates import (
    DEVELOPMENT_CONFIG,     # All in-memory (no dependencies)
    LIGHTWEIGHT_CONFIG,     # Redis only (fast, simple)
    STANDARD_CONFIG,        # Redis + ChromaDB (balanced)
    PRODUCTION_CONFIG,      # Redis + Pinecone (scalable)
    QDRANT_CONFIG,         # Redis + Qdrant (high-performance)
)
```

### Development Config

Perfect for local development and testing:

```python
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

# All in-memory - no external dependencies required
memory = MemorySystem(DEVELOPMENT_CONFIG)
```

**Features:**

- ✓ No external dependencies (Redis, databases)
- ✓ Fast startup and execution
- ✓ Perfect for testing and CI/CD
- ✗ Data lost on restart

### Standard Config

Balanced setup for most applications:

```python
from axon.core.templates import STANDARD_CONFIG

# Redis for caching + ChromaDB for vectors
memory = MemorySystem(STANDARD_CONFIG)
```

**Features:**

- ✓ Redis for ephemeral/session tiers (fast)
- ✓ ChromaDB for persistent tier (vector search)
- ✓ Good balance of performance and features
- ⚠️ Requires: Redis, ChromaDB

**Setup:**

```bash
# Install dependencies
pip install "axon-sdk[all]"

# Start Redis (Docker)
docker run -d -p 6379:6379 redis:latest
```

### Production Config

High-scale production deployments:

```python
from axon.core.templates import PRODUCTION_CONFIG

# Redis + Pinecone for production scale
memory = MemorySystem(PRODUCTION_CONFIG)
```

**Features:**

- ✓ Redis for caching (distributed)
- ✓ Pinecone for vectors (managed, scalable)
- ✓ Automatic tier promotion/demotion
- ⚠️ Requires: Redis, Pinecone account

---

## Understanding Memory Tiers

Axon automatically routes memories to different tiers based on importance and access patterns.

### The Three Tiers

| Tier | Purpose | Typical TTL | Storage | Use Cases |
|------|---------|-------------|---------|-----------|
| **Ephemeral** | Short-lived cache | 30-60s | Redis/Memory | API responses, calculations |
| **Session** | Session-scoped | 5-30min | Redis | User activity, cart data |
| **Persistent** | Long-term storage | Unlimited | Vector DB | User profiles, knowledge |

### Automatic Tier Routing

```python
# Importance determines the tier
await memory.store("temp data", importance=0.1)  # → Ephemeral
await memory.store("session data", importance=0.5)  # → Session  
await memory.store("user profile", importance=0.9)  # → Persistent
```

### Tier Visualization

```
           Importance Score
0.0 ────────┬────────────┬──────────── 1.0
            │            │
      Ephemeral     Session    Persistent
      (0.0-0.3)   (0.3-0.7)    (0.7-1.0)
```

---

## Common Patterns

### Pattern 1: User Preferences

```python
async def save_user_preference(user_id: str, key: str, value: str):
    """Store user preference with high importance."""
    await memory.store(
        f"User preference: {key} = {value}",
        importance=0.8,  # Persistent tier
        metadata={"user_id": user_id, "preference_key": key},
        tags=["preferences", "user_settings"]
    )

async def get_user_preferences(user_id: str):
    """Retrieve all preferences for a user."""
    from axon.models import Filter
    
    filter_obj = Filter(
        metadata={"user_id": user_id},
        tags=["preferences"]
    )
    return await memory.recall(
        "user preferences",
        k=50,
        filter=filter_obj,
        tiers=["persistent"]
    )
```

### Pattern 2: Session Management

```python
from datetime import datetime

async def track_user_action(session_id: str, action: str):
    """Track user actions in current session."""
    await memory.store(
        f"User action: {action}",
        importance=0.5,  # Session tier
        metadata={
            "session_id": session_id,
            "action_type": action,
            "timestamp": datetime.now().isoformat()
        },
        tags=["session", "activity"]
    )

async def get_session_history(session_id: str):
    """Get all actions in current session."""
    from axon.models import Filter
    
    filter_obj = Filter(metadata={"session_id": session_id})
    return await memory.recall(
        "session history",
        k=100,
        filter=filter_obj,
        tiers=["session"]
    )
```

### Pattern 3: Temporary Cache

```python
async def cache_api_response(key: str, data: str):
    """Cache API response briefly."""
    await memory.store(
        f"API cache: {key} = {data}",
        importance=0.1,  # Ephemeral tier
        tier="ephemeral",
        tags=["cache", "api"],
        metadata={"cache_key": key}
    )

async def get_cached_response(key: str):
    """Try to retrieve from cache."""
    from axon.models import Filter
    
    filter_obj = Filter(metadata={"cache_key": key})
    results = await memory.recall(
        f"cache {key}",
        k=1,
        filter=filter_obj,
        tiers=["ephemeral"]
    )
    return results[0] if results else None
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Learn about custom policies, tier configuration, and advanced settings.

    [:octicons-arrow-right-24: Configuration Guide](configuration.md)

-   :material-layers:{ .lg .middle } **Core Concepts**

    ---

    Deep dive into memory tiers, policies, routing, and lifecycle.

    [:octicons-arrow-right-24: Core Concepts](../concepts/overview.md)

-   :material-database:{ .lg .middle } **Storage Adapters**

    ---

    Learn about Redis, ChromaDB, Qdrant, Pinecone, and custom adapters.

    [:octicons-arrow-right-24: Adapters Guide](../adapters/overview.md)

-   :material-code-braces:{ .lg .middle } **Examples**

    ---

    Explore 45+ working examples covering all features.

    [:octicons-arrow-right-24: Browse Examples](../examples/basic.md)

</div>

---

## Quick Reference

### Essential Imports

```python
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG, STANDARD_CONFIG
from axon.models import Filter
```

### Basic Operations

```python
# Store
entry_id = await memory.store(text, importance=0.5, tags=[], metadata={})

# Recall
results = await memory.recall(query, k=10, filter=None, tiers=None)

# Forget
await memory.forget(entry_id)
```

### Configuration

```python
# Use a template
memory = MemorySystem(DEVELOPMENT_CONFIG)

# Or create custom config
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,
        max_entries=1000
    ),
    default_tier="session"
)
memory = MemorySystem(config)
```

---

## Troubleshooting

### "No module named 'redis'"

Install Redis client:

```bash
pip install redis>=5.0.0
```

### "Connection refused" (Redis)

Start Redis server:

```bash
docker run -d -p 6379:6379 redis:latest
```

### "Async function not awaited"

Remember to use `await` and `async`:

```python
# Wrong
entry_id = memory.store("text")

# Correct
entry_id = await memory.store("text")
```

### Need more help?

- 📖 [Full Documentation](http://axon.saranmahadev.in)
- 💬 [GitHub Discussions](https://github.com/saranmahadev/Axon/discussions)
- 🐛 [Report Issues](https://github.com/saranmahadev/Axon/issues)
