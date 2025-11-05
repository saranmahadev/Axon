# Sprint 2.3: Policy DSL & Configuration - Planning Document

**Sprint Goal:** Implement the Policy DSL system that defines tier selection rules, TTL policies, and routing logic for the MemorySystem's multi-tier architecture.

**Start Date:** 2025-11-05  
**Estimated Duration:** 2 days  
**Status:** Planning

---

## 📋 Sprint Overview

### Context
With all storage adapters now complete (InMemory, Chroma, Qdrant, Pinecone, Redis), we need the configuration layer that determines:
- Which adapter stores which type of memory
- How long memories persist in each tier
- When to promote/demote between tiers
- Compaction and eviction strategies

The Policy DSL provides a declarative way to configure these rules without hardcoding logic.

### Why Policy DSL?
- **Declarative Configuration:** Define behavior through config, not code
- **Flexibility:** Different applications have different memory needs
- **Validation:** Catch configuration errors early
- **Serialization:** Store/load policies from JSON/YAML
- **Type Safety:** Pydantic models ensure correctness

---

## 🎯 Sprint Goal

**Primary Objective:**  
Build the Policy configuration system that enables declarative tier management, TTL rules, and routing logic for the MemorySystem.

**Success Criteria:**
- [ ] Policy base class with validation
- [ ] EphemeralPolicy, SessionPolicy, PersistentPolicy implementations
- [ ] Configuration serialization (to/from dict/JSON)
- [ ] Policy validation and error handling
- [ ] Default policy templates
- [ ] 95%+ test pass rate
- [ ] 60%+ code coverage
- [ ] 2-3 working example configurations

---

## 📦 Scope

### Core Components to Implement:

#### 1. **Policy Base Class** (`src/axon/core/policy.py`)
```python
class Policy(BaseModel):
    """Base policy for tier configuration."""
    tier_name: str  # "ephemeral", "session", "persistent"
    adapter_type: str  # "redis", "chroma", "pinecone", etc.
    ttl_seconds: Optional[int] = None  # None = no expiration
    max_entries: Optional[int] = None  # Capacity limit
    compaction_threshold: Optional[int] = None  # When to compact
    eviction_strategy: str = "ttl"  # "ttl", "lru", "fifo"
```

#### 2. **Tier-Specific Policies**

**EphemeralPolicy** (src/axon/core/policies/ephemeral.py)
- Short-lived memories (seconds to minutes)
- Always uses Redis or InMemory
- Aggressive TTL (default: 60 seconds)
- No compaction needed (auto-eviction)
- Use case: Rate limiting, temporary flags, one-time tokens

**SessionPolicy** (src/axon/core/policies/session.py)
- Medium-lived memories (minutes to hours)
- Typically Redis with longer TTL
- TTL: 300-3600 seconds (5min - 1hr)
- Optional overflow to persistent tier
- Use case: Conversation context, user sessions, active workspaces

**PersistentPolicy** (src/axon/core/policies/persistent.py)
- Long-lived memories (hours to forever)
- Vector DB (Chroma, Qdrant, Pinecone)
- TTL: None or very long (days/months)
- Compaction enabled
- Use case: Long-term knowledge, user history, learned facts

#### 3. **MemoryConfig Class** (`src/axon/core/config.py`)
```python
class MemoryConfig(BaseModel):
    """Complete memory system configuration."""
    ephemeral: Optional[EphemeralPolicy] = None
    session: Optional[SessionPolicy] = None
    persistent: PersistentPolicy  # Required
    
    # Global settings
    default_tier: str = "session"
    enable_promotion: bool = False  # Session → Persistent
    enable_demotion: bool = False   # Persistent → Archive
    
    # Validation
    @validator("persistent")
    def validate_persistent_required(cls, v):
        if v is None:
            raise ValueError("persistent tier is required")
        return v
```

#### 4. **Configuration Serialization**
- to_dict() / from_dict()
- to_json() / from_json()
- to_yaml() / from_yaml() (optional)
- Validation on load

