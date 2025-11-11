# Utilities API

Complete API reference for utility modules - auditing, privacy, transactions, filters, and more.

---

## Overview

Axon provides utility modules for advanced features like audit logging, PII detection, distributed transactions, and filtering.

```python
from axon.core.audit import AuditLogger
from axon.core.privacy import PIIDetector
from axon.core.transaction import TransactionCoordinator
from axon.models.filter import Filter
```

---

## Audit Logging

### AuditLogger

Track all memory operations with comprehensive audit trail.

#### Constructor

```python
class AuditLogger:
    def __init__(self, storage_path: str | None = None)
```

**Parameters:**
- `storage_path` (`str | None`): File path for audit log storage (None = memory only)

**Example:**

```python
from axon.core.audit import AuditLogger

# Memory-only audit log
audit_logger = AuditLogger()

# Persistent audit log
audit_logger = AuditLogger(storage_path="/var/log/axon/audit.log")
```

---

#### Methods

##### `log_event`

```python
async def log_event(
    self,
    operation: OperationType,
    user_id: str,
    session_id: str | None = None,
    entry_id: str | None = None,
    status: EventStatus = EventStatus.SUCCESS,
    metadata: dict | None = None,
    error: str | None = None
) -> str
```

Log an audit event.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `operation` | `OperationType` | Type of operation |
| `user_id` | `str` | User identifier |
| `session_id` | `str \| None` | Session identifier |
| `entry_id` | `str \| None` | Memory entry ID |
| `status` | `EventStatus` | Success/failure status |
| `metadata` | `dict \| None` | Additional metadata |
| `error` | `str \| None` | Error message if failed |

**Returns:**
- `str`: Event ID

**Example:**

```python
from axon.models.audit import OperationType, EventStatus

# Log successful store
await audit_logger.log_event(
    operation=OperationType.STORE,
    user_id="user_123",
    session_id="session_abc",
    entry_id="entry-uuid",
    status=EventStatus.SUCCESS,
    metadata={"tier": "persistent", "importance": 0.9}
)

# Log failed recall
await audit_logger.log_event(
    operation=OperationType.RECALL,
    user_id="user_456",
    status=EventStatus.FAILURE,
    error="Invalid query format"
)
```

---

##### `get_events`

```python
async def get_events(
    self,
    operation: OperationType | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    status: EventStatus | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100
) -> list[AuditEvent]
```

Retrieve audit events with filtering.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `operation` | `OperationType \| None` | `None` | Filter by operation type |
| `user_id` | `str \| None` | `None` | Filter by user |
| `session_id` | `str \| None` | `None` | Filter by session |
| `status` | `EventStatus \| None` | `None` | Filter by status |
| `start_time` | `datetime \| None` | `None` | Start of time range |
| `end_time` | `datetime \| None` | `None` | End of time range |
| `limit` | `int` | `100` | Maximum number of events |

**Returns:**
- `list[AuditEvent]`: Filtered audit events

**Example:**

```python
from axon.models.audit import OperationType, EventStatus
from datetime import datetime, timedelta

# Get all STORE operations
store_events = await audit_logger.get_events(
    operation=OperationType.STORE
)

# Get failed events in last hour
recent_failures = await audit_logger.get_events(
    status=EventStatus.FAILURE,
    start_time=datetime.now() - timedelta(hours=1)
)

# Get user's events
user_events = await audit_logger.get_events(
    user_id="user_123",
    limit=50
)
```

---

### OperationType

Enum for audit event operation types.

```python
class OperationType(Enum):
    STORE = "store"
    RECALL = "recall"
    FORGET = "forget"
    UPDATE = "update"
    COMPACT = "compact"
    EXPORT = "export"
    IMPORT = "import"
    CUSTOM = "custom"
```

---

### EventStatus

Enum for audit event status.

```python
class EventStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
```

---

### AuditEvent

Data class for audit events.

```python
@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    operation: OperationType
    user_id: str
    session_id: str | None
    entry_id: str | None
    status: EventStatus
    metadata: dict
    error: str | None
```

---

## Privacy & PII Detection

### PIIDetector

Detect Personally Identifiable Information (PII) in text.

#### Constructor

```python
class PIIDetector:
    def __init__(self)
```

**Example:**

```python
from axon.core.privacy import PIIDetector

detector = PIIDetector()
```

---

#### Methods

##### `detect`

```python
def detect(self, text: str) -> PIIDetectionResult
```

