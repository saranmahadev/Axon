# Policies

Learn how to configure tier policies, understand policy constraints, and create custom policy rules.

---

## Overview

**Policies** define the rules and constraints for each memory tier. They control:

- Which storage adapters can be used
- How long memories live (TTL)
- Capacity limits and overflow behavior
- Compaction strategies
- Vector search capabilities

Policies are **declarative** - you define what you want, and Axon enforces it automatically.

```python
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

# Define policies
ephemeral = EphemeralPolicy(adapter_type="redis", ttl_seconds=60)
session = SessionPolicy(adapter_type="redis", ttl_seconds=600, max_entries=1000)
persistent = PersistentPolicy(adapter_type="chroma", compaction_threshold=10000)
```

---

## Policy Types

### EphemeralPolicy

For **very short-lived** memories (5 seconds to 1 hour).

```python
from axon.core.policies import EphemeralPolicy

policy = EphemeralPolicy(
    adapter_type="redis",  # "redis" or "memory" only
    ttl_seconds=60         # 5-3600 seconds
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tier_name` | `Literal["ephemeral"]` | `"ephemeral"` | Always "ephemeral" |
| `adapter_type` | `Literal["redis", "memory"]` | `"redis"` | Storage adapter |
| `ttl_seconds` | `int` | `60` | Time to live (5-3600) |
| `eviction_strategy` | `Literal["ttl"]` | `"ttl"` | Always TTL-based |
| `enable_vector_search` | `Literal[False]` | `False` | Always disabled |

**Constraints:**

- ✓ Only `redis` or `memory` adapters allowed
- ✓ TTL must be 5-3600 seconds (max 1 hour)
- ✗ Vector search not supported
- ✗ Eviction strategy cannot be changed

**Use Cases:**
- Rate limiting tokens
- OTP codes
- Temporary feature flags
- Recent activity tracking

---

### SessionPolicy

For **session-scoped** memories (minutes to hours).

```python
from axon.core.policies import SessionPolicy

policy = SessionPolicy(
    adapter_type="redis",              # Any adapter
    ttl_seconds=1800,                  # ≥60s or None
    max_entries=1000,                  # ≥10 or None
    overflow_to_persistent=True,       # Auto-promote when full
    enable_vector_search=False         # Adapter-dependent
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tier_name` | `Literal["session"]` | `"session"` | Always "session" |
| `adapter_type` | `Literal[...]` | `"redis"` | Any adapter type |
| `ttl_seconds` | `int \| None` | `600` | TTL ≥60s or None |
| `max_entries` | `int \| None` | `1000` | Capacity limit ≥10 |
| `overflow_to_persistent` | `bool` | `False` | Promote when full |
| `enable_vector_search` | `bool` | `True` | If adapter supports |

**Constraints:**

- ✓ Any adapter type allowed
- ✓ TTL must be ≥60 seconds if set
- ✓ Max entries must be ≥10 if set
- ✓ Vector search depends on adapter

**Use Cases:**
- Conversation history
- Active workspace state
- Shopping cart data
- Session preferences

---

### PersistentPolicy

For **long-term** memories (days to forever).

```python
from axon.core.policies import PersistentPolicy

policy = PersistentPolicy(
    adapter_type="chroma",                    # Vector-capable adapter
    ttl_seconds=None,                         # No expiration
    compaction_threshold=10000,               # Compact at 10K
    compaction_strategy="importance",         # Strategy
    enable_vector_search=True,                # Always True
    archive_adapter=None                      # Optional archival
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tier_name` | `Literal["persistent"]` | `"persistent"` | Always "persistent" |
| `adapter_type` | `Literal[...]` | `"chroma"` | Vector DB adapter |
| `ttl_seconds` | `int \| None` | `None` | Usually None |
| `compaction_threshold` | `int \| None` | `10000` | Compact at N entries |
| `compaction_strategy` | `Literal[...]` | `"count"` | Compaction method |
| `enable_vector_search` | `Literal[True]` | `True` | Always enabled |
| `archive_adapter` | `str \| None` | `None` | Cold storage adapter |

**Constraints:**

- ✓ Only vector-capable adapters (`chroma`, `qdrant`, `pinecone`, `memory`)
- ✓ Compaction threshold ≥100 if set
- ✓ Vector search always enabled
- ✓ TTL usually None or very long

**Use Cases:**
- Knowledge bases
- User profiles
- Permanent records
- Training data

---

## PolicyEngine

The **PolicyEngine** orchestrates lifecycle decisions using policies and scoring.

### Responsibilities

