# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Axon** is a unified Memory SDK for LLM applications that provides multi-tier storage, policy-driven lifecycle management, and intelligent summarization/compaction. It abstracts multiple storage backends (in-memory, Redis, vector databases) behind a single programmable API with automatic tier selection, semantic recall, and observability.

**Current Status:** MVP 0.1 - Core infrastructure complete with basic adapters (InMemory, ChromaDB, Qdrant, Pinecone, Redis) and policy engine.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test markers
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m slow             # Slow tests only

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestMemoryEntry::test_entry_creation_minimal

# Generate HTML coverage report
pytest --cov=axon --cov-report=html
```

### Code Quality
```bash
# Format code (line length: 100)
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/axon
```

## Architecture Overview

### Core Components

**MemorySystem** (`src/axon/core/memory_system.py`)
- Main user-facing API providing `store()`, `recall()`, `forget()`, `compact()`, `export()`
- Coordinates Router, PolicyEngine, ScoringEngine, and AdapterRegistry
- Handles tracing, validation, and observability

**Router** (`src/axon/core/router.py`)
- Intelligently routes operations across tiers (ephemeral → session → persistent)
- Implements tier selection based on importance scores
- Handles automatic promotion/demotion based on access patterns
- NOT thread-safe (single event loop design)

**PolicyEngine** (`src/axon/core/policy_engine.py`)
- Orchestrates memory lifecycle decisions using ScoringEngine and tier policies
- Determines promotion/demotion eligibility
- Manages tier capacity and eviction
- Tier hierarchy: ephemeral → session → persistent (lower to higher)

**ScoringEngine** (`src/axon/core/scoring.py`)
- Calculates importance scores for promotion/demotion decisions
- Configurable weights for: access frequency, recency, base importance, session continuity
- Uses exponential decay for temporal relevance

**AdapterRegistry** (`src/axon/core/adapter_registry.py`)
- Registry for storage adapters with lazy initialization
- Maps tier names to StorageAdapter instances
- Thread-safe adapter initialization

### Data Models

**MemoryEntry** (`src/axon/models/entry.py`)
- Canonical data structure for all memory units
- Fields: `id`, `type`, `text`, `embedding`, `metadata`
- Metadata includes: user_id, session_id, importance (0.0-1.0), tags, provenance, privacy_level

**Filter** (`src/axon/models/filter.py`)
- Declarative filtering for queries: user_id, session_id, tags, date ranges, privacy levels

**AuditEvent** (`src/axon/models/audit.py`)
- Structured audit trail for compliance and observability
- Fields: event_id, timestamp, operation, user_id, session_id, entry_ids, metadata, status, error_message, duration_ms
- Operation types: STORE, RECALL, FORGET, COMPACT, EXPORT, BULK_STORE, REINDEX
- Status types: SUCCESS, FAILURE, PARTIAL

### Audit System

**AuditLogger** (`src/axon/core/audit.py`)
- Thread-safe audit logging for tracking all memory operations
- Features:
  - Structured event logging with timestamps
  - In-memory storage with optional file export
  - Automatic rotation when max_events reached
  - Query/filter capabilities by operation, user, session, status, time range
  - JSON export for compliance and analysis

**Usage:**
```python
from axon import MemorySystem
from axon.core import AuditLogger, MemoryConfig
from axon.models.audit import OperationType

# Create audit logger
audit_logger = AuditLogger(max_events=10000, enable_rotation=True)

# Create MemorySystem with audit logging
system = MemorySystem(config=config, audit_logger=audit_logger)

# All operations are automatically logged
await system.store("User prefers dark mode", importance=0.8)
await system.recall("user preferences", k=5)

# Query audit log
events = await system.export_audit_log(operation=OperationType.STORE)
```

**Provenance Tracking:**
- `system.get_provenance_chain(entry_id)` - Trace entry lineage back to source
- `system.find_derived_entries(entry_id)` - Find all summaries/transformations of an entry

### Privacy & PII Detection

**PIIDetector** (`src/axon/core/privacy.py`)
- Automatic detection of Personally Identifiable Information (PII) using regex patterns
- Auto-classifies privacy levels based on detected PII types
- Features:
  - Detects 5 PII types: email, phone, SSN, credit cards, IP addresses
  - Privacy level mapping: SSN/credit cards → RESTRICTED, email/phone/IP → INTERNAL
  - Most restrictive level wins when multiple PII types detected

### Structured Logging

**Logging System** (`src/axon/core/logging_config.py`)
- Production-grade structured logging with JSON formatting for machine readability
- Correlation ID tracking for distributed request tracing
- Automatic performance metrics via decorators
- Features:
  - **JSONFormatter** - Outputs logs as JSON with timestamp, level, logger, message, correlation ID, and custom fields
  - **StructuredLogger** - Enhanced logger with convenience methods: `log_operation()`, `log_metric()`, `log_error()`
  - **Correlation IDs** - Async-safe context propagation via ContextVar for request tracking
  - **Performance Decorator** - `@log_performance()` automatically logs latency and errors for async/sync functions
  - **Environment Configuration** - AXON_LOG_LEVEL (DEBUG/INFO/WARNING/ERROR), AXON_STRUCTURED_LOGGING (true/false)

**Usage:**
```python
from axon import get_logger, set_correlation_id, log_performance