#### 5. **Default Templates** (`src/axon/core/templates.py`)
```python
# Lightweight config (Redis only)
LIGHTWEIGHT_CONFIG = MemoryConfig(
    session=SessionPolicy(tier_name="session", adapter_type="redis", ttl_seconds=300),
    persistent=SessionPolicy(tier_name="persistent", adapter_type="redis", ttl_seconds=3600)
)

# Standard config (Redis + Chroma)
STANDARD_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(tier_name="ephemeral", adapter_type="redis", ttl_seconds=60),
    session=SessionPolicy(tier_name="session", adapter_type="redis", ttl_seconds=600),
    persistent=PersistentPolicy(tier_name="persistent", adapter_type="chroma")
)

# Production config (Redis + Pinecone)
PRODUCTION_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(tier_name="ephemeral", adapter_type="redis", ttl_seconds=30),
    session=SessionPolicy(tier_name="session", adapter_type="redis", ttl_seconds=1800),
    persistent=PersistentPolicy(tier_name="persistent", adapter_type="pinecone")
)
```

---

## 🗂️ File Structure

```
src/axon/core/
├── __init__.py                 # Export Policy classes
├── policy.py                   # Policy base class (NEW)
├── config.py                   # MemoryConfig class (NEW)
├── templates.py                # Default config templates (NEW)
└── policies/
    ├── __init__.py             # Export tier policies
    ├── ephemeral.py            # EphemeralPolicy (NEW)
    ├── session.py              # SessionPolicy (NEW)
    └── persistent.py           # PersistentPolicy (NEW)

tests/unit/
├── test_policy.py              # Policy base class tests (NEW)
├── test_ephemeral_policy.py    # EphemeralPolicy tests (NEW)
├── test_session_policy.py      # SessionPolicy tests (NEW)
├── test_persistent_policy.py   # PersistentPolicy tests (NEW)
├── test_config.py              # MemoryConfig tests (NEW)
└── test_templates.py           # Template validation tests (NEW)

examples/
├── 10_policy_basic.py          # Basic policy configuration (NEW)
├── 11_policy_custom.py         # Custom policy creation (NEW)
└── 12_policy_serialization.py  # Save/load configurations (NEW)
```

---

## 📝 Detailed Tasks

### Task 1: Policy Base Class (4 hours)
**File:** `src/axon/core/policy.py`

**Implementation:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal

