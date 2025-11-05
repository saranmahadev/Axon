# Sprint 2.4: Router & Policy Engine

**Phase:** 2 - Core Storage & Routing
**Sprint:** 2.4
**Start Date:** 2025-11-05
**Estimated Duration:** 4-5 days
**Status:** Planning

---

## SPRINT PLANNING

### Sprint Goal
Build the Router and Policy Engine that connects the Policy DSL to storage adapters, enabling intelligent tier selection, routing decisions, and sophisticated memory lifecycle management with a full scoring algorithm for promotion/demotion decisions.

### Context
Sprint 2.3 delivered a complete Policy DSL with:
- Policy base class and tier-specific policies (Ephemeral, Session, Persistent)
- MemoryConfig for multi-tier orchestration
- 6 pre-configured templates
- Full validation and serialization

Sprint 2.4 will make this actionable by implementing the routing logic that:
- Selects the appropriate tier for storage operations
- Resolves the correct adapter instance for each tier
- Manages memory lifecycle (promotion from ephemeral → session → persistent)
- Handles tier overflow and compaction triggers

This sprint is **critical** as it bridges the Policy DSL (configuration) with the actual storage operations that will be used by the MemorySystem API in Sprint 3.1.

---

### Scope

**Core Components:**
- [ ] **Router** - Main routing orchestrator
  - Policy-based tier selection
  - Adapter resolution and management
  - Route storage/recall/forget operations
  - Tier overflow handling

- [ ] **PolicyEngine** - Policy evaluation and lifecycle
  - Evaluate tier policies for storage decisions
  - **Full scoring algorithm** for promotion/demotion decisions
  - Scoring factors: access frequency, importance, recency, decay
  - Promotion logic (ephemeral → session → persistent)
  - Demotion logic (persistent → session → ephemeral)
  - TTL and capacity monitoring
  - Compaction triggers
  - Configurable scoring weights and thresholds

- [ ] **AdapterRegistry** - Adapter lifecycle management
  - Register and initialize adapters
  - Resolve adapter instances by tier
  - Connection pooling and reuse
  - Health checks and fallback

**Integration Points:**
- [ ] Integrate with Policy DSL (MemoryConfig, tier policies)
- [ ] Connect to existing adapters (Memory, Chroma, Redis)
- [ ] Prepare interfaces for MemorySystem API (Sprint 3.1)

**Testing & Examples:**
- [ ] Comprehensive test suite (70+ tests)
- [ ] Integration tests with real adapters
- [ ] Example scripts demonstrating routing scenarios

---

### Deliverables

**Implementation (4 core files):**
1. `src/axon/core/router.py` - Router class with tier selection and routing logic
2. `src/axon/core/policy_engine.py` - PolicyEngine for lifecycle management
3. `src/axon/core/scoring.py` - Scoring algorithm for promotion/demotion decisions
4. `src/axon/core/adapter_registry.py` - AdapterRegistry for adapter management

**Test Suite (5 test files, 90+ tests):**
1. `tests/unit/test_router.py` - Router tests (~25 tests)
2. `tests/unit/test_policy_engine.py` - PolicyEngine tests (~25 tests)
3. `tests/unit/test_scoring.py` - Scoring algorithm tests (~20 tests)
4. `tests/unit/test_adapter_registry.py` - AdapterRegistry tests (~15 tests)
5. `tests/integration/test_router_integration.py` - Integration tests (~10 tests)

**Example Scripts (4 files):**
1. `examples/13_router_basic.py` - Basic routing demonstration
2. `examples/14_router_promotion.py` - Promotion/demotion with scoring examples
3. `examples/15_router_multi_tier.py` - Complex multi-tier scenarios
4. `examples/16_router_scoring.py` - Scoring algorithm configuration and tuning

**Documentation:**
1. This sprint plan document
2. Inline docstrings for all classes/methods
3. Architecture decision records (ADRs)

---

### Success Criteria

**Functional Requirements:**
- [ ] Router correctly selects tier based on policy (default, explicit, overflow)
- [ ] PolicyEngine evaluates promotion conditions (access frequency, TTL expiration)
- [ ] PolicyEngine evaluates demotion conditions (importance drop, capacity pressure)
- [ ] AdapterRegistry manages adapter lifecycle (initialization, pooling, cleanup)
- [ ] Router handles tier overflow (session → persistent when session full)
- [ ] Router triggers compaction when thresholds reached
- [ ] All operations are async-ready

