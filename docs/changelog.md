# Changelog

All notable changes to Axon are documented here. This project follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0-beta] - November 9, 2025

### 🎉 First Beta Release

This is the **first beta release** of Axon, representing the initial public version of the unified memory SDK for LLM applications.

---

### ✨ Added

#### Core Features

- **MemorySystem API** - Main interface for store, recall, forget, compact, export operations
- **Multi-Tier Routing** - Automatic routing across ephemeral, session, and persistent tiers
- **PolicyEngine** - Orchestrates lifecycle decisions (promotion, demotion, eviction)
- **ScoringEngine** - Importance scoring using access frequency, recency, and base importance
- **Router** - Intelligent tier selection with fallback and capacity management

#### Storage Adapters

| Adapter | Use Case | Status |
|---------|----------|--------|
| InMemory | Development/Testing | ✅ Complete |
| Redis | Ephemeral/Session | ✅ Complete |
| ChromaDB | Local Vector Storage | ✅ Complete |
| Qdrant | Production Vector DB | ✅ Complete |
| Pinecone | Managed Vector DB | ✅ Complete |

#### Embedders

- **OpenAI** - text-embedding-3-small/large models
- **Voyage AI** - Voyage embedding models  
- **Sentence Transformers** - Local open-source models
- **HuggingFace** - HuggingFace inference API

#### Advanced Features

##### Audit Logging

- Complete audit trail system with AuditLogger
- Structured event logging with timestamps
- Query/filter by operation, user, session, status
- JSON export for compliance (GDPR, HIPAA)
- Automatic rotation when max_events reached

##### Privacy & PII Detection

- Automatic PII detection (emails, phones, SSNs, credit cards, IPs)
- Auto-assigns privacy levels (PUBLIC, INTERNAL, SENSITIVE, RESTRICTED)
- Detection results stored in entry metadata
- User override capability

##### Structured Logging

- JSON logging for production
- Correlation ID tracking
- Performance metrics via decorators
- Environment-based configuration

##### Transaction Support (2PC)

- Two-phase commit for atomic operations
- Multiple isolation levels
- Atomic multi-tier operations
- Automatic rollback on failure
- Context manager API

##### Compaction Strategies

- Count-based compaction
- Semantic similarity clustering
- Importance-based selection
- Time-based grouping
- Hybrid strategies

#### Integrations

**LangChain**
- `AxonChatMemory` implementing `BaseChatMessageHistory`
- Backward compatibility with `BaseMemory`
- `AxonVectorStore` for vector storage

**LlamaIndex**
- `AxonVectorStore` implementing `BasePydanticVectorStore`
- Query engine support
- Metadata filtering

#### Configuration

- **MemoryConfig** - Hierarchical configuration system
- **Policy Classes** - Tier-specific policies
- **Pre-configured Templates**:
  - `DEVELOPMENT_CONFIG` - In-memory, no embeddings
  - `aggressive_caching()` - Short TTLs, frequent compaction
  - `balanced()` - Recommended defaults
  - `long_term_retention()` - Extended TTLs, high capacity

#### Data Models

- **MemoryEntry** - Pydantic-validated memory structure
- **Filter** - Declarative query filtering
- **AuditEvent** - Structured audit events
- **PIIDetectionResult** - PII detection metadata
- **CompactionResult** - Compaction operation results

---

### 🔄 Changed

- **Async-First API** - All operations are async for better performance
- **Lazy Imports** - Heavy dependencies loaded on-demand
- **Type Safety** - Full type hints with mypy strict mode

---

### 🐛 Fixed

- Memory export with missing embeddings
- Compact dry-run OpenAI API key error
- Missing `await` for async adapter access
- Test expectations for async event ordering

---

### 📚 Documentation

- **MkDocs Site** - Complete documentation with Material theme
- **Getting Started** - Installation and quickstart
- **Core Concepts** - Architecture deep dive
- **API Reference** - Comprehensive API docs
- **Examples** - 27 working code examples
- **Contributing** - Development, testing, and style guides

---

### ✅ Testing

- **Overall Coverage**: 97.8% passing (634/646 tests)
- **Unit Tests**: 100/101 passing (99.0%)
- **Integration Tests**: 92/94 passing (97.9%)
- **Framework Tests**: 38/38 passing (100%)
- **Code Coverage**: 42% overall, 70%+ on core modules

---

### ⚡ Performance

- Single event loop design (Router)
- Thread-safe adapter registry
- Signature-based embedder caching

---

### 🔒 Security

- Automatic PII detection
- Four-tier privacy classification
- Complete provenance tracking
- Immutable audit trails

---

## What's Working

✅ All core memory operations (store, recall, forget, compact, export, import)  
✅ Multi-tier routing with automatic promotion/demotion  
✅ 5 production storage adapters  
✅ LangChain and LlamaIndex integrations  
✅ Audit logging and PII detection  
✅ Transaction support with 2PC  
✅ Advanced compaction strategies  

---

## In Progress

🚧 Documentation optimization  
🚧 Performance tuning  
🚧 Security audit  

---

## Not Yet Implemented

❌ SQLite adapter  
❌ CLI tools for backup/restore  
❌ GraphQL API  
❌ Real-time sync  

---

## Versioning Policy

Axon follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality
- **PATCH**: Backwards-compatible bug fixes
- **Beta/RC**: Pre-release versions

---

## Future Releases

### v1.0.0 (Stable) - Q1 2025

- Complete documentation
- Performance benchmarks
- Security audit
- Production deployment guide
- SQLite adapter

### v1.1.0 - Q2 2025

- CLI backup/restore tools
- Extended monitoring
- Performance optimizations
- Additional embedder integrations

### v2.0.0 - Q3 2025

- GraphQL API
- Real-time sync
- Multi-tenancy support
- Advanced security features
- PostgreSQL adapter with pgvector

---

## Links

- [Roadmap](https://github.com/saranmahadev/AxonMemoryCore/blob/main/ROADMAP.md) - Sprint planning and future features
- [Contributing](contributing/development.md) - How to contribute
- [GitHub Repository](https://github.com/saranmahadev/AxonMemoryCore)
- [Issue Tracker](https://github.com/saranmahadev/AxonMemoryCore/issues)

---

**Format**: Based on [Keep a Changelog](https://keepachangelog.com/)  
**Versioning**: [Semantic Versioning](https://semver.org/)
