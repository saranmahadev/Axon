"""
Tests for EphemeralPolicy class.

Tests the ephemeral tier policy with its specific constraints
and validation rules.
"""

import pytest
from pydantic import ValidationError

from axon.core.policies.ephemeral import EphemeralPolicy


class TestEphemeralPolicyDefaults:
    """Test EphemeralPolicy defaults and initialization."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        policy = EphemeralPolicy()

        assert policy.tier_name == "ephemeral"
        assert policy.adapter_type == "redis"  # default
        assert policy.ttl_seconds == 60  # default
        assert policy.eviction_strategy == "ttl"
        assert policy.enable_vector_search is False

    def test_custom_adapter(self):
        """Test setting custom adapter."""
        policy = EphemeralPolicy(adapter_type="memory")
        assert policy.adapter_type == "memory"

    def test_custom_ttl(self):
        """Test setting custom TTL."""
        policy = EphemeralPolicy(ttl_seconds=120)
        assert policy.ttl_seconds == 120


class TestEphemeralPolicyConstraints:
    """Test EphemeralPolicy constraint validation."""

    def test_tier_name_locked(self):
        """Test that tier_name is always 'ephemeral'."""
        policy = EphemeralPolicy()
        assert policy.tier_name == "ephemeral"

    def test_adapter_type_restricted(self):
        """Test that only in-memory adapters are allowed."""
        # Valid adapters
        EphemeralPolicy(adapter_type="redis")
        EphemeralPolicy(adapter_type="memory")

        # Invalid adapters
        with pytest.raises(ValidationError) as exc_info:
            EphemeralPolicy(adapter_type="chroma")
        # Check that validation error occurred for adapter_type
        assert "adapter_type" in str(exc_info.value)

        with pytest.raises(ValidationError):
            EphemeralPolicy(adapter_type="qdrant")

        with pytest.raises(ValidationError):
            EphemeralPolicy(adapter_type="pinecone")

    def test_ttl_minimum(self):
        """Test that TTL must be at least 5 seconds."""
        # At minimum is valid
        policy = EphemeralPolicy(ttl_seconds=5)
        assert policy.ttl_seconds == 5

        # Below minimum is invalid
        with pytest.raises(ValidationError) as exc_info:
            EphemeralPolicy(ttl_seconds=4)
        # Check that validation error occurred for ttl_seconds
        assert "ttl_seconds" in str(exc_info.value)

    def test_ttl_maximum(self):
        """Test that TTL must not exceed 1 hour."""
        # At maximum is valid
        policy = EphemeralPolicy(ttl_seconds=3600)
        assert policy.ttl_seconds == 3600

        # Above maximum is invalid
        with pytest.raises(ValidationError) as exc_info:
            EphemeralPolicy(ttl_seconds=3601)
        assert "1 hour" in str(exc_info.value) or "3600" in str(exc_info.value)

    def test_eviction_strategy_locked(self):
        """Test that eviction_strategy is always 'ttl'."""
        policy = EphemeralPolicy()
        assert policy.eviction_strategy == "ttl"

    def test_vector_search_disabled(self):
        """Test that vector search is always disabled."""
        policy = EphemeralPolicy()
        assert policy.enable_vector_search is False


class TestEphemeralPolicySerialization:
    """Test EphemeralPolicy serialization."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        policy = EphemeralPolicy(adapter_type="memory", ttl_seconds=30)
        data = policy.to_dict()

        assert data["tier_name"] == "ephemeral"
        assert data["adapter_type"] == "memory"
        assert data["ttl_seconds"] == 30
        assert data["enable_vector_search"] is False

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {"adapter_type": "redis", "ttl_seconds": 90}
        policy = EphemeralPolicy.from_dict(data)

        assert policy.tier_name == "ephemeral"
        assert policy.adapter_type == "redis"
        assert policy.ttl_seconds == 90

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = EphemeralPolicy(adapter_type="memory", ttl_seconds=120)
        data = original.to_dict()
        restored = EphemeralPolicy.from_dict(data)

        assert restored.tier_name == original.tier_name
        assert restored.adapter_type == original.adapter_type
        assert restored.ttl_seconds == original.ttl_seconds
