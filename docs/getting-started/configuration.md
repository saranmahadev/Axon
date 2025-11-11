# Configuration

Learn how to configure Axon for your specific use case, from simple in-memory setups to production-scale multi-tier architectures.

---

## Configuration Overview

Axon uses a **policy-based configuration system** where you define:

1. **Tier Policies**: Rules for ephemeral, session, and persistent tiers
2. **Storage Adapters**: Backend storage for each tier (Redis, ChromaDB, etc.)
3. **Lifecycle Rules**: TTLs, capacity limits, compaction strategies
4. **Routing Behavior**: Default tier, promotion, demotion

```python
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,  # 10 minutes
        max_entries=1000
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma",
        compaction_threshold=10000
    ),
    default_tier="session",
    enable_promotion=True
)
```

---

## Pre-Built Templates

Axon provides 6 pre-configured templates for common use cases.

### DEVELOPMENT_CONFIG

Perfect for local development and testing.

```python
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

memory = MemorySystem(DEVELOPMENT_CONFIG)
```

**Configuration:**

- **Ephemeral**: InMemory adapter, 60s TTL
- **Session**: InMemory adapter, 600s TTL, 100 entries
- **Persistent**: InMemory adapter, no TTL, 1000 entries
- **Default tier**: Session
- **Dependencies**: None (all in-memory)

**Use Cases:**

- ✓ Local development
- ✓ Unit testing
- ✓ CI/CD pipelines
- ✓ Quick prototyping

**Pros:** No external dependencies, fast startup  
**Cons:** Data lost on restart, no production use

---

### LIGHTWEIGHT_CONFIG

Minimal setup with Redis only.

```python
from axon.core.templates import LIGHTWEIGHT_CONFIG

memory = MemorySystem(LIGHTWEIGHT_CONFIG)
```

**Configuration:**

- **Session**: Redis adapter, 300s TTL, 500 entries, overflow to persistent
- **Persistent**: InMemory adapter, no TTL, 5000 entries
- **Default tier**: Session
- **Dependencies**: Redis server

**Use Cases:**

- ✓ Small applications
- ✓ Development with persistence simulation
- ✓ Microservices with temporary state

**Setup:**

```bash
# Install Redis client
pip install redis>=5.0.0

# Start Redis (Docker)
docker run -d -p 6379:6379 redis:latest
```

---

### STANDARD_CONFIG

Balanced setup for most applications.

```python
from axon.core.templates import STANDARD_CONFIG

memory = MemorySystem(STANDARD_CONFIG)
```

**Configuration:**

- **Ephemeral**: Redis adapter, 60s TTL
- **Session**: Redis adapter, 600s TTL, 1000 entries, overflow enabled
- **Persistent**: ChromaDB adapter, no TTL, 10K compaction threshold
- **Default tier**: Session
- **Promotion**: Enabled
- **Dependencies**: Redis, ChromaDB

**Use Cases:**

- ✓ Most web applications
- ✓ Chatbots and conversational AI
- ✓ Knowledge management systems
- ✓ RAG applications

**Setup:**

```bash
# Install dependencies
pip install "axon-sdk[all]"

# Start Redis
docker run -d -p 6379:6379 redis:latest

# ChromaDB runs embedded (no setup needed)
```

---

### PRODUCTION_CONFIG

High-scale production deployments.

```python
from axon.core.templates import PRODUCTION_CONFIG

memory = MemorySystem(PRODUCTION_CONFIG)
```

**Configuration:**

- **Ephemeral**: Redis adapter, 30s TTL
- **Session**: Redis adapter, 1800s TTL, 2000 entries, overflow enabled
- **Persistent**: Pinecone adapter, no TTL, 50K compaction threshold
- **Default tier**: Session
- **Promotion**: Enabled
- **Demotion**: Enabled
- **Archive**: S3 support
- **Dependencies**: Redis, Pinecone account

**Use Cases:**

- ✓ Production applications at scale
- ✓ Multi-tenant systems
- ✓ Distributed deployments
- ✓ Enterprise applications

**Setup:**

```bash
# Install dependencies
pip install "axon-sdk[all]"
pip install pinecone-client

# Start Redis
docker run -d -p 6379:6379 redis:latest

# Configure Pinecone
export PINECONE_API_KEY="your-api-key"
export PINECONE_ENVIRONMENT="us-east-1-aws"
```

---

### QDRANT_CONFIG

High-performance alternative to ChromaDB.

