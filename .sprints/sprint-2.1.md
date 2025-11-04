# Sprint 2.1: Multi-Provider Vector Storage (ChromaDB + Qdrant + Pinecone)

**Start Date:** 2025-11-04
**End Date:** 2025-11-08 (4 days)
**Status:** In Progress - Planning Complete

---

## Sprint Goal

Implement **3 production-ready vector database adapters** (ChromaDB, Qdrant, Pinecone) with unified API, enabling users to choose the best backend for their deployment model (embedded, self-hosted, or cloud-managed).

---

## Scope

### **Phase 1: ChromaDB Adapter (Day 1-2)**
- [ ] Task 1: Install `chromadb>=0.4.0` dependency
- [ ] Task 2: Create `src/axon/adapters/chroma.py` with ChromaAdapter
- [ ] Task 3: Implement all 6 StorageAdapter methods (save, query, get, delete, bulk_save, reindex)
- [ ] Task 4: Metadata serialization (Pydantic → ChromaDB dict)
- [ ] Task 5: Collection management utilities
- [ ] Task 6: Create `tests/unit/test_chroma_adapter.py` with 25+ tests
- [ ] Task 7: Integration test with all 4 embedders
- [ ] Task 8: Example demonstrating ChromaDB usage

### **Phase 2: Qdrant Adapter (Day 3)**
- [ ] Task 9: Install `qdrant-client>=1.7.0` dependency
- [ ] Task 10: Create `src/axon/adapters/qdrant.py` with QdrantAdapter
- [ ] Task 11: Implement all 6 StorageAdapter methods
- [ ] Task 12: Qdrant-specific metadata mapping
- [ ] Task 13: Collection management with Qdrant API
- [ ] Task 14: Create `tests/unit/test_qdrant_adapter.py` with 25+ tests
- [ ] Task 15: Docker Compose setup for local Qdrant
- [ ] Task 16: Integration test with all 4 embedders

### **Phase 3: Pinecone Adapter (Day 4)**
- [ ] Task 17: Install `pinecone-client>=3.0.0` dependency
- [ ] Task 18: Create `src/axon/adapters/pinecone.py` with PineconeAdapter
- [ ] Task 19: Implement all 6 StorageAdapter methods
- [ ] Task 20: Pinecone namespace and index management
- [ ] Task 21: Metadata conversion for Pinecone format
- [ ] Task 22: Create `tests/unit/test_pinecone_adapter.py` with 25+ tests
- [ ] Task 23: Integration test with all 4 embedders
- [ ] Task 24: Example showing adapter swapping

### **Final Integration**
- [ ] Task 25: Update `src/axon/adapters/__init__.py` with all 3 exports
- [ ] Task 26: Create comprehensive comparison example
- [ ] Task 27: Update sprint documentation
- [ ] Task 28: Performance benchmarks (optional)

---

## Deliverables

### **1. ChromaDB Adapter** (~350 lines)
- `src/axon/adapters/chroma.py`
- Embedded vector storage, persistent to disk
- Supports collections, metadata filtering
- No external dependencies (runs in-process)

### **2. Qdrant Adapter** (~350 lines)
- `src/axon/adapters/qdrant.py`
- Self-hosted vector storage (Docker/K8s)
- High-performance Rust backend
- Rich metadata filtering

### **3. Pinecone Adapter** (~300 lines)
- `src/axon/adapters/pinecone.py`
- Cloud-managed vector storage
- Zero-ops, auto-scaling
- Namespace-based multi-tenancy

### **4. Test Suites** (~750 lines total)
- `tests/unit/test_chroma_adapter.py` (25+ tests)
- `tests/unit/test_qdrant_adapter.py` (25+ tests)
- `tests/unit/test_pinecone_adapter.py` (25+ tests)

### **5. Docker Setup**
- `docker-compose.yml` for local testing
- Qdrant container configuration
- Optional: Local Pinecone alternative

### **6. Examples**
- Adapter comparison example
- Migration guide (switching adapters)
- Performance comparison

---

## Success Criteria