**Quality Requirements:**
- [ ] 90+ tests with 95%+ pass rate
- [ ] 90%+ code coverage on router/engine/registry/scoring
- [ ] All edge cases covered (missing tier, adapter failure, policy conflicts)
- [ ] Clear error messages for misconfigurations
- [ ] Performance: <1ms routing decision, <5ms scoring calculation, <10ms adapter resolution
- [ ] Scoring algorithm validated with diverse scenarios
- [ ] Configurable scoring weights with sensible defaults

**Integration Requirements:**
- [ ] Works with all existing adapters (Memory, Chroma, Redis)
- [ ] Integrates seamlessly with Policy DSL
- [ ] Clean interfaces for MemorySystem API (Sprint 3.1)

---

### Technical Design

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      MemorySystem API                       │
│                    (Sprint 3.1 - Future)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │         Router              │
         │  - select_tier()            │
         │  - route_store()            │
         │  - route_recall()           │
         │  - route_forget()           │
         └──────┬──────────────┬───────┘
                │              │
        ┌───────▼──────┐  ┌───▼──────────────┐
        │ PolicyEngine │  │ AdapterRegistry  │
        │              │  │                  │
        │ - evaluate() │  │ - get_adapter()  │
        │ - promote()  │  │ - register()     │
        │ - demote()   │  │ - initialize()   │
        └──────┬───────┘  └──────┬───────────┘
               │                 │
               │                 │
        ┌──────▼─────────────────▼─────────────┐
        │        MemoryConfig (Policy DSL)     │
        │  - EphemeralPolicy                   │
        │  - SessionPolicy                     │
        │  - PersistentPolicy                  │
        └──────────────────────────────────────┘
                       │
        ┌──────────────┴────────────────┐
        │                               │
   ┌────▼─────┐  ┌────▼─────┐  ┌──────▼──────┐
   │  Memory  │  │  Chroma  │  │   Redis     │
   │ Adapter  │  │ Adapter  │  │  Adapter    │
   └──────────┘  └──────────┘  └─────────────┘
