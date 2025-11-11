# Advanced Examples

Master advanced features: audit logging, privacy, transactions, compaction, and performance from `examples/03-advanced/`.

---

## Overview

These advanced examples demonstrate enterprise features for production deployments.

**Examples Covered:**
- Audit & Privacy (3 examples)
- Transactions (2 examples)
- Compaction (3 examples)
- Performance (3 examples)

**What You'll Learn:**
- Compliance and audit trails
- PII detection and privacy
- Distributed transactions
- Memory compaction strategies
- Performance optimization
- Production best practices

**Prerequisites:**
- Completed intermediate examples
- Understanding of distributed systems
- Production deployment experience

**Location:** `examples/03-advanced/`

---

## Audit & Privacy

### 01_audit_logging.py

**Complete audit trail** - Track all memory operations for compliance.

**File:** `examples/03-advanced/audit-privacy/01_audit_logging.py`

**What it demonstrates:**
- Enable audit logging
- Log all operations automatically
- Export audit logs
- Filter by operation type
- Filter by user/session
- Compliance reporting

**Setup:**

```python
from axon import MemorySystem
from axon.core import AuditLogger
from axon.models.audit import OperationType

# Create audit logger
audit_logger = AuditLogger(
    max_events=1000,
    enable_rotation=True,
    storage_path="/var/log/axon/audit.log"
)

memory = MemorySystem(config, audit_logger=audit_logger)
```

**Export audit log:**

```python
# Export all events
events = await memory.export_audit_log()

# Filter by operation
store_events = await memory.export_audit_log(
    operation=OperationType.STORE
)

# Filter by user
user_events = await memory.export_audit_log(
    user_id="user_123",
    start_time=datetime.now() - timedelta(hours=1)
)
```

**Audit event structure:**

```json
{
  "event_id": "evt_550e8400",
  "timestamp": "2024-01-15T10:30:00Z",
  "operation": "STORE",
  "user_id": "user_123",
  "session_id": "session_abc",
  "entry_id": "entry_xyz",
  "status": "SUCCESS",
  "duration_ms": 12.5,
  "metadata": {
    "tier": "persistent",
    "importance": 0.9
  }
}
```

---

### 02_pii_detection.py

**Privacy protection** - Automatic PII detection and handling.

**File:** `examples/03-advanced/audit-privacy/02_pii_detection.py`

**What it demonstrates:**
- Enable PII detection
- Automatic privacy level assignment
- PII types detected
- Privacy-aware storage
- Compliance with data regulations

**Setup:**

```python
from axon.core.privacy import PIIDetector

detector = PIIDetector()

memory = MemorySystem(
    config,
    pii_detector=detector,
    enable_pii_detection=True
)
```

**PII detection:**

```python
# Detect PII in text
result = detector.detect("My email is john@example.com and SSN is 123-45-6789")

print(f"Has PII: {result.has_pii}")
print(f"Types: {result.detected_types}")  # {'email', 'ssn'}
print(f"Privacy Level: {result.recommended_privacy_level}")  # RESTRICTED
```

**Detected PII types:**
- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- IP addresses
- Person names (NER)
- Physical addresses

**Privacy levels:**
- `PUBLIC` - No PII, safe to share
- `INTERNAL` - Internal use only
- `CONFIDENTIAL` - Sensitive, limited access
- `RESTRICTED` - Highly sensitive, strict access

---

### 03_privacy_policies.py

**Privacy-aware storage** - Implement privacy policies.

**File:** `examples/03-advanced/audit-privacy/03_privacy_policies.py`

**What it demonstrates:**
- Privacy level enforcement
- Access control by privacy level
- Redaction strategies
- Compliance workflows

---

## Transactions

### 01_basic_transactions.py

**ACID transactions** - Ensure data consistency across operations.

**File:** `examples/03-advanced/transactions/01_basic_transactions.py`

**What it demonstrates:**
- Begin transaction
- Perform multiple operations
- Commit or rollback
- Two-Phase Commit (2PC)
- Transaction isolation

**Basic transaction:**

```python
from axon.core.transaction import IsolationLevel

# Begin transaction
tx_id = await memory.begin_transaction(
    isolation_level=IsolationLevel.SERIALIZABLE
)

try:
    # Perform operations within transaction
    await memory.store("Data 1", transaction_id=tx_id)
    await memory.store("Data 2", transaction_id=tx_id)
    await memory.forget("old_entry", transaction_id=tx_id)
    
    # Commit
    await memory.commit_transaction(tx_id)
    print("Transaction committed successfully")
    
except Exception as e:
    # Rollback on error
    await memory.rollback_transaction(tx_id)
    print(f"Transaction rolled back: {e}")
```

**Transaction guarantees:**
- **Atomicity**: All operations succeed or all fail
- **Consistency**: Data remains valid
- **Isolation**: Transactions don't interfere
- **Durability**: Committed changes persist

---

### 02_isolation_levels.py

**Transaction isolation** - Control concurrent access patterns.

**File:** `examples/03-advanced/transactions/02_isolation_levels.py`

**What it demonstrates:**
- READ_UNCOMMITTED
- READ_COMMITTED (default)
- REPEATABLE_READ
- SERIALIZABLE (strictest)
- Performance vs. consistency trade-offs

**Isolation levels:**

```python
from axon.core.transaction import IsolationLevel

# Read uncommitted (fastest, least safe)
tx_id = await memory.begin_transaction(
    isolation_level=IsolationLevel.READ_UNCOMMITTED
)

# Read committed (default, balanced)
tx_id = await memory.begin_transaction(
    isolation_level=IsolationLevel.READ_COMMITTED
)

# Serializable (slowest, most safe)
tx_id = await memory.begin_transaction(
    isolation_level=IsolationLevel.SERIALIZABLE
)
```

