# Router API Reference

The Router orchestrates memory operations across multiple tiers, handling intelligent tier selection, routing, and automatic promotion/demotion based on policies.

---

## Overview

The `Router` class manages:

- **Tier Selection**: Determines which tier to store memories in
- **Routing**: Routes operations to appropriate tier adapters
- **Promotion**: Moves frequently accessed memories to faster tiers
- **Demotion**: Moves cold memories to cheaper tiers
- **Statistics**: Tracks tier operation metrics

---

## Router Class

```python
from axon.core import Router
```

### Constructor

```python
def __init__(
    config: MemoryConfig,
    registry: AdapterRegistry,
    policy_engine: PolicyEngine | None = None,
    embedder: Any | None = None
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `MemoryConfig` | Memory configuration with tier policies |
| `registry` | `AdapterRegistry` | Adapter registry for tier storage |
| `policy_engine` | `PolicyEngine \| None` | Optional policy engine for routing decisions |
| `embedder` | `Any \| None` | Optional embedder for vector operations |

**Example:**
```python
from axon.core import Router, MemoryConfig, AdapterRegistry

config = MemoryConfig.balanced()
registry = AdapterRegistry()
registry.register("ephemeral", ephemeral_adapter)
registry.register("session", session_adapter)
registry.register("persistent", persistent_adapter)

router = Router(config, registry)
```

---

## Core Methods

### route_store()

Store a memory entry to the appropriate tier.

```python
async def route_store(entry: MemoryEntry) -> str
```

**Parameters:**

- `entry` (`MemoryEntry`): Memory entry to store

**Returns:**

- `str`: Memory entry ID

**Example:**
```python
from axon.models import MemoryEntry, MemoryTier

entry = MemoryEntry(
    tier=MemoryTier.PERSISTENT,
    content="Important user preference",
    metadata={"user_id": "user123"}
)

entry_id = await router.route_store(entry)
print(f"Stored: {entry_id}")
```

---

### route_recall()

Recall memories matching a query, with automatic promotion.

```python
async def route_recall(
    query: str,
    k: int = 10,
    filter: Filter | None = None,
    tiers: list[str] | None = None
) -> list[MemoryEntry]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | Required | Search query text |
| `k` | `int` | `10` | Number of results to return |
| `filter` | `Filter \| None` | `None` | Optional filter criteria |
| `tiers` | `list[str] \| None` | `None` | Specific tiers to search (all if None) |

**Returns:**

- `list[MemoryEntry]`: Matching memory entries

**Example:**
```python
# Search across all tiers
results = await router.route_recall("user preferences", k=5)

# Search specific tiers
results = await router.route_recall(
    "conversations",
    k=10,
    tiers=["session", "persistent"]
)

# With filter
from axon.models import MemoryFilter

filter = MemoryFilter(tags=["important"])
results = await router.route_recall("urgent", filter=filter)
```

---

### route_forget()

Delete a memory entry from its tier.

```python
async def route_forget(entry_id: str) -> bool
```

**Parameters:**

- `entry_id` (`str`): Memory entry ID to delete

**Returns:**

- `bool`: True if deleted, False if not found

**Example:**
```python
success = await router.route_forget("entry-123")
if success:
    print("Memory deleted")
```

---

### select_tier()

Determine the appropriate tier for a memory entry.

```python
async def select_tier(entry: MemoryEntry) -> str
```

**Parameters:**

- `entry` (`MemoryEntry`): Memory entry to evaluate

**Returns:**

- `str`: Tier name ("ephemeral", "session", "persistent")

**Selection Logic:**

1. Check `entry.metadata` for explicit tier hint
2. Use PolicyEngine if available
3. Fall back to entry.tier attribute
4. Default to "persistent"

**Example:**
```python
from axon.models import MemoryEntry, MemoryTier

entry = MemoryEntry(
    tier=MemoryTier.SESSION,
    content="Temporary data",
    metadata={"hint": "ephemeral"}  # Explicit tier hint
)

tier = await router.select_tier(entry)
print(f"Selected tier: {tier}")
```

---

## Promotion & Demotion

### promote()

Promote a memory entry to a faster/more persistent tier.

```python
async def promote(entry: MemoryEntry, from_tier: str, to_tier: str) -> bool
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry` | `MemoryEntry` | Entry to promote |
| `from_tier` | `str` | Current tier |
| `to_tier` | `str` | Target tier |

**Returns:**

- `bool`: True if promoted successfully