```python
from axon.core.templates import QDRANT_CONFIG

memory = MemorySystem(QDRANT_CONFIG)
```

**Configuration:**

- **Ephemeral**: Redis adapter, 60s TTL
- **Session**: Redis adapter, 900s TTL, 1500 entries, overflow enabled
- **Persistent**: Qdrant adapter, no TTL, 20K compaction threshold
- **Default tier**: Session
- **Promotion**: Enabled
- **Dependencies**: Redis, Qdrant

**Use Cases:**

- ✓ High-performance vector search
- ✓ Large-scale knowledge bases
- ✓ Real-time similarity search
- ✓ Self-hosted production deployments

**Setup:**

```bash
# Install dependencies
pip install qdrant-client>=1.6.0

# Start Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant:latest

# Or use Qdrant Cloud (managed)
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
```

---

### MINIMAL_CONFIG

Single persistent tier only.

```python
from axon.core.templates import MINIMAL_CONFIG

memory = MemorySystem(MINIMAL_CONFIG)
```

**Configuration:**

- **Persistent**: ChromaDB adapter only
- **Default tier**: Persistent
- **Dependencies**: ChromaDB

**Use Cases:**

- ✓ Simplest possible setup
- ✓ Knowledge bases only
- ✓ No need for caching layers

---

## Template Comparison

| Template | Tiers | Primary Storage | Use Case | Complexity |
|----------|-------|----------------|----------|------------|
| **DEVELOPMENT** | 3 | InMemory | Development/Testing | ⭐ Minimal |
| **LIGHTWEIGHT** | 2 | Redis + InMemory | Small apps | ⭐⭐ Low |
| **STANDARD** | 3 | Redis + ChromaDB | Most applications | ⭐⭐⭐ Medium |
| **PRODUCTION** | 3 | Redis + Pinecone | Large scale | ⭐⭐⭐⭐ High |
| **QDRANT** | 3 | Redis + Qdrant | High performance | ⭐⭐⭐ Medium |
| **MINIMAL** | 1 | ChromaDB | Simplest setup | ⭐ Minimal |

---

## Custom Configuration

Create your own configuration from scratch.

### Basic Custom Config

```python
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,
        max_entries=1000
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma"
    ),
    default_tier="session"
)

memory = MemorySystem(config)
```

### Full Custom Config

```python
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

config = MemoryConfig(
    # Ephemeral tier - very short-lived
    ephemeral=EphemeralPolicy(
        adapter_type="redis",
        ttl_seconds=30  # 30 seconds
    ),
    
    # Session tier - medium-lived
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800,  # 30 minutes
        max_entries=2000,
        overflow_to_persistent=True,
        enable_vector_search=False
    ),
    
    # Persistent tier - long-lived
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        ttl_seconds=None,  # Never expire
        compaction_threshold=15000,
        compaction_strategy="importance",
        enable_vector_search=True
    ),
    
    # Routing behavior
    default_tier="session",
    enable_promotion=True,
    enable_demotion=False
)

memory = MemorySystem(config)
```

---

## Policy Types

### EphemeralPolicy

Short-lived memories (seconds to minutes).

```python
from axon.core.policies import EphemeralPolicy

ephemeral = EphemeralPolicy(
    adapter_type="redis",  # or "memory"
    ttl_seconds=60         # 5s to 3600s (1 hour max)
)
```

**Constraints:**

- ✓ Adapter: Only `redis` or `memory`
- ✓ TTL: 5 seconds to 1 hour
- ✗ Vector search: Disabled (not needed for short-lived)
- ✗ Eviction: Always TTL-based

**Use Cases:**

- Rate limiting tokens
- OTP codes
- Temporary feature flags
- Recent activity tracking
- Short-term cache

---

### SessionPolicy

Session-scoped memories (minutes to hours).

```python
from axon.core.policies import SessionPolicy

session = SessionPolicy(
    adapter_type="redis",              # redis, memory, chroma, qdrant, pinecone
    ttl_seconds=1800,                  # ≥60s or None
    max_entries=1000,                  # ≥10 or None
    overflow_to_persistent=True,       # Auto-promote when full
    enable_vector_search=True          # If adapter supports it
)
```

**Constraints:**

- ✓ Adapter: Any adapter type
- ✓ TTL: ≥60 seconds (or None)
- ✓ Vector search: Optional (adapter-dependent)
- ✓ Overflow: Can promote to persistent

**Use Cases:**

