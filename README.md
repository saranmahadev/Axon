# Memory SDK — Technical Specification & Module Architecture

**Purpose:**
This document defines the technical specification, module architecture, interfaces, data models, and example skeleton code for a unified Memory SDK that orchestrates ephemeral, session, persistent, and cache memory for LLM applications.

**Audience:** Platform engineers, SDK authors (Python/TypeScript), system architects, and technical PMs.

---

## 1. Executive summary

The Memory SDK provides a single programmable API that abstracts multiple memory tiers, lifecycle policies, summarization/compaction flows, auditability, and pluggable storage adapters. It exposes simple primitives (`store`, `recall`, `forget`, `compact`, `trace`) and a policy engine that routes and transforms data across tiers.

Key goals:

* Multi-tier memory (Ephemeral / Session / Persistent / Archive)
* Pluggable backends (in-memory, Redis, vector DBs, object stores)
* Policy-driven lifecycle and summarization
* Auditability and explainability
* Caching & deterministic response support
* Privacy and encryption hooks

---

## 2. High-level architecture

```
Application
   │
   ├─ Memory SDK (Router + Policy Engine)
   │    ├─ Interface Layer (Memory API)
   │    ├─ Policy Engine
   │    ├─ Storage Adapters
   │    ├─ Summarizer / Compactor
   │    ├─ Cache Layer
   │    └─ Audit / Observability
   │
   ├─ Backend Services (pluggable)
   │    ├─ Redis / Memcached
   │    ├─ Vector DBs (Qdrant/Pinecone/Chroma/Milvus/pgvector)
   │    ├─ SQL / NoSQL
   │    └─ Object Storage (S3)
   └─ LLM Providers
```

---

## 3. Core concepts and data model

### 3.1 MemoryEntry (canonical)

```json
{
  "id": "uuid",
  "type": "note | event | conversation_turn | profile | embedding_summary",
  "text": "raw text or blob",
  "embedding": "vector|null",
  "metadata": {
    "user_id": "string",
    "session_id": "string",
    "source": "app|system|agent",
    "created_at": "ISO8601",
    "last_accessed_at": "ISO8601",
    "tags": ["string"],
    "importance": 0.0-1.0,
    "privacy_level": "public|sensitive|private",
    "version": "embedder:2025-xx",
    "provenance": [{"action":"store","by":"module","ts":"ISO"}]
  }
}
```

Fields:

* `embedding` may be null for ephemeral text-only entries; the SDK will lazily embed on `store` or `recall` depending on policy.
* `metadata` supports arbitrary key/value pairs but enforces a set of reserved keys for policy and auditing.

### 3.2 MemoryTiers

* **Ephemeral**: in-memory or per-request ring buffer (short TTL)
* **Session**: session-scoped summaries and short-term vectors
* **Persistent**: vector-indexed semantic store for long-term recall
* **Archive**: cold storage for infrequent access (S3 + re-index later)

---

## 4. Public API (Python-first, TypeScript analogs follow)

### 4.1 Core classes and interfaces

```
class MemorySystem:
    def store(self, entry: MemoryEntry, tier: Optional[str]=None) -> str
    def recall(self, query: str, context: Optional[dict]=None, k: int=5) -> List[MemoryEntry]
    def forget(self, id: Optional[str]=None, filter: Optional[Filter]=None) -> bool
    def compact(self, policy: Optional[Policy]=None) -> CompactionReport
    def trace(self, recall_id: str) -> TraceReport
    def observe(self, callback: Callable[[Event], None]) -> None
    def export(self, filter: Optional[Filter]=None, format: str='json') -> bytes
    def sync(self) -> None
```

`Filter` is a declarative filter object (user_id, tags, date range, privacy_level).

### 4.2 Policy DSL (example)

```python
policy = Policy(
    tiers=[
        EphemeralPolicy(ttl_minutes=10, max_items=50),
        SessionPolicy(summarize_after=20),
        PersistentPolicy(backend='qdrant', embedder='openai/text-embedding-3-large', compact_after=500)
    ],
    summarizer=SummarizerConfig(model='gpt-4o-mini', max_tokens=256),
    eviction=EvictionConfig(strategy='lrucost', retention_days=365),
    privacy=PrivacyConfig(redact=['ssn','credit_card'], encrypt=True)
)
```