**Promotion Rules:**

- Ephemeral → Session → Persistent
- Only moves up the hierarchy
- Updates tier metadata
- Preserves all other data

**Example:**
```python
# Automatic promotion on frequent access
entry = await memory.get("entry-123")
if entry.metadata.get("access_count", 0) > 100:
    await router.promote(entry, "session", "persistent")
```

---

### demote()

Demote a memory entry to a slower/cheaper tier.

```python
async def demote(entry: MemoryEntry, from_tier: str, to_tier: str) -> bool
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry` | `MemoryEntry` | Entry to demote |
| `from_tier` | `str` | Current tier |
| `to_tier` | `str` | Target tier |

**Returns:**

- `bool`: True if demoted successfully

**Demotion Rules:**

- Persistent → Session → Ephemeral
- Only moves down the hierarchy
- Based on low access frequency
- Configured via compaction policies

**Example:**
```python
# Demote cold memories
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)
if entry.updated_at < cutoff:
    await router.demote(entry, "persistent", "session")
```

---

## Statistics & Monitoring

### get_stats()

Get routing statistics for all tiers.

```python
def get_stats() -> dict[str, dict[str, int]]
```

**Returns:**

Dict mapping tier names to operation counts:

```python
{
    "ephemeral": {
        "stores": 150,
        "recalls": 300,
        "forgets": 50,
        "promotions": 10
    },
    "session": {
        "stores": 100,
        "recalls": 200,
        "forgets": 20,
        "promotions": 5,
        "demotions": 3
    },
    "persistent": {
        "stores": 500,
        "recalls": 1000,
        "forgets": 50,
        "demotions": 8
    }
}
```

**Example:**
```python
stats = router.get_stats()
print(f"Total persistent stores: {stats['persistent']['stores']}")
print(f"Session promotions: {stats['session']['promotions']}")
```

---

### reset_stats()

Reset all tier statistics to zero.

```python
def reset_stats() -> None
```

**Example:**
```python
# Reset after monitoring period
router.reset_stats()
```

---

## Advanced Usage

### Custom Routing Logic

```python
from axon.core import Router
from axon.models import MemoryEntry

class CustomRouter(Router):
    async def select_tier(self, entry: MemoryEntry) -> str:
        """Custom tier selection logic."""
        # VIP users get persistent storage
        if entry.metadata.get("user_type") == "vip":
            return "persistent"
        
        # High importance goes to session
        if entry.metadata.get("importance", 0) > 7:
            return "session"
        
        # Default to ephemeral
        return "ephemeral"

router = CustomRouter(config, registry)
```

---

### Multi-Tier Search

```python
# Search with tier priority
async def search_with_fallback(query: str, k: int = 10):
    # Try ephemeral first (fastest)
    results = await router.route_recall(query, k, tiers=["ephemeral"])
    
    if len(results) < k:
        # Fall back to session
        session_results = await router.route_recall(
            query, k - len(results), tiers=["session"]
        )
        results.extend(session_results)
    
    if len(results) < k:
        # Final fallback to persistent
        persistent_results = await router.route_recall(
            query, k - len(results), tiers=["persistent"]
        )
        results.extend(persistent_results)
    
    return results[:k]
```

---

### Automatic Promotion on Access

```python
async def recall_with_auto_promote(query: str):
    results = await router.route_recall(query, k=10)
    
    for entry in results:
        # Track access count
        access_count = entry.metadata.get("access_count", 0) + 1
        entry.metadata["access_count"] = access_count
        
        # Promote if accessed frequently
        if access_count > 10 and entry.tier == "session":
            await router.promote(entry, "session", "persistent")
        elif access_count > 5 and entry.tier == "ephemeral":
            await router.promote(entry, "ephemeral", "session")
    
    return results
```

---

## Thread Safety

!!! warning "Not Thread-Safe"
    Router is designed for single-threaded async operation. All async methods should be awaited from the same event loop. For concurrent access, use locks or separate Router instances per context.

---

## Performance Considerations

- **Tier Order**: Ephemeral (fastest) → Session → Persistent (slowest)
- **Promotion Cost**: Involves cross-tier data copy
- **Demotion Cost**: Minimal, typically just metadata update
- **Statistics**: O(1) tracking overhead per operation

---

## See Also

- [Memory System API](memory-system.md) - High-level memory operations
- [Configuration API](config.md) - Tier configuration
- [Policies API](policies.md) - Routing policies
- [Adapters API](adapters.md) - Storage adapters
