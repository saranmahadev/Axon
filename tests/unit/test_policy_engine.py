"""
Tests for PolicyEngine.

Validates promotion/demotion decision logic, capacity management,
and tier path resolution.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from axon.core.adapter_registry import AdapterRegistry
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.core.policy import Policy
from axon.core.policy_engine import PolicyEngine
from axon.core.scoring import ScoringConfig, ScoringEngine
from axon.models.entry import MemoryEntry, MemoryMetadata


def create_test_entry(
    text: str = "test memory",
    importance: float = 0.5,
    access_count: int = 0,
    created_at: datetime = None,
    last_accessed: datetime = None,
) -> MemoryEntry:
    """Helper to create test MemoryEntry."""
    created_at = created_at or datetime.now()
    last_accessed = last_accessed or created_at

    metadata = MemoryMetadata(
        importance=importance,
        created_at=created_at,
        last_accessed_at=last_accessed,
        tags=["test"],
        user_id="test_user",
    )

    # Add access_count to extra fields
    metadata.__pydantic_extra__ = {"access_count": access_count}

    return MemoryEntry(text=text, metadata=metadata, id="test-entry-id")


@pytest.fixture
def mock_registry():
    """Create mock AdapterRegistry."""
    registry = Mock(spec=AdapterRegistry)
    return registry


@pytest.fixture
def scoring_engine():
    """Create ScoringEngine with default config."""
    config = ScoringConfig()
    return ScoringEngine(config)


@pytest.fixture
def tier_policies():
    """Create standard tier policies."""
    return {
        "ephemeral": EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
        "session": SessionPolicy(adapter_type="redis", ttl_seconds=3600, max_entries=1000),
        "persistent": PersistentPolicy(adapter_type="chroma", max_entries=10000),
    }


@pytest.fixture
def policy_engine(mock_registry, scoring_engine, tier_policies):
    """Create PolicyEngine with standard configuration."""
    return PolicyEngine(
        registry=mock_registry, scoring_engine=scoring_engine, tier_policies=tier_policies
    )


# ============================================================================
# Test Initialization
# ============================================================================


class TestPolicyEngineInit:
    """Test PolicyEngine initialization."""

    def test_init_success(self, mock_registry, scoring_engine, tier_policies):
        """Test successful initialization."""
        engine = PolicyEngine(
            registry=mock_registry, scoring_engine=scoring_engine, tier_policies=tier_policies
        )

        assert engine._registry is mock_registry
        assert engine._scoring is scoring_engine
        assert engine._policies == tier_policies

    def test_init_empty_policies_raises(self, mock_registry, scoring_engine):
        """Test that empty tier_policies raises ValueError."""
        with pytest.raises(ValueError, match="tier_policies cannot be empty"):
            PolicyEngine(registry=mock_registry, scoring_engine=scoring_engine, tier_policies={})


# ============================================================================
# Test Promotion Decisions
# ============================================================================


class TestPromotionDecisions:
    """Test promotion decision logic."""

    def test_promote_high_score_entry(self, policy_engine):
        """Test promotion of high-scoring entry."""
        # Create entry with high importance and access count
        entry = create_test_entry(importance=0.95, access_count=100, last_accessed=datetime.now())

        should_promote, details = policy_engine.should_promote(entry, "ephemeral", "session")

        assert should_promote is True
        assert details["score"] >= details["threshold"]
        assert details["current_tier"] == "ephemeral"
        assert details["target_tier"] == "session"
        assert "reason" in details

    def test_no_promote_low_score_entry(self, policy_engine):
        """Test no promotion for low-scoring entry."""
        # Create entry with low importance and few accesses
        old_time = datetime.now() - timedelta(days=5)
        entry = create_test_entry(
            importance=0.3, access_count=1, created_at=old_time, last_accessed=old_time
        )

        should_promote, details = policy_engine.should_promote(entry, "ephemeral", "session")

        assert should_promote is False
        assert details["score"] < details["threshold"]
        assert "does not qualify" in details["reason"]

    def test_promote_invalid_path_rejected(self, policy_engine):
        """Test that invalid promotion paths are rejected."""
        entry = create_test_entry(importance=0.9, access_count=100)

        # Try to promote backwards (session → ephemeral)
        should_promote, details = policy_engine.should_promote(entry, "session", "ephemeral")

        assert should_promote is False
        assert "Invalid promotion path" in details["reason"]
        assert details["tier_order"] == ["ephemeral", "session", "persistent"]

    def test_promote_to_nonexistent_tier(self, policy_engine):
        """Test promotion to non-existent tier (not in hierarchy)."""
        entry = create_test_entry(importance=0.9, access_count=100)

        should_promote, details = policy_engine.should_promote(entry, "ephemeral", "nonexistent")

        assert should_promote is False
        # Tier not in hierarchy is caught as invalid path
        assert "Invalid promotion path" in details["reason"]
        assert details["tier_order"] == ["ephemeral", "session", "persistent"]

    def test_promote_capacity_pressure_included(self, policy_engine):
        """Test that capacity_pressure is included in details."""
        entry = create_test_entry(importance=0.9, access_count=100)

        should_promote, details = policy_engine.should_promote(
            entry, "ephemeral", "session", capacity_pressure=0.85
        )

        assert details["capacity_pressure"] == 0.85


# ============================================================================
# Test Demotion Decisions
# ============================================================================


class TestDemotionDecisions:
    """Test demotion decision logic."""

    def test_demote_old_low_importance_entry(self, policy_engine):
        """Test demotion of old, low-importance entry."""
        # Create old entry with low importance
        old_time = datetime.now() - timedelta(days=40)
        entry = create_test_entry(
            importance=0.2, access_count=1, created_at=old_time, last_accessed=old_time
        )

        should_demote, details = policy_engine.should_demote(
            entry, "persistent", "session", capacity_pressure=0.9
        )

        assert should_demote is True
        assert details["score"] >= details["threshold"]
        assert details["current_tier"] == "persistent"
        assert details["target_tier"] == "session"
        assert details["capacity_pressure"] == 0.9

    def test_no_demote_recent_important_entry(self, policy_engine):
        """Test no demotion for recent, important entry."""
        recent_time = datetime.now() - timedelta(minutes=5)
        entry = create_test_entry(
            importance=0.9, access_count=50, created_at=recent_time, last_accessed=datetime.now()
        )

        should_demote, details = policy_engine.should_demote(
            entry, "persistent", "session", capacity_pressure=0.5
        )

        assert should_demote is False
        assert details["score"] < details["threshold"]

    def test_demote_invalid_path_rejected(self, policy_engine):
        """Test that invalid demotion paths are rejected."""
        entry = create_test_entry(importance=0.1, access_count=1)

        # Try to demote upwards (ephemeral → session)
        should_demote, details = policy_engine.should_demote(entry, "ephemeral", "session")

        assert should_demote is False
        assert "Invalid demotion path" in details["reason"]

    def test_demote_to_nonexistent_tier(self, policy_engine):
        """Test demotion to non-existent tier (not in hierarchy)."""
        entry = create_test_entry(importance=0.1, access_count=1)

        should_demote, details = policy_engine.should_demote(
            entry, "session", "archive"  # Doesn't exist in hierarchy
        )

        assert should_demote is False
        # Tier not in hierarchy is caught as invalid path
        assert "Invalid demotion path" in details["reason"]

    def test_demote_high_capacity_pressure(self, policy_engine):
        """Test demotion decision with high capacity pressure."""
        old_time = datetime.now() - timedelta(days=10)
        entry = create_test_entry(
            importance=0.5, access_count=5, created_at=old_time, last_accessed=old_time
        )

        # High capacity pressure should influence demotion
        should_demote, details = policy_engine.should_demote(
            entry, "session", "ephemeral", capacity_pressure=0.95
        )

        # Capacity pressure is factored into demotion score
        assert details["capacity_pressure"] == 0.95


# ============================================================================
# Test Capacity Management
# ============================================================================


class TestCapacityManagement:
    """Test capacity and compaction checks."""

    def test_should_compact_no_max_entries(self, policy_engine):
        """Test compaction check when tier has no max_entries."""
        # Ephemeral policy has no max_entries
        should_compact, details = policy_engine.should_compact("ephemeral")

        assert should_compact is False
        assert "unlimited capacity" in details["reason"]
        assert details["max_entries"] is None

    def test_should_compact_no_threshold(self, mock_registry, scoring_engine):
        """Test compaction when no compaction_threshold set."""
        # Create policy with max_entries but no compaction_threshold
        policies = {
            "test": Policy(
                tier_name="test",
                adapter_type="chroma",
                max_entries=1000,
                compaction_threshold=None,  # Explicitly None
            )
        }

        engine = PolicyEngine(
            registry=mock_registry, scoring_engine=scoring_engine, tier_policies=policies
        )

        should_compact, details = engine.should_compact("test")

        assert should_compact is False
        assert "no compaction_threshold" in details["reason"]

    def test_should_compact_tier_not_found(self, policy_engine):
        """Test compaction check for non-existent tier."""
        should_compact, details = policy_engine.should_compact("nonexistent")

        assert should_compact is False
        assert "not found in policies" in details["reason"]

    def test_check_overflow_no_max_entries(self, policy_engine):
        """Test overflow check when tier has unlimited capacity."""
        is_overflow, details = policy_engine.check_overflow("ephemeral")

        assert is_overflow is False
        assert "unlimited capacity" in details["reason"]

    def test_check_overflow_tier_not_found(self, policy_engine):
        """Test overflow check for non-existent tier."""
        is_overflow, details = policy_engine.check_overflow("nonexistent")

        assert is_overflow is False
        assert "not found in policies" in details["reason"]


# ============================================================================
# Test Tier Path Resolution
# ============================================================================


class TestTierPathResolution:
    """Test promotion/demotion path resolution."""

    def test_get_promotion_path_from_ephemeral(self, policy_engine):
        """Test promotion path from ephemeral tier."""
        # High-scoring entry should promote to session
        entry = create_test_entry(importance=0.95, access_count=100, last_accessed=datetime.now())

        target = policy_engine.get_promotion_path(entry, "ephemeral")

        assert target == "session"

    def test_get_promotion_path_from_session(self, policy_engine):
        """Test promotion path from session tier."""
        entry = create_test_entry(importance=0.95, access_count=100, last_accessed=datetime.now())

        target = policy_engine.get_promotion_path(entry, "session")

        assert target == "persistent"

    def test_get_promotion_path_from_highest_tier(self, policy_engine):
        """Test promotion path from highest tier (should be None)."""
        entry = create_test_entry(importance=0.95, access_count=100)

        target = policy_engine.get_promotion_path(entry, "persistent")

        assert target is None

    def test_get_promotion_path_low_score(self, policy_engine):
        """Test promotion path for low-scoring entry (should be None)."""
        old_time = datetime.now() - timedelta(days=5)
        entry = create_test_entry(
            importance=0.2, access_count=1, created_at=old_time, last_accessed=old_time
        )

        target = policy_engine.get_promotion_path(entry, "ephemeral")

        assert target is None

    def test_get_promotion_path_invalid_tier(self, policy_engine):
        """Test promotion path from invalid tier."""
        entry = create_test_entry(importance=0.9, access_count=100)

        target = policy_engine.get_promotion_path(entry, "nonexistent")

        assert target is None

    def test_get_demotion_path_from_persistent(self, policy_engine):
        """Test demotion path from persistent tier."""
        old_time = datetime.now() - timedelta(days=40)
        entry = create_test_entry(
            importance=0.1, access_count=1, created_at=old_time, last_accessed=old_time
        )

        target = policy_engine.get_demotion_path(entry, "persistent", capacity_pressure=0.9)

        assert target == "session"

    def test_get_demotion_path_from_session(self, policy_engine):
        """Test demotion path from session tier."""
        old_time = datetime.now() - timedelta(days=40)
        entry = create_test_entry(
            importance=0.1, access_count=1, created_at=old_time, last_accessed=old_time
        )

        target = policy_engine.get_demotion_path(entry, "session", capacity_pressure=0.9)

        assert target == "ephemeral"

    def test_get_demotion_path_from_lowest_tier(self, policy_engine):
        """Test demotion path from lowest tier (should be None)."""
        entry = create_test_entry(importance=0.1, access_count=1)

        target = policy_engine.get_demotion_path(entry, "ephemeral")

        assert target is None

    def test_get_demotion_path_high_score(self, policy_engine):
        """Test demotion path for high-scoring entry (should be None)."""
        recent_time = datetime.now() - timedelta(minutes=5)
        entry = create_test_entry(
            importance=0.9, access_count=100, created_at=recent_time, last_accessed=datetime.now()
        )

        target = policy_engine.get_demotion_path(entry, "persistent", capacity_pressure=0.3)

        assert target is None


# ============================================================================
# Test Edge Cases and Validation
# ============================================================================


class TestEdgeCases:
    """Test edge cases and validation."""

    def test_tier_order_constant(self, policy_engine):
        """Test that tier order is correct."""
        assert policy_engine._TIER_ORDER == ["ephemeral", "session", "persistent"]

    def test_promote_same_tier_rejected(self, policy_engine):
        """Test promotion to same tier is rejected."""
        entry = create_test_entry(importance=0.9, access_count=100)

        should_promote, details = policy_engine.should_promote(entry, "session", "session")

        assert should_promote is False
        assert "Invalid promotion path" in details["reason"]

    def test_demote_same_tier_rejected(self, policy_engine):
        """Test demotion to same tier is rejected."""
        entry = create_test_entry(importance=0.1, access_count=1)

        should_demote, details = policy_engine.should_demote(entry, "session", "session")

        assert should_demote is False
        assert "Invalid demotion path" in details["reason"]

    def test_promotion_path_with_missing_tier_in_policies(self, mock_registry, scoring_engine):
        """Test promotion path when next tier not in policies."""
        # Only define ephemeral, skip session
        policies = {
            "ephemeral": EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
            "persistent": PersistentPolicy(adapter_type="chroma"),
        }

        engine = PolicyEngine(
            registry=mock_registry, scoring_engine=scoring_engine, tier_policies=policies
        )

        entry = create_test_entry(importance=0.9, access_count=100)

        # Should return None because session tier is missing
        target = engine.get_promotion_path(entry, "ephemeral")

        assert target is None

    def test_details_contain_all_required_fields(self, policy_engine):
        """Test that decision details contain all expected fields."""
        entry = create_test_entry(importance=0.9, access_count=100)

        should_promote, details = policy_engine.should_promote(entry, "ephemeral", "session")

        # Check required fields
        assert "should_promote" in details
        assert "score" in details
        assert "threshold" in details
        assert "current_tier" in details
        assert "target_tier" in details
        assert "capacity_pressure" in details
        assert "reason" in details

        # Check score components
        assert "frequency" in details
        assert "importance" in details
        assert "recency" in details
        assert "velocity" in details