Detect PII in text.

**Parameters:**
- `text` (`str`): Text to analyze

**Returns:**
- `PIIDetectionResult`: Detection result with PII types and recommended privacy level

**Example:**

```python
# Detect PII
result = detector.detect("My email is john@example.com and SSN is 123-45-6789")

print(f"Has PII: {result.has_pii}")
print(f"Types: {result.detected_types}")
print(f"Privacy Level: {result.recommended_privacy_level}")

# Output:
# Has PII: True
# Types: {'email', 'ssn'}
# Privacy Level: PrivacyLevel.RESTRICTED
```

---

### PIIDetectionResult

Result of PII detection.

```python
@dataclass
class PIIDetectionResult:
    has_pii: bool
    detected_types: set[str]  # {'email', 'phone', 'ssn', 'credit_card', ...}
    recommended_privacy_level: PrivacyLevel
    confidence: float  # 0.0-1.0
```

**Detected PII Types:**
- `email`: Email addresses
- `phone`: Phone numbers
- `ssn`: Social Security Numbers
- `credit_card`: Credit card numbers
- `ip_address`: IP addresses
- `person_name`: Person names (NER)
- `address`: Physical addresses

---

### PrivacyLevel

Enum for privacy levels.

```python
class PrivacyLevel(Enum):
    PUBLIC = "public"          # No PII, safe to share
    INTERNAL = "internal"      # Internal use only
    CONFIDENTIAL = "confidential"  # Sensitive, limited access
    RESTRICTED = "restricted"  # Highly sensitive, strict access
```

---

## Distributed Transactions

### TransactionCoordinator

Coordinate distributed transactions across multiple adapters using Two-Phase Commit (2PC).

#### Constructor

```python
class TransactionCoordinator:
    def __init__(self, adapters: dict[str, StorageAdapter])
```

**Parameters:**
- `adapters` (`dict[str, StorageAdapter]`): Mapping of tier names to adapters

**Example:**

```python
from axon.core.transaction import TransactionCoordinator

coordinator = TransactionCoordinator(adapters={
    "session": redis_adapter,
    "persistent": chroma_adapter
})
```

---

#### Methods

##### `begin_transaction`

```python
async def begin_transaction(
    self,
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
) -> str
```

Begin a new distributed transaction.

**Parameters:**
- `isolation_level` (`IsolationLevel`): Transaction isolation level

**Returns:**
- `str`: Transaction ID

**Example:**

```python
from axon.core.transaction import IsolationLevel

tx_id = await coordinator.begin_transaction(
    isolation_level=IsolationLevel.SERIALIZABLE
)
```

---

##### `commit_transaction`

```python
async def commit_transaction(self, transaction_id: str) -> bool
```

Commit transaction using Two-Phase Commit protocol.

**Parameters:**
- `transaction_id` (`str`): Transaction ID

**Returns:**
- `bool`: `True` if committed successfully

**Raises:**
- `TransactionError`: If commit fails

**Example:**

```python
try:
    # Perform operations within transaction
    await store_with_tx(tx_id, "Data 1")
    await store_with_tx(tx_id, "Data 2")
    
    # Commit
    success = await coordinator.commit_transaction(tx_id)
    if success:
        print("Transaction committed")
except TransactionError as e:
    print(f"Commit failed: {e}")
```

---

##### `rollback_transaction`

```python
async def rollback_transaction(self, transaction_id: str) -> bool
```

Rollback transaction and undo all changes.

**Parameters:**
- `transaction_id` (`str`): Transaction ID

**Returns:**
- `bool`: `True` if rolled back successfully

**Example:**

```python
try:
    await store_with_tx(tx_id, "Data")
except Exception:
    # Rollback on error
    await coordinator.rollback_transaction(tx_id)
```

---

### IsolationLevel

Enum for transaction isolation levels.

```python
class IsolationLevel(Enum):
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"      # Default
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"          # Strictest
```

---

## Filtering

### Filter

Filter memories by metadata, tags, and other criteria.

#### Constructor

```python
class Filter(BaseModel):
    metadata: dict[str, Any] | None = None
    tags: list[str] | None = None
    importance_range: tuple[float, float] | None = None
    time_range: tuple[datetime, datetime] | None = None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `metadata` | `dict \| None` | Filter by metadata key-value pairs (AND logic) |
| `tags` | `list[str] \| None` | Filter by tags (AND logic) |
| `importance_range` | `tuple[float, float] \| None` | Filter by importance range (min, max) |
| `time_range` | `tuple[datetime, datetime] \| None` | Filter by time range (start, end) |

**Example:**

```python
from axon.models.filter import Filter
from datetime import datetime, timedelta