### 4.3 Example usage

```python
from memory_sdk import MemorySystem, MemoryEntry, Policy

mem = MemorySystem(policy=my_policy)

id = mem.store(MemoryEntry(text="User: I like sci-fi", metadata={"user_id":"u123"}))

results = mem.recall("favorite movie genre", context={"user_id":"u123"}, k=3)

mem.compact()

mem.forget(filter={"user_id":"u123","older_than_days":365})
```

---

## 5. Module breakdown and responsibilities

### 5.1 API Layer

* Exposes user-facing primitives.
* Validates input and maps to internal models.
* Adds request-level tracing IDs.

### 5.2 Router & Policy Engine

* Decides which tier to route `store` operations to.
* Determines lazy embedding behavior, summarization triggers, and re-routing between tiers.
* Policy evaluation uses a rules engine (simple first) or WASM-based sandbox for advanced rules.

### 5.3 Storage Adapters

* Implement `StorageAdapter` interface:

```python
class StorageAdapter:
    def save(self, entry: MemoryEntry) -> str
    def query(self, vector: List[float], k:int, filter: Optional[Filter]) -> List[MemoryEntry]
    def get(self, id: str) -> MemoryEntry
    def delete(self, id: str) -> bool
    def bulk_save(self, entries: List[MemoryEntry]) -> List[str]
    def reindex(self) -> None
```

* Provide implementations for: `InMemoryAdapter`, `RedisAdapter`, `VectorAdapter(QdrantAdapter, PineconeAdapter, ChromaAdapter)`, `SQLAdapter`, `S3Adapter` (for archived blobs).

### 5.4 Summarizer / Compactor

* Uses LLMs to summarize groups of entries into compact representations.
* Responsible for compaction policies (size-based, semantic-redundancy-based).
* Supports human-in-the-loop review hooks for summaries.

### 5.5 Cache Layer

* LLM response caching by a deterministic key (hash(prompt+context+model+policy_version)).
* Embedding cache keyed by (text + embedder_signature).
* TTL & version-aware invalidation.

### 5.6 Audit & Trace

* Log `store`, `recall`, `forget`, `compact` events with provenance.
* Provide `trace(recall_id)` that returns retrieval chain: which entries matched, scores, summaries used, timestamps.

### 5.7 Encryption & Privacy

* Pre-storage redaction hooks (PII detection), format-preserving encryption adapters.
* Provide `privacy.policy` enforcement: e.g., deny storage of sensitive data unless consented.

### 5.8 Observability

* Metrics: avg recall latency, recall relevance (optional human feedback), memory growth, summarization rate.
* Export Prometheus metrics and structured logs.

---

## 6. Storage adapters: details & tradeoffs

### 6.1 InMemoryAdapter

* Use: local dev, testing, ephemeral tier.
* Pros: fastest, zero infra.
* Cons: non-persistent.

### 6.2 RedisAdapter

* Use: ephemeral & caching tiers, small session stores.
* Pros: TTL, atomic ops.
* Cons: not ideal for large-scale vectors (unless Redis vector modules used).

### 6.3 VectorAdapter (Qdrant/Pinecone/Chroma/Milvus/pgvector)

* Use: persistent semantic recall.
* Responsibilities: vector indexing, metadata filtering, hybrid search.
* Tradeoffs: filtering APIs and feature parity differ across vendors — adapter normalizes them.

### 6.4 SQLAdapter

* Use: authoritative facts, ACLs, structured attributes.
* Complement vector store with authoritative values (e.g., email, account id).

### 6.5 S3Adapter

* Use: cold archive of raw conversation logs or attachments.
* Reindexing off cold storage is supported periodically.

---

## 7. Embeddings & Models

* The SDK must be model-agnostic; embedder and LLM provider are pluggable.
* Use `Embedder` interface:

```python
class Embedder:
    def embed(self, texts: List[str]) -> List[List[float]]
    def signature(self) -> str  # model name + version
```

* Maintain `embedder_signature` per MemoryEntry and re-embed with migration tools.

---

## 8. Summarization & Compaction strategies

