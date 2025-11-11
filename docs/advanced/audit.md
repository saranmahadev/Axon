# Audit Logging

Comprehensive audit trail for compliance, debugging, and observability.

---

## Overview

The **Audit Logging** system provides structured tracking of all memory operations for compliance requirements, debugging, and observability. Every significant operation is logged with timestamps, user context, and outcomes.

**Key Features:**
- ✓ Structured event logging
- ✓ Async-safe operation
- ✓ In-memory with optional file export
- ✓ Automatic rotation
- ✓ Query and filter capabilities
- ✓ Compliance-ready formats

---

## Why Audit Logging?

### Compliance
- GDPR: Track personal data access and deletion
- HIPAA: Audit healthcare information access
- SOC 2: Demonstrate security controls
- ISO 27001: Evidence of information security

### Debugging
- Trace user actions leading to errors
- Analyze performance bottlenecks
- Understand usage patterns
- Reproduce issues from logs

### Observability
- Monitor system health
- Track operation success rates
- Measure latencies
- Identify anomalies

---

## Basic Usage

```python
from axon import MemorySystem
from axon.core.audit import AuditLogger

# Enable audit logging
audit_logger = AuditLogger(max_events=10000)
memory = MemorySystem(config, audit_logger=audit_logger)

# Operations are automatically logged
await memory.store("Important data", user_id="user_123")
await memory.recall("query", user_id="user_123")
await memory.forget("entry_id", user_id="user_123")

# Query audit trail
events = audit_logger.query_events(
    user_id="user_123",
    operation="STORE",
    start_time=datetime.now() - timedelta(hours=1)
)

print(f"User stored {len(events)} entries in the last hour")
```

---

## Configuration

### Initialize Audit Logger

```python
from axon.core.audit import AuditLogger
from pathlib import Path

# Basic configuration
audit_logger = AuditLogger(
    max_events=10000,              # Keep 10K events in memory
    auto_export_path=None,         # No auto-export
    enable_rotation=True           # Rotate when max reached
)

# With auto-export
audit_logger = AuditLogger(
    max_events=10000,
    auto_export_path=Path("./audit_logs"),
    enable_rotation=True
)
```

### Attach to Memory System

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig

config = MemoryConfig(...)
memory = MemorySystem(config, audit_logger=audit_logger)
```

---

## Event Types

### Operations

All memory operations are tracked:

```python
from axon.models.audit import OperationType

# Supported operations
OperationType.STORE       # Storing new entries
OperationType.RECALL      # Querying/searching
OperationType.FORGET      # Deleting entries
OperationType.COMPACT     # Compaction operations
OperationType.EXPORT      # Data exports
OperationType.IMPORT      # Data imports
```

### Event Status

```python
from axon.models.audit import EventStatus

EventStatus.SUCCESS       # Operation succeeded
EventStatus.FAILURE       # Operation failed
EventStatus.PARTIAL       # Partially succeeded (e.g., some entries)
```

---

## Manual Logging

Log custom events:

```python
from axon.models.audit import OperationType, EventStatus

# Log successful operation
await audit_logger.log_event(
    operation=OperationType.STORE,
    user_id="user_123",
    session_id="session_abc",
    entry_ids=["entry_1", "entry_2"],
    metadata={"source": "api", "batch_size": 2},
    status=EventStatus.SUCCESS,
    duration_ms=45.2
)

# Log failed operation
await audit_logger.log_event(
    operation=OperationType.RECALL,
    user_id="user_456",
    status=EventStatus.FAILURE,
    error_message="Database connection timeout",
    duration_ms=5000.0
)
```

---

## Querying Events

### By User

```python
# All events for a user
events = audit_logger.query_events(user_id="user_123")

# Specific operation
events = audit_logger.query_events(
    user_id="user_123",
    operation=OperationType.STORE
)
```

### By Time Range

```python
from datetime import datetime, timedelta

# Last hour
events = audit_logger.query_events(
    start_time=datetime.now() - timedelta(hours=1)
)

# Specific date range
events = audit_logger.query_events(
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 1, 31)
)
```

### By Status

```python
# Failed operations only
failures = audit_logger.query_events(status=EventStatus.FAILURE)

# Successful stores
successful_stores = audit_logger.query_events(
    operation=OperationType.STORE,
    status=EventStatus.SUCCESS
)
```

### Complex Queries

```python
# Failed recalls for specific user in last 24 hours
events = audit_logger.query_events(
    user_id="user_123",
    operation=OperationType.RECALL,
    status=EventStatus.FAILURE,
    start_time=datetime.now() - timedelta(days=1)
)

# All operations on specific entries
events = audit_logger.query_events(entry_ids=["entry_1", "entry_2"])
```

---

## Exporting Audit Logs

### Manual Export

```python
from pathlib import Path

# Export to JSON file
audit_logger.export_to_file(Path("./audit_trail.json"))

# Export filtered events
events = audit_logger.query_events(user_id="user_123")
audit_logger.export_events(events, Path("./user_123_audit.json"))
```

### Auto-Export on Rotation

```python
# Automatically export when max_events reached
audit_logger = AuditLogger(
    max_events=10000,
    auto_export_path=Path("./audit_logs"),
    enable_rotation=True
)

