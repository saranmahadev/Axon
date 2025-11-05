# Sprint 3.1 Plan - MemorySystem Core API (Part 1)

**Sprint:** 3.1  
**Phase:** PHASE 3 - Core API & Operations (MVP 0.1 completion)  
**Duration:** 2 days (November 6-7, 2025)  
**Complexity:** Medium  

---

## Sprint Goal

Implement the core MemorySystem API methods `store()` and `recall()` with basic validation and tracing capabilities.

**Success Criteria:**
- MemorySystem class with store() and recall() methods working
- Basic validation for input parameters
- Tracing foundation for observability
- Integration with Router, PolicyEngine, and AdapterRegistry
- Comprehensive unit and integration tests
- Working example demonstrating MemorySystem usage

---

## Scope

### In Scope ✅
- [ ] MemorySystem class initialization
- [ ] `store()` method - Store memories with automatic tier selection
- [ ] `recall()` method - Search and retrieve memories across tiers
- [ ] Basic input validation (entry validation, filter validation)
- [ ] Tracing foundation (event logging, operation tracking)
- [ ] Unit tests (target: 90%+ coverage)
- [ ] Integration tests with real Router/PolicyEngine
- [ ] Example script demonstrating core operations

### Out of Scope ❌
- `forget()` method (Sprint 3.2)
- `export()` method (Sprint 3.2)
- `sync()` method (Sprint 3.2)
- Advanced tracing/metrics (Phase 4)
- Encryption/PII redaction (Phase 4)
- Summarization/compaction (Sprint 3.3)

---

## Dependencies

### Required (Available) ✅
- Router implementation ✅ (Sprint 2.4)
- PolicyEngine implementation ✅ (Sprint 2.4)
- AdapterRegistry implementation ✅ (Sprint 2.4)
- ScoringEngine implementation ✅ (Sprint 2.4)
- Data models (MemoryEntry, Filter) ✅ (Foundation)
- InMemoryAdapter ✅ (Foundation)

### Optional
- ChromaDB adapter (Phase 2, can use mocks)
- Redis adapter (Phase 2, can use mocks)

---

## Deliverables

### Day 1: MemorySystem Class & store() Method

**File:** `src/axon/core/memory_system.py` (~200-250 lines)

**Class: MemorySystem**

```python
class MemorySystem:
    """
    Central interface for memory storage and retrieval.
    
    Coordinates Router, PolicyEngine, and adapters to provide
    intelligent memory management across tiers.
    """
    
    def __init__(
        self,
        config: MemoryConfig,
        router: Optional[Router] = None,
        registry: Optional[AdapterRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        scoring_engine: Optional[ScoringEngine] = None
    ):
        """Initialize MemorySystem with configuration and components."""
        
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        tier: Optional[str] = None
    ) -> str:
        """
        Store a memory with automatic tier selection.
        
        Args:
            content: Text content to store
            metadata: Additional metadata
            importance: Importance score (0.0-1.0)
            tags: List of tags for categorization
            tier: Explicit tier override (optional)
            
        Returns:
            Memory entry ID
            
        Raises:
            ValueError: Invalid parameters
            RuntimeError: Storage failure
        """
        
    async def recall(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Filter] = None,
        tiers: Optional[List[str]] = None,
        min_importance: Optional[float] = None
    ) -> List[MemoryEntry]:
        """
        Search and retrieve memories across tiers.
        
        Args:
            query: Search query text
            k: Maximum number of results
            filter: Optional filter criteria
            tiers: Specific tiers to search (default: all)
            min_importance: Minimum importance threshold
            
        Returns:
            List of matching memory entries
            
        Raises:
            ValueError: Invalid parameters
        """
```

**Key Features:**
1. Automatic tier selection via Router
2. Input validation (content not empty, importance in range)
3. Metadata handling (merge user metadata with system metadata)
4. ID generation for new entries
5. Tracing/logging of operations
6. Error handling and helpful error messages

**Testing:**
- File: `tests/unit/test_memory_system.py` (~400 lines)
- Target: 25+ tests, 90%+ coverage

**Test Categories:**
- TestMemorySystemInit: 5 tests
  - Successful initialization with all components
  - Initialization with default components
  - Initialization with custom config
  - Invalid config handling
  - Component validation

- TestStoreMethod: 10 tests
  - Basic store operation
  - Store with metadata
  - Store with tags
  - Store with importance
  - Store with explicit tier
  - Store with invalid content (empty string)
  - Store with invalid importance (>1.0, <0.0)
  - Store with invalid tier name
  - Store generates unique IDs
  - Store updates tier statistics

- TestRecallMethod: 10 tests
  - Basic recall operation
  - Recall with k limit
  - Recall with filter
  - Recall specific tiers
  - Recall with min_importance
  - Recall with empty query
  - Recall with invalid k (negative, zero)
  - Recall with non-existent tiers
  - Recall returns sorted results
  - Recall deduplicates across tiers

