# Compaction Strategies

Intelligent memory management through advanced compaction strategies.

---

## Overview

**Compaction** is the process of reducing memory storage by summarizing or merging related entries. Axon provides multiple compaction strategies to intelligently manage memory lifecycle based on your application's needs.

**Key Features:**
- ✓ Multiple compaction strategies
- ✓ Semantic similarity grouping
- ✓ Importance-based prioritization
- ✓ Time-based aging
- ✓ Hybrid approaches
- ✓ Customizable thresholds

---

## Why Compaction?

### The Problem

```python
# Memory grows unbounded
for i in range(100000):
    await memory.store(f"Entry {i}")

# Eventually: OutOfMemory or slow queries
```

### The Solution

```python
# Automatic compaction keeps memory manageable
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_threshold=10000,    # Compact when > 10K entries
        compaction_strategy="semantic"  # Group similar entries
    )
)

# System automatically compacts
# 100K entries → 10K summaries
# Storage reduced 10x, key information preserved
```

---

## Compaction Strategies

### 1. Semantic Compaction

Groups semantically similar entries:

```python
from axon.core.compaction_strategies import SemanticCompactionStrategy

strategy = SemanticCompactionStrategy(
    similarity_threshold=0.85,  # 85% similarity to group
    min_cluster_size=2          # Min 2 entries per cluster
)

# Groups similar entries into clusters
# Example: All entries about "Python programming" → 1 summary
```

**Best For:**
- Reducing redundancy
- Knowledge bases with similar content
- Long-term memory consolidation

**Example:**
```python
# Before compaction: 100 similar entries
entries = [
    "Python is a programming language",
    "Python is used for data science",
    "Python is great for beginners",
    # ... 97 more similar entries
]

# After compaction: 1 summary
summary = "Python is a versatile programming language widely used for data science, web development, and automation. It's beginner-friendly and has a rich ecosystem."
```

---

### 2. Importance Compaction

Prioritizes low-importance entries:

```python
from axon.core.compaction_strategies import ImportanceCompactionStrategy

strategy = ImportanceCompactionStrategy(
    importance_threshold=0.5  # Compact entries below 0.5 importance
)

# Selects low-importance entries first
# Preserves high-value memories
```

**Best For:**
- Preserving critical information
- User-prioritized memories
- Tiered storage systems

**Example:**
```python
# High importance (0.9) - KEPT
"Critical business decision: Approved $1M budget"

# Medium importance (0.5) - KEPT
"Team meeting notes from Q4 review"

# Low importance (0.2) - COMPACTED
"Coffee machine is on 3rd floor"
"Lunch menu for Tuesday"
```

---

### 3. Time-Based Compaction

Compacts older entries first:

```python
from axon.core.compaction_strategies import TimeBasedCompactionStrategy

strategy = TimeBasedCompactionStrategy(
    age_threshold_days=30  # Compact entries older than 30 days
)

# Prioritizes older entries
# Recent memories stay detailed
```

**Best For:**
- Recency-focused applications
- Conversation history
- Event logs

**Example:**
```python
# Recent (2 days old) - KEPT DETAILED
"User reported bug in payment flow"

# Old (60 days) - COMPACTED
"Daily standup notes from January" → "January standup summary"
```

---

### 4. Hybrid Compaction

Combines multiple strategies:

```python
from axon.core.compaction_strategies import HybridCompactionStrategy

strategy = HybridCompactionStrategy(
    strategies=[
        SemanticCompactionStrategy(similarity_threshold=0.85),
        ImportanceCompactionStrategy(importance_threshold=0.5),
        TimeBasedCompactionStrategy(age_threshold_days=30)
    ],
    weights=[0.4, 0.4, 0.2]  # 40% semantic, 40% importance, 20% time
)

# Best of all strategies combined
```

**Best For:**
- Production applications
- Balanced approach
- Complex memory management needs

---

## Configuration

### Policy-Level Configuration

```python
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy

config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        compaction_threshold=10000,      # Compact when > 10K entries
        compaction_batch_size=100,       # Summarize 100 entries at a time
        compaction_strategy="semantic"   # Use semantic clustering
    )
)
```

### Strategy-Specific Configuration

```python
# Semantic with custom parameters
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_strategy="semantic",
        compaction_config={
            "similarity_threshold": 0.90,  # Stricter similarity
            "min_cluster_size": 3          # Larger clusters
        }
    )
)

# Importance with custom threshold
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_strategy="importance",
        compaction_config={
            "importance_threshold": 0.6  # Higher threshold
        }
    )
)
```

---

## Manual Compaction

### Trigger Compaction

```python
# Manual compaction trigger
await memory.compact(tier="persistent")

# Or compact all tiers
await memory.compact_all()
```

### Scheduled Compaction

```python
import schedule
import asyncio

async def scheduled_compaction():
    """Run compaction daily at 2 AM."""
    await memory.compact(tier="persistent")
    print(f"Compaction complete at {datetime.now()}")

# Schedule daily
schedule.every().day.at("02:00").do(lambda: asyncio.create_task(scheduled_compaction()))
```

---

## Examples

### Semantic Compaction in Action

```python
from axon.core.compaction_strategies import SemanticCompactionStrategy

# Setup
strategy = SemanticCompactionStrategy(similarity_threshold=0.85)
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_threshold=1000,
        compaction_strategy=strategy
    )
)

memory = MemorySystem(config)

# Store related entries
await memory.store("Python is great for data science", importance=0.7)
await memory.store("Python has excellent data science libraries", importance=0.7)
await memory.store("NumPy and Pandas make Python ideal for data", importance=0.7)

# After threshold reached, these get compacted into:
# "Python is a popular language for data science, with powerful libraries like NumPy and Pandas."
```