---

## Compaction

### 01_count_based.py

**Count-based compaction** - Trigger compaction by entry count.

**File:** `examples/03-advanced/compaction/01_count_based.py`

**What it demonstrates:**
- Count threshold configuration
- Automatic compaction triggers
- Manual compaction
- Compaction results

**Configuration:**

```python
config = MemoryConfig(
    session=SessionPolicy(
        compaction_threshold=100,  # Compact at 100 entries
        compaction_strategy="count"
    ),
    persistent=PersistentPolicy(
        compaction_threshold=10000
    )
)
```

**Manual compaction:**

```python
# Dry run (preview)
result = await memory.compact(
    tier="session",
    strategy="count",
    threshold=50,
    dry_run=True
)

print(f"Would compact {len(result.entries_to_compact)} entries")
print(f"Into {result.num_summaries} summaries")

# Execute compaction
result = await memory.compact(tier="session")
print(f"Compacted {result.entries_removed} entries")
```

---

### 02_semantic_compaction.py

**Semantic compaction** - Cluster similar memories together.

**File:** `examples/03-advanced/compaction/02_semantic_compaction.py`

**What it demonstrates:**
- Similarity-based clustering
- Automatic summarization
- Cluster configuration
- Embedding-based grouping

**Configuration:**

```python
# Semantic compaction
result = await memory.compact(
    tier="persistent",
    strategy="semantic",
    threshold=0.85,  # 85% similarity
    min_cluster_size=3
)
```

---

### 03_importance_compaction.py

**Importance-based compaction** - Remove low-value memories.

**File:** `examples/03-advanced/compaction/03_importance_compaction.py`

**What it demonstrates:**
- Importance threshold
- Preserve high-value memories
- Remove low-importance entries
- Time decay consideration

**Configuration:**

```python
# Remove low-importance entries
result = await memory.compact(
    tier="session",
    strategy="importance",
    threshold=0.3  # Remove entries < 0.3 importance
)
```

---

## Performance

### 01_benchmarking.py

**Performance benchmarks** - Measure system performance.

**File:** `examples/03-advanced/performance/01_benchmarking.py`

**What it demonstrates:**
- Latency measurement
- Throughput testing
- Adapter comparison
- Bottleneck identification

**Benchmark results:**

| Adapter | Store Latency | Recall Latency | Throughput |
|---------|--------------|----------------|------------|
| InMemory | 0.1-1ms | 0.5-2ms | 50K+ ops/sec |
| Redis | 5-20ms | 10-30ms | 10K+ ops/sec |
| ChromaDB | 20-100ms | 50-150ms | 5K+ ops/sec |
| Qdrant | 20-100ms | 30-120ms | 5K+ ops/sec |
| Pinecone | 50-150ms | 100-200ms | 2K-5K ops/sec |

---

### 02_optimization.py

**Performance optimization** - Optimize for production.

**File:** `examples/03-advanced/performance/02_optimization.py`

**What it demonstrates:**
- Batch operations
- Connection pooling
- Caching strategies
- Async concurrency
- Query optimization

**Optimization techniques:**

```python
# 1. Batch operations
entries = [entry1, entry2, entry3]
ids = await adapter.bulk_save(entries)

# 2. Connection pooling
config = {
    "url": "redis://localhost:6379",
    "max_connections": 50  # Connection pool
}

# 3. Embedding caching
@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return embedder.embed(text)

# 4. Async concurrency
results = await asyncio.gather(
    memory.store("Data 1"),
    memory.store("Data 2"),
    memory.store("Data 3")
)
```

---

### 03_load_testing.py

**Load testing** - Stress test your system.

**File:** `examples/03-advanced/performance/03_load_testing.py`

**What it demonstrates:**
- Concurrent operations
- Sustained load
- Peak load handling
- Resource monitoring
- Failure scenarios

**Load test:**

```python
async def load_test(num_operations=1000, concurrency=10):
    tasks = []
    for i in range(num_operations):
        task = memory.store(f"Data {i}", importance=random.random())
        tasks.append(task)
        
        if len(tasks) >= concurrency:
            await asyncio.gather(*tasks)
            tasks = []
    
    if tasks:
        await asyncio.gather(*tasks)
```

---

## Summary

Advanced examples demonstrate:

**Audit & Privacy:**
- Complete audit trails
- PII detection
- Privacy-aware storage

**Transactions:**
- ACID guarantees
- Two-Phase Commit
- Isolation levels

**Compaction:**
- Count-based strategies
- Semantic clustering
- Importance-based removal

**Performance:**
- Benchmarking tools
- Optimization techniques
- Load testing

**Run All Advanced Examples:**

```bash
cd examples/03-advanced

# Audit & privacy
python audit-privacy/01_audit_logging.py
python audit-privacy/02_pii_detection.py
python audit-privacy/03_privacy_policies.py

# Transactions
python transactions/01_basic_transactions.py
python transactions/02_isolation_levels.py

# Compaction
python compaction/01_count_based.py
python compaction/02_semantic_compaction.py
python compaction/03_importance_compaction.py

# Performance
python performance/01_benchmarking.py
python performance/02_optimization.py
python performance/03_load_testing.py
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-puzzle:{ .lg .middle } **Integration Examples**

    ---

    LangChain and LlamaIndex integrations.

    [:octicons-arrow-right-24: Integration Examples](integrations.md)

-   :material-application:{ .lg .middle } **Real-World Examples**

    ---

    Complete applications and use cases.

    [:octicons-arrow-right-24: Real-World Examples](real-world.md)

-   :material-book-open-variant:{ .lg .middle } **Documentation**

    ---

    Deep dive into features.

    [:octicons-arrow-right-24: Advanced Features](../advanced/audit.md)

</div>