1. **Promotion Decisions**: When to move memories to higher tiers
2. **Demotion Decisions**: When to move memories to lower tiers
3. **Capacity Management**: Enforce max_entries limits
4. **Compaction Scheduling**: Trigger compaction at thresholds

### Promotion Logic

```python
# PolicyEngine checks if entry should promote
should_promote, reason = policy_engine.should_promote(
    entry=memory_entry,
    current_tier="session",
    target_tier="persistent",
    capacity_pressure=0.8  # 80% full
)

if should_promote:
    print(f"Promote because: {reason['reason']}")
    # Reasons might be:
    # - "high_score": Importance score exceeds threshold
    # - "capacity_pressure": Current tier is full
    # - "access_pattern": Frequently accessed
```

**Promotion Triggers:**

- ✅ High importance score (≥0.7 for persistent)
- ✅ Frequent access (>10 accesses in short period)
- ✅ Capacity pressure (tier near max_entries)
- ✅ Overflow enabled (overflow_to_persistent=True)

### Demotion Logic

```python
# PolicyEngine checks if entry should demote
should_demote, reason = policy_engine.should_demote(
    entry=memory_entry,
    current_tier="persistent",
    target_tier="session",
    capacity_pressure=0.2  # 20% full (low pressure)
)

if should_demote:
    print(f"Demote because: {reason['reason']}")
    # Reasons might be:
    # - "low_score": Importance score below threshold
    # - "stale": Not accessed in long time
    # - "low_capacity_pressure": Tier has room
```

**Demotion Triggers:**

- ✅ Low importance score (<0.3 for ephemeral)
- ✅ Infrequent access (no access in 30+ days)
- ✅ Low capacity pressure (plenty of room)
- ✅ Manual demotion request

---

## Policy Validation

Axon validates policies at configuration time using **Pydantic**.

### Automatic Validation

```python
# ❌ Invalid adapter for ephemeral
try:
    policy = EphemeralPolicy(adapter_type="pinecone")
except ValueError as e:
    print(e)  # "Ephemeral tier requires in-memory adapter, got 'pinecone'"

# ❌ TTL too short
try:
    policy = EphemeralPolicy(ttl_seconds=2)
except ValueError as e:
    print(e)  # "Ephemeral TTL must be at least 5 seconds"

# ❌ Invalid compaction threshold
try:
    policy = PersistentPolicy(compaction_threshold=50)
except ValueError as e:
    print(e)  # "Compaction threshold should be at least 100 entries"
```

### Custom Validators

Policies use **Pydantic field validators** for complex validation:

```python
@field_validator("ttl_seconds")
@classmethod
def validate_ephemeral_ttl(cls, v: int) -> int:
    """Validate that TTL is appropriate for ephemeral tier."""
    if v < 5:
        raise ValueError("Ephemeral TTL must be at least 5 seconds")
    if v > 3600:
        raise ValueError("Ephemeral TTL should not exceed 1 hour (3600s)")
    return v
```

---

## Policy Configuration Patterns

### Pattern 1: All Tiers Configured

```python
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="redis",
        ttl_seconds=60
    ),
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,
        max_entries=1000,
        overflow_to_persistent=True
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma",
        compaction_threshold=10000,
        compaction_strategy="importance"
    ),
    default_tier="session",
    enable_promotion=True,
    enable_demotion=False
)
```

### Pattern 2: Session + Persistent Only

```python
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800
    ),
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        compaction_threshold=20000
    ),
    default_tier="session"
)
# No ephemeral tier - starts at session
```

### Pattern 3: Persistent Only (Simplest)

```python
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="chroma"
    ),
    default_tier="persistent"
)
# Single tier, no promotion/demotion
```

---

## Advanced Policy Features

### Overflow Management

When session tier reaches `max_entries`:

```python
session = SessionPolicy(
    max_entries=100,
    overflow_to_persistent=True  # Auto-promote oldest entries
)

# Store 101st entry
await memory.store("Entry 101", tier="session")

# Oldest entry automatically promoted to persistent
# Session tier remains at 100 entries
```

### Compaction Strategies

Four strategies available for persistent tier:

```python
# 1. Count-based (simple batching)
policy = PersistentPolicy(compaction_strategy="count")

# 2. Importance-based (keep high-value)
policy = PersistentPolicy(compaction_strategy="importance")

# 3. Semantic-based (group similar)
policy = PersistentPolicy(compaction_strategy="semantic")

# 4. Time-based (compact oldest)
policy = PersistentPolicy(compaction_strategy="time")
```

### Archival Support

Move compacted data to cold storage:

```python
policy = PersistentPolicy(
    adapter_type="pinecone",
    compaction_threshold=50000,
    archive_adapter="s3"  # Archive to S3
)

# When compaction runs:
# 1. Summarize/compress memories
# 2. Move originals to S3
# 3. Keep summaries in Pinecone
```

---

## Custom Policies

You can create custom policies by extending the base `Policy` class:

```python
from axon.core.policy import Policy
from pydantic import Field, field_validator
from typing import Literal

class CustomPolicy(Policy):
    """Custom policy for special use case."""
    
    tier_name: str = "custom"
    adapter_type: str = "custom_adapter"
    custom_field: int = Field(100, description="Custom constraint")
    
    @field_validator("custom_field")
    @classmethod
    def validate_custom_field(cls, v: int) -> int:
        if v < 10:
            raise ValueError("custom_field must be >= 10")
        return v

# Use custom policy
config = MemoryConfig(
    custom=CustomPolicy(custom_field=200),
    default_tier="custom"
)
```

---

## Policy Best Practices

### 1. Match Policies to Use Cases

```python
# ✓ Good: Cache with Redis, knowledge with vector DB
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="redis"),
    persistent=PersistentPolicy(adapter_type="chroma")
)

# ✗ Bad: Vector DB for cache (expensive)
config = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="memory"),  # OK
    session=SessionPolicy(adapter_type="pinecone")     # Expensive!
)
```

### 2. Enable Overflow for Session

```python
# ✓ Good: Prevent data loss
session = SessionPolicy(
    max_entries=1000,
    overflow_to_persistent=True  # Promote when full
)

# ⚠️ Risky: May drop important data
session = SessionPolicy(
    max_entries=1000,
    overflow_to_persistent=False  # Evict oldest
)
```

### 3. Set Reasonable Compaction Thresholds

```python
# ✓ Good: Balance frequency and overhead
persistent = PersistentPolicy(
    compaction_threshold=10000  # Every 10K entries
)

# ✗ Too frequent (overhead)
persistent = PersistentPolicy(
    compaction_threshold=100  # Every 100 entries
)

# ⚠️ May delay too long
persistent = PersistentPolicy(
    compaction_threshold=1000000  # Every 1M entries
)
```

### 4. Use Appropriate TTLs

```python
# ✓ Good TTL ranges
ephemeral: 30-300 seconds
session: 600-3600 seconds (10-60 minutes)
persistent: None (no expiration)

# ✗ Bad TTL choices
ephemeral: 7200 seconds  # Use session instead
session: 30 seconds      # Use ephemeral instead
persistent: 600 seconds  # Defeats purpose
```

---

## Policy Configuration Reference

### Complete Field Reference

#### EphemeralPolicy Fields

```python
{
    "tier_name": "ephemeral",           # Fixed
    "adapter_type": "redis" | "memory", # In-memory only
    "ttl_seconds": 5-3600,              # Max 1 hour
    "eviction_strategy": "ttl",         # Fixed
    "enable_vector_search": False       # Fixed
}
```

#### SessionPolicy Fields

```python
{
    "tier_name": "session",                              # Fixed
    "adapter_type": "redis" | "memory" | "chroma" | 
                    "qdrant" | "pinecone",               # Any adapter
    "ttl_seconds": ≥60 | None,                           # Min 60s
    "max_entries": ≥10 | None,                           # Min 10
    "overflow_to_persistent": True | False,              # Configurable
    "enable_vector_search": True | False                 # Adapter-dependent
}
```

#### PersistentPolicy Fields

```python
{
    "tier_name": "persistent",                           # Fixed
    "adapter_type": "chroma" | "qdrant" | 
                    "pinecone" | "memory",               # Vector-capable
    "ttl_seconds": None | very_long,                     # Usually None
    "compaction_threshold": ≥100 | None,                 # Min 100
    "compaction_strategy": "count" | "semantic" | 
                           "importance" | "time",        # Strategy
    "enable_vector_search": True,                        # Fixed
    "archive_adapter": "s3" | "gcs" | None               # Optional
}
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-router:{ .lg .middle } **Routing**

    ---

    Learn how tier selection and routing works.

    [:octicons-arrow-right-24: Routing Guide](routing.md)

-   :material-layers-triple:{ .lg .middle } **Memory Tiers**

    ---

    Deep dive into ephemeral, session, and persistent tiers.

    [:octicons-arrow-right-24: Tier Details](tiers.md)

-   :material-autorenew:{ .lg .middle } **Lifecycle**

    ---

    Memory lifecycle from creation to archival.

    [:octicons-arrow-right-24: Lifecycle Guide](lifecycle.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Configure policies with pre-built templates.

    [:octicons-arrow-right-24: Configuration](../getting-started/configuration.md)

</div>
