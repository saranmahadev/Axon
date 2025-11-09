# Quick Start

Get started with Axon in under 5 minutes! This guide will walk you through the basics of storing, recalling, and managing memories.

---

## Your First Memory System

### Step 1: Install Axon

```bash
pip install axon
```

### Step 2: Create a Memory System

```python
import asyncio
from axon import MemorySystem
from axon.core.templates import balanced

# Create memory system with balanced configuration
system = MemorySystem(config=balanced())
```

### Step 3: Store Memories

```python
async def main():
    # Store a memory with importance score
    entry_id = await system.store(
        "User prefers dark mode for the UI",
        importance=0.8,
        tags=["preference", "ui"]
    )
    print(f"Stored memory: {entry_id}")

    # Store more memories
    await system.store(
        "Meeting scheduled for 3 PM tomorrow",
        importance=0.6,
        tags=["calendar", "todo"]
    )

    await system.store(
        "Temporary note: check email",
        importance=0.2,  # Low importance -> ephemeral tier
        tags=["temporary"]
    )

# Run the async function
asyncio.run(main())
```

### Step 4: Recall Memories

```python
async def recall_example():
    # Semantic search across all tiers
    results = await system.recall(
        "What are the user's UI preferences?",
        k=5  # Return top 5 results
    )

    for entry in results:
        print(f"Score: {entry.metadata.importance:.2f}")
        print(f"Text: {entry.text}")
        print(f"Tags: {entry.metadata.tags}")
        print("---")

asyncio.run(recall_example())
```

**Output**:

```
Score: 0.80
Text: User prefers dark mode for the UI
Tags: ['preference', 'ui']
---
```

---

## Understanding Tiers

Axon automatically routes memories to different tiers based on importance:

```python
async def tier_example():
    # Low importance -> Ephemeral tier (short-lived)
    await system.store("Temporary calculation result: 42", importance=0.1)

    # Medium importance -> Session tier (session-scoped)
    await system.store("User browsing history page 5", importance=0.5)

    # High importance -> Persistent tier (long-term)
    await system.store("User's home address: 123 Main St", importance=0.9)

    # Check where memories are stored
    export = await system.export()
    for tier, entries in export.items():
        print(f"{tier}: {len(entries)} memories")

asyncio.run(tier_example())
```

**Output**:

```
ephemeral: 1 memories
session: 1 memories
persistent: 1 memories
```

---

## Working with Metadata

Add rich metadata to memories for better filtering and organization:

```python
async def metadata_example():
    from axon.models.base import PrivacyLevel

    await system.store(
        "Customer support ticket #1234 resolved",
        importance=0.7,
        metadata={
            "user_id": "user_123",
            "session_id": "sess_456",
            "ticket_id": "1234",
            "status": "resolved",
            "privacy_level": PrivacyLevel.INTERNAL
        },
        tags=["support", "ticket", "resolved"]
    )

    # Recall with metadata filter
    from axon.models import Filter

    filter_obj = Filter(
        user_id="user_123",
        tags=["support"]
    )

    results = await system.recall(
        "support tickets",
        k=10,
        filter=filter_obj
    )

    print(f"Found {len(results)} support tickets for user_123")

asyncio.run(metadata_example())
```

---

## Memory Lifecycle

### Forgetting Memories

Remove memories you no longer need:

```python
async def forget_example():
    # Store a temporary memory
    entry_id = await system.store("Temporary data", importance=0.3)

    # Forget by ID
    await system.forget(entry_id)
    print("Memory forgotten!")

    # Or forget by filter
    from axon.models import Filter

    filter_obj = Filter(tags=["temporary"])
    count = await system.forget(filter_obj)
    print(f"Forgot {count} temporary memories")

asyncio.run(forget_example())
```

### Compacting Memories

Summarize and compact memories to save space:

```python
async def compact_example():
    # Store many related memories
    for i in range(20):
        await system.store(
            f"Meeting note {i}: Discussed quarterly targets",
            importance=0.6,
            tags=["meeting"]
        )

    # Compact using count-based strategy
    result = await system.compact(
        tier="session",
        strategy="count",
        threshold=10,  # Compact when >10 entries
        dry_run=True   # Preview without executing
    )

    print(f"Would compact {len(result.entries_to_compact)} entries")
    print(f"Into {result.num_summaries} summaries")

asyncio.run(compact_example())
```

---

## Using Templates

Axon provides pre-configured templates for common use cases:

### Development Template

```python
from axon.core.templates import DEVELOPMENT_CONFIG

system = MemorySystem(config=DEVELOPMENT_CONFIG)
# - In-memory storage (no external dependencies)
# - Relaxed policies
# - No embeddings required
```