- Conversation history
- Active workspace state
- Recent user interactions
- Shopping cart data
- Session-specific preferences

---

### PersistentPolicy

Long-term memories (indefinite).

```python
from axon.core.policies import PersistentPolicy

persistent = PersistentPolicy(
    adapter_type="chroma",                    # chroma, qdrant, pinecone, memory
    ttl_seconds=None,                         # Usually None (no expiration)
    compaction_threshold=10000,               # ≥100 or None
    compaction_strategy="importance",         # count, semantic, importance, time
    enable_vector_search=True,                # Always True (required)
    archive_adapter=None                      # Optional: s3, gcs
)
```

**Constraints:**

- ✓ Adapter: Vector-capable (chroma, qdrant, pinecone) or memory (testing)
- ✓ TTL: None or very long (days/months)
- ✓ Vector search: Always enabled
- ✓ Compaction: Optional but recommended

**Use Cases:**

- Long-term knowledge base
- User history and preferences
- Learned facts and insights
- Important conversations
- Permanent records

---

## Adapter Configuration

### InMemory Adapter

```python
from axon.core.policies import PersistentPolicy

policy = PersistentPolicy(adapter_type="memory")
```

**When to use:**

- ✓ Development and testing
- ✓ CI/CD pipelines
- ✓ Unit tests
- ✗ Production (data lost on restart)

**No additional configuration needed.**

---

### Redis Adapter

```python
from axon.core.policies import SessionPolicy

policy = SessionPolicy(
    adapter_type="redis",
    ttl_seconds=600
)
```

**When to use:**

- ✓ Ephemeral tier (fast cache)
- ✓ Session tier (distributed sessions)
- ✓ Multi-process/multi-server deployments
- ✗ Long-term storage (no vector search)

**Configuration** (via environment or adapter-specific):

```python
# Default connection (localhost:6379)
# Or configure via environment:
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=your-password
```

---

### ChromaDB Adapter

```python
from axon.core.policies import PersistentPolicy

policy = PersistentPolicy(
    adapter_type="chroma",
    compaction_threshold=10000
)
```

**When to use:**

- ✓ Persistent tier with vector search
- ✓ Local deployments
- ✓ Development with persistence
- ✓ Small to medium datasets (<1M vectors)

**Features:**

- Embedded (no separate server)
- SQLite-backed persistence
- Good for single-machine deployments

---

### Qdrant Adapter

```python
from axon.core.policies import PersistentPolicy

policy = PersistentPolicy(
    adapter_type="qdrant",
    compaction_threshold=20000
)
```

**When to use:**

- ✓ High-performance vector search
- ✓ Large-scale deployments
- ✓ Production environments
- ✓ Self-hosted or cloud

**Configuration:**

```bash
# Local Qdrant
export QDRANT_URL="http://localhost:6333"

# Qdrant Cloud
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
```

---

### Pinecone Adapter

```python
from axon.core.policies import PersistentPolicy

policy = PersistentPolicy(
    adapter_type="pinecone",
    compaction_threshold=50000
)
```

**When to use:**

- ✓ Production at scale
- ✓ Managed infrastructure
- ✓ Global distribution
- ✓ Enterprise deployments

**Configuration:**

```bash
export PINECONE_API_KEY="your-api-key"
export PINECONE_ENVIRONMENT="us-east-1-aws"
```

---

## Configuration Options

### Default Tier

```python
config = MemoryConfig(
    session=SessionPolicy(...),
    persistent=PersistentPolicy(...),
    default_tier="session"  # or "ephemeral", "persistent"
)
```

The default tier is used when:

- No tier is specified in `store()`
- Importance score is exactly 0.5
- No explicit routing rules apply

---

### Tier Promotion

```python
config = MemoryConfig(
    session=SessionPolicy(...),
    persistent=PersistentPolicy(...),
    enable_promotion=True  # Auto-promote important memories
)
```

**When promotion happens:**

- Memory accessed frequently
- Importance score increases over time
- Session tier overflow (if configured)

**Example:**

```python
# Stored in session tier (importance=0.5)
await memory.store("User viewed pricing page", importance=0.5)

# After 10 accesses, promoted to persistent tier
for _ in range(10):
    await memory.recall("pricing", k=1)
```

---

### Tier Demotion

```python
config = MemoryConfig(
    ephemeral=EphemeralPolicy(...),
    session=SessionPolicy(...),
    enable_demotion=True  # Auto-demote stale memories
)
```

**When demotion happens:**