---

### Day 2: Integration Tests & Examples

**File:** `tests/integration/test_memory_system_integration.py` (~300 lines)

**Integration Test Scenarios:**

1. **TestEndToEndWorkflow** (5 tests)
   - Store and recall lifecycle
   - Multiple store operations
   - Recall with different filters
   - Cross-tier recall
   - Empty recall handling

2. **TestTierSelection** (3 tests)
   - Automatic tier selection based on importance
   - Explicit tier override
   - Tier statistics validation

3. **TestMetadataHandling** (3 tests)
   - Custom metadata preservation
   - System metadata injection
   - Tag handling

4. **TestErrorHandling** (3 tests)
   - Invalid input handling
   - Adapter failure recovery
   - Router error handling

**Target:** 15+ integration tests, all passing

---

**File:** `examples/memory_system_basic.py` (~200 lines)

**Example Demonstrating:**
1. MemorySystem initialization
2. Storing memories with different importance levels
3. Recalling memories with queries
4. Using filters to narrow results
5. Tier-specific recalls
6. Statistics monitoring

**Example Structure:**
```python
"""
Example: MemorySystem Basic Usage

Demonstrates:
- Initializing MemorySystem
- Storing memories with automatic tier selection
- Searching across tiers
- Using filters
- Monitoring statistics
"""

async def main():
    # 1. Setup
    # 2. Store memories
    # 3. Recall with queries
    # 4. Filter results
    # 5. View statistics
```

---

## File Structure

```
src/axon/core/
├── memory_system.py          # NEW: Core MemorySystem class
├── router.py                  # Existing (Sprint 2.4)
├── policy_engine.py          # Existing (Sprint 2.4)
├── adapter_registry.py       # Existing (Sprint 2.4)
└── scoring.py                # Existing (Sprint 2.4)

tests/unit/
├── test_memory_system.py     # NEW: MemorySystem unit tests
├── test_router.py            # Existing
├── test_policy_engine.py     # Existing
└── test_scoring.py           # Existing

tests/integration/
├── test_memory_system_integration.py  # NEW: Integration tests
└── test_router_integration.py         # Existing

examples/
├── memory_system_basic.py    # NEW: Basic usage example
├── router_basic_usage.py     # Existing
└── ...
```

---

## Technical Design

### MemorySystem Architecture

```
User
  ↓
MemorySystem (Coordinator)
  ├── store() → Router.route_store() → Adapter.save()
  ├── recall() → Router.route_recall() → Adapter.query()
  └── Tracing/Validation Layer
```

### store() Flow

```
1. Validate inputs (content, importance, tier)
2. Create MemoryEntry with metadata
3. Generate unique ID (UUID)
4. Call Router.route_store(entry, tier)
5. Log operation to trace
6. Return entry ID
```

### recall() Flow

```
1. Validate inputs (query, k, filter, tiers)
2. Call Router.route_recall(query, k, filter, tiers)
3. Apply min_importance filter if specified
4. Log operation to trace
5. Return results
```

### Tracing Design (Foundation)

```python
class TraceEvent:
    """Basic trace event for operations."""
    timestamp: datetime
    operation: str  # "store", "recall"
    duration_ms: float
    entry_id: Optional[str]
    tier: Optional[str]
    success: bool
    error: Optional[str]

class MemorySystem:
    def __init__(...):
        self._trace_events: List[TraceEvent] = []
    
    def _log_trace(self, event: TraceEvent):
        """Log trace event (basic implementation)."""
        self._trace_events.append(event)
    
    def get_trace_events(self) -> List[TraceEvent]:
        """Get trace events (for debugging/testing)."""
        return self._trace_events.copy()
```

---

## Acceptance Criteria

### Functional Requirements

- [x] MemorySystem can be initialized with config
- [x] store() creates and stores memories
- [x] store() returns unique entry IDs
- [x] store() validates inputs and raises errors appropriately
- [x] recall() searches across tiers and returns results
- [x] recall() respects k limit and filters
- [x] recall() validates inputs
- [x] Tracing logs operations

### Quality Requirements

- [x] 25+ unit tests passing
- [x] 15+ integration tests passing
- [x] 90%+ code coverage for MemorySystem
- [x] All edge cases handled
- [x] Error messages are clear and helpful
- [x] Example script runs successfully

### Performance Requirements

- [x] store() completes in <50ms (with InMemory adapter)
- [x] recall() completes in <100ms for 5 results
- [x] Batch store (10 entries) completes in <500ms

---

## Risks & Mitigations

### Risk 1: Integration Complexity
**Risk:** Coordinating Router, PolicyEngine, and Registry is complex  
**Mitigation:** Use existing tested components, comprehensive integration tests  
**Severity:** Medium  