### Aggressive Caching

```python
from axon.core.templates import aggressive_caching

config = aggressive_caching()
system = MemorySystem(config=config)
# - Short TTLs for ephemeral data
# - Frequent compaction
# - Optimized for high-volume, low-retention
```

### Long-Term Retention

```python
from axon.core.templates import long_term_retention

config = long_term_retention()
system = MemorySystem(config=config)
# - Extended TTLs
# - Higher capacity limits
# - Optimized for knowledge retention
```

### Balanced (Recommended)

```python
from axon.core.templates import balanced

config = balanced()
system = MemorySystem(config=config)
# - Balanced TTLs and capacity
# - Moderate compaction
# - Good for most applications
```

---

## Adding Embeddings

For semantic search, add an embedder:

=== "OpenAI"

    ```python
    import os
    from axon import MemorySystem
    from axon.embedders import OpenAIEmbedder
    from axon.core.config import MemoryConfig
    from axon.core.policies import PersistentPolicy
    from axon.adapters import ChromaAdapter

    os.environ["OPENAI_API_KEY"] = "sk-..."

    config = MemoryConfig(
        tiers={
            "persistent": PersistentPolicy(
                backend="chromadb",
                embedder="openai"
            )
        }
    )

    embedder = OpenAIEmbedder(model="text-embedding-3-small")
    system = MemorySystem(config=config, embedder=embedder)

    # Now store and recall with embeddings
    await system.store("Quantum computing fundamentals")
    results = await system.recall("explain quantum mechanics", k=3)
    ```

=== "Sentence Transformers (Local)"

    ```python
    from axon.embedders import SentenceTransformerEmbedder

    embedder = SentenceTransformerEmbedder(
        model_name="all-MiniLM-L6-v2"  # Fast local model
    )

    system = MemorySystem(config=config, embedder=embedder)

    # Embedding happens automatically
    await system.store("Machine learning tutorial")
    ```

---

## Enabling Audit Logging

Track all operations for compliance:

```python
from axon.core import AuditLogger

# Create audit logger
audit_logger = AuditLogger(
    max_events=10000,
    enable_rotation=True
)

# Create system with audit logging
system = MemorySystem(
    config=balanced(),
    audit_logger=audit_logger
)

# All operations are automatically logged
await system.store("Sensitive data", importance=0.8)
await system.recall("sensitive", k=5)

# Export audit log
events = await system.export_audit_log()
print(f"Logged {len(events)} events")

# Filter by operation type
from axon.models.audit import OperationType

store_events = await system.export_audit_log(
    operation=OperationType.STORE
)
print(f"Stored {len(store_events)} items")
```

---

## Privacy & PII Detection

Automatically detect and classify sensitive information:

```python
# PII detection enabled by default
system = MemorySystem(config=balanced(), enable_pii_detection=True)

# Store text with PII
entry_id = await system.store(
    "Contact customer at john.doe@example.com or 555-1234"
)

# Retrieve and check privacy level
tier, entry = await system._get_entry_by_id(entry_id)

print(f"Privacy Level: {entry.metadata.privacy_level}")
# Output: Privacy Level: PrivacyLevel.INTERNAL

print(f"Detected PII: {entry.metadata.pii_detection.detected_types}")
# Output: Detected PII: {'email', 'phone'}
```

---

## Integration with LangChain

Use Axon as LangChain memory:

```python
from axon import MemorySystem
from axon.integrations.langchain import AxonChatMemory
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Create memory-backed chatbot
system = MemorySystem(config=balanced())
memory = AxonChatMemory(system=system)

llm = ChatOpenAI(model="gpt-4")
template = PromptTemplate(
    input_variables=["history", "input"],
    template="Conversation history:\n{history}\n\nHuman: {input}\nAI:"
)

chain = LLMChain(llm=llm, memory=memory, prompt=template)

# Chat with persistent memory
response = await chain.arun("Hello, my name is Alice")
# AI: Nice to meet you, Alice!

response = await chain.arun("What's my name?")
# AI: Your name is Alice!
```

---

## Integration with LlamaIndex

Use Axon as LlamaIndex vector store:

```python
from axon import MemorySystem
from axon.integrations.llamaindex import AxonVectorStore
from llama_index.core import VectorStoreIndex, Document

# Create vector store
system = MemorySystem(config=balanced())
vector_store = AxonVectorStore(system=system)

# Create index
documents = [
    Document(text="Paris is the capital of France"),
    Document(text="Berlin is the capital of Germany"),
]

index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# Query
query_engine = index.as_query_engine()
response = await query_engine.aquery("What is the capital of France?")
print(response)
# Output: Paris is the capital of France
```