# Basic structured logging
logger = get_logger(__name__)
logger.info("Processing request", extra={"user_id": "user_123", "operation": "store"})

# Correlation ID for request tracing
set_correlation_id("req-abc-123")
logger.info("Request started")  # Correlation ID automatically included

# Performance tracking
@log_performance("store_operation")
async def store_memory(content: str) -> str:
    # Operation code
    return entry_id  # Latency automatically logged

# Custom metrics
logger.log_metric("cache_hit_rate", 0.85, unit="%", operation="recall")
```

**JSON Output Example:**
```json
{
  "timestamp": "2025-11-08T10:30:45.123456Z",
  "level": "INFO",
  "logger": "axon.core.memory_system",
  "message": "Memory stored successfully",
  "correlation_id": "req-abc123",
  "user_id": "user_456",
  "entry_id": "entry_789",
  "latency_ms": 12.5
}
```
  - PII detection metadata stored in `entry.metadata.pii_detection`
  - Can be disabled via `enable_pii_detection=False`

**PIIDetectionResult:**
- `detected_types` - Set of PII type names found
- `recommended_privacy_level` - Recommended PrivacyLevel based on detected PII
- `has_pii` - Boolean indicating if any PII was detected
- `details` - Dict with count of each PII type

**Privacy Levels (PrivacyLevel enum):**
- `PUBLIC` - No PII detected, safe for public access
- `INTERNAL` - Contains emails, phone numbers, or IP addresses
- `SENSITIVE` - Business-sensitive but not PII (reserved for future use)
- `RESTRICTED` - Contains SSN, credit cards, or other highly sensitive PII

**Usage:**
```python
from axon import MemorySystem
from axon.core import PIIDetector
from axon.models.base import PrivacyLevel

# Automatic PII detection (default)
system = MemorySystem(config=config)  # enable_pii_detection=True by default
entry_id = await system.store("Contact sales@company.com")

# Retrieve and check privacy level
tier, entry = await system._get_entry_by_id(entry_id)
print(entry.metadata.privacy_level)  # PrivacyLevel.INTERNAL
print(entry.metadata.pii_detection)  # {"detected_types": ["email"], ...}

# User override of privacy level
entry_id = await system.store(
    "Email: user@example.com",
    metadata={"privacy_level": PrivacyLevel.RESTRICTED}
)

# Filter recalls by privacy level
restricted = await system.recall("data", k=10, filter_dict={"privacy_level": PrivacyLevel.RESTRICTED})