* **Time-based:** summarize session after N minutes or M turns.
* **Count-based:** summarize after N entries.
* **Semantic redundancy:** cluster similar vectors and replace cluster with summary vector.
* **Importance-based:** keep high-importance items and compress low-importance ones.

Compaction output is stored as a new MemoryEntry with provenance linking to source IDs.

---

## 9. Traceability and Explainability

* Each recall returns `TraceReport` with:

  * query vector, matched IDs, similarity scores
  * pre/post summaries used
  * policy decisions (why a certain tier matched)
* Support for `why_forget(id)` explaining why an entry was evicted.

---

## 10. Consistency, concurrency & transactions

* For multi-writer environments (webscale), provide optimistic concurrency:

  * `store()` returns write token; `compact()` uses CAS to avoid conflicts.
* Bulk operations provide atomic semantics per adapter where available; otherwise eventual consistency is documented.

---

## 11. Security & compliance

* Support encrypted-at-rest and in-transit for all adapters.
* Provide PII detection & redaction before embedding (configurable).
* Provide GDPR-friendly export and delete APIs (right-to-be-forgotten hooks).

---

## 12. SDK design patterns & ergonomics

* **Fluent config** and `Policy` as declarative object.
* **Async-first API** (async/await) with sync wrappers for convenience.
* **Pluggable adapters** via registration and dependency injection.
* **Versioning**: memory schema and policy version used in cache keys to allow invalidation.

---

## 13. CLI, MemoryDaemon & SaaS considerations

* **CLI** for backup/export, reindex, re-embed, and compaction jobs.
* **MemoryDaemon**: a microservice to run heavy async jobs (compaction, re-embedding, migration).
* **SaaS** exposes HTTP API + Web UI for policies, analytics, and audit.

---

## 14. Testing and benchmarks

* Unit tests for adapters and policy engine.
* Integration tests with at least one vector DB and Redis.
* Benchmarks: recall latency, embedding throughput, compaction quality (human-rated), storage cost per 1M entries.
* Reproducible datasets and scenarios for regression testing.

---

## 15. Roadmap (MVP -> v1 -> v1.5)

**MVP (0.1)**

* MemorySystem API, InMemoryAdapter, simple VectorAdapter (Chroma), RedisAdapter, Embedder interface (OpenAI), basic Policy DSL, basic summarizer.

**v1.0**

* Qdrant & Pinecone adapters, SQLAdapter, S3Adapter, encryption adapter, audit+trace, CLI, async API.

**v1.5**

* Policy engine enhancements (WASM sandbox), memory graph support, compaction autoscaler, dashboard for analytics, SaaS offering.

---

## 16. Example module skeleton (Python)

```python
# memory_sdk/core.py
class MemorySystem:
    def __init__(self, policy: Policy, adapters: Dict[str,StorageAdapter], embedder: Embedder, summarizer: Summarizer, cache: Cache):
        ...

    async def store(self, entry: MemoryEntry, tier: Optional[str]=None):
        ...

    async def recall(self, query: str, context: dict=None, k:int=5):
        ...

    async def compact(self, policy:Policy=None):
        ...
```

```python
# memory_sdk/adapters/vector_adapter.py
class VectorAdapter(StorageAdapter):
    def __init__(self, client_cfg):
        ...
    def save(self, entry: MemoryEntry) -> str:
        # embed if necessary, push to index with metadata
```

---

## 17. API compatibility with LangChain / LlamaIndex

* Provide adapter plugins to let MemorySystem be consumed by LangChain `Memory` or LlamaIndex `DocumentStore` so adoption is frictionless.

---

## 18. Open questions & tradeoffs to decide early

* CLI vs Daemon responsibilities split.
* Which vector DBs to target first (Chroma for dev, Qdrant/Pinecone for prod).
* Default summarizer model and cost controls.
* Whether to provide hosted SaaS or focus on OSS-first model.

---

## 19. Next steps (implementation plan)

1. Define exact `MemoryEntry` JSON schema and reserved metadata keys.
2. Implement minimal Python SDK with InMemoryAdapter + ChromaAdapter + OpenAI embedder.
3. Implement Policy DSL and Router heuristics for tiering.
4. Add RedisAdapter and simple summarizer.
5. Build tests and a demo app (FastAPI + simple UI) showing per-user memory and recall tracing.

