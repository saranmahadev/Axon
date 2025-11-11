# Models API Reference

This page documents the core data models, enums, and schemas used throughout Axon.

---

## Overview

Axon uses Pydantic models for data validation and serialization. The models are organized into:

- **Base Types**: Core enums and base classes
- **Memory Entries**: Memory entry models
- **Filters**: Query and filter models
- **Audit**: Audit trail models

---

## Base Types

### MemoryTier

Memory storage tiers with different persistence and access characteristics.

```python
from axon.models import MemoryTier
```

**Values:**

| Tier | Description | Lifetime |
|------|-------------|----------|
| `EPHEMERAL` | Short-lived in-memory storage | Minutes |
| `SESSION` | Session-scoped storage | Hours to days |
| `PERSISTENT` | Long-term vector-indexed storage | Indefinite |
| `ARCHIVE` | Cold storage for infrequent access | Years |

**Example:**
```python
tier = MemoryTier.PERSISTENT
```

---

### PrivacyLevel

Privacy classification levels for memory entries. Levels ordered from least to most restrictive.

```python
from axon.models import PrivacyLevel
```

**Values:**

| Level | Description | Use Cases |
|-------|-------------|-----------|
| `PUBLIC` | Non-sensitive information | Public documents, general knowledge |
| `INTERNAL` | Internal use only | Emails, phone numbers, IP addresses |
| `SENSITIVE` | Requires careful handling | Personal preferences, private conversations |
| `RESTRICTED` | Highly confidential | SSN, credit cards, passwords |

**Example:**
```python
level = PrivacyLevel.SENSITIVE
```

---

### SourceType

Origin source of a memory entry.

```python
from axon.models import SourceType
```

**Values:**

- `APP`: Created by the application
- `SYSTEM`: Created by system/automation
- `AGENT`: Created by an AI agent

---

### MemoryEntryType

Type classification for memory entries.

```python
from axon.models import MemoryEntryType
```

**Values:**

| Type | Description |
|------|-------------|
| `NOTE` | Simple text note |
| `EVENT` | Time-bound event or action |
| `CONVERSATION_TURN` | Chat message or dialogue turn |
| `PROFILE` | User profile or preference data |
| `EMBEDDING_SUMMARY` | Summarized/compacted embedding |

---

## Core Models

### MemoryEntry

The primary model for storing memories in Axon.

```python
from axon.models import MemoryEntry
```

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (auto-generated UUID) |
| `tier` | `MemoryTier` | Storage tier |
| `content` | `str` | Memory text content |
| `embedding` | `list[float] \| None` | Vector embedding |
| `metadata` | `dict` | Additional metadata |
| `entry_type` | `MemoryEntryType` | Entry type |
| `source` | `SourceType` | Source of entry |
| `privacy_level` | `PrivacyLevel` | Privacy classification |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |
| `expires_at` | `datetime \| None` | Optional expiration |
| `tags` | `list[str]` | Searchable tags |
| `provenance` | `list[ProvenanceEvent]` | Audit trail |

**Example:**
```python
from axon.models import MemoryEntry, MemoryTier, PrivacyLevel, SourceType

entry = MemoryEntry(
    tier=MemoryTier.PERSISTENT,
    content="User prefers dark mode",
    metadata={"user_id": "user123"},
    privacy_level=PrivacyLevel.INTERNAL,
    source=SourceType.APP,
    tags=["preference", "ui"]
)
```

---

### ProvenanceEvent

Audit trail event tracking actions on memory entries.

```python
from axon.models import ProvenanceEvent
```

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `action` | `str` | Action performed (store, recall, compact, forget) |
| `by` | `str` | Module or component |
| `timestamp` | `datetime` | When action occurred |
| `metadata` | `dict[str, str]` | Additional context |

**Example:**
```python
event = ProvenanceEvent(
    action="store",
    by="MemorySystem",
    metadata={"reason": "user_input"}
)
```

---

## Filter Models

### MemoryFilter

Query filter for searching memories.

```python
from axon.models import MemoryFilter
```

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `tier` | `MemoryTier \| None` | Filter by tier |
| `tags` | `list[str] \| None` | Filter by tags |
| `metadata` | `dict \| None` | Filter by metadata |
| `entry_type` | `MemoryEntryType \| None` | Filter by type |
| `privacy_level` | `PrivacyLevel \| None` | Filter by privacy |
| `created_after` | `datetime \| None` | Filter by creation date |
| `created_before` | `datetime \| None` | Filter by creation date |

**Example:**
```python
from axon.models import MemoryFilter, MemoryTier

filter = MemoryFilter(
    tier=MemoryTier.PERSISTENT,
    tags=["important"],
    created_after=datetime(2024, 1, 1)
)

results = memory.search(filter=filter)
```

---

## Audit Models

### AuditLog

Complete audit log entry for a memory operation.

```python
from axon.models import AuditLog
```

**Attributes:**

| Field | Type | Description |
|-------|------|-------------|
| `operation` | `str` | Operation performed |
| `tier` | `MemoryTier` | Target tier |
| `memory_id` | `str \| None` | Memory entry ID |
| `timestamp` | `datetime` | When occurred |
| `metadata` | `dict` | Additional context |
| `success` | `bool` | Operation success |
| `error` | `str \| None` | Error message if failed |

**Example:**
```python
# Audit logs are created automatically
logs = memory.get_audit_logs(limit=10)
for log in logs:
    print(f"{log.timestamp}: {log.operation} on {log.tier}")
```

---

## Model Configuration

All Axon models use Pydantic v2 with strict validation:

- **JSON serialization** via `.model_dump_json()`
- **Dict conversion** via `.model_dump()`
- **Validation** on instantiation
- **Type hints** for IDE support

**Example:**
```python
# Serialize to JSON
json_str = entry.model_dump_json(indent=2)

# Convert to dict
data = entry.model_dump()

# Load from dict
entry = MemoryEntry.model_validate(data)
```

---

## Type Annotations

Axon provides full type annotations for static analysis:

```python
from axon.models import MemoryEntry, MemoryTier
from typing import List

def process_memories(entries: List[MemoryEntry]) -> dict:
    """Process a list of memory entries."""
    return {"count": len(entries)}
```

---

## See Also

- [Configuration API](config.md) - System configuration
- [Policies API](policies.md) - Policy definitions
- [Adapters API](adapters.md) - Storage adapters
- [Memory System API](memory-system.md) - Core memory operations