### **All 3 Adapters Must**:
- [ ] Implement all 6 StorageAdapter methods correctly
- [ ] Support embeddings from 384 to 3072 dimensions
- [ ] Handle metadata filtering (tags, user_id, importance, dates)
- [ ] Support bulk operations (batch save)
- [ ] Work with all 4 embedders (OpenAI, Voyage, SentenceTransformers, HuggingFace)
- [ ] Have >90% test coverage
- [ ] Pass >25 tests each
- [ ] Include error handling and edge cases

### **Adapter-Specific**:

**ChromaDB**:
- [ ] Persistent storage to disk
- [ ] Embedded mode (no server needed)
- [ ] Collection management (create, delete, clear)
- [ ] Survives process restart

**Qdrant**:
- [ ] Docker container connectivity
- [ ] Collection management via Qdrant API
- [ ] Payload (metadata) indexing
- [ ] Efficient batch operations

**Pinecone**:
- [ ] Cloud API integration
- [ ] Index management
- [ ] Namespace support
- [ ] Metadata filtering via Pinecone query syntax

### **Integration**:
- [ ] All 3 adapters interchangeable (same API)
- [ ] Example shows swapping adapters with <5 line changes
- [ ] Self-hosted testing verified (Qdrant via Docker)
- [ ] Performance benchmarks documented

---

## File Structure

```
src/axon/adapters/
├── __init__.py          # Export all 4 adapters
├── base.py              # ✅ StorageAdapter ABC
├── memory.py            # ✅ InMemoryAdapter
├── chroma.py            # 🆕 ChromaAdapter
├── qdrant.py            # 🆕 QdrantAdapter
└── pinecone.py          # 🆕 PineconeAdapter

tests/unit/
├── test_models.py       # ✅ Existing (29 tests)
├── test_adapters.py     # ✅ Existing (26 tests - InMemory)
├── test_embedders.py    # ✅ Existing (26 tests)
├── test_chroma_adapter.py   # 🆕 ChromaDB tests (25+ tests)
├── test_qdrant_adapter.py   # 🆕 Qdrant tests (25+ tests)
└── test_pinecone_adapter.py # 🆕 Pinecone tests (25+ tests)

examples/
├── embedder_examples.py      # ✅ Existing
├── vector_adapter_comparison.py  # 🆕 Compare all 3 adapters
└── adapter_migration.py      # 🆕 Switching adapters guide

docker/
└── docker-compose.yml   # 🆕 Qdrant + optional services
```

---

## Dependencies

### **New Packages**:
```toml
chromadb = "^1.3.0"          # Embedded vector DB (installed: v1.3.2)
qdrant-client = "^1.15.0"    # Qdrant Python client (installed: v1.15.1)
pinecone = "^7.0.0"          # Pinecone Python client (installed: v7.3.0)
```

### **Prerequisites Met**:
- ✅ StorageAdapter ABC (Sprint 1.2)
- ✅ MemoryEntry, Filter models (Sprint 1.1)
- ✅ All 4 embedders (Sprint 1.3)
- ✅ InMemoryAdapter reference (Sprint 1.2)

---

## Technical Design

### **Unified API Pattern**

```python
# All adapters implement the same interface:
class VectorAdapter(StorageAdapter):
    
    async def save(self, entry: MemoryEntry) -> str:
        """Store entry with vector indexing."""
        # 1. Extract embedding from entry
        # 2. Convert metadata to DB format
        # 3. Call DB-specific API
        # 4. Return entry ID
    
    async def query(
        self, 
        vector: list[float], 
        k: int = 5,
        filter: Filter | None = None
    ) -> list[MemoryEntry]:
        """Semantic search with metadata filtering."""
        # 1. Convert Filter to DB-specific format
        # 2. Execute similarity search
        # 3. Convert results back to MemoryEntry
        # 4. Return ordered by similarity
```

### **Metadata Conversion Strategy**

Each DB has different metadata requirements:

**ChromaDB**:
```python
# Flat dict, supports lists
metadata = {
    "user_id": entry.metadata.user_id,
    "tags": entry.metadata.tags,  # List supported
    "importance": entry.metadata.importance,
    "created_at": entry.metadata.created_at.isoformat(),
    "provenance": json.dumps([p.dict() for p in entry.metadata.provenance])
}
```

**Qdrant**:
```python
# Payload (nested dicts supported)
payload = {
    "text": entry.text,
    "metadata": {
        "user_id": entry.metadata.user_id,
        "tags": entry.metadata.tags,
        "importance": entry.metadata.importance,
        "created_at": entry.metadata.created_at.isoformat(),
        "provenance": [p.dict() for p in entry.metadata.provenance]
    }
}
```