class Policy(BaseModel):
    """Base policy configuration for a memory tier."""
    
    tier_name: str = Field(..., description="Name of the tier")
    adapter_type: Literal["redis", "chroma", "qdrant", "pinecone", "memory"] = Field(
        ..., description="Storage adapter to use"
    )
    ttl_seconds: Optional[int] = Field(
        None, ge=0, description="Time-to-live in seconds (None = no expiration)"
    )
    max_entries: Optional[int] = Field(
        None, gt=0, description="Maximum entries before eviction"
    )
    compaction_threshold: Optional[int] = Field(
        None, gt=0, description="Entry count that triggers compaction"
    )
    eviction_strategy: Literal["ttl", "lru", "fifo", "importance"] = Field(
        "ttl", description="Strategy for removing entries"
    )
    enable_vector_search: bool = Field(
        True, description="Whether this tier supports vector search"
    )
    
    @validator("ttl_seconds")
    def validate_ttl_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("TTL must be non-negative")
        return v
    
    def to_dict(self) -> dict:
        """Convert policy to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        """Create policy from dictionary."""
        return cls(**data)
```

**Tests:**
- Initialization with valid data
- Validation errors (negative TTL, invalid adapter)
- Serialization (to_dict/from_dict)
- Default values

---

### Task 2: EphemeralPolicy Implementation (2 hours)
**File:** `src/axon/core/policies/ephemeral.py`

**Implementation:**
```python
from typing import Literal
from pydantic import Field, validator
from ..policy import Policy

class EphemeralPolicy(Policy):
    """Policy for ephemeral (short-lived) memories."""
    
    tier_name: str = Field(default="ephemeral", const=True)
    adapter_type: Literal["redis", "memory"] = Field(
        "redis", description="Only in-memory adapters allowed"
    )
    ttl_seconds: int = Field(
        60, ge=5, le=3600, description="TTL: 5 seconds to 1 hour"
    )
    eviction_strategy: Literal["ttl"] = Field(
        "ttl", const=True, description="Always TTL-based"
    )
    enable_vector_search: bool = Field(
        False, const=True, description="No vector search for ephemeral"
    )
    
    @validator("ttl_seconds")
    def validate_ephemeral_ttl(cls, v):
        if v > 3600:
            raise ValueError("Ephemeral TTL should not exceed 1 hour")
        return v
```

**Tests:**
- Default initialization
- TTL constraints (5-3600)
- Adapter type validation (only redis/memory)
- Serialization

---

### Task 3: SessionPolicy Implementation (2 hours)
**File:** `src/axon/core/policies/session.py`

**Implementation:**
```python
from typing import Literal, Optional
from pydantic import Field, validator
from ..policy import Policy

class SessionPolicy(Policy):
    """Policy for session-scoped memories."""
    
    tier_name: str = Field(default="session", const=True)
    adapter_type: Literal["redis", "memory", "chroma"] = Field(
        "redis", description="Typically cache adapters"
    )
    ttl_seconds: Optional[int] = Field(
        600, ge=60, description="TTL: 1 minute to days (default 10min)"
    )
    max_entries: Optional[int] = Field(
        1000, gt=0, description="Max entries per session"
    )
    overflow_to_persistent: bool = Field(
        False, description="Promote to persistent on overflow"
    )
    enable_vector_search: bool = Field(
        True, description="Enable if using vector adapter"
    )
    
    @validator("ttl_seconds")
    def validate_session_ttl(cls, v):
        if v is not None and v < 60:
            raise ValueError("Session TTL should be at least 60 seconds")
        return v
```

**Tests:**
- Default initialization
- TTL constraints (min 60 seconds)
- Max entries validation
- Overflow behavior
- Serialization

---

### Task 4: PersistentPolicy Implementation (2 hours)
**File:** `src/axon/core/policies/persistent.py`

**Implementation:**
```python
from typing import Literal, Optional
from pydantic import Field, validator
from ..policy import Policy

class PersistentPolicy(Policy):
    """Policy for persistent (long-term) memories."""
    
    tier_name: str = Field(default="persistent", const=True)
    adapter_type: Literal["chroma", "qdrant", "pinecone", "memory"] = Field(
        "chroma", description="Vector database required"
    )
    ttl_seconds: Optional[int] = Field(
        None, description="Usually None (no expiration)"
    )
    compaction_threshold: Optional[int] = Field(
        10000, gt=0, description="Compact after N entries"
    )
    compaction_strategy: Literal["count", "semantic", "importance", "time"] = Field(
        "count", description="How to compact memories"
    )
    enable_vector_search: bool = Field(
        True, const=True, description="Always enabled for persistent"
    )
    archive_adapter: Optional[str] = Field(
        None, description="Adapter for archived memories (e.g., S3)"
    )
    
    @validator("compaction_threshold")
    def validate_threshold(cls, v):
        if v is not None and v < 100:
            raise ValueError("Compaction threshold should be at least 100")
        return v
```

**Tests:**
- Default initialization
- Adapter type validation (must support vectors)
- Compaction threshold
- Archive adapter configuration
- Serialization

---

### Task 5: MemoryConfig Implementation (3 hours)
**File:** `src/axon/core/config.py`

**Implementation:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
import json
from .policies.ephemeral import EphemeralPolicy
from .policies.session import SessionPolicy
from .policies.persistent import PersistentPolicy

class MemoryConfig(BaseModel):
    """Complete memory system configuration."""
    
    ephemeral: Optional[EphemeralPolicy] = Field(
        None, description="Ephemeral tier (optional)"
    )
    session: Optional[SessionPolicy] = Field(
        None, description="Session tier (optional)"
    )
    persistent: PersistentPolicy = Field(
        ..., description="Persistent tier (required)"
    )
    
    default_tier: Literal["ephemeral", "session", "persistent"] = Field(
        "session", description="Default tier for new memories"
    )
    enable_promotion: bool = Field(
        False, description="Auto-promote important memories"
    )
    enable_demotion: bool = Field(
        False, description="Auto-demote old memories"
    )
    
    @validator("default_tier")
    def validate_default_tier_exists(cls, v, values):
        """Ensure default tier is configured."""
        if v == "ephemeral" and values.get("ephemeral") is None:
            raise ValueError("Default tier 'ephemeral' is not configured")
        if v == "session" and values.get("session") is None:
            raise ValueError("Default tier 'session' is not configured")
        return v
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryConfig":
        """Create config from dictionary."""
        return cls(**data)
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "MemoryConfig":
        """Load from JSON string."""
        return cls.from_dict(json.loads(json_str))
```

**Tests:**
- Minimal config (persistent only)
- Full config (all tiers)
- Validation errors (invalid default tier)
- Serialization (dict/JSON)
- Promotion/demotion flags

---

### Task 6: Configuration Templates (2 hours)
**File:** `src/axon/core/templates.py`

**Templates:**
1. **MINIMAL_CONFIG** - Persistent tier only (Chroma)
2. **LIGHTWEIGHT_CONFIG** - Redis for session + persistent
3. **STANDARD_CONFIG** - Redis ephemeral + session, Chroma persistent
4. **PRODUCTION_CONFIG** - Redis cache tiers, Pinecone persistent
5. **DEVELOPMENT_CONFIG** - All InMemory for testing

**Tests:**
- All templates validate successfully
- Templates have expected structure
- Can be serialized/deserialized

---

### Task 7: Test Suite (6 hours)
**Files:** `tests/unit/test_policy.py`, `test_*_policy.py`, `test_config.py`

**Coverage:**
- Policy base class (15 tests)
- EphemeralPolicy (10 tests)
- SessionPolicy (12 tests)
- PersistentPolicy (12 tests)
- MemoryConfig (15 tests)
- Templates (5 tests)

**Total:** ~70 tests

---

### Task 8: Example Scripts (3 hours)
**Files:** `examples/10_policy_basic.py`, `11_policy_custom.py`, `12_policy_serialization.py`

**10_policy_basic.py:**
- Show default templates
- Print configurations
- Explain tier purposes

**11_policy_custom.py:**
- Create custom policies
- Modify template configs
- Validate custom rules

**12_policy_serialization.py:**
- Save config to JSON
- Load config from JSON
- Demonstrate config persistence

---

## 🎯 Success Criteria

### Functional Requirements:
- [ ] Policy base class with full validation
- [ ] All 3 tier policies implemented
- [ ] MemoryConfig with serialization
- [ ] 5 configuration templates
- [ ] Validation catches all error cases

### Quality Requirements:
- [ ] 95%+ test pass rate (target: 70+ tests)
- [ ] 60%+ code coverage on policy modules
- [ ] All templates validate successfully
- [ ] 3 working example scripts
- [ ] Complete docstrings and type hints

### Integration Requirements:
- [ ] Compatible with existing adapters
- [ ] Ready for Router integration (Sprint 2.4)
- [ ] JSON serialization working
- [ ] Pydantic validation comprehensive

---

## 📊 Dependencies

### Completed Prerequisites:
- ✅ All storage adapters (InMemory, Chroma, Qdrant, Pinecone, Redis)
- ✅ MemoryEntry and Filter models
- ✅ Pydantic infrastructure

### Blocks:
- Sprint 2.4: Router (needs Policy system to determine tier selection)

---

## 🚨 Risks & Mitigations

**Risk 1:** Policy validation too restrictive
- **Mitigation:** Make validation configurable, allow override

**Risk 2:** Template configs don't match real-world needs
- **Mitigation:** Start with simple templates, iterate based on usage

**Risk 3:** Serialization edge cases (nested models)
- **Mitigation:** Leverage Pydantic's built-in serialization

---

## 📈 Estimated Complexity: Medium

**Breakdown:**
- Policy classes: 300-400 lines
- MemoryConfig: 150-200 lines
- Templates: 100-150 lines
- Test suite: 800-1000 lines (70+ tests)
- Examples: 300-400 lines (3 scripts)

**Time Estimate:**
- Day 1: Policy classes + MemoryConfig + initial tests
- Day 2: Templates + complete tests + examples + verification

---

## 🔄 Next Steps After Approval

1. **Implementation Agent:** Create Policy base class
2. **Implementation Agent:** Create tier-specific policies
3. **Implementation Agent:** Create MemoryConfig class
4. **Implementation Agent:** Create configuration templates
5. **Implementation Agent:** Create test suite
6. **Verification Agent:** Run tests and verify coverage
7. **Implementation Agent:** Create example scripts
8. **Testing Agent:** Validate examples
9. **Review Agent:** Create sprint review and get approval

---

## 🎯 Definition of Done

- [ ] Policy base class implemented
- [ ] EphemeralPolicy, SessionPolicy, PersistentPolicy implemented
- [ ] MemoryConfig with validation implemented
- [ ] 5 configuration templates created
- [ ] 70+ tests with 95%+ pass rate
- [ ] 60%+ code coverage on policy modules
- [ ] 3 example scripts running successfully
- [ ] Module exports updated
- [ ] Sprint review document created
- [ ] User approval for completion

---

**Planning Agent:** Sprint 2.3 plan complete. Ready for user approval to proceed to implementation.

This sprint will establish the declarative configuration layer that makes the MemorySystem flexible and production-ready. After this, Sprint 2.4 (Router) will use these policies to make intelligent tier selection decisions.
