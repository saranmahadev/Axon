# Sprint 3.3 Plan: Basic Summarization

**Sprint Goal:** Implement LLM-based summarization and count-based compaction to reduce memory footprint

**Phase:** Phase 3 - Core API & Operations (MVP 0.1 completion)  
**Duration:** 2 days  
**Complexity:** Medium  
**Status:** Planning

---

## Sprint Goal

Implement a basic summarization pipeline that uses LLMs to compact groups of memories into concise summaries, reducing storage footprint while preserving key information. Focus on count-based compaction strategy first.

---

## Scope

### ✅ In Scope
- [ ] **Summarizer Interface (ABC)** - Abstract base class for all summarizers
- [ ] **LLMSummarizer Implementation** - OpenAI-based summarization
- [ ] **compact() Method** - MemorySystem method for triggering compaction
- [ ] **Count-based Compaction** - Compact when tier exceeds entry threshold
- [ ] **Unit Tests** - Comprehensive test coverage for summarizer and compact()
- [ ] **Integration Tests** - Test with real LLM and adapters

### ❌ Out of Scope (Future Sprints)
- Semantic redundancy detection
- Importance-based compaction
- Time-based compaction triggers
- Custom compaction strategies
- Incremental summarization
- Multi-pass summarization

---

## Deliverables

### 1. Summarizer Interface & Implementation

**File: `src/axon/core/summarizer.py`** (~200 lines)

#### Summarizer ABC
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.entry import MemoryEntry