# Disable PII detection
system_no_pii = MemorySystem(config=config, enable_pii_detection=False)
```

**Supported PII Patterns:**
- **Email:** `user@example.com` → INTERNAL
- **Phone:** `(555) 123-4567`, `555-123-4567` → INTERNAL
- **IP Address:** `192.168.1.100` → INTERNAL
- **SSN:** `123-45-6789`, `123456789` → RESTRICTED
- **Credit Card:** `4532 1234 5678 9010`, `4532-1234-5678-9010` → RESTRICTED

**Integration with Audit:**
PII detection results are included in audit log metadata when `audit_logger` is enabled, providing complete compliance tracking.

### Storage Adapters

All adapters implement `StorageAdapter` interface (`src/axon/adapters/base.py`):
- `save(entry)` - Store a single entry
- `query(vector, k, filter)` - Semantic search with metadata filtering
- `get(id)` - Retrieve by ID
- `delete(id)` - Remove by ID
- `bulk_save(entries)` - Batch storage
- `reindex()` - Rebuild index

**Available Adapters:**
- `InMemoryAdapter` - In-memory storage for dev/testing
- `ChromaAdapter` - ChromaDB vector store
- `QdrantAdapter` - Qdrant vector store
- `PineconeAdapter` - Pinecone vector store
- `RedisAdapter` - Redis for ephemeral/session storage with TTL support

### Embedders

All embedders implement `Embedder` interface (`src/axon/embedders/base.py`):
- `embed(texts)` - Convert text list to vectors
- `signature()` - Model name + version for cache invalidation

**Available Embedders:**
- `OpenAIEmbedder` - OpenAI text-embedding models
- `VoyageAIEmbedder` - Voyage AI embeddings
- `SentenceTransformerEmbedder` - sentence-transformers models
- `HuggingFaceEmbedder` - HuggingFace inference API

**Note:** Heavy embedders use lazy loading via `__getattr__` in `__init__.py` for fast import times.

### Policy System

**Policy** (`src/axon/core/policy.py`)
- Base class for tier policies
- Defines capacity, TTL, summarization rules

**Concrete Policies:**
- `EphemeralPolicy` - Short-lived, high-volume memory (TTL, max items)
- `SessionPolicy` - Session-scoped with summarization triggers
- `PersistentPolicy` - Long-term semantic storage with compaction

**Templates** (`src/axon/core/templates.py`)
- Pre-configured templates: `aggressive_caching()`, `balanced()`, `long_term_retention()`

## Key Design Patterns

### Async-First API
All storage operations are async (`async def`). The SDK uses `asyncio` internally. Adapters must implement async methods even if the underlying client is sync.

### Lazy Imports
Heavy dependencies (OpenAI, HuggingFace) are lazy-loaded to keep import time fast. See `__getattr__` in `src/axon/__init__.py`.

### Provenance Tracking
Every operation adds a `ProvenanceEvent` to `entry.metadata.provenance` for audit trails and explainability.

### Tier Selection Logic
1. Check explicit tier hint in metadata
2. Use importance score thresholds from policy config
3. Default to ephemeral if uncertain

### Promotion/Demotion
- Promotion: triggered by recall operations if score exceeds threshold
- Demotion: triggered by capacity pressure or low scores
- Access count and timestamps automatically tracked

## Sprint-Based Development Process

Axon follows a structured sprint workflow defined in [AGENTS.md](AGENTS.md):
1. **Planning** - Define scope, deliverables, success criteria
2. **Confirmation** - Get stakeholder approval
3. **Implementation** - Write code to spec
4. **Verification** - Review quality and adherence
5. **Testing** - Run automated tests
6. **Review** - Document outcomes and prepare next sprint

Sprint artifacts stored in `.sprints/` directory (if present).

## Code Style Requirements

- **Line length:** 100 characters (Black enforced)
- **Type hints:** Required for all function signatures (mypy strict mode)
- **Docstrings:** Google style, required for all public APIs
- **Test coverage:** Aim for >90% coverage on core modules
- **Naming conventions:**
  - Private attributes: `_private_attr`
  - Protected methods: `_protected_method()`
  - Class constants: `_UPPER_SNAKE_CASE`

## Common Patterns

### Creating a MemorySystem
```python
from axon import MemorySystem, MemoryEntry
from axon.core.config import MemoryConfig
from axon.core.templates import balanced

config = balanced()  # or MemoryConfig(...) for custom
system = MemorySystem(config)

# Store
entry_id = await system.store("User prefers dark mode", importance=0.8)

# Recall
results = await system.recall("user preferences", k=5)
```

### Registering Custom Adapters
```python
from axon.core.adapter_registry import AdapterRegistry
from axon.adapters import ChromaAdapter

registry = AdapterRegistry()
registry.register("persistent", ChromaAdapter(
    collection_name="my_collection",
    persist_directory="./chroma_db"
))
```

### Policy Configuration
```python
from axon.core.policy import Policy
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy

config = MemoryConfig(
    tiers={
        "ephemeral": EphemeralPolicy(ttl_minutes=10, max_items=50),
        "session": SessionPolicy(summarize_after=20),
        "persistent": PersistentPolicy(backend="qdrant", embedder="openai")
    }
)
```

## Testing Conventions

- **Unit tests:** `tests/unit/` - Test individual components in isolation
- **Integration tests:** `tests/integration/` - Test adapter integrations, multi-tier workflows
- **Fixtures:** Defined in `tests/conftest.py` for shared test data
- **Markers:** Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Test naming:** `test_<what>_<condition>_<expected>`

## Important Implementation Notes

### Thread Safety
- **Router:** NOT thread-safe - assumes single event loop
- **AdapterRegistry:** Thread-safe initialization
- **MemorySystem:** Not designed for concurrent access from multiple threads

### Error Handling
- Use fail-fast approach with descriptive error messages
- Adapters should raise `ValueError` for invalid inputs
- Storage errors should propagate with context

### Version Tracking
- Embedder signature stored in `entry.metadata.version`
- Used for cache invalidation when embedder changes
- Format: `model_name:version` (e.g., "text-embedding-3-large:2025-01")

### Compaction
- Not yet fully implemented (basic summarizer exists in `src/axon/core/summarizer.py`)
- Compaction creates new MemoryEntry with provenance linking to source IDs
- Roadmap: semantic redundancy detection, importance-based compaction

## Common Development Workflows

### Adding a New Storage Adapter
1. Create file in `src/axon/adapters/`
2. Inherit from `StorageAdapter` and implement all abstract methods
3. Add async implementations even if client is sync
4. Add to `src/axon/adapters/__init__.py`
5. Write integration tests in `tests/integration/`
6. Add example usage in `examples/`

### Adding a New Embedder
1. Create file in `src/axon/embedders/`
2. Inherit from `Embedder` and implement `embed()` and `signature()`
3. Add lazy import to `src/axon/__init__.py` in `__getattr__`
4. Add to `__all__` list in `src/axon/__init__.py`
5. Write unit tests
6. Update `pyproject.toml` optional dependencies if needed

### Running Examples
```bash
# Basic examples require minimal dependencies
python examples/basic_usage.py
python examples/memory_system_basic.py

