# Configuration API

Complete API reference for `MemoryConfig` and tier policies.

---

## Overview

The configuration system defines how your memory tiers behave, including storage adapters, TTL, capacity limits, and eviction strategies.

```python
from axon import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy

config = MemoryConfig(
    session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
    persistent=PersistentPolicy(adapter_type="chroma")
)
```

---

## MemoryConfig

Main configuration class for the memory system.

### Constructor

```python
class MemoryConfig(BaseModel):
    def __init__(
        self,
        ephemeral: EphemeralPolicy | None = None,
        session: SessionPolicy | None = None,
        persistent: PersistentPolicy = ...,
        default_tier: Literal["ephemeral", "session", "persistent"] = "session",
        enable_promotion: bool = False,
        enable_demotion: bool = False
    )
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ephemeral` | `EphemeralPolicy \| None` | `None` | Ephemeral tier policy (optional) |
| `session` | `SessionPolicy \| None` | `None` | Session tier policy (optional) |
| `persistent` | `PersistentPolicy` | required | Persistent tier policy (required) |
| `default_tier` | `str` | `"session"` | Default tier for new memories |
| `enable_promotion` | `bool` | `False` | Auto-promote important memories |
| `enable_demotion` | `bool` | `False` | Auto-demote old/unimportant memories |

**Example:**

```python
from axon import MemoryConfig
from axon.core.policies import (
    EphemeralPolicy,
    SessionPolicy,
    PersistentPolicy
)

config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="memory",
        ttl_seconds=60,
        max_entries=100
    ),
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,
        max_entries=1000
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma",
        max_entries=None  # Unlimited
    ),
    default_tier="session",
    enable_promotion=True,
    enable_demotion=True
)
```

---

### Properties

#### `tiers`

```python
@property
def tiers(self) -> dict
```

Get configured tiers as a dictionary.

**Returns:**
- `dict`: Mapping of tier names to policy configurations

**Example:**

```python
for tier_name, policy in config.tiers.items():
    print(f"{tier_name}: {policy.adapter_type}")
```

---

### Methods

#### `to_dict`

```python
def to_dict(self) -> dict
```

Convert configuration to dictionary.

**Returns:**
- `dict`: Dictionary representation with all policies

**Example:**

```python
config_dict = config.to_dict()
print(config_dict["session"]["ttl_seconds"])
```

---

#### `from_dict`

```python
@classmethod
def from_dict(cls, data: dict) -> MemoryConfig
```

Create configuration from dictionary.

**Parameters:**
- `data` (`dict`): Dictionary containing configuration

**Returns:**
- `MemoryConfig`: Configuration instance

**Raises:**
- `ValidationError`: If data doesn't match schema

**Example:**

```python
data = {
    "session": {
        "tier_name": "session",
        "adapter_type": "redis",
        "ttl_seconds": 600
    },
    "persistent": {
        "tier_name": "persistent",
        "adapter_type": "chroma"
    }
}

config = MemoryConfig.from_dict(data)
```

---

#### `to_json`

```python
def to_json(self, indent: int = 2) -> str
```

Convert configuration to JSON string.

**Parameters:**
- `indent` (`int`): JSON indentation level

**Returns:**
- `str`: JSON representation

**Example:**

```python
json_str = config.to_json(indent=2)
print(json_str)
```

---

#### `from_json`

```python
@classmethod
def from_json(cls, json_str: str) -> MemoryConfig
```

Create configuration from JSON string.

**Parameters:**
- `json_str` (`str`): JSON string containing configuration

**Returns:**
- `MemoryConfig`: Configuration instance

**Example:**

```python
json_str = '''
{
  "session": {"adapter_type": "redis", "ttl_seconds": 600},
  "persistent": {"adapter_type": "chroma"}
}
'''

config = MemoryConfig.from_json(json_str)
```

---

## Policy Classes

Base class for all tier policies.

### Policy (Base Class)

```python
class Policy(BaseModel):
    tier_name: str
    adapter_type: Literal["redis", "chroma", "qdrant", "pinecone", "memory"]
    ttl_seconds: int | None = None
    max_entries: int | None = None
    compaction_threshold: int | None = None
    eviction_strategy: Literal["ttl", "lru", "fifo", "importance"] = "ttl"
    enable_vector_search: bool = True
```

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `tier_name` | `str` | required | Unique tier name (1-50 chars) |
| `adapter_type` | `str` | required | Storage adapter type |
| `ttl_seconds` | `int \| None` | `None` | Time-to-live (None = no expiration) |
| `max_entries` | `int \| None` | `None` | Max entries before eviction (None = unlimited) |
| `compaction_threshold` | `int \| None` | `None` | Entry count triggering compaction |
| `eviction_strategy` | `str` | `"ttl"` | Eviction strategy |
| `enable_vector_search` | `bool` | `True` | Enable vector similarity search |

---

### EphemeralPolicy

Policy for ephemeral (short-lived) tier.

```python
class EphemeralPolicy(Policy):
    tier_name: str = "ephemeral"
    adapter_type: Literal["memory", "redis"] = "memory"
    ttl_seconds: int = 60
    max_entries: int = 100
    eviction_strategy: Literal["lru", "fifo"] = "lru"
```

**Defaults:**
- TTL: 60 seconds
- Max entries: 100
- Adapter: in-memory
- Eviction: LRU

**Example:**

```python
from axon.core.policies import EphemeralPolicy

ephemeral = EphemeralPolicy(
    adapter_type="memory",
    ttl_seconds=30,
    max_entries=50
)
```

