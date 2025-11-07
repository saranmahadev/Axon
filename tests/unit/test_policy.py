"""
Tests for Policy base class.

Tests the foundational Policy class with validation,
serialization, and error handling.
"""

import pytest
from pydantic import ValidationError

from axon.core.policy import Policy


class TestPolicyInitialization:
    """Test Policy initialization and defaults."""

    def test_basic_initialization(self):
        """Test creating policy with minimum required fields."""
        policy = Policy(tier_name="test", adapter_type="redis")
        assert policy.tier_name == "test"
        assert policy.adapter_type == "redis"
        assert policy.ttl_seconds is None
        assert policy.max_entries is None
        assert policy.eviction_strategy == "ttl"  # default
        assert policy.enable_vector_search is True  # default

    def test_full_initialization(self):
        """Test creating policy with all fields specified."""
        policy = Policy(
            tier_name="session",
            adapter_type="chroma",
            ttl_seconds=600,
            max_entries=1000,
            compaction_threshold=5000,
            eviction_strategy="lru",
            enable_vector_search=True,
        )
        assert policy.tier_name == "session"
        assert policy.adapter_type == "chroma"
        assert policy.ttl_seconds == 600
        assert policy.max_entries == 1000
        assert policy.compaction_threshold == 5000
        assert policy.eviction_strategy == "lru"
        assert policy.enable_vector_search is True

    def test_tier_name_required(self):
        """Test that tier_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Policy(adapter_type="redis")
        assert "tier_name" in str(exc_info.value)

    def test_adapter_type_required(self):
        """Test that adapter_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            Policy(tier_name="test")
        assert "adapter_type" in str(exc_info.value)


class TestPolicyValidation:
    """Test Policy validation rules."""

    def test_valid_adapter_types(self):
        """Test all valid adapter types."""
        adapters = ["redis", "chroma", "qdrant", "pinecone", "memory"]
        for adapter in adapters:
            policy = Policy(tier_name="test", adapter_type=adapter)
            assert policy.adapter_type == adapter

    def test_invalid_adapter_type(self):
        """Test that invalid adapter types are rejected."""
        with pytest.raises(ValidationError):
            Policy(tier_name="test", adapter_type="invalid")

    def test_ttl_non_negative(self):
        """Test that TTL must be non-negative."""
        # Zero is valid
        policy = Policy(tier_name="test", adapter_type="redis", ttl_seconds=0)
        assert policy.ttl_seconds == 0

        # Positive is valid
        policy = Policy(tier_name="test", adapter_type="redis", ttl_seconds=100)
        assert policy.ttl_seconds == 100

        # Negative is invalid
        with pytest.raises(ValidationError) as exc_info:
            Policy(tier_name="test", adapter_type="redis", ttl_seconds=-100)
        # Check that validation error occurred (message may vary)
        assert "ttl_seconds" in str(exc_info.value)

    def test_max_entries_positive(self):
        """Test that max_entries must be positive if specified."""
        # Positive is valid
        policy = Policy(tier_name="test", adapter_type="redis", max_entries=100)
        assert policy.max_entries == 100

        # Zero is invalid
        with pytest.raises(ValidationError):
            Policy(tier_name="test", adapter_type="redis", max_entries=0)

        # Negative is invalid
        with pytest.raises(ValidationError):
            Policy(tier_name="test", adapter_type="redis", max_entries=-100)

    def test_compaction_threshold_minimum(self):
        """Test that compaction threshold has minimum value."""
        # 10 is minimum
        policy = Policy(tier_name="test", adapter_type="redis", compaction_threshold=10)
        assert policy.compaction_threshold == 10

        # Above minimum is valid
        policy = Policy(tier_name="test", adapter_type="redis", compaction_threshold=1000)
        assert policy.compaction_threshold == 1000

        # Below minimum is invalid
        with pytest.raises(ValidationError) as exc_info:
            Policy(tier_name="test", adapter_type="redis", compaction_threshold=5)
        assert "at least 10" in str(exc_info.value)

    def test_valid_eviction_strategies(self):
        """Test all valid eviction strategies."""
        strategies = ["ttl", "lru", "fifo", "importance"]
        for strategy in strategies:
            policy = Policy(tier_name="test", adapter_type="redis", eviction_strategy=strategy)
            assert policy.eviction_strategy == strategy

    def test_invalid_eviction_strategy(self):
        """Test that invalid eviction strategies are rejected."""
        with pytest.raises(ValidationError):
            Policy(tier_name="test", adapter_type="redis", eviction_strategy="invalid")


class TestPolicySerialization:
    """Test Policy serialization and deserialization."""

    def test_to_dict(self):
        """Test converting policy to dictionary."""
        policy = Policy(tier_name="test", adapter_type="redis", ttl_seconds=600, max_entries=1000)
        data = policy.to_dict()

        assert isinstance(data, dict)
        assert data["tier_name"] == "test"
        assert data["adapter_type"] == "redis"
        assert data["ttl_seconds"] == 600
        assert data["max_entries"] == 1000

    def test_from_dict(self):
        """Test creating policy from dictionary."""
        data = {
            "tier_name": "test",
            "adapter_type": "redis",
            "ttl_seconds": 600,
            "max_entries": 1000,
            "eviction_strategy": "lru",
        }
        policy = Policy.from_dict(data)

        assert policy.tier_name == "test"
        assert policy.adapter_type == "redis"
        assert policy.ttl_seconds == 600
        assert policy.max_entries == 1000
        assert policy.eviction_strategy == "lru"

    def test_roundtrip_serialization(self):
        """Test that serialization preserves all data."""
        original = Policy(
            tier_name="session",
            adapter_type="chroma",
            ttl_seconds=1800,
            max_entries=5000,
            compaction_threshold=10000,
            eviction_strategy="importance",
            enable_vector_search=True,
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Policy.from_dict(data)

        # Compare all fields
        assert restored.tier_name == original.tier_name
        assert restored.adapter_type == original.adapter_type
        assert restored.ttl_seconds == original.ttl_seconds
        assert restored.max_entries == original.max_entries
        assert restored.compaction_threshold == original.compaction_threshold
        assert restored.eviction_strategy == original.eviction_strategy
        assert restored.enable_vector_search == original.enable_vector_search


class TestPolicyStringRepresentation:
    """Test Policy string representation."""

    def test_str_with_ttl(self):
        """Test __str__ with TTL specified."""
        policy = Policy(
            tier_name="session", adapter_type="redis", ttl_seconds=600, max_entries=1000
        )
        s = str(policy)
        assert "session" in s
        assert "redis" in s
        assert "600s" in s
        assert "1000" in s

    def test_str_without_ttl(self):
        """Test __str__ without TTL (infinite)."""
        policy = Policy(tier_name="persistent", adapter_type="chroma")
        s = str(policy)
        assert "persistent" in s
        assert "chroma" in s
        assert "∞" in s  # Infinity symbol for no TTL/max