# Adapter examples require specific backends
python examples/01_qdrant_basic.py          # Requires Qdrant running
python examples/04_pinecone_basic.py        # Requires Pinecone API key
python examples/07_redis_session_cache.py   # Requires Redis running
```

## Project Structure Reference

```
axon/
├── src/axon/
│   ├── models/          # Data models (MemoryEntry, Filter, base types)
│   ├── adapters/        # Storage backend implementations
│   ├── embedders/       # Embedding model integrations
│   ├── core/           # Core logic (Router, PolicyEngine, MemorySystem)
│   └── utils/          # Utility functions
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── examples/           # Usage examples and demos
├── AGENTS.md          # Sprint-based development process
└── CONTRIBUTING.md    # Development guidelines
```

## Dependencies

**Core:** pydantic, typing-extensions

**Optional (install with `pip install axon[all]`):**
- openai - OpenAI embeddings
- chromadb - ChromaDB vector store
- redis - Redis adapter
- qdrant-client - Qdrant vector store
- pinecone-client - Pinecone vector store

**Dev:** pytest, pytest-cov, pytest-asyncio, black, ruff, mypy

## Commit Message Format

Use conventional commits:
```
type(scope): subject

body (optional)

footer (optional)
```

**Types:** feat, fix, docs, style, refactor, test, chore

**Example:**
```
feat(adapters): add Qdrant batch operations support

Implement bulk_save() with batching for improved performance
on large-scale ingestion.

Closes #42
```

## Repository Cleanup & Maintenance

### Files to Keep Clean

**Never commit these (already in .gitignore):**
- `__pycache__/` directories
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `htmlcov/` (coverage reports)
- `.coverage` (coverage data)
- `*.pyc`, `*.pyo`, `*.pyd` files
- `.venv/`, `venv/`, `env/` (virtual environments)
- `.env`, `.env.local` (environment variables)
- `.claude/` (Claude Code local settings)
- `nul` (accidental empty files)
- `*.egg-info/`, `dist/`, `build/` (build artifacts)
- `chroma_db/`, `qdrant_storage/`, `demo_knowledge_db/` (test databases)

### Clean Build Command

To clean all build artifacts and caches:
```bash
# Remove Python caches
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove test/build artifacts
rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
rm -rf dist build *.egg-info

# Remove test databases (be careful!)
rm -rf chroma_db qdrant_storage demo_knowledge_db
```

### Repository Standards

**File Naming:**
- Source files: `snake_case.py`
- Test files: `test_<module_name>.py`
- Example files: Numbered with descriptive names (e.g., `01_qdrant_basic.py`)
- No duplicate numbering in examples/

**Code Quality Standards:**
- **Black**: 100% formatted (line length 100)
- **Ruff**: Zero linting errors
- **Tests**: All tests passing (use `pytest`)
- **MyPy**: Minimize type errors (strict mode with Pydantic plugin)

**Before Committing:**
```bash
# 1. Format code
black src/ tests/

# 2. Check linting
ruff check src/ tests/

# 3. Run tests
pytest

# 4. Optional: Check types
mypy src/axon
```

### Directory Structure Standards

```
axon/
├── src/axon/           # Source code only
├── tests/              # Tests only (unit/ and integration/)
├── examples/           # Runnable examples (numbered)
├── docs/               # Documentation (if needed)
├── .github/            # GitHub workflows (if needed)
├── CLAUDE.md           # This file - Claude Code guidance
├── CONTRIBUTING.md     # Contributor guidelines
├── README.md           # Project documentation
├── pyproject.toml      # Python project config
└── .gitignore          # Git ignore rules
```

**Do NOT commit:**
- IDE-specific files (`.vscode/`, `.idea/`)
- Personal config files
- Temporary files or scratch work
- Large binary files
- API keys or secrets