- Memory not accessed for long time
- Importance score decreases
- Tier is near capacity

**Not commonly used** - let TTL handle expiration instead.

---

## Compaction Strategies

### Count-Based

```python
persistent = PersistentPolicy(
    compaction_strategy="count",
    compaction_threshold=10000
)
```

Compact when tier reaches threshold. Groups entries by batch size.

**Best for:** General use, simple strategy

---

### Importance-Based

```python
persistent = PersistentPolicy(
    compaction_strategy="importance",
    compaction_threshold=10000
)
```

Compact low-importance entries first, preserve high-importance.

**Best for:** Preserving valuable data

---

### Semantic-Based

```python
persistent = PersistentPolicy(
    compaction_strategy="semantic",
    compaction_threshold=10000
)
```

Group similar content together for summarization.

**Best for:** Knowledge bases, content aggregation

---

### Time-Based

```python
persistent = PersistentPolicy(
    compaction_strategy="time",
    compaction_threshold=10000
)
```

Compact oldest entries first.

**Best for:** Time-series data, chronological records

---

## Best Practices

### 1. Match Adapters to Tiers

```python
# ✓ Good
ephemeral = EphemeralPolicy(adapter_type="redis")    # Fast cache
session = SessionPolicy(adapter_type="redis")        # Distributed sessions
persistent = PersistentPolicy(adapter_type="chroma") # Vector search

# ✗ Avoid
ephemeral = EphemeralPolicy(adapter_type="memory")   # OK for dev only
persistent = PersistentPolicy(adapter_type="redis")  # No vector search!
```

### 2. Set Appropriate TTLs

```python
# ✓ Good
ephemeral: 30-60 seconds
session: 600-1800 seconds (10-30 minutes)
persistent: None (no expiration)

# ✗ Avoid
ephemeral: 3600 seconds (use session instead)
session: 30 seconds (use ephemeral instead)
persistent: 300 seconds (defeats purpose)
```

### 3. Configure Overflow

```python
# ✓ Good - Prevent data loss
session = SessionPolicy(
    max_entries=1000,
    overflow_to_persistent=True  # Promote when full
)

# ⚠️ Risky - May lose data
session = SessionPolicy(
    max_entries=1000,
    overflow_to_persistent=False  # Drops old entries
)
```

### 4. Use Promotion Wisely

```python
# ✓ Good for user data
config = MemoryConfig(
    enable_promotion=True  # Preserve frequently accessed
)

# ✓ Good for temporary data
config = MemoryConfig(
    enable_promotion=False  # Let TTL handle cleanup
)
```

---

## Configuration Validation

Axon validates your configuration at startup:

```python
# ❌ This will fail
config = MemoryConfig(
    default_tier="session"  # Session tier not configured!
)
# ValueError: default_tier is 'session' but session policy is not configured

# ✓ This is valid
config = MemoryConfig(
    session=SessionPolicy(adapter_type="redis"),
    persistent=PersistentPolicy(adapter_type="chroma"),
    default_tier="session"  # Session tier exists
)
```

**Common validation errors:**

- Default tier not configured
- Promotion enabled without higher tier
- Invalid TTL ranges
- Incompatible adapter for tier

---

## Environment Variables

Configure adapters via environment:

```bash
# Redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your-password

# Qdrant
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-api-key

# Pinecone
export PINECONE_API_KEY=your-api-key
export PINECONE_ENVIRONMENT=us-east-1-aws

# OpenAI (for embeddings/compaction)
export OPENAI_API_KEY=sk-...
```

Load in code:

```python
from dotenv import load_dotenv
load_dotenv()

memory = MemorySystem(PRODUCTION_CONFIG)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-layers:{ .lg .middle } **Core Concepts**

    ---

    Deep dive into tiers, policies, and routing behavior.

    [:octicons-arrow-right-24: Learn More](../concepts/overview.md)

-   :material-database:{ .lg .middle } **Storage Adapters**

    ---

    Detailed guides for each storage backend.

    [:octicons-arrow-right-24: Adapter Guide](../adapters/overview.md)

-   :material-code-braces:{ .lg .middle } **Examples**

    ---

    See configuration in action with 45+ examples.

    [:octicons-arrow-right-24: Browse Examples](../examples/basic.md)

-   :material-cog-play:{ .lg .middle } **Advanced Features**

    ---

    Audit logging, transactions, compaction, and more.

    [:octicons-arrow-right-24: Advanced](../advanced/audit.md)

</div>
