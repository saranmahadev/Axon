# Transactions

Atomic operations across multiple storage tiers using Two-Phase Commit (2PC).

---

## Overview

The **Transaction System** provides atomic guarantees for operations spanning multiple storage tiers. Using the Two-Phase Commit (2PC) protocol, you can ensure that either all operations succeed or all are rolled back.

**Key Features:**
- ✓ Two-Phase Commit (2PC) protocol
- ✓ Atomic operations across tiers
- ✓ Automatic rollback on failure
- ✓ Context manager for easy use
- ✓ Isolation level support
- ✓ Timeout protection

---

## Why Transactions?

### Without Transactions

```python
# ❌ Risk: Partial failure leaves inconsistent state
await memory.store("Important data", tier="ephemeral")    # Success
await memory.store("Important data", tier="session")      # Success  
await memory.store("Important data", tier="persistent")   # FAILS!

# Result: Data in ephemeral and session, but not persistent
# State is inconsistent!
```

### With Transactions

```python
# ✓ All-or-nothing guarantee
async with memory.transaction() as txn:
    await txn.store("Important data", tier="ephemeral")
    await txn.store("Important data", tier="session")
    await txn.store("Important data", tier="persistent")
    # If any fails, ALL are rolled back
```

---

## Basic Usage

### Context Manager (Recommended)

```python
from axon import MemorySystem

memory = MemorySystem(config)

# Transactional store
async with memory.transaction() as txn:
    await txn.store("Entry 1", tier="ephemeral")
    await txn.store("Entry 2", tier="persistent")
    # Commits automatically on exit
    # Rolls back on exception
```

### Manual Transaction Control

```python
# Begin transaction
txn_id = await memory.begin_transaction()

try:
    # Add operations
    await memory.store("Entry 1", tier="ephemeral", transaction_id=txn_id)
    await memory.store("Entry 2", tier="persistent", transaction_id=txn_id)
    
    # Commit
    success = await memory.commit_transaction(txn_id)
    if not success:
        raise RuntimeError("Transaction commit failed")
        
except Exception as e:
    # Rollback on error
    await memory.abort_transaction(txn_id)
    raise
```

---

## Two-Phase Commit Protocol

### Phase 1: Prepare

All participants (adapters) prepare to commit:

```python
# 1. Coordinator asks: "Can you commit?"
prepare_success = await adapter.prepare_transaction(txn_id)

# Each adapter:
# - Validates all operations
# - Reserves resources
# - Writes to transaction log
# - Responds: YES or NO
```

### Phase 2: Commit/Abort

Based on Phase 1 responses:

```python
if all(prepare_responses):
    # All said YES → commit all
    for adapter in adapters:
        await adapter.commit_transaction(txn_id)
else:
    # Any said NO → abort all
    for adapter in adapters:
        await adapter.abort_transaction(txn_id)
```

---

## Isolation Levels

### Available Levels

```python
from axon.core.transaction import IsolationLevel

# Four standard isolation levels
IsolationLevel.READ_UNCOMMITTED  # Lowest isolation (fast, risky)
IsolationLevel.READ_COMMITTED    # Default (balanced)
IsolationLevel.REPEATABLE_READ   # Higher consistency
IsolationLevel.SERIALIZABLE      # Highest isolation (slow, safe)
```

### Configure Isolation

```python
from axon.core.transaction import TransactionCoordinator

coordinator = TransactionCoordinator(
    adapters=adapters,
    isolation_level=IsolationLevel.READ_COMMITTED,
    timeout_seconds=30.0
)

memory = MemorySystem(config, transaction_coordinator=coordinator)
```

---

## Operations

### Store Operations

```python
async with memory.transaction() as txn:
    # Store across multiple tiers atomically
    id1 = await txn.store("Entry 1", tier="ephemeral", importance=0.5)
    id2 = await txn.store("Entry 2", tier="session", importance=0.7)
    id3 = await txn.store("Entry 3", tier="persistent", importance=0.9)
    
    # All three succeed or all three fail
```

### Update Operations

```python
async with memory.transaction() as txn:
    # Update multiple entries atomically
    entry1 = await memory.get("entry_1")
    entry1.metadata.importance = 0.9
    await txn.update(entry1, tier="persistent")
    
    entry2 = await memory.get("entry_2")
    entry2.metadata.tags.append("verified")
    await txn.update(entry2, tier="persistent")
```

### Delete Operations

```python
async with memory.transaction() as txn:
    # Delete from multiple tiers atomically
    await txn.forget("entry_1", tier="ephemeral")
    await txn.forget("entry_1", tier="session")
    await txn.forget("entry_1", tier="persistent")
    
    # Entry deleted from all tiers or none
```

---

## Error Handling

### Automatic Rollback

```python
async with memory.transaction() as txn:
    await txn.store("Entry 1", tier="ephemeral")
    await txn.store("Entry 2", tier="persistent")
    
    # Simulated error
    if some_condition:
        raise ValueError("Validation failed")
    
    # Transaction automatically rolls back
    # Neither entry is saved
```

### Explicit Abort

```python
txn_id = await memory.begin_transaction()

try:
    await memory.store("Entry 1", tier="ephemeral", transaction_id=txn_id)
    
    # Check business logic
    if not business_logic_valid():
        # Explicit abort
        await memory.abort_transaction(txn_id)
        return
    
    await memory.store("Entry 2", tier="persistent", transaction_id=txn_id)
    await memory.commit_transaction(txn_id)
    
except Exception as e:
    await memory.abort_transaction(txn_id)
    raise
```