### Risk 2: Error Handling Edge Cases
**Risk:** Many failure modes (adapter errors, invalid input, etc.)  
**Mitigation:** Systematic error handling with try/catch, clear error messages  
**Severity:** Low  

### Risk 3: Tracing Overhead
**Risk:** Tracing could impact performance  
**Mitigation:** Keep tracing simple initially, optimize later  
**Severity:** Low  

---

## Definition of Done

### Code Complete
- [x] MemorySystem class implemented
- [x] store() method working
- [x] recall() method working
- [x] Input validation complete
- [x] Tracing foundation implemented

### Testing Complete
- [x] All unit tests passing (target: 25+)
- [x] All integration tests passing (target: 15+)
- [x] Code coverage ≥90%
- [x] Edge cases tested
- [x] Error handling tested

### Documentation Complete
- [x] Docstrings for all public methods
- [x] Example script working
- [x] README updated (if needed)
- [x] Sprint review document created

### Quality Gates
- [x] No linting errors
- [x] Type hints present
- [x] Error messages clear
- [x] Performance benchmarks met

---

## Sprint Execution Plan

### Day 1: Implementation

**Morning (4 hours):**
1. Create `memory_system.py` skeleton
2. Implement `__init__` method
3. Implement `store()` method
4. Add input validation
5. Add basic tracing

**Afternoon (4 hours):**
6. Implement `recall()` method
7. Add filtering logic
8. Complete error handling
9. Write docstrings

**Evening (2 hours):**
10. Begin unit tests (TestMemorySystemInit, TestStoreMethod)
11. Fix any bugs found

**Deliverable:** MemorySystem class with store() and recall() methods

---

### Day 2: Testing & Examples

**Morning (4 hours):**
1. Complete unit tests (TestRecallMethod)
2. Run coverage analysis
3. Fix coverage gaps
4. Create integration test file
5. Write integration test scenarios

**Afternoon (3 hours):**
6. Complete integration tests
7. Run all tests (unit + integration)
8. Fix any failures
9. Performance validation

**Evening (3 hours):**
10. Create example script
11. Test example thoroughly
12. Write sprint review document
13. Final validation run

**Deliverable:** Complete test suite + working example

---

## Testing Strategy

### Unit Test Approach
- Mock Router, PolicyEngine, AdapterRegistry
- Test MemorySystem logic in isolation
- Verify correct method calls to dependencies
- Test all error paths

### Integration Test Approach
- Use real components (Router, PolicyEngine, etc.)
- Use InMemoryAdapter for speed
- Test end-to-end workflows
- Validate statistics and tracing

### Example Validation
- Run example script
- Verify output is correct
- Ensure no errors
- Check performance

---

## Success Metrics

### Code Metrics
- Lines of Code: ~200-250 (MemorySystem)
- Test Lines: ~700 (400 unit + 300 integration)
- Code Coverage: ≥90%
- Tests Passing: 40+ (25 unit + 15 integration)

### Quality Metrics
- Zero critical bugs
- All error paths handled
- Clear error messages
- Performance within targets

### Velocity Metrics
- Sprint completed in 2 days
- All deliverables complete
- No scope creep
- Ready for Sprint 3.2

---

## Next Sprint Preview

### Sprint 3.2: MemorySystem Core API - Part 2 (1-2 days)

**Scope:**
- Implement `forget()` method
- Implement `export()` method  
- Implement `sync()` method
- Additional validation
- More examples

**Dependencies:** Sprint 3.1 complete

---

## Resources

### Required
- Python environment ✅
- VS Code ✅
- Pytest ✅
- Existing components (Router, PolicyEngine, etc.) ✅

### Documentation
- SPEC.md (Memory System specification)
- AGENTS.md (Sprint process)
- Previous sprint reviews

---

## Stakeholder Communication

### Daily Updates
- End of Day 1: MemorySystem implementation status
- End of Day 2: Test results and sprint completion

### Sprint Review
- Demo: Running example script
- Metrics: Test coverage, performance
- Discussion: Lessons learned, next steps

---

## Sprint Checklist

### Pre-Sprint
- [x] Sprint plan approved
- [x] Dependencies verified (Router, PolicyEngine, etc. complete)
- [x] Environment ready
- [x] Previous sprint closed (Sprint 2.4)

### During Sprint
- [ ] Daily progress tracking
- [ ] Test-driven development
- [ ] Code review (self-review)
- [ ] Documentation as you go

### Post-Sprint
- [ ] All tests passing
- [ ] Example validated
- [ ] Sprint review created
- [ ] Next sprint planned
- [ ] Stakeholder approval

---

**Sprint Plan Status:** ✅ READY TO BEGIN

**Start Date:** November 6, 2025  
**Target Completion:** November 7, 2025  
**Next Review:** End of Day 1 (November 6, 2025)

---

**Planning Agent Sign-Off:** Sprint 3.1 plan complete and ready for approval.
