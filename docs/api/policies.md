# Policies API

Complete API reference for policy engine and tier policies.

---

## Overview

The policy engine manages automatic memory promotion, demotion, and tier selection based on importance scores and access patterns.

```python
from axon.core.policy_engine import PolicyEngine
from axon.core.adapter_registry import AdapterRegistry
from axon.core.scoring import ScoringEngine

policy_engine = PolicyEngine(
    registry=registry,
    scoring_engine=scoring_engine,
    tier_policies={"session": session_policy, "persistent": persistent_policy}
)
```

---

## PolicyEngine

Manages policy decisions and tier routing.

### Constructor

```python
class PolicyEngine:
    def __init__(
        self,
        registry: AdapterRegistry,
        scoring_engine: ScoringEngine,
        tier_policies: dict[str, Policy]
    )
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `registry` | `AdapterRegistry` | Adapter registry for storage backends |
| `scoring_engine` | `ScoringEngine` | Scoring engine for importance calculation |
| `tier_policies` | `dict[str, Policy]` | Mapping of tier names to policies |

**Example:**

```python
from axon.core.policy_engine import PolicyEngine
from axon.core.policies import SessionPolicy, PersistentPolicy

policies = {
    "session": SessionPolicy(adapter_type="redis", ttl_seconds=600),
    "persistent": PersistentPolicy(adapter_type="chroma")
}

engine = PolicyEngine(
    registry=registry,
    scoring_engine=scoring_engine,
    tier_policies=policies
)
```

---

### Methods

#### `should_promote`

```python
def should_promote(
    self,
    entry: MemoryEntry,
    current_tier: str
) -> bool
```

Determine if entry should be promoted to higher tier.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry` | `MemoryEntry` | Memory entry to evaluate |
| `current_tier` | `str` | Current tier name |

**Returns:**
- `bool`: `True` if entry should be promoted

**Promotion Criteria:**
- High importance score (>= 0.7)
- High access frequency (>= 5 accesses)
- Recent access pattern

**Example:**

```python
entry = await system.get("entry-uuid")

if policy_engine.should_promote(entry, "session"):
    # Promote to persistent
    await system.store(
        entry.text,
        importance=entry.metadata.importance,
        tier="persistent"
    )
```

---

#### `should_demote`

```python
def should_demote(
    self,
    entry: MemoryEntry,
    current_tier: str
) -> bool
```

Determine if entry should be demoted to lower tier.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry` | `MemoryEntry` | Memory entry to evaluate |
| `current_tier` | `str` | Current tier name |

**Returns:**
- `bool`: `True` if entry should be demoted

**Demotion Criteria:**
- Low importance score (< 0.3)
- Low access frequency (< 2 accesses)
- Old entry (> 30 days without access)

**Example:**

```python
entry = await system.get("entry-uuid")

if policy_engine.should_demote(entry, "persistent"):
    # Demote to session
    await system.forget("entry-uuid", tier="persistent")
    await system.store(
        entry.text,
        importance=entry.metadata.importance,
        tier="session"
    )
```

---

#### `select_tier`

```python
def select_tier(
    self,
    importance: float,
    tags: list[str] | None = None,
    metadata: dict | None = None
) -> str
```

Select appropriate tier for new entry based on importance.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `importance` | `float` | Importance score (0.0-1.0) |
| `tags` | `list[str] \| None` | Optional tags |
| `metadata` | `dict \| None` | Optional metadata |

**Returns:**
- `str`: Selected tier name

**Selection Logic:**
- importance >= 0.7 → persistent
- 0.3 <= importance < 0.7 → session
- importance < 0.3 → ephemeral

**Example:**

```python
# High importance → persistent
tier = policy_engine.select_tier(importance=0.9)
# Returns: "persistent"

# Medium importance → session
tier = policy_engine.select_tier(importance=0.5)
# Returns: "session"

# Low importance → ephemeral
tier = policy_engine.select_tier(importance=0.2)
# Returns: "ephemeral"
```

---

#### `get_eviction_candidates`

```python
async def get_eviction_candidates(
    self,
    tier: str,
    count: int
) -> list[MemoryEntry]
```

Get entries to evict based on eviction strategy.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tier` | `str` | Tier to get candidates from |
| `count` | `int` | Number of candidates needed |

**Returns:**
- `list[MemoryEntry]`: Entries to evict

**Eviction Strategies:**
- **TTL**: Oldest entries by creation time
- **LRU**: Least recently accessed
- **FIFO**: First in, first out
- **Importance**: Lowest importance scores

**Example:**

```python
# Get 10 eviction candidates
candidates = await policy_engine.get_eviction_candidates(
    tier="session",
    count=10
)

# Evict them
for entry in candidates:
    await system.forget(entry.id)
```

---

## ScoringEngine

Calculate importance scores for memories.

### Constructor

```python
class ScoringEngine:
    def __init__(self, default_importance: float = 0.5)
```

**Parameters:**
- `default_importance` (`float`): Default score when not specified

---

### Methods

#### `calculate_importance`

```python
def calculate_importance(
    self,
    content: str,
    metadata: dict | None = None,
    tags: list[str] | None = None
) -> float
```