---

## Examples

### Cross-Tier Consistency

```python
async def store_with_consistency(memory, text: str):
    """Store in multiple tiers with consistency guarantee."""
    
    async with memory.transaction() as txn:
        # Store in ephemeral for fast access
        await txn.store(
            text,
            tier="ephemeral",
            importance=0.5,
            tags=["recent"]
        )
        
        # Store in persistent for durability
        await txn.store(
            text,
            tier="persistent",
            importance=0.8,
            tags=["important", "verified"]
        )
        
        # Both succeed or both fail
        # No partial state
```

### Batch Updates

```python
async def update_importance_batch(memory, entry_ids: list[str], new_importance: float):
    """Update importance for multiple entries atomically."""
    
    async with memory.transaction() as txn:
        for entry_id in entry_ids:
            entry = await memory.get(entry_id)
            entry.metadata.importance = new_importance
            await txn.update(entry, tier="persistent")
        
        # All updates succeed or all fail
```

### Data Migration

```python
async def migrate_tier(memory, from_tier: str, to_tier: str):
    """Migrate all entries from one tier to another atomically."""
    
    # Get all entries from source tier
    entries = await memory.export(tier=from_tier)
    
    async with memory.transaction() as txn:
        # Copy to destination tier
        for entry in entries:
            await txn.store(
                entry.text,
                tier=to_tier,
                importance=entry.metadata.importance,
                tags=entry.metadata.tags
            )
        
        # Delete from source tier
        for entry in entries:
            await txn.forget(entry.id, tier=from_tier)
        
        # Migration is atomic: all succeed or all fail
```

---

## Performance

### Overhead

| Aspect | Cost | Notes |
|--------|------|-------|
| **Latency** | +50-200ms | 2PC coordination overhead |
| **Throughput** | -30-50% | Sequential prepare + commit |
| **Memory** | +1KB per txn | Transaction state tracking |

### Optimization Tips

```python
# 1. Batch operations in single transaction
async with memory.transaction() as txn:
    for entry in entries:  # Batch in one txn
        await txn.store(entry)

# vs multiple single-entry transactions (slower)
for entry in entries:
    async with memory.transaction() as txn:
        await txn.store(entry)

# 2. Use lower isolation levels for better performance
coordinator = TransactionCoordinator(
    isolation_level=IsolationLevel.READ_COMMITTED  # Faster than SERIALIZABLE
)

# 3. Set appropriate timeouts
coordinator = TransactionCoordinator(
    timeout_seconds=10.0  # Fail fast on slow operations
)
```

---

## Best Practices

### 1. Use for Critical Operations Only

```python
# ✓ Good: Critical multi-tier operation
async with memory.transaction() as txn:
    await txn.store("Payment record", tier="persistent")
    await txn.store("Audit log", tier="session")

# ✗ Bad: Single-tier, non-critical operation
async with memory.transaction() as txn:
    await txn.store("Temp cache", tier="ephemeral")  # Overkill!
```

### 2. Keep Transactions Short

```python
# ✓ Good: Quick transaction
async with memory.transaction() as txn:
    await txn.store("Entry 1")
    await txn.store("Entry 2")

# ✗ Bad: Long-running transaction
async with memory.transaction() as txn:
    for i in range(10000):  # Too many operations!
        await txn.store(f"Entry {i}")
    # Holds locks too long
```

### 3. Handle Errors Explicitly

```python
try:
    async with memory.transaction() as txn:
        await txn.store("Critical data")
except Exception as e:
    logger.error(f"Transaction failed: {e}")
    # Notify user/admin
    # Retry with exponential backoff
    # Or fail gracefully
```

---

## Adapter Support

### Check Support

```python
# Check if adapter supports transactions
supports_txn = await adapter.supports_transactions()

if supports_txn:
    # Use transactional operations
    async with memory.transaction() as txn:
        await txn.store("data")
else:
    # Fallback to non-transactional
    await memory.store("data")
```

### Adapter Implementation

| Adapter | Transaction Support | Notes |
|---------|---------------------|-------|
| **InMemory** | ❌ No | Not needed (single-process) |
| **Redis** | ✅ Yes | MULTI/EXEC |
| **ChromaDB** | ❌ No | No transaction support |
| **Qdrant** | ❌ No | No transaction support |
| **Pinecone** | ❌ No | No transaction support |

---

## Limitations

### 1. Performance Overhead

2PC adds latency due to coordination:
- Prepare phase: N adapter calls
- Commit phase: N adapter calls
- Total: 2N round trips

### 2. Adapter Support Required

Not all adapters support transactions:
- Vector databases often don't support 2PC
- Fallback to best-effort consistency

### 3. Distributed Failures

Edge cases in distributed systems:
- Network partitions
- Coordinator crashes
- Participant timeouts

**Mitigation:**
- Use timeouts
- Implement transaction recovery
- Monitor transaction failures

---

## Next Steps

<div class="grid cards" markdown>

-   :material-clipboard-text:{ .lg .middle } **Audit Logging**

    ---

    Audit transaction operations.

    [:octicons-arrow-right-24: Audit Guide](audit.md)

-   :material-package-variant:{ .lg .middle } **Compaction**

    ---

    Compact entries with consistency.

    [:octicons-arrow-right-24: Compaction Guide](compaction.md)

-   :material-server:{ .lg .middle } **Production Deployment**

    ---

    Deploy with transactions enabled.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