class Summarizer(ABC):
    """Abstract base class for memory summarization."""
    
    @abstractmethod
    async def summarize(
        self,
        entries: List[MemoryEntry],
        context: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> str:
        """
        Summarize a list of memory entries into a single text.
        
        Args:
            entries: List of memory entries to summarize
            context: Optional context to guide summarization
            max_length: Maximum length of summary in characters
            
        Returns:
            Summarized text
        """
        pass
    
    def summarize_sync(
        self,
        entries: List[MemoryEntry],
        context: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> str:
        """Synchronous wrapper for summarize()."""
        pass
```

#### LLMSummarizer Implementation
```python
class LLMSummarizer(Summarizer):
    """LLM-based summarization using OpenAI or compatible APIs."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 500
    ):
        """Initialize LLM summarizer."""
        pass
    
    async def summarize(
        self,
        entries: List[MemoryEntry],
        context: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> str:
        """Use LLM to create concise summary of entries."""
        # Build prompt from entries
        # Call OpenAI API
        # Return summary text
        pass
    
    def _build_prompt(
        self,
        entries: List[MemoryEntry],
        context: Optional[str]
    ) -> str:
        """Build summarization prompt."""
        pass
```

**Key Features:**
- OpenAI API integration
- Configurable model and temperature
- Context-aware summarization
- Token limit handling
- Error handling and retries

---

### 2. MemorySystem compact() Method

**File: `src/axon/core/memory_system.py`** (~150 lines added)

```python
async def compact(
    self,
    tier: Optional[str] = None,
    strategy: str = "count",
    threshold: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Compact memories in a tier by summarizing groups of entries.
    
    Args:
        tier: Tier to compact (None = all tiers that need it)
        strategy: Compaction strategy ("count", "semantic", "importance", "time")
        threshold: Entry count threshold (overrides policy default)
        dry_run: If True, return what would be compacted without doing it
        
    Returns:
        {
            "tier": "persistent",
            "entries_before": 15000,
            "entries_after": 1500,
            "summaries_created": 135,
            "reduction_ratio": 0.9,  # 90% reduction
            "dry_run": false
        }
    
    Raises:
        ValueError: If tier invalid or strategy not supported
        
    Example:
        >>> # Compact persistent tier when over 10,000 entries
        >>> result = await memory_system.compact(
        ...     tier="persistent",
        ...     strategy="count",
        ...     threshold=10000
        ... )
        >>> print(f"Reduced from {result['entries_before']} to {result['entries_after']}")
    """
    # Validate tier and strategy
    # Determine which tiers need compaction
    # For each tier:
    #   - Get entries sorted by importance/date
    #   - Group entries for summarization (batches of ~100)
    #   - Use summarizer to create summaries
    #   - Replace original entries with summary entries
    #   - Update provenance chain
    # Create COMPACT trace event
    # Return statistics
```

**Compaction Logic (Count-based):**

1. **Check Threshold**
   - Get current entry count from adapter
   - Compare to `compaction_threshold` from policy
   - Skip if below threshold

2. **Select Entries for Compaction**
   - Sort by importance (low to high) and date (old to new)
   - Select bottom 50% of entries for compaction
   - Keep high-importance and recent entries

3. **Group Entries**
   - Create batches of 50-100 entries
   - Group by temporal proximity or topic similarity
   - Maintain chronological order within groups

4. **Summarize Each Group**
   - Call `summarizer.summarize(entries, context=...)`
   - Create new MemoryEntry for summary
   - Set metadata: `entry_type=SUMMARY`, aggregate importance, etc.
   - Add provenance tracking which entries were summarized

5. **Replace in Storage**
   - Delete original entries
   - Save summary entries
   - Update statistics

6. **Return Results**
   - Entries before/after counts
   - Number of summaries created
   - Reduction ratio
   - Execution time

---

### 3. Integration with Policy Engine

**File: `src/axon/core/policy_engine.py`** (~50 lines added)

```python
def should_compact(
    self,
    tier_name: str,
    current_count: int
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if a tier should be compacted.
    
    Args:
        tier_name: Name of tier to check
        current_count: Current entry count in tier
        
    Returns:
        (should_compact, details)
        
    Example:
        >>> should, details = engine.should_compact("persistent", 15000)
        >>> if should:
        ...     print(f"Compact {tier_name}: {details['reason']}")
    """
    # Get policy for tier
    # Check if compaction_threshold is set
    # Check if current_count >= threshold
    # Return decision with details
```

---

### 4. Unit Tests

**File: `tests/unit/test_summarizer.py`** (~400 lines)

#### TestSummarizerInterface (5 tests)
- `test_cannot_instantiate_abc` - ABC enforcement
- `test_summarizer_has_required_methods` - Interface contract
- `test_sync_wrapper_calls_async` - Sync wrapper works
- `test_llm_summarizer_implements_interface` - Implementation check
- `test_summarizer_with_empty_list_raises` - Validation

#### TestLLMSummarizer (10 tests)
- `test_initialization` - Basic init
- `test_initialization_invalid_api_key` - Validation
- `test_initialization_invalid_model` - Model validation
- `test_summarize_basic` - Simple summarization
- `test_summarize_with_context` - Context-aware
- `test_summarize_with_max_length` - Length limit
- `test_summarize_single_entry` - Edge case
- `test_summarize_many_entries` - Large batch
- `test_summarize_preserves_key_info` - Quality check
- `test_summarize_error_handling` - API error handling

#### TestPromptBuilding (5 tests)
- `test_build_prompt_basic` - Prompt structure
- `test_build_prompt_with_context` - Context injection
- `test_build_prompt_with_metadata` - Include metadata
- `test_build_prompt_truncates_long_text` - Token management
- `test_build_prompt_sorts_by_date` - Chronological order

**File: `tests/unit/test_memory_system.py`** (add ~300 lines)

#### TestCompactMethod (12 tests)
- `test_compact_basic` - Basic compaction
- `test_compact_specific_tier` - Single tier
- `test_compact_count_based` - Count strategy
- `test_compact_with_threshold_override` - Custom threshold
- `test_compact_dry_run` - Dry run mode
- `test_compact_below_threshold_skips` - Skip when not needed
- `test_compact_invalid_tier_raises` - Validation
- `test_compact_invalid_strategy_raises` - Strategy validation
- `test_compact_creates_summary_entries` - Entry creation
- `test_compact_updates_provenance` - Provenance tracking
- `test_compact_creates_trace_event` - Tracing
- `test_compact_returns_statistics` - Statistics format

---

### 5. Integration Tests

**File: `tests/integration/test_compaction_integration.py`** (~200 lines)

#### TestCompactionWorkflow (5 tests)
- `test_compact_with_real_llm` - End-to-end with OpenAI
- `test_compact_with_chroma_adapter` - Vector DB integration
- `test_compact_reduces_entry_count` - Verify reduction
- `test_compact_preserves_searchability` - Summaries are searchable
- `test_compact_maintains_provenance` - Provenance chain intact

---

## File Structure

```
src/axon/core/
  summarizer.py          # New: Summarizer ABC + LLMSummarizer (200 lines)
  memory_system.py       # Modified: +compact() method (150 lines)
  policy_engine.py       # Modified: +should_compact() (50 lines)
  __init__.py           # Modified: Export Summarizer

tests/unit/
  test_summarizer.py     # New: Summarizer tests (400 lines)
  test_memory_system.py  # Modified: +TestCompactMethod (300 lines)

tests/integration/
  test_compaction_integration.py  # New: Integration tests (200 lines)

examples/
  09_memory_compaction_demo.py    # New: Example usage (200 lines)
```

---

## Dependencies

### Depends On
- Sprint 3.1 (store/recall) - ✅ Complete
- Sprint 3.2 (export/import/sync) - ✅ Complete
- Existing adapters (InMemory, Chroma, Redis, etc.) - ✅ Available
- Existing embedders (OpenAI) - ✅ Available

### Required Packages
- `openai>=1.0.0` - Already in pyproject.toml ✅
- `pydantic>=2.0.0` - Already in pyproject.toml ✅
- `asyncio` - Python stdlib ✅

### New Imports
```python
# In memory_system.py
from .summarizer import Summarizer, LLMSummarizer

# In __init__.py
from .summarizer import Summarizer, LLMSummarizer
```

---

## Success Criteria

### Functional Requirements
- ✅ Summarizer ABC is properly abstract
- ✅ LLMSummarizer creates coherent summaries
- ✅ compact() reduces entry count by >50%
- ✅ Summaries preserve key information
- ✅ Provenance tracks summarized entries
- ✅ Count-based strategy works correctly
- ✅ Dry run mode doesn't modify data
- ✅ Integration with policy engine

### Quality Requirements
- ✅ All unit tests pass (20+ tests)
- ✅ Integration tests pass (5+ tests)
- ✅ Code coverage ≥85% for new code
- ✅ No regressions in existing tests
- ✅ Type hints complete
- ✅ Docstrings for all public methods
- ✅ Example script demonstrates usage

### Performance Requirements
- ✅ Summarize 100 entries in <10 seconds
- ✅ Compact 10,000 entries in <2 minutes
- ✅ Memory usage stays reasonable during compaction

---

## Estimated Complexity: **Medium**

### Complexity Factors

**High Complexity:**
- LLM integration (API calls, error handling, retries)
- Prompt engineering for good summaries
- Entry grouping logic (which entries to summarize together)
- Provenance chain management

**Medium Complexity:**
- Summarizer interface design
- compact() method implementation
- Policy integration
- Statistics calculation

**Low Complexity:**
- Dry run logic
- Basic validation
- Trace event creation

---

## Risks

### Risk 1: LLM API Reliability
**Issue:** OpenAI API may fail, rate limit, or timeout

**Mitigation:**
- Implement exponential backoff retry logic
- Set reasonable timeouts
- Provide fallback to simple concatenation
- Add detailed error messages
- Test with mock LLM responses

### Risk 2: Summary Quality
**Issue:** LLM summaries may lose important information

**Mitigation:**
- Careful prompt engineering
- Include importance scores in prompt
- Test with various entry types
- Add quality validation
- Make summary length configurable

### Risk 3: Performance
**Issue:** Compacting large tiers may be slow

**Mitigation:**
- Batch LLM calls (summarize multiple groups in parallel)
- Add progress callbacks
- Implement incremental compaction
- Test with realistic data volumes
- Optimize entry grouping algorithm

### Risk 4: Provenance Tracking
**Issue:** Complex to track which entries were summarized

**Mitigation:**
- Design clear provenance schema
- Store entry IDs in summary metadata
- Add helper methods for provenance queries
- Test provenance chain integrity

---

## Implementation Strategy

### Day 1: Core Implementation
1. **Morning (3-4 hours)**
   - Create `summarizer.py` with ABC
   - Implement `LLMSummarizer` class
   - Write prompt building logic
   - Add OpenAI API integration

2. **Afternoon (3-4 hours)**
   - Implement `compact()` in MemorySystem
   - Add count-based compaction logic
   - Integrate with policy engine
   - Add dry run support

### Day 2: Testing & Polish
1. **Morning (3-4 hours)**
   - Write all unit tests (700 lines)
   - Test summarizer thoroughly
   - Test compact() method
   - Fix any bugs found

2. **Afternoon (3-4 hours)**
   - Write integration tests
   - Create example script
   - Run full test suite
   - Document any issues
   - Sprint review document

---

## Acceptance Criteria

### Must Have (Required)
- ✅ Summarizer ABC with abstract methods
- ✅ LLMSummarizer with OpenAI integration
- ✅ compact() method in MemorySystem
- ✅ Count-based compaction strategy
- ✅ 20+ unit tests all passing
- ✅ 5+ integration tests passing
- ✅ No regressions (all 553 existing tests pass)
- ✅ Code coverage ≥85% for new modules
- ✅ Documentation for all public APIs

### Should Have (Desired)
- ✅ Example script demonstrating compaction
- ✅ Dry run mode for testing
- ✅ Progress callbacks for long operations
- ✅ Detailed statistics reporting
- ✅ Error recovery mechanisms

### Could Have (Nice to Have)
- ⏸️ Parallel summarization
- ⏸️ Custom summarization templates
- ⏸️ Summary quality metrics
- ⏸️ Incremental compaction

---

## Testing Strategy

### Unit Tests
1. **Summarizer Interface** - ABC behavior, contracts
2. **LLMSummarizer** - Initialization, summarization, error handling
3. **Prompt Building** - Prompt quality, context injection
4. **compact() Method** - Strategy logic, validation, statistics
5. **Policy Integration** - should_compact() logic

### Integration Tests
1. **End-to-End Compaction** - Real LLM + adapters
2. **Multi-Tier Compaction** - Compact multiple tiers
3. **Searchability** - Summaries are semantically searchable
4. **Provenance** - Chain integrity maintained

### Manual Testing
1. Run example script with real OpenAI key
2. Verify summary quality manually
3. Check reduction ratios are reasonable
4. Test with different tier sizes

---

## Documentation Plan

### Code Documentation
- Docstrings for Summarizer ABC
- Docstrings for LLMSummarizer
- Docstrings for compact() method
- Usage examples in docstrings
- Type hints everywhere

### Example Script
- Basic compaction workflow
- Custom threshold usage
- Dry run demonstration
- Statistics interpretation
- Error handling

### Sprint Review
- Implementation summary
- Test results
- Metrics (coverage, performance)
- Lessons learned
- Next steps

---

## Definition of Done

- [ ] Summarizer ABC created with abstract methods
- [ ] LLMSummarizer implemented with OpenAI integration
- [ ] compact() method added to MemorySystem
- [ ] Count-based compaction strategy working
- [ ] 20+ unit tests created and passing
- [ ] 5+ integration tests created and passing
- [ ] All 553+ existing tests still pass
- [ ] Code coverage ≥85% for summarizer.py
- [ ] Code coverage ≥88% for memory_system.py (maintained)
- [ ] Example script created and tested
- [ ] Sprint review document created
- [ ] No syntax errors, no type errors
- [ ] All public APIs documented

---

## Version History

- **v1.0** (2025-01-04): Initial sprint plan created

---

**This plan follows the AGENTS.md process and is ready for approval.**

**Awaiting user approval to proceed with implementation.**