# Files created: audit_2025_01_15_103045.json, etc.
```

### Export Format

```json
{
  "events": [
    {
      "event_id": "evt_abc123",
      "timestamp": "2025-01-15T10:30:45.123456Z",
      "operation": "STORE",
      "user_id": "user_123",
      "session_id": "session_abc",
      "entry_ids": ["entry_1"],
      "metadata": {
        "importance": 0.8,
        "tags": ["verified"]
      },
      "status": "SUCCESS",
      "duration_ms": 45.2
    }
  ],
  "total_events": 1,
  "exported_at": "2025-01-15T11:00:00.000000Z"
}
```

---

## Statistics

### Event Statistics

```python
# Get statistics
stats = audit_logger.get_statistics()

print(f"Total events: {stats['total_events']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average latency: {stats['avg_duration_ms']:.2f}ms")

# By operation
print(f"Stores: {stats['by_operation']['STORE']}")
print(f"Recalls: {stats['by_operation']['RECALL']}")
```

### User Activity

```python
# Activity by user
user_stats = audit_logger.get_user_statistics("user_123")

print(f"Total operations: {user_stats['total_operations']}")
print(f"Last activity: {user_stats['last_activity']}")
print(f"Most common operation: {user_stats['most_common_operation']}")
```

---

## Examples

### Compliance Reporting

```python
from datetime import datetime, timedelta

# Generate monthly compliance report
async def generate_compliance_report(month: int, year: int):
    start_time = datetime(year, month, 1)
    end_time = datetime(year, month + 1, 1)
    
    # All events in month
    events = audit_logger.query_events(
        start_time=start_time,
        end_time=end_time
    )
    
    # Group by user
    users = {}
    for event in events:
        user_id = event.user_id or "anonymous"
        if user_id not in users:
            users[user_id] = []
        users[user_id].append(event)
    
    # Generate report
    report = {
        "period": f"{year}-{month:02d}",
        "total_events": len(events),
        "users": len(users),
        "operations": {},
        "user_activity": {}
    }
    
    # Count operations
    for event in events:
        op = event.operation.value
        report["operations"][op] = report["operations"].get(op, 0) + 1
    
    # User activity
    for user_id, user_events in users.items():
        report["user_activity"][user_id] = {
            "total": len(user_events),
            "stores": sum(1 for e in user_events if e.operation == OperationType.STORE),
            "recalls": sum(1 for e in user_events if e.operation == OperationType.RECALL),
            "deletions": sum(1 for e in user_events if e.operation == OperationType.FORGET)
        }
    
    return report
```

### Security Monitoring

```python
# Monitor for suspicious activity
async def monitor_security():
    """Check for unusual patterns."""
    
    # Excessive deletions
    recent_deletes = audit_logger.query_events(
        operation=OperationType.FORGET,
        start_time=datetime.now() - timedelta(hours=1)
    )
    
    if len(recent_deletes) > 100:
        logger.warning(f"Excessive deletions: {len(recent_deletes)} in last hour")
    
    # Failed access attempts
    failures = audit_logger.query_events(
        status=EventStatus.FAILURE,
        start_time=datetime.now() - timedelta(minutes=15)
    )
    
    if len(failures) > 10:
        logger.warning(f"Multiple failures: {len(failures)} in 15 minutes")
    
    # Unusual export activity
    exports = audit_logger.query_events(
        operation=OperationType.EXPORT,
        start_time=datetime.now() - timedelta(hours=24)
    )
    
    if len(exports) > 5:
        logger.warning(f"Unusual export activity: {len(exports)} in 24 hours")
```

---

## Performance

### Overhead

- **Logging latency:** 1-5ms per event (async)
- **Memory usage:** ~1KB per event
- **Query performance:** O(n) for filters, O(1) for index

### Optimization Tips

```python
# 1. Batch operations reduce log entries
await memory.import_data(entries)  # 1 log entry
# vs
for entry in entries:
    await memory.store(entry)      # N log entries

# 2. Limit max_events for bounded memory
audit_logger = AuditLogger(max_events=10000)  # ~10MB max

# 3. Enable rotation and export
audit_logger = AuditLogger(
    max_events=10000,
    enable_rotation=True,
    auto_export_path=Path("./logs")
)
```

---

## Best Practices

### 1. Include User Context

```python
# ✓ Good: Trackable
await memory.store("data", user_id="user_123", session_id="session_abc")

# ✗ Bad: Anonymous
await memory.store("data")
```

### 2. Regular Exports

```python
# Export daily for compliance
import schedule

def export_daily():
    timestamp = datetime.now().strftime("%Y%m%d")
    audit_logger.export_to_file(Path(f"./audit_{timestamp}.json"))

schedule.every().day.at("00:00").do(export_daily)
```

### 3. Monitor Statistics

```python
# Check health periodically
stats = audit_logger.get_statistics()

if stats['success_rate'] < 0.95:
    logger.warning("Low success rate: investigate failures")

if stats['avg_duration_ms'] > 1000:
    logger.warning("High latency: performance issue")
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-shield-lock:{ .lg .middle } **Privacy & PII Detection**

    ---

    Detect and protect sensitive data.

    [:octicons-arrow-right-24: Privacy Guide](privacy.md)

-   :material-database-sync:{ .lg .middle } **Transactions**

    ---

    Atomic operations across tiers.

    [:octicons-arrow-right-24: Transactions Guide](transactions.md)

-   :material-file-document:{ .lg .middle } **Logging Configuration**

    ---

    Structured logging for production.

    [:octicons-arrow-right-24: Logging Guide](logging.md)

</div>