### Importance-Based Preservation

```python
# High-importance entries are preserved
await memory.store("Quarterly revenue: $10M", importance=0.95)  # PRESERVED
await memory.store("Sales target: $12M", importance=0.90)       # PRESERVED

# Low-importance entries are compacted
for i in range(100):
    await memory.store(f"Daily log entry {i}", importance=0.3)  # COMPACTED

# After compaction:
# - 2 high-importance entries stay detailed
# - 100 low-importance → 1 summary: "Daily activity logs from Q1"
```

### Time-Based Memory Management

```python
# Recent entries (last 7 days) - high detail
recent_entries = [...]  # Kept as-is

# Older entries (30+ days) - compacted
old_entries = [...]  # Summarized by month

# Example output after compaction:
# "January 2025: 500 entries about project planning, team meetings, and code reviews"
```

---

## Monitoring Compaction

### Track Compaction Events

```python
# Compaction is logged to audit trail
audit_logger = AuditLogger()
memory = MemorySystem(config, audit_logger=audit_logger)

# After compaction
events = audit_logger.query_events(operation=OperationType.COMPACT)

for event in events:
    print(f"Compacted {len(event.entry_ids)} entries")
    print(f"Duration: {event.duration_ms}ms")
    print(f"Tier: {event.metadata['tier']}")
```

### Compaction Metrics

```python
# Get compaction statistics
stats = memory.get_compaction_stats(tier="persistent")

print(f"Total compactions: {stats['total_compactions']}")
print(f"Entries compacted: {stats['entries_compacted']}")
print(f"Space saved: {stats['space_saved_mb']}MB")
print(f"Average compression: {stats['avg_compression_ratio']}x")
```

---

## Performance

### Compaction Overhead

| Strategy | Selection Cost | Grouping Cost | Best For |
|----------|----------------|---------------|----------|
| **Semantic** | O(n) | O(n²) | < 10K entries |
| **Importance** | O(n log n) | O(n) | Any scale |
| **Time-Based** | O(n log n) | O(n) | Any scale |
| **Hybrid** | O(n log n) | O(n²) | Balanced |

### Optimization Tips

```python
# 1. Adjust batch size for your workload
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_batch_size=50  # Smaller batches = more frequent summarization
    )
)

# 2. Use background compaction
async def background_compaction():
    while True:
        await asyncio.sleep(3600)  # Every hour
        await memory.compact(tier="persistent")

# 3. Monitor and adjust thresholds
stats = memory.get_tier_stats("persistent")
if stats["entry_count"] > 20000:
    # Adjust threshold
    memory.update_policy(
        tier="persistent",
        compaction_threshold=15000
    )
```

---

## Best Practices

### 1. Choose the Right Strategy

```python
# ✓ Good: Match strategy to use case
# Knowledge base → Semantic
config = MemoryConfig(
    persistent=PersistentPolicy(compaction_strategy="semantic")
)

# User preferences → Importance
config = MemoryConfig(
    session=SessionPolicy(compaction_strategy="importance")
)

# Event logs → Time-based
config = MemoryConfig(
    ephemeral=EphemeralPolicy(compaction_strategy="time_based")
)
```

### 2. Set Appropriate Thresholds

```python
# ✓ Good: Based on actual usage
# Small app: 1K threshold
config = MemoryConfig(
    persistent=PersistentPolicy(compaction_threshold=1000)
)

# Large app: 100K threshold
config = MemoryConfig(
    persistent=PersistentPolicy(compaction_threshold=100000)
)
```

### 3. Monitor Compaction Quality

```python
# Check if compaction is preserving important information
before_count = len(await memory.export(tier="persistent"))
await memory.compact(tier="persistent")
after_count = len(await memory.export(tier="persistent"))

compression_ratio = before_count / after_count
print(f"Compression: {compression_ratio}x")

if compression_ratio > 100:
    logger.warning("Very high compression - may be losing information")
```

---

## Custom Strategies

### Implement Custom Strategy

```python
from axon.core.compaction_strategies import CompactionStrategy

class CustomCompactionStrategy(CompactionStrategy):
    """Custom strategy for domain-specific needs."""
    
    def select_entries_to_compact(
        self, 
        entries: list[MemoryEntry], 
        threshold: int,
        **kwargs
    ) -> list[MemoryEntry]:
        """Select entries based on custom logic."""
        # Your selection logic here
        # e.g., select entries with specific tags
        return [e for e in entries if "compact_me" in e.tags]
    
    def group_entries(
        self,
        entries: list[MemoryEntry],
        batch_size: int = 100,
        **kwargs
    ) -> list[list[MemoryEntry]]:
        """Group entries for summarization."""
        # Your grouping logic here
        # e.g., group by date ranges
        return self._group_by_month(entries)
    
    @property
    def name(self) -> str:
        return "custom"

# Use custom strategy
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_strategy=CustomCompactionStrategy()
    )
)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-file-document:{ .lg .middle } **Logging**

    ---

    Monitor compaction with structured logging.

    [:octicons-arrow-right-24: Logging Guide](logging.md)

-   :material-speedometer:{ .lg .middle } **Performance**

    ---

    Optimize compaction performance.

    [:octicons-arrow-right-24: Performance Guide](../deployment/performance.md)

-   :material-cloud:{ .lg .middle } **Adapters**

    ---

    Compaction support by adapter.

    [:octicons-arrow-right-24: Adapters Guide](../adapters/overview.md)

</div>