---

## Complete Example

Here's a full example combining multiple features:

```python
import asyncio
from dotenv import load_dotenv
from axon import MemorySystem
from axon.core.templates import balanced
from axon.core import AuditLogger
from axon.models import Filter
from axon.models.base import PrivacyLevel

load_dotenv()

async def main():
    # Setup
    audit_logger = AuditLogger()
    system = MemorySystem(
        config=balanced(),
        audit_logger=audit_logger,
        enable_pii_detection=True
    )

    # Store memories
    print("Storing memories...")
    await system.store(
        "User John prefers email notifications",
        importance=0.8,
        metadata={"user_id": "john"},
        tags=["preference", "notifications"]
    )

    await system.store(
        "Meeting scheduled for tomorrow at 2 PM",
        importance=0.6,
        metadata={"user_id": "john"},
        tags=["calendar", "todo"]
    )

    # Recall
    print("\nRecalling memories...")
    results = await system.recall(
        "john's preferences",
        k=5,
        filter=Filter(tags=["preference"])
    )

    for entry in results:
        print(f"- {entry.text} (importance: {entry.metadata.importance})")

    # Export audit log
    print("\nAudit log:")
    events = await system.export_audit_log()
    print(f"Total events: {len(events)}")

    # Compact
    print("\nCompacting session tier...")
    result = await system.compact(tier="session", dry_run=True)
    print(f"Would compact {len(result.entries_to_compact)} entries")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Next Steps

<div class="grid cards" markdown>

-   :fontawesome-solid-book:{ .lg .middle } **Core Concepts**

    ---

    Deep dive into tiers, policies, and routing.

    [:octicons-arrow-right-24: Learn More](../concepts/overview.md)

-   :material-database:{ .lg .middle } **Storage Adapters**

    ---

    Configure Redis, ChromaDB, Qdrant, and more.

    [:octicons-arrow-right-24: Adapters](../adapters/overview.md)

-   :material-shield-check:{ .lg .middle } **Advanced Features**

    ---

    Explore audit logging, transactions, and privacy.

    [:octicons-arrow-right-24: Advanced](../advanced/audit.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation.

    [:octicons-arrow-right-24: API Docs](../api/memory-system.md)

</div>

---

## Common Patterns

### Session-Scoped Memories

```python
session_id = "sess_123"

await system.store(
    "User viewing product page",
    importance=0.4,
    metadata={"session_id": session_id}
)

# Recall session-specific memories
results = await system.recall(
    "session activity",
    filter=Filter(session_id=session_id)
)
```

### Time-Based Queries

```python
from datetime import datetime, timedelta

# Recall recent memories
one_hour_ago = datetime.utcnow() - timedelta(hours=1)

filter_obj = Filter(
    created_after=one_hour_ago
)

recent = await system.recall("activity", filter=filter_obj)
```

### Bulk Operations

```python
# Bulk store
entries = [
    "Memory 1",
    "Memory 2",
    "Memory 3"
]

ids = []
for text in entries:
    entry_id = await system.store(text, importance=0.5)
    ids.append(entry_id)

# Bulk forget
for entry_id in ids:
    await system.forget(entry_id)
```

---

## Tips & Best Practices

!!! tip "Importance Scores"
    - **0.0-0.3**: Ephemeral data (logs, temporary calculations)
    - **0.3-0.7**: Session data (browsing history, conversation context)
    - **0.7-1.0**: Critical data (user preferences, knowledge base)

!!! info "Tags"
    Use consistent tagging for better filtering:
    ```python
    tags=["category", "subcategory", "status"]
    ```

!!! warning "Embeddings"
    Only enable embeddings if you need semantic search. Text-only mode is faster and cheaper.

!!! success "Async All the Way"
    Always use `await` with Axon methods - they're all async!

---

## Troubleshooting

### No Results from Recall

**Problem**: `recall()` returns empty list

**Solution**: Check if embedder is configured for semantic search, or use text-only mode

### Slow Performance

**Problem**: Operations take too long

**Solution**: Use appropriate tier routing and consider Redis for ephemeral tier

### Memory Not Persisting

**Problem**: Memories disappear after restart

**Solution**: Ensure persistent tier uses a durable backend (ChromaDB, Qdrant, not in-memory)

---

Ready to build amazing LLM applications with Axon? Dive deeper into the [Core Concepts](../concepts/overview.md)!