**Pinecone**:
```python
# Flat metadata (no nested), lists as JSON strings
metadata = {
    "user_id": entry.metadata.user_id,
    "tags": ",".join(entry.metadata.tags),  # CSV string
    "importance": entry.metadata.importance,
    "created_at": entry.metadata.created_at.isoformat(),
    "text": entry.text,  # Store with metadata
}
```

### **Filter Translation**

```python
# Axon Filter
filter = Filter(
    tags=["python", "ai"],
    importance_range=(0.7, 1.0),
    user_id="user123"
)

# ChromaDB where clause
chroma_where = {
    "$and": [
        {"tags": {"$in": ["python", "ai"]}},
        {"importance": {"$gte": 0.7, "$lte": 1.0}},
        {"user_id": "user123"}
    ]
}

# Qdrant filter
qdrant_filter = Filter(
    must=[
        FieldCondition(key="metadata.tags", match=MatchAny(any=["python", "ai"])),
        FieldCondition(key="metadata.importance", range=Range(gte=0.7, lte=1.0)),
        FieldCondition(key="metadata.user_id", match=MatchValue(value="user123"))
    ]
)

# Pinecone filter (expression string)
pinecone_filter = {
    "user_id": {"$eq": "user123"},
    "importance": {"$gte": 0.7, "$lte": 1.0},
    # Tags require special handling (CSV check)
}
```

---

## Testing Strategy

### **Unit Tests (Per Adapter)**:
1. **Initialization** - Valid config, invalid config
2. **Save** - Single entry, with/without embedding
3. **Query** - Similarity search, with filter, empty results
4. **Get** - Existing ID, non-existent ID
5. **Delete** - Existing entry, non-existent entry
6. **Bulk Save** - Multiple entries, empty list
7. **Reindex** - Collection rebuild
8. **Metadata Filtering** - Tags, importance, dates, user_id
9. **Edge Cases** - Empty vectors, zero magnitude, unicode text
10. **Error Handling** - Connection errors, invalid data

### **Integration Tests (All Adapters)**:
1. **Multi-Embedder** - Test with all 4 embedders (different dimensions)
2. **Persistence** - Save, restart adapter, query (ChromaDB, Qdrant)
3. **Large Batch** - 1000+ entries, performance check
4. **Adapter Swapping** - Save with Chroma, query with Qdrant (same data)

### **Self-Hosted Testing**:
- Qdrant: Docker container on localhost:6333
- ChromaDB: Embedded mode, persist to ./chroma_test_db
- Pinecone: Either mock or use free tier index

---

## Docker Setup for Testing

### **docker-compose.yml**:
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

**Usage**:
```bash
# Start Qdrant
docker-compose up -d

# Run tests
pytest tests/unit/test_qdrant_adapter.py -v

# Stop services
docker-compose down
```

---

## Estimated Complexity

**Overall: Medium-High** (4 days)

### **Per Adapter**:
- **ChromaDB**: Medium (14 hours)
  - Simple API, well-documented
  - Embedded mode is straightforward
  
- **Qdrant**: Medium (7 hours)
  - More complex filter syntax
  - Docker setup needed
  - 70% code reuse from ChromaDB
  
- **Pinecone**: Low-Medium (7 hours)
  - Simplest API of the three
  - Cloud-based, no local setup
  - 70% code reuse from ChromaDB

**Total**: ~28 hours = 3.5 days (with 0.5 day buffer)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Metadata conversion bugs | High | Extensive serialization tests |
| Filter translation errors | High | Test all filter combinations |
| Qdrant Docker issues | Medium | Provide docker-compose, clear docs |
| Pinecone API rate limits | Medium | Use free tier carefully, mock for most tests |
| Different dimension support | Medium | Test with all 4 embedders (384-3072) |
| Persistence not working | Medium | Explicit restart tests |

---

## Implementation

[To be filled during implementation]

---

## Verification

[To be filled during verification]

---

## Testing

[To be filled during testing]

---

## Review

[To be filled during review]

---

## Approval

- [x] Plan approved by: User on 2025-11-04
- [ ] Sprint completed and approved by: [Pending]
