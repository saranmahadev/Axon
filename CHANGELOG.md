# Changelog

All notable changes to Axon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta] - 2025-11-09

### Added

#### Core Features
- **MemorySystem API** - Main interface for store, recall, forget, compact, export operations
- **Multi-Tier Routing** - Automatic routing across ephemeral, session, and persistent tiers based on importance scores
- **PolicyEngine** - Orchestrates lifecycle decisions including promotion, demotion, and eviction
- **ScoringEngine** - Calculates importance scores using access frequency, recency, and base importance
- **Router** - Intelligent tier selection with fallback and capacity management

#### Storage Adapters
- **InMemoryAdapter** - In-memory storage for development and testing
- **RedisAdapter** - Redis backend with TTL support for ephemeral/session tiers
- **ChromaAdapter** - ChromaDB integration for local vector storage
- **QdrantAdapter** - Qdrant vector database integration for production
- **PineconeAdapter** - Pinecone managed vector database integration

#### Embedders
- **OpenAIEmbedder** - OpenAI text-embedding-3-small/large models
- **VoyageAIEmbedder** - Voyage AI embedding models
- **SentenceTransformerEmbedder** - Local sentence-transformers models
- **HuggingFaceEmbedder** - HuggingFace inference API integration

#### Advanced Features
- **Audit Logging** - Complete audit trail system with AuditLogger
  - Structured event logging with timestamps
  - Query/filter capabilities by operation, user, session, status
  - JSON export for compliance (GDPR, HIPAA)
  - Automatic rotation when max_events reached

- **Privacy & PII Detection** - Automatic PII detection and classification
  - Detects emails, phone numbers, SSNs, credit cards, IP addresses
  - Auto-assigns privacy levels (PUBLIC, INTERNAL, SENSITIVE, RESTRICTED)
  - Stores detection results in entry metadata
  - User override capability

- **Structured Logging** - Production-grade JSON logging
  - JSONFormatter for machine-readable logs
  - Correlation ID tracking for request tracing
  - Performance metrics via decorators
  - Environment-based configuration

- **Transaction Support (2PC)** - Two-phase commit for atomic operations
  - TransactionManager with multiple isolation levels
  - Atomic multi-tier operations
  - Automatic rollback on failure
  - Context manager API

- **Advanced Compaction Strategies**
  - Count-based compaction
  - Semantic similarity clustering
  - Importance-based selection
  - Time-based grouping
  - Hybrid strategy combining multiple approaches

#### Integrations
- **LangChain Integration**
  - AxonChatMemory implementing BaseChatMessageHistory
  - Backward compatibility with BaseMemory
  - AxonVectorStore for vector storage

- **LlamaIndex Integration**
  - AxonVectorStore implementing BasePydanticVectorStore
  - Query engine support
  - Metadata filtering

#### Configuration & Templates
- **MemoryConfig** - Hierarchical configuration system
- **Policy Classes** - EphemeralPolicy, SessionPolicy, PersistentPolicy
- **Pre-configured Templates**
  - `DEVELOPMENT_CONFIG` - In-memory, no embeddings
  - `aggressive_caching()` - Short TTLs, frequent compaction
  - `balanced()` - Recommended for most use cases
  - `long_term_retention()` - Extended TTLs, high capacity

#### Data Models
- **MemoryEntry** - Canonical data structure with Pydantic validation
- **Filter** - Declarative filtering for queries
- **AuditEvent** - Structured audit event model
- **PIIDetectionResult** - PII detection metadata
- **CompactionResult** - Compaction operation result

### Changed
- **Async-First API** - All operations are async for better performance
- **Lazy Imports** - Heavy dependencies loaded on-demand for fast import times
- **Type Safety** - Full type hints with mypy strict mode support

### Fixed
- **Memory Export** - Fixed empty results when entries have no embeddings
- **Compact Dry-Run** - Fixed OpenAI API key error in dry-run mode
- **Async Adapter Access** - Fixed missing `await` for `get_adapter()` calls
- **Test Expectations** - Fixed 3 test failures related to async event ordering

### Documentation
- **MkDocs Site** - Complete documentation with Material theme
- **Getting Started Guide** - Installation and quickstart tutorials
- **Core Concepts** - Deep dive into architecture and design
- **API Reference** - Comprehensive API documentation
- **Examples** - 27 working code examples

### Testing
- **Test Coverage** - 97.8% passing (634/646 tests)
- **Unit Tests** - 100/101 passing (99.0%)
- **Integration Tests** - 92/94 passing (97.9%)
- **LangChain/LlamaIndex Tests** - 38/38 passing (100%)
- **Code Coverage** - 42% overall, 70%+ on core modules

### Performance
- **Router** - Single event loop design (not thread-safe)
- **Adapter Registry** - Thread-safe lazy initialization
- **Embedder Caching** - Signature-based cache invalidation

### Security
- **PII Detection** - Automatic sensitive data identification
- **Privacy Levels** - Four-tier classification system
- **Provenance Tracking** - Complete lineage for all entries
- **Audit Trails** - Immutable operation logs

---

## [0.1.0] - 2025-01-15

### Added
- Initial project scaffolding
- Basic data models (MemoryEntry, Filter)
- InMemoryAdapter prototype
- Router skeleton
- PolicyEngine MVP

### Known Issues
- No vector storage support
- Limited test coverage
- No production adapters

---

## Release Notes

### v1.0.0-beta Highlights

This is the **first beta release** of Axon, representing ~60% completion toward production readiness.

**What's Working:**
- ✅ All core memory operations (store, recall, forget, compact, export, import)
- ✅ Multi-tier routing with automatic promotion/demotion
- ✅ 5 production storage adapters
- ✅ LangChain and LlamaIndex integrations
- ✅ Audit logging and PII detection
- ✅ Transaction support with 2PC
- ✅ Advanced compaction strategies

**What's In Progress:**
- 🚧 Documentation (partially complete)
- 🚧 Performance optimization
- 🚧 Security audit

**Not Yet Implemented:**
- ❌ SQLite adapter
- ❌ CLI tools for backup/restore
- ❌ GraphQL API
- ❌ Real-time sync

### Upgrade Guide

This is the first public beta release, so there is no upgrade path from earlier versions.

### Breaking Changes

None (first release).

### Deprecations

None (first release).

### Contributors

- **Core Team** - Architecture, implementation, testing
- **Community** - Bug reports, feature requests

---

## Versioning Policy

Axon follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes
- **Beta/RC** tags for pre-release versions

---

## Future Releases

### v1.0.0 (Stable) - Planned Q1 2025
- Complete documentation
- Performance benchmarks
- Security audit
- Production deployment guide
- SQLite adapter

### v1.1.0 - Planned Q2 2025
- CLI tools for backup/restore
- Extended monitoring and observability
- Performance optimizations
- Additional embedder integrations

### v2.0.0 - Planned Q3 2025
- GraphQL API
- Real-time sync across instances
- Multi-tenancy support
- Advanced security features
- PostgreSQL adapter with pgvector

---

For detailed sprint planning, see [ROADMAP.md](ROADMAP.md).

For contributing guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
