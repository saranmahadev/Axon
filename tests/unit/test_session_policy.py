"""
Tests for SessionPolicy class.

Tests the session tier policy with its specific constraints
and validation rules.
"""

import pytest
from pydantic import ValidationError

from axon.core.policies.session import SessionPolicy


class TestSessionPolicyDefaults:
    """Test SessionPolicy defaults and initialization."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        policy = SessionPolicy()

        assert policy.tier_name == "session"
        assert policy.adapter_type == "redis"  # default
        assert policy.ttl_seconds == 600  # default (10 minutes)
        assert policy.max_entries == 1000  # default
        assert policy.overflow_to_persistent is False  # default
        assert policy.enable_vector_search is True  # default

    def test_custom_values(self):
        """Test setting custom values."""
        policy = SessionPolicy(
            adapter_type="chroma",
            ttl_seconds=1800,
            max_entries=5000,
            overflow_to_persistent=True,
            enable_vector_search=True,
        )

        assert policy.adapter_type == "chroma"
        assert policy.ttl_seconds == 1800
        assert policy.max_entries == 5000
        assert policy.overflow_to_persistent is True


class TestSessionPolicyConstraints:
    """Test SessionPolicy constraint validation."""

    def test_tier_name_locked(self):
        """Test that tier_name is always 'session'."""
        policy = SessionPolicy()
        assert policy.tier_name == "session"

    def test_valid_adapter_types(self):
        """Test all valid adapter types for session tier."""
        adapters = ["redis", "memory", "chroma", "qdrant", "pinecone"]
        for adapter in adapters:
            policy = SessionPolicy(adapter_type=adapter)
            assert policy.adapter_type == adapter

    def test_invalid_adapter_type(self):
        """Test that invalid adapters are rejected."""
        with pytest.raises(ValidationError):
            SessionPolicy(adapter_type="invalid")

    def test_ttl_minimum(self):
        """Test that TTL must be at least 60 seconds if specified."""
        # At minimum is valid
        policy = SessionPolicy(ttl_seconds=60)
        assert policy.ttl_seconds == 60

        # Above minimum is valid
        policy = SessionPolicy(ttl_seconds=1800)
        assert policy.ttl_seconds == 1800

        # Below minimum is invalid
        with pytest.raises(ValidationError) as exc_info:
            SessionPolicy(ttl_seconds=59)
        # Check that validation error occurred for ttl_seconds
        assert "ttl_seconds" in str(exc_info.value)

        # None is valid (no expiration)
        policy = SessionPolicy(ttl_seconds=None)
        assert policy.ttl_seconds is None

    def test_max_entries_positive(self):
        """Test that max_entries must be positive if specified."""
        # Positive is valid
        policy = SessionPolicy(max_entries=100)
        assert policy.max_entries == 100

        # Zero is invalid
        with pytest.raises(ValidationError):
            SessionPolicy(max_entries=0)

        # None is valid (unlimited)
        policy = SessionPolicy(max_entries=None)
        assert policy.max_entries is None

    def test_max_entries_reasonable(self):
        """Test that max_entries has reasonable minimum."""
        # At least 10 is valid
        policy = SessionPolicy(max_entries=10)
        assert policy.max_entries == 10

        # Below 10 is invalid
        with pytest.raises(ValidationError) as exc_info:
            SessionPolicy(max_entries=5)
        assert "at least 10" in str(exc_info.value)


class TestSessionPolicyFeatures:
    """Test SessionPolicy specific features."""

    def test_overflow_to_persistent(self):
        """Test overflow_to_persistent flag."""
        policy = SessionPolicy(overflow_to_persistent=True)
        assert policy.overflow_to_persistent is True

        policy = SessionPolicy(overflow_to_persistent=False)
        assert policy.overflow_to_persistent is False

    def test_vector_search_configurable(self):
        """Test that vector search can be enabled/disabled."""
        policy = SessionPolicy(enable_vector_search=True)
        assert policy.enable_vector_search is True

        policy = SessionPolicy(enable_vector_search=False)
        assert policy.enable_vector_search is False


class TestSessionPolicySerialization:
    """Test SessionPolicy serialization."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        policy = SessionPolicy(
            adapter_type="redis", ttl_seconds=900, max_entries=2000, overflow_to_persistent=True
        )
        data = policy.to_dict()

        assert data["tier_name"] == "session"
        assert data["adapter_type"] == "redis"
        assert data["ttl_seconds"] == 900
        assert data["max_entries"] == 2000
        assert data["overflow_to_persistent"] is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "adapter_type": "chroma",
            "ttl_seconds": 1200,
            "max_entries": 500,
            "overflow_to_persistent": False,
        }
        policy = SessionPolicy.from_dict(data)

        assert policy.tier_name == "session"
        assert policy.adapter_type == "chroma"
        assert policy.ttl_seconds == 1200
        assert policy.max_entries == 500
        assert policy.overflow_to_persistent is False

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = SessionPolicy(
            adapter_type="qdrant",
            ttl_seconds=3600,
            max_entries=10000,
            overflow_to_persistent=True,
            enable_vector_search=True,
        )
        data = original.to_dict()
        restored = SessionPolicy.from_dict(data)

        assert restored.tier_name == original.tier_name
        assert restored.adapter_type == original.adapter_type
        assert restored.ttl_seconds == original.ttl_seconds
        assert restored.max_entries == original.max_entries
        assert restored.overflow_to_persistent == original.overflow_to_persistent
        assert restored.enable_vector_search == original.enable_vector_search