Calculate importance score based on content and metadata.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Memory content |
| `metadata` | `dict \| None` | Optional metadata |
| `tags` | `list[str] \| None` | Optional tags |

**Returns:**
- `float`: Importance score (0.0-1.0)

**Scoring Factors:**
- Content length (longer = more important)
- Tag presence (more tags = more important)
- Metadata richness (more metadata = more important)
- Keyword detection (certain keywords boost score)

**Example:**

```python
from axon.core.scoring import ScoringEngine

engine = ScoringEngine()

# Basic content
score = engine.calculate_importance("User prefers dark mode")
# Returns: 0.5

# Rich content with tags and metadata
score = engine.calculate_importance(
    "Important: API key for production",
    metadata={"service": "openai", "environment": "prod"},
    tags=["credentials", "api", "production"]
)
# Returns: 0.85
```

---

#### `update_importance`

```python
def update_importance(
    self,
    entry: MemoryEntry,
    decay_factor: float = 0.9
) -> float
```

Update importance based on access patterns and time decay.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry` | `MemoryEntry` | Entry to update |
| `decay_factor` | `float` | Time decay factor (0.0-1.0) |

**Returns:**
- `float`: Updated importance score

**Update Logic:**
- Increase: High access frequency
- Decrease: Time decay (older entries lose importance)
- Boost: Recent access

**Example:**

```python
entry = await system.get("entry-uuid")

# Update based on access pattern
new_importance = engine.update_importance(
    entry,
    decay_factor=0.95
)

await system.update(
    entry.id,
    importance=new_importance
)
```

---

## Promotion/Demotion Policies

### Promotion Thresholds

| Criteria | Threshold | Action |
|----------|-----------|--------|
| High importance | >= 0.7 | Promote to higher tier |
| High access count | >= 5 accesses | Promote to higher tier |
| Recent access | < 1 hour since last access | Promote to higher tier |

### Demotion Thresholds

| Criteria | Threshold | Action |
|----------|-----------|--------|
| Low importance | < 0.3 | Demote to lower tier |
| Low access count | < 2 accesses | Demote to lower tier |
| Stale | > 30 days without access | Demote to lower tier |

---

## Eviction Strategies

### TTL (Time-To-Live)

Evict entries based on creation time.

```python
policy = SessionPolicy(
    adapter_type="redis",
    ttl_seconds=600,
    eviction_strategy="ttl"
)
```

**Best For:**
- Temporary data
- Time-sensitive information
- Session data

---

### LRU (Least Recently Used)

Evict least recently accessed entries.

```python
policy = EphemeralPolicy(
    adapter_type="memory",
    max_entries=100,
    eviction_strategy="lru"
)
```

**Best For:**
- Cache-like behavior
- Frequently accessed data
- Limited capacity

---

### FIFO (First-In-First-Out)

Evict oldest entries by creation order.

```python
policy = SessionPolicy(
    adapter_type="redis",
    max_entries=1000,
    eviction_strategy="fifo"
)
```

**Best For:**
- Queue-like behavior
- Predictable eviction
- Simple scenarios

---

### Importance-Based

Evict entries with lowest importance scores.

```python
policy = PersistentPolicy(
    adapter_type="chroma",
    compaction_threshold=10000,
    eviction_strategy="importance"
)
```

**Best For:**
- Long-term storage
- Value-based retention
- Intelligent compaction

---

## Complete Example

```python
import asyncio
from axon import MemorySystem, MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy
from axon.core.policy_engine import PolicyEngine
from axon.core.scoring import ScoringEngine
from axon.core.adapter_registry import AdapterRegistry

async def main():
    # Configure policies
    config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=600,
            max_entries=1000,
            eviction_strategy="lru"
        ),
        persistent=PersistentPolicy(
            adapter_type="chroma",
            compaction_threshold=10000,
            eviction_strategy="importance"
        ),
        enable_promotion=True,
        enable_demotion=True
    )
    
    # Create system
    system = MemorySystem(config)
    
    # Store with automatic tier selection
    id1 = await system.store(
        "Important data",
        importance=0.9  # → persistent tier
    )
    
    id2 = await system.store(
        "Temporary note",
        importance=0.2  # → ephemeral tier
    )
    
    # Access patterns trigger promotion
    for _ in range(10):
        await system.get(id2)  # High access count
    
    # Check if should promote
    entry = await system.get(id2)
    if system.policy_engine.should_promote(entry, "ephemeral"):
        print("Promoting to session tier")
        await system.store(
            entry.text,
            importance=entry.metadata.importance,
            tier="session"
        )

asyncio.run(main())
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-memory:{ .lg .middle } **MemorySystem**

    ---

    Use policies with MemorySystem.

    [:octicons-arrow-right-24: MemorySystem API](memory-system.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Configure tier policies.

    [:octicons-arrow-right-24: Configuration API](config.md)

-   :material-robot-outline:{ .lg .middle } **Core Concepts**

    ---

    Learn about policy concepts.

    [:octicons-arrow-right-24: Policy Concepts](../concepts/policies.md)

</div>