---

### SessionPolicy

Policy for session (medium-lived) tier.

```python
class SessionPolicy(Policy):
    tier_name: str = "session"
    adapter_type: Literal["redis", "memory"] = "redis"
    ttl_seconds: int = 3600
    max_entries: int = 1000
    eviction_strategy: Literal["ttl", "lru"] = "ttl"
```

**Defaults:**
- TTL: 3600 seconds (1 hour)
- Max entries: 1000
- Adapter: Redis
- Eviction: TTL-based

**Example:**

```python
from axon.core.policies import SessionPolicy

session = SessionPolicy(
    adapter_type="redis",
    adapter_config={
        "url": "redis://localhost:6379",
        "password": "secret"
    },
    ttl_seconds=600,
    max_entries=500
)
```

---

### PersistentPolicy

Policy for persistent (long-lived) tier.

```python
class PersistentPolicy(Policy):
    tier_name: str = "persistent"
    adapter_type: Literal["chroma", "qdrant", "pinecone"]
    ttl_seconds: int | None = None  # No expiration
    max_entries: int | None = None  # Unlimited
    compaction_threshold: int | None = 10000
    eviction_strategy: Literal["importance", "fifo"] = "importance"
```

**Defaults:**
- TTL: None (never expires)
- Max entries: None (unlimited)
- Compaction: 10,000 entries
- Eviction: Importance-based

**Example:**

```python
from axon.core.policies import PersistentPolicy

persistent = PersistentPolicy(
    adapter_type="chroma",
    adapter_config={
        "host": "localhost",
        "port": 8000
    },
    compaction_threshold=5000
)
```

---

## Adapter Configuration

Each policy accepts an `adapter_config` dict with adapter-specific settings.

### Redis Adapter Config

```python
adapter_config = {
    "url": "redis://localhost:6379",
    "password": "secret",
    "db": 0,
    "max_connections": 50,
    "socket_timeout": 5
}
```

### ChromaDB Adapter Config

```python
adapter_config = {
    "host": "localhost",
    "port": 8000,
    "collection_name": "memories",
    "distance_metric": "cosine"
}
```

### Qdrant Adapter Config

```python
adapter_config = {
    "url": "http://localhost:6333",
    "api_key": "your-api-key",
    "collection_name": "memories",
    "distance": "Cosine",
    "vector_size": 1536
}
```

### Pinecone Adapter Config

```python
adapter_config = {
    "api_key": "your-api-key",
    "environment": "us-west1-gcp",
    "index_name": "memories",
    "dimension": 1536
}
```

---

## Validation

The configuration system validates:

- ✓ At least one tier is configured (persistent required)
- ✓ Default tier exists in configuration
- ✓ TTL is non-negative
- ✓ Max entries is positive
- ✓ Compaction threshold ≥ 10 entries
- ✓ Promotion/demotion requires multiple tiers

**Example Validation Errors:**

```python
# Missing persistent tier
config = MemoryConfig()
# ValidationError: persistent tier required

# Invalid default tier
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="chroma"),
    default_tier="ephemeral"  # But ephemeral not configured
)
# ValidationError: default_tier is 'ephemeral' but not configured

# Enable promotion with only one tier
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="chroma"),
    enable_promotion=True  # But only 1 tier
)
# ValidationError: enable_promotion requires at least 2 tiers
```

---

## Configuration Templates

Pre-configured templates for common use cases.

### Minimal (Persistent Only)

```python
from axon.core.templates import minimal

config = minimal()
# Only persistent tier (ChromaDB)
```

### Balanced (Session + Persistent)

```python
from axon.core.templates import balanced

config = balanced()
# Session (Redis) + Persistent (ChromaDB)
```

### Full (All Tiers)

```python
from axon.core.templates import full

config = full()
# Ephemeral (Memory) + Session (Redis) + Persistent (ChromaDB)
```

---

## Complete Example

```python
from axon import MemoryConfig
from axon.core.policies import (
    EphemeralPolicy,
    SessionPolicy,
    PersistentPolicy
)

# Define policies
ephemeral = EphemeralPolicy(
    adapter_type="memory",
    ttl_seconds=60,
    max_entries=100,
    eviction_strategy="lru"
)

session = SessionPolicy(
    adapter_type="redis",
    adapter_config={
        "url": "redis://localhost:6379",
        "password": "secret"
    },
    ttl_seconds=600,
    max_entries=1000,
    eviction_strategy="ttl"
)

persistent = PersistentPolicy(
    adapter_type="chroma",
    adapter_config={
        "host": "localhost",
        "port": 8000,
        "collection_name": "memories"
    },
    compaction_threshold=10000
)

# Create config
config = MemoryConfig(
    ephemeral=ephemeral,
    session=session,
    persistent=persistent,
    default_tier="session",
    enable_promotion=True,
    enable_demotion=True
)

# Use with MemorySystem
from axon import MemorySystem

system = MemorySystem(config)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-memory:{ .lg .middle } **MemorySystem**

    ---

    Use the configuration with MemorySystem.

    [:octicons-arrow-right-24: MemorySystem API](memory-system.md)

-   :material-robot:{ .lg .middle } **Policies**

    ---

    Learn about policy behavior.

    [:octicons-arrow-right-24: Policies API](policies.md)

-   :material-database:{ .lg .middle } **Adapters**

    ---

    Configure storage adapters.

    [:octicons-arrow-right-24: Adapters API](adapters.md)

</div>