# Filter by metadata
filter1 = Filter(metadata={"category": "finance", "user_id": "user_123"})

# Filter by tags
filter2 = Filter(tags=["important", "reviewed"])

# Filter by importance
filter3 = Filter(importance_range=(0.7, 1.0))

# Filter by time range
filter4 = Filter(
    time_range=(
        datetime.now() - timedelta(days=7),
        datetime.now()
    )
)

# Combine filters
filter5 = Filter(
    metadata={"category": "finance"},
    tags=["important"],
    importance_range=(0.8, 1.0)
)

# Use with recall
results = await system.recall("query", filter=filter5)
```

---

## Compaction Strategies

Strategies for memory compaction and summarization.

### CountStrategy

Compact when entry count exceeds threshold.

```python
from axon.core.compaction_strategies import CountStrategy

strategy = CountStrategy(threshold=100)
```

---

### SemanticStrategy

Compact similar entries together using clustering.

```python
from axon.core.compaction_strategies import SemanticStrategy

strategy = SemanticStrategy(
    similarity_threshold=0.85,
    min_cluster_size=3
)
```

---

### ImportanceStrategy

Compact low-importance entries.

```python
from axon.core.compaction_strategies import ImportanceStrategy

strategy = ImportanceStrategy(importance_threshold=0.3)
```

---

### TimeStrategy

Compact old entries.

```python
from axon.core.compaction_strategies import TimeStrategy
from datetime import timedelta

strategy = TimeStrategy(age_threshold=timedelta(days=30))
```

---

### HybridStrategy

Combine multiple strategies.

```python
from axon.core.compaction_strategies import HybridStrategy

strategy = HybridStrategy(
    strategies=[
        CountStrategy(threshold=100),
        ImportanceStrategy(importance_threshold=0.3)
    ]
)
```

---

## Complete Example

```python
import asyncio
from axon import MemorySystem, MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy
from axon.core.audit import AuditLogger
from axon.core.privacy import PIIDetector
from axon.core.transaction import TransactionCoordinator, IsolationLevel
from axon.models.filter import Filter
from axon.models.audit import OperationType
from datetime import datetime, timedelta

async def main():
    # Setup with audit and PII detection
    audit_logger = AuditLogger(storage_path="/var/log/axon/audit.log")
    pii_detector = PIIDetector()
    
    config = MemoryConfig(
        session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
        persistent=PersistentPolicy(adapter_type="chroma")
    )
    
    system = MemorySystem(
        config=config,
        audit_logger=audit_logger,
        pii_detector=pii_detector
    )
    
    # Store with PII detection
    entry_id = await system.store(
        "Contact: john@example.com",
        importance=0.9
    )
    # Automatically detects PII and sets privacy level
    
    # Use transactions
    tx_id = await system.begin_transaction(
        isolation_level=IsolationLevel.SERIALIZABLE
    )
    
    try:
        await system.store("Data 1", transaction_id=tx_id)
        await system.store("Data 2", transaction_id=tx_id)
        await system.commit_transaction(tx_id)
    except Exception:
        await system.rollback_transaction(tx_id)
    
    # Filter recall
    results = await system.recall(
        "contact information",
        filter=Filter(
            importance_range=(0.7, 1.0),
            time_range=(
                datetime.now() - timedelta(days=7),
                datetime.now()
            )
        )
    )
    
    # Export audit log
    events = await audit_logger.get_events(
        operation=OperationType.STORE,
        start_time=datetime.now() - timedelta(hours=1)
    )
    
    print(f"Recent stores: {len(events)}")

asyncio.run(main())
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } **Privacy**

    ---

    Learn about PII protection.

    [:octicons-arrow-right-24: Privacy Guide](../advanced/privacy.md)

-   :material-clipboard-text:{ .lg .middle } **Audit Logging**

    ---

    Complete audit trail setup.

    [:octicons-arrow-right-24: Audit Guide](../advanced/audit.md)

-   :material-swap-horizontal:{ .lg .middle } **Transactions**

    ---

    Distributed transactions guide.

    [:octicons-arrow-right-24: Transactions Guide](../advanced/transactions.md)

</div>