```

#### Component Specifications

##### 1. Router (`src/axon/core/router.py`)

**Responsibility:** Orchestrate routing decisions and adapter operations

**Key Methods:**
```python
class Router:
    def __init__(self, config: MemoryConfig, registry: AdapterRegistry):
        """Initialize router with config and adapter registry."""
        
    def select_tier(
        self, 
        explicit_tier: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """Select appropriate tier for operation.
        
        Priority:
        1. Explicit tier if provided and valid
        2. Context-based selection (e.g., importance score)
        3. Default tier from config
        
        Returns tier name: "ephemeral" | "session" | "persistent"
        """
        
    async def route_store(
        self,
        entry: MemoryEntry,
        tier: Optional[str] = None
    ) -> str:
        """Route store operation to appropriate adapter.
        
        - Select tier
        - Get adapter from registry
        - Check capacity and overflow
        - Store entry
        - Trigger promotion/compaction if needed
        
        Returns entry ID
        """
        
    async def route_recall(
        self,
        query: str,
        tiers: Optional[List[str]] = None,
        k: int = 5
    ) -> List[MemoryEntry]:
        """Route recall operation across tiers.
        
        - Query specified tiers (or all configured tiers)
        - Merge and rank results
        - Update access metadata
        - Trigger promotion for hot entries
        
        Returns list of MemoryEntry
        """
        
    async def route_forget(
        self,
        entry_id: Optional[str] = None,
        filter: Optional[Filter] = None,
        tiers: Optional[List[str]] = None
    ) -> int:
        """Route forget operation to tiers.
        
        Returns count of deleted entries
        """
        
    def get_tier_stats(self) -> Dict[str, Dict]:
        """Get statistics for all tiers (count, capacity, etc.)."""
```

**Design Decisions:**
- Async-first for adapter operations (automatic on recall)
- Tier selection is synchronous (fast policy evaluation)
- Clear separation: routing logic vs. adapter operations
- Registry pattern for adapter management
- Fail-fast error handling with clear error messages

##### 2. PolicyEngine (`src/axon/core/policy_engine.py`)

**Responsibility:** Evaluate policies and manage memory lifecycle with intelligent scoring

**Key Methods:**
```python
class PolicyEngine:
    def __init__(self, config: MemoryConfig, scoring_config: Optional[ScoringConfig] = None):
        """Initialize with memory configuration and optional scoring config."""
        
    def should_promote(
        self,
        entry: MemoryEntry,
        current_tier: str,
        tier_stats: Optional[Dict] = None
    ) -> Optional[Tuple[str, float]]:
        """Determine if entry should be promoted to higher tier.
        
        Uses full scoring algorithm considering:
        - Access frequency (how often accessed)
        - Importance score (metadata.importance)
        - Recency (time since last access)
        - Access velocity (rate of access increase)
        - Semantic importance (future: embedding-based)
        
        Returns (target_tier, score) or None
        """
        
    def should_demote(
        self,
        entry: MemoryEntry,
        current_tier: str,
        tier_stats: Optional[Dict] = None
    ) -> Optional[Tuple[str, float]]:
        """Determine if entry should be demoted to lower tier.
        
        Uses full scoring algorithm considering:
        - Access decay (time since last access with decay function)
        - Importance drop (decreasing metadata.importance)
        - Capacity pressure (tier approaching limits)
        - Staleness (created long ago but rarely accessed)
        
        Returns (target_tier, score) or None
        """
        
    def calculate_promotion_score(
        self,
        entry: MemoryEntry,
        current_tier: str
    ) -> float:
        """Calculate promotion score using weighted algorithm.
        
        Score = w1*access_frequency + w2*importance + w3*recency + w4*velocity
        
        Returns score in range [0.0, 1.0]
        """
        
    def calculate_demotion_score(
        self,
        entry: MemoryEntry,
        current_tier: str,
        capacity_ratio: float
    ) -> float:
        """Calculate demotion score using weighted algorithm.
        
        Score = w1*access_decay + w2*importance_drop + w3*capacity_pressure + w4*staleness
        
        Returns score in range [0.0, 1.0]
        """
        
    def should_compact(
        self,
        tier: str,
        current_count: int
    ) -> bool:
        """Check if tier should trigger compaction.
        
        Returns True if compaction_threshold exceeded
        """
        
    def check_overflow(
        self,
        tier: str,
        current_count: int
    ) -> Optional[str]:
        """Check if tier should overflow to next tier.
        
        For SessionPolicy with overflow_to_persistent=True
        
        Returns target tier name or None
        """
        
    def get_ttl(self, tier: str) -> Optional[int]:
        """Get TTL in seconds for tier (None = no expiration)."""
        
    def get_promotion_path(self, current_tier: str) -> Optional[str]:
        """Get next tier in promotion path.
        
        ephemeral → session → persistent
        
        Returns None if already at top tier or promotion disabled
        """
        
    def get_demotion_path(self, current_tier: str) -> Optional[str]:
        """Get next tier in demotion path.
        
        persistent → session → ephemeral
        
        Returns None if already at bottom tier or demotion disabled
        """
```

**Design Decisions:**
- Pure policy evaluation (no I/O)
- Returns recommendations with scores, Router executes
- Full scoring algorithm with configurable weights
- Automatic promotion on recall (updates metadata and checks scores)
- Fail-fast error handling with clear messages

##### 3. ScoringEngine (`src/axon/core/scoring.py`)

**Responsibility:** Implement sophisticated scoring algorithms for promotion/demotion

**Core Algorithm Design:**

**Promotion Scoring Formula:**
```
promotion_score = (
    w_frequency * frequency_score +
    w_importance * importance_score +
    w_recency * recency_score +
    w_velocity * velocity_score
)

Where:
- frequency_score = normalize(access_count / time_alive)
- importance_score = metadata.importance (0.0-1.0)
- recency_score = 1.0 / (1.0 + hours_since_access)
- velocity_score = (recent_accesses_7d - recent_accesses_30d) / 7
```

**Demotion Scoring Formula:**
```
demotion_score = (
    w_decay * decay_score +
    w_drop * importance_drop_score +
    w_pressure * capacity_pressure_score +
    w_staleness * staleness_score
)

Where:
- decay_score = exponential_decay(hours_since_access, half_life=168h)
- importance_drop_score = max(0, initial_importance - current_importance)
- capacity_pressure_score = current_count / max_entries
- staleness_score = (1.0 - access_count / age_in_days)
```

**Key Classes:**
```python
@dataclass
class ScoringConfig:
    """Configuration for scoring algorithms."""
    
    # Promotion weights (sum to 1.0)
    promotion_weight_frequency: float = 0.35
    promotion_weight_importance: float = 0.30
    promotion_weight_recency: float = 0.20
    promotion_weight_velocity: float = 0.15
    
    # Demotion weights (sum to 1.0)
    demotion_weight_decay: float = 0.40
    demotion_weight_importance_drop: float = 0.25
    demotion_weight_capacity_pressure: float = 0.20
    demotion_weight_staleness: float = 0.15
    
    # Thresholds
    promotion_threshold: float = 0.70  # Score >= 0.70 triggers promotion
    demotion_threshold: float = 0.60   # Score >= 0.60 triggers demotion
    
    # Decay parameters
    access_decay_half_life_hours: float = 168.0  # 7 days
    min_access_count_for_promotion: int = 3
    
    # Velocity window (for calculating access velocity)
    velocity_recent_window_days: int = 7
    velocity_baseline_window_days: int = 30


class ScoringEngine:
    """Engine for calculating promotion and demotion scores."""
    
    def __init__(self, config: Optional[ScoringConfig] = None):
        """Initialize with optional custom scoring config."""
        self.config = config or ScoringConfig()
        self._validate_weights()
    
    def calculate_promotion_score(
        self,
        entry: MemoryEntry,
        current_tier: str,
        tier_stats: Optional[Dict] = None
    ) -> float:
        """Calculate promotion score for entry.
        
        Returns score in [0.0, 1.0]
        """
        
    def calculate_demotion_score(
        self,
        entry: MemoryEntry,
        current_tier: str,
        capacity_ratio: float
    ) -> float:
        """Calculate demotion score for entry.
        
        Returns score in [0.0, 1.0]
        """
    
    def _calculate_frequency_score(self, entry: MemoryEntry) -> float:
        """Access frequency normalized by time alive."""
        
    def _calculate_recency_score(self, entry: MemoryEntry) -> float:
        """Recency score using inverse time decay."""
        
    def _calculate_velocity_score(self, entry: MemoryEntry) -> float:
        """Access velocity (acceleration of access pattern)."""
        
    def _calculate_decay_score(self, entry: MemoryEntry) -> float:
        """Exponential decay based on time since last access."""
        
    def _calculate_importance_drop_score(self, entry: MemoryEntry) -> float:
        """Score based on decrease in importance over time."""
        
    def _calculate_staleness_score(self, entry: MemoryEntry) -> float:
        """Score based on low access relative to age."""
    
    def explain_score(
        self,
        entry: MemoryEntry,
        score_type: Literal["promotion", "demotion"],
        current_tier: str
    ) -> Dict[str, Any]:
        """Generate detailed explanation of score calculation.
        
        Returns breakdown of all components for debugging/observability.
        """
```

**Design Decisions:**
- Configurable weights with sensible defaults
- All scores normalized to [0.0, 1.0]
- Promotion threshold: 0.70 (requires strong signal)
- Demotion threshold: 0.60 (easier to demote than promote)
- Exponential decay for recency (realistic memory patterns)
- Velocity detection (catch trending memories)
- Explainability via explain_score() method

##### 4. AdapterRegistry (`src/axon/core/adapter_registry.py`)

**Responsibility:** Manage adapter instances and lifecycle

**Key Methods:**
```python
class AdapterRegistry:
    def __init__(self):
        """Initialize empty registry."""
        
    def register(
        self,
        tier: str,
        adapter_type: str,
        adapter_instance: Optional[StorageAdapter] = None,
        adapter_config: Optional[Dict] = None
    ):
        """Register adapter for tier.
        
        Can provide:
        - Existing adapter_instance, OR
        - adapter_config to create instance
        """
        
    async def get_adapter(self, tier: str) -> StorageAdapter:
        """Get adapter for tier.
        
        - Returns cached instance if available
        - Initializes on first access if needed
        - Raises error if tier not registered
        """
        
    async def initialize_all(self):
        """Initialize all registered adapters."""
        
    async def close_all(self):
        """Close all adapter connections."""
        
    def is_registered(self, tier: str) -> bool:
        """Check if tier has registered adapter."""
        
    def get_all_tiers(self) -> List[str]:
        """Get list of all registered tier names."""
```

**Design Decisions:**
- Lazy initialization (create on first use)
- Singleton per tier (one adapter instance per tier)
- Support both pre-configured and dynamic initialization
- Graceful shutdown with close_all()

---

### File Structure

```
src/axon/core/
  router.py                     # Router class (300-350 lines)
  policy_engine.py              # PolicyEngine class (250-300 lines)
  scoring.py                    # ScoringEngine + ScoringConfig (300-350 lines)
  adapter_registry.py           # AdapterRegistry class (150-200 lines)
  __init__.py                   # Export Router, PolicyEngine, ScoringEngine, AdapterRegistry

tests/unit/
  test_router.py                # Router tests (~25 tests, 400+ lines)
  test_policy_engine.py         # PolicyEngine tests (~25 tests, 400+ lines)
  test_scoring.py               # Scoring algorithm tests (~20 tests, 400+ lines)
  test_adapter_registry.py      # AdapterRegistry tests (~15 tests, 300+ lines)

tests/integration/
  test_router_integration.py    # Integration tests (~10 tests, 350+ lines)

examples/
  13_router_basic.py            # Basic routing (150+ lines)
  14_router_promotion.py        # Promotion/demotion (250+ lines)
  15_router_multi_tier.py       # Multi-tier scenarios (250+ lines)
  16_router_scoring.py          # Scoring configuration (200+ lines)
```

**Estimated Lines of Code:**
- Implementation: ~1,200 lines
- Tests: ~1,850 lines
- Examples: ~850 lines
- **Total: ~3,900 lines**

---

### Dependencies

**Internal:**
- `src/axon/core/config.py` - MemoryConfig, tier policies
- `src/axon/core/policy.py` - Policy base class
- `src/axon/models/entry.py` - MemoryEntry
- `src/axon/models/filter.py` - Filter
- `src/axon/adapters/base.py` - StorageAdapter ABC
- `src/axon/adapters/memory.py` - InMemoryAdapter (for tests)
- `src/axon/adapters/chroma.py` - ChromaAdapter (for integration tests)
- `src/axon/adapters/redis.py` - RedisAdapter (for integration tests)

**External:**
- None (uses existing dependencies)

---

### Estimated Complexity

**Overall: High**

**Breakdown:**
- **Router**: Medium
  - Tier selection logic: straightforward
  - Adapter coordination: moderate
  - Error handling: fail-fast with clear messages
  
- **PolicyEngine**: High
  - Integration with ScoringEngine: moderate complexity
  - Promotion/demotion decision logic: requires careful orchestration
  - Multiple evaluation criteria: requires careful design
  - Edge cases: many scenarios to consider
  
- **ScoringEngine**: High
  - Full scoring algorithm: complex mathematical formulas
  - Weight balancing: requires testing and tuning
  - Velocity calculation: time-series analysis
  - Exponential decay: careful implementation
  - Normalization: ensure all scores in [0.0, 1.0]
  - Performance: must be fast (<5ms per score)
  
- **AdapterRegistry**: Low-Medium
  - Registry pattern: well-established
  - Lazy initialization: straightforward
  - Connection management: standard async patterns

**Risk Factors:**
- Scoring algorithm accuracy (requires validation with real data)
- Scoring performance (must calculate quickly)
- Weight tuning (finding optimal defaults)
- Multiple adapters interacting (race conditions?)
- Promotion/demotion timing (when to execute - automatic on recall)
- Capacity monitoring (real-time vs. cached stats?)

---

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scoring algorithm accuracy | High | Medium | Test with diverse scenarios, provide tuning guide |
| Scoring performance overhead | Medium | Medium | Optimize calculations, cache where possible |
| Weight tuning complexity | Medium | High | Provide sensible defaults, extensive documentation |
| Promotion/demotion thrashing | High | Medium | Add cooldown periods, minimum score thresholds |
| Adapter state synchronization | High | Medium | Use adapter's own count/stats methods, don't cache |
| Race conditions in multi-tier ops | Medium | Low | Single-threaded assumption for MVP, document |
| Config changes during runtime | Low | Low | Document as read-only after initialization |

**Mitigation Strategy:**
1. **Start with defaults**: Ship with well-tested default weights
2. **Test thoroughly**: Unit tests for each scoring component, integration tests with real patterns
3. **Document clearly**: Explain scoring algorithm, provide tuning guide
4. **Monitor performance**: Add timing logs for scoring operations
5. **Validate scientifically**: Test scoring with synthetic data (high frequency, low frequency, importance changes)
6. **Provide tools**: Add explain_score() for debugging scoring decisions

---

### Testing Strategy

**Unit Tests (80 tests):**

**Router (25 tests):**
- Tier selection (8 tests)
  - Default tier selection
  - Explicit tier override
  - Invalid tier handling
  - Context-based selection
  - Tier not configured error
  - Importance-based routing
  - Overflow tier selection
  - Multi-tier availability

- Routing operations (12 tests)
  - route_store success
  - route_store with overflow
  - route_store with automatic promotion check
  - route_recall single tier
  - route_recall multi-tier
  - route_recall with ranking
  - route_recall triggers promotion
  - route_forget by ID
  - route_forget by filter
  - route_forget across tiers
  - Adapter error handling (fail-fast)
  - get_tier_stats

- Integration points (5 tests)
  - Registry integration
  - PolicyEngine integration
  - ScoringEngine integration
  - Config validation
  - Adapter lifecycle

**PolicyEngine (25 tests):**
- Promotion logic (10 tests)
  - should_promote with high score (>0.70)
  - should_promote with low score (no promotion)
  - should_promote when promotion disabled
  - should_promote from ephemeral to session
  - should_promote from session to persistent
  - should_promote at top tier (no-op)
  - get_promotion_path
  - Promotion with tier stats consideration
  - Promotion threshold configuration
  - Promotion cooldown period

- Demotion logic (8 tests)
  - should_demote with high decay score
  - should_demote with capacity pressure
  - should_demote when demotion disabled
  - should_demote at bottom tier (no-op)
  - get_demotion_path
  - Demotion threshold configuration
  - Demotion with importance drop
  - Demotion priority ordering

- Capacity & lifecycle (7 tests)
  - should_compact threshold check
  - check_overflow for session tier
  - check_overflow when not configured
  - get_ttl for each tier
  - TTL None handling
  - Compaction strategy selection
  - Integration with ScoringEngine

**ScoringEngine (20 tests):**
- Promotion scoring (8 tests)
  - calculate_promotion_score with high frequency
  - calculate_promotion_score with high importance
  - calculate_promotion_score with high recency
  - calculate_promotion_score with high velocity
  - Promotion score weight validation (sum to 1.0)
  - Promotion score normalization (0.0-1.0)
  - Promotion score with custom weights
  - Promotion threshold comparison

- Demotion scoring (8 tests)
  - calculate_demotion_score with access decay
  - calculate_demotion_score with importance drop
  - calculate_demotion_score with capacity pressure
  - calculate_demotion_score with staleness
  - Demotion score weight validation (sum to 1.0)
  - Demotion score normalization (0.0-1.0)
  - Demotion score with custom weights
  - Exponential decay calculation

- Score components (4 tests)
  - Frequency score calculation
  - Recency score calculation
  - Velocity score calculation
  - Staleness score calculation

**AdapterRegistry (15 tests):**
- Registration (5 tests)
  - register with instance
  - register with config
  - register duplicate tier (override)
  - is_registered check
  - get_all_tiers

- Adapter resolution (5 tests)
  - get_adapter lazy init
  - get_adapter cached
  - get_adapter unregistered tier error (fail-fast)
  - get_adapter initialization error (fail-fast)
  - Concurrent get_adapter calls

- Lifecycle (5 tests)
  - initialize_all
  - close_all
  - Partial initialization failure (fail-fast)
  - Close with errors
  - Cleanup on context manager exit

**Integration Tests (10 tests):**
- End-to-end routing (5 tests)
  - Store and recall from single tier
  - Store and recall from multiple tiers
  - Automatic promotion flow (ephemeral → session on high score)
  - Overflow flow (session → persistent when full)
  - Demotion flow (persistent → session on low activity)

- Real adapter integration (3 tests)
  - With InMemoryAdapter
  - With ChromaAdapter (requires Chroma running)
  - With RedisAdapter (requires Redis running)

- Scoring in action (2 tests)
  - High-frequency access triggers promotion
  - Capacity pressure triggers demotion

---

### Example Scenarios

**Example 1: Basic Routing (`examples/13_router_basic.py`)**
```python
from axon.core import Router, AdapterRegistry, templates
from axon.adapters import InMemoryAdapter
from axon.models import MemoryEntry

# Setup
config = templates.STANDARD_CONFIG
registry = AdapterRegistry()
registry.register("ephemeral", "memory", InMemoryAdapter())
registry.register("session", "memory", InMemoryAdapter())
registry.register("persistent", "memory", InMemoryAdapter())

router = Router(config, registry)

# Store to default tier
entry = MemoryEntry(text="User likes sci-fi", metadata={"user_id": "u123"})
entry_id = await router.route_store(entry)

# Store to explicit tier
entry2 = MemoryEntry(text="Important note", metadata={"importance": 0.9})
entry_id2 = await router.route_store(entry2, tier="persistent")

# Recall from all tiers
results = await router.route_recall("sci-fi movies", k=5)
```

**Example 2: Promotion with Scoring (`examples/14_router_promotion.py`)**
```python
from axon.core import Router, ScoringEngine, ScoringConfig

# Configure custom scoring weights
scoring_config = ScoringConfig(
    promotion_weight_frequency=0.40,  # Emphasize frequency
    promotion_weight_importance=0.30,
    promotion_weight_recency=0.20,
    promotion_weight_velocity=0.10,
    promotion_threshold=0.75  # Higher threshold
)

scoring_engine = ScoringEngine(scoring_config)
policy_engine = PolicyEngine(config, scoring_config)
router = Router(config, registry, policy_engine)

# Store low-importance entry in ephemeral
entry = MemoryEntry(
    text="Random thought",
    metadata={"importance": 0.2, "access_count": 0}
)
await router.route_store(entry, tier="ephemeral")

# Simulate frequent access (increases frequency and recency scores)
for _ in range(10):
    results = await router.route_recall("random thought")
    # Router automatically:
    # 1. Updates access metadata (access_count++, last_accessed_at)
    # 2. Calculates promotion score
    # 3. If score >= 0.75, promotes to session tier
    
# Check promotion score
score = scoring_engine.calculate_promotion_score(entry, "ephemeral")
explanation = scoring_engine.explain_score(entry, "promotion", "ephemeral")
print(f"Promotion score: {score:.3f}")
print(f"Breakdown: {explanation}")
```

**Example 3: Multi-tier Query with Scoring (`examples/15_router_multi_tier.py`)**
```python
# Query across all tiers with ranking
results = await router.route_recall(
    query="product features",
    tiers=["ephemeral", "session", "persistent"],
    k=10
)

# Results ranked by:
# 1. Semantic similarity (from vector search)
# 2. Recency (last_accessed_at)
# 3. Importance (metadata.importance)
# 4. Tier priority (persistent > session > ephemeral)
```

**Example 4: Scoring Configuration (`examples/16_router_scoring.py`)**
```python
from axon.core import ScoringConfig, ScoringEngine

# Show default weights
default_config = ScoringConfig()
print(f"Default promotion weights:")
print(f"  Frequency: {default_config.promotion_weight_frequency}")
print(f"  Importance: {default_config.promotion_weight_importance}")
print(f"  Recency: {default_config.promotion_weight_recency}")
print(f"  Velocity: {default_config.promotion_weight_velocity}")

# Custom configuration for different use cases
high_frequency_config = ScoringConfig(
    promotion_weight_frequency=0.50,  # Emphasize frequency
    promotion_weight_importance=0.20,
    promotion_weight_recency=0.20,
    promotion_weight_velocity=0.10
)

importance_first_config = ScoringConfig(
    promotion_weight_frequency=0.20,
    promotion_weight_importance=0.50,  # Emphasize importance
    promotion_weight_recency=0.15,
    promotion_weight_velocity=0.15
)

# Test scoring with synthetic data
test_entry = MemoryEntry(
    text="Test memory",
    metadata={
        "importance": 0.8,
        "access_count": 15,
        "created_at": "2025-11-01T10:00:00Z",
        "last_accessed_at": "2025-11-05T14:30:00Z"
    }
)

# Compare scores with different configs
for name, config in [
    ("Default", default_config),
    ("Frequency-First", high_frequency_config),
    ("Importance-First", importance_first_config)
]:
    engine = ScoringEngine(config)
    score = engine.calculate_promotion_score(test_entry, "ephemeral")
    print(f"{name}: {score:.3f}")
```

---

### Next Sprint Dependencies

**Sprint 3.1 (MemorySystem Core API - Part 1) depends on:**
- ✅ Router.route_store() - for store() method
- ✅ Router.route_recall() - for recall() method
- ✅ AdapterRegistry - for adapter management
- ✅ PolicyEngine - for lifecycle hooks

**Sprint 2.4 enables:**
- Complete separation of concerns (config → routing → storage)
- Testable routing logic independent of adapters
- Foundation for observability (routing decisions = trace events)
- Clear extension points for advanced features (custom routing strategies)

---

### Estimated Timeline

**Day 1:**
- ✅ Planning complete (this document)
- [ ] User approval
- [ ] AdapterRegistry implementation (foundation)
- [ ] AdapterRegistry tests (15 tests)
- [ ] Basic Router skeleton

**Day 2:**
- [ ] ScoringEngine implementation (core algorithm)
- [ ] ScoringConfig dataclass
- [ ] ScoringEngine tests (20 tests)
- [ ] Scoring algorithm validation

**Day 3:**
- [ ] PolicyEngine implementation (with ScoringEngine integration)
- [ ] PolicyEngine tests (25 tests)
- [ ] Router implementation (basic routing)
- [ ] Router tests (25 tests, part 1)

**Day 4:**
- [ ] Router implementation complete (promotion/demotion integration)
- [ ] Router tests complete (part 2)
- [ ] Integration tests (10 tests)
- [ ] End-to-end validation

**Day 5:**
- [ ] Example scripts (4 scripts)
- [ ] Scoring tuning and validation
- [ ] Documentation
- [ ] Performance testing
- [ ] Sprint review

**Buffer:** 0.5 days for edge cases, performance optimization, and scoring weight tuning

---

## APPROVAL CHECKPOINT

**Status:** ✋ AWAITING USER APPROVAL

Before proceeding to implementation, please review:
1. Architecture design (Router, PolicyEngine, AdapterRegistry)
2. Component responsibilities and interfaces
3. Testing strategy (75 total tests)
4. Example scenarios
5. Timeline and deliverables

**Questions for consideration:**
- ✅ **DECIDED: Automatic promotion on recall** - Router updates metadata and checks scores automatically
- ✅ **DECIDED: Single-threaded assumption** - Document thread-safety, add locks in future if needed
- ✅ **DECIDED: Full scoring algorithm** - Implement complete weighted scoring with frequency, importance, recency, velocity
- ✅ **DECIDED: Fail-fast error handling** - Clear error messages, no silent fallbacks
- Should scoring weights be tunable per-tier or global?
- Should we add a scoring cache to avoid recalculating frequently?
- Should velocity calculation use sliding windows or fixed periods?

**Ready to proceed?** Type "APPROVED" or provide feedback for adjustments.

---

## Implementation Notes (to be filled during sprint)

### Day 1 Progress:
- TBD

### Day 2 Progress:
- TBD

### Day 3 Progress:
- TBD

### Issues Encountered:
- TBD

### Decisions Made:
- TBD

---

**End of Sprint 2.4 Planning Document**
