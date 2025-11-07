"""
Tests for PersistentPolicy class.

Tests the persistent tier policy with its specific constraints
and validation rules.
"""

import pytest
from pydantic import ValidationError

from axon.core.policies.persistent import PersistentPolicy


class TestPersistentPolicyDefaults:
    """Test PersistentPolicy defaults and initialization."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        policy = PersistentPolicy()

        assert policy.tier_name == "persistent"
        assert policy.adapter_type == "chroma"  # default
        assert policy.ttl_seconds is None  # default (no expiration)
        assert policy.compaction_threshold == 10000  # default
        assert policy.compaction_strategy == "count"  # default
        assert policy.enable_vector_search is True  # always True
        assert policy.archive_adapter is None  # default

    def test_custom_values(self):
        """Test setting custom values."""
        policy = PersistentPolicy(
            adapter_type="pinecone",
            ttl_seconds=None,
            compaction_threshold=50000,
            compaction_strategy="importance",
            archive_adapter="s3",
        )

        assert policy.adapter_type == "pinecone"
        assert policy.ttl_seconds is None
        assert policy.compaction_threshold == 50000
        assert policy.compaction_strategy == "importance"
        assert policy.archive_adapter == "s3"


class TestPersistentPolicyConstraints:
    """Test PersistentPolicy constraint validation."""

    def test_tier_name_locked(self):
        """Test that tier_name is always 'persistent'."""
        policy = PersistentPolicy()
        assert policy.tier_name == "persistent"

    def test_valid_adapter_types(self):
        """Test all valid adapter types for persistent tier."""
        adapters = ["chroma", "qdrant", "pinecone", "memory"]
        for adapter in adapters:
            policy = PersistentPolicy(adapter_type=adapter)
            assert policy.adapter_type == adapter

    def test_invalid_adapter_type(self):
        """Test that non-vector adapters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PersistentPolicy(adapter_type="redis")
        # Check that validation error occurred for adapter_type
        assert "adapter_type" in str(exc_info.value)

        with pytest.raises(ValidationError):
            PersistentPolicy(adapter_type="invalid")

    def test_compaction_threshold_minimum(self):
        """Test that compaction threshold has reasonable minimum."""
        # At minimum is valid
        policy = PersistentPolicy(compaction_threshold=100)
        assert policy.compaction_threshold == 100

        # Above minimum is valid
        policy = PersistentPolicy(compaction_threshold=50000)
        assert policy.compaction_threshold == 50000

        # Below minimum is invalid
        with pytest.raises(ValidationError) as exc_info:
            PersistentPolicy(compaction_threshold=50)
        assert "at least 100" in str(exc_info.value)

        # None is valid (no compaction)
        policy = PersistentPolicy(compaction_threshold=None)
        assert policy.compaction_threshold is None

    def test_valid_compaction_strategies(self):
        """Test all valid compaction strategies."""
        strategies = ["count", "semantic", "importance", "time"]
        for strategy in strategies:
            policy = PersistentPolicy(compaction_strategy=strategy)
            assert policy.compaction_strategy == strategy

    def test_invalid_compaction_strategy(self):
        """Test that invalid compaction strategies are rejected."""
        with pytest.raises(ValidationError):
            PersistentPolicy(compaction_strategy="invalid")

    def test_ttl_minimum_if_specified(self):
        """Test that if TTL is set, it must be at least 1 day."""
        # None is valid (no expiration - preferred)
        policy = PersistentPolicy(ttl_seconds=None)
        assert policy.ttl_seconds is None

        # At minimum (1 day) is valid
        policy = PersistentPolicy(ttl_seconds=86400)
        assert policy.ttl_seconds == 86400

        # Above minimum is valid
        policy = PersistentPolicy(ttl_seconds=604800)  # 1 week
        assert policy.ttl_seconds == 604800

        # Below minimum is invalid
        with pytest.raises(ValidationError) as exc_info:
            PersistentPolicy(ttl_seconds=3600)  # 1 hour
        assert "1 day" in str(exc_info.value) or "86400" in str(exc_info.value)

    def test_vector_search_always_enabled(self):
        """Test that vector search is always enabled."""
        policy = PersistentPolicy()
        assert policy.enable_vector_search is True


class TestPersistentPolicyFeatures:
    """Test PersistentPolicy specific features."""

    def test_archive_adapter(self):
        """Test archive_adapter configuration."""
        # None is valid (no archival)
        policy = PersistentPolicy(archive_adapter=None)
        assert policy.archive_adapter is None

        # String value is valid
        policy = PersistentPolicy(archive_adapter="s3")
        assert policy.archive_adapter == "s3"

        policy = PersistentPolicy(archive_adapter="gcs")
        assert policy.archive_adapter == "gcs"


class TestPersistentPolicySerialization:
    """Test PersistentPolicy serialization."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        policy = PersistentPolicy(
            adapter_type="qdrant",
            compaction_threshold=20000,
            compaction_strategy="semantic",
            archive_adapter="s3",
        )
        data = policy.to_dict()

        assert data["tier_name"] == "persistent"
        assert data["adapter_type"] == "qdrant"
        assert data["compaction_threshold"] == 20000
        assert data["compaction_strategy"] == "semantic"
        assert data["archive_adapter"] == "s3"
        assert data["enable_vector_search"] is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "adapter_type": "pinecone",
            "ttl_seconds": None,
            "compaction_threshold": 100000,
            "compaction_strategy": "importance",
        }
        policy = PersistentPolicy.from_dict(data)

        assert policy.tier_name == "persistent"
        assert policy.adapter_type == "pinecone"
        assert policy.ttl_seconds is None
        assert policy.compaction_threshold == 100000
        assert policy.compaction_strategy == "importance"

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = PersistentPolicy(
            adapter_type="qdrant",
            ttl_seconds=None,
            compaction_threshold=50000,
            compaction_strategy="semantic",
            archive_adapter="s3",
        )
        data = original.to_dict()
        restored = PersistentPolicy.from_dict(data)

        assert restored.tier_name == original.tier_name
        assert restored.adapter_type == original.adapter_type
        assert restored.ttl_seconds == original.ttl_seconds
        assert restored.compaction_threshold == original.compaction_threshold
        assert restored.compaction_strategy == original.compaction_strategy
        assert restored.archive_adapter == original.archive_adapter
        assert restored.enable_vector_search == original.enable_vector_search
