"""
Tests for MemoryConfig class.

Tests the complete memory system configuration with
multi-tier setup, validation, and serialization.
"""

import json

import pytest
from pydantic import ValidationError

from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy


class TestMemoryConfigMinimal:
    """Test minimal MemoryConfig (persistent tier only)."""

    def test_persistent_only(self):
        """Test config with only persistent tier."""
        config = MemoryConfig(
            persistent=PersistentPolicy(adapter_type="chroma"), default_tier="persistent"
        )

        assert config.persistent is not None
        assert config.session is None
        assert config.ephemeral is None
        assert config.default_tier == "persistent"
        assert config.get_tier_names() == ["persistent"]

    def test_persistent_required(self):
        """Test that persistent tier is required."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig()
        assert "persistent" in str(exc_info.value)


class TestMemoryConfigFullSetup:
    """Test full MemoryConfig with all tiers."""

    def test_all_tiers(self):
        """Test config with all three tiers."""
        config = MemoryConfig(
            ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
            session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
            persistent=PersistentPolicy(adapter_type="chroma"),
            default_tier="session",
        )

        assert config.ephemeral is not None
        assert config.session is not None
        assert config.persistent is not None
        assert config.default_tier == "session"
        assert set(config.get_tier_names()) == {"ephemeral", "session", "persistent"}

    def test_custom_flags(self):
        """Test promotion and demotion flags."""
        config = MemoryConfig(
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
            enable_promotion=True,
            enable_demotion=True,
        )

        assert config.enable_promotion is True
        assert config.enable_demotion is True


class TestMemoryConfigValidation:
    """Test MemoryConfig validation rules."""

    def test_default_tier_must_exist_ephemeral(self):
        """Test that default_tier='ephemeral' requires ephemeral policy."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(
                persistent=PersistentPolicy(adapter_type="chroma"),
                default_tier="ephemeral",  # But ephemeral not configured!
            )
        assert "ephemeral" in str(exc_info.value).lower()

    def test_default_tier_must_exist_session(self):
        """Test that default_tier='session' requires session policy."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(
                persistent=PersistentPolicy(adapter_type="chroma"),
                default_tier="session",  # But session not configured!
            )
        assert "session" in str(exc_info.value).lower()

    def test_default_tier_persistent_always_valid(self):
        """Test that default_tier='persistent' is always valid."""
        config = MemoryConfig(
            persistent=PersistentPolicy(adapter_type="chroma"), default_tier="persistent"
        )
        assert config.default_tier == "persistent"

    def test_promotion_requires_multiple_tiers(self):
        """Test that promotion requires at least 2 tiers."""
        # This should work with 2 tiers
        config = MemoryConfig(
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
            enable_promotion=True,
        )
        assert config.enable_promotion is True

        # Single tier with promotion should fail
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(
                persistent=PersistentPolicy(adapter_type="chroma"),
                default_tier="persistent",
                enable_promotion=True,
            )
        assert "2 tiers" in str(exc_info.value).lower()

    def test_demotion_requires_multiple_tiers(self):
        """Test that demotion requires at least 2 tiers."""
        # This should work with 2 tiers
        config = MemoryConfig(
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
            enable_demotion=True,
        )
        assert config.enable_demotion is True

        # Single tier with demotion should fail
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(
                persistent=PersistentPolicy(adapter_type="chroma"),
                default_tier="persistent",
                enable_demotion=True,
            )
        assert "2 tiers" in str(exc_info.value).lower()


class TestMemoryConfigSerialization:
    """Test MemoryConfig serialization."""

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = MemoryConfig(
            session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
            persistent=PersistentPolicy(adapter_type="chroma"),
            default_tier="session",
        )

        data = config.to_dict()
        assert isinstance(data, dict)
        assert "session" in data
        assert "persistent" in data
        assert data["default_tier"] == "session"
        assert data["session"]["adapter_type"] == "redis"

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "session": {"adapter_type": "redis", "ttl_seconds": 600},
            "persistent": {"adapter_type": "chroma"},
            "default_tier": "session",
        }

        config = MemoryConfig.from_dict(data)
        assert config.session.adapter_type == "redis"
        assert config.persistent.adapter_type == "chroma"
        assert config.default_tier == "session"

    def test_to_json(self):
        """Test converting config to JSON string."""
        config = MemoryConfig(
            persistent=PersistentPolicy(adapter_type="chroma"), default_tier="persistent"
        )

        json_str = config.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert "persistent" in parsed

    def test_from_json(self):
        """Test creating config from JSON string."""
        json_str = """
        {
            "session": {
                "adapter_type": "redis",
                "ttl_seconds": 600
            },
            "persistent": {
                "adapter_type": "chroma"
            },
            "default_tier": "session"
        }
        """

        config = MemoryConfig.from_json(json_str)
        assert config.session.adapter_type == "redis"
        assert config.persistent.adapter_type == "chroma"

    def test_roundtrip_serialization(self):
        """Test that serialization preserves all data."""
        original = MemoryConfig(
            ephemeral=EphemeralPolicy(adapter_type="memory", ttl_seconds=30),
            session=SessionPolicy(
                adapter_type="redis",
                ttl_seconds=1800,
                max_entries=5000,
                overflow_to_persistent=True,
            ),
            persistent=PersistentPolicy(
                adapter_type="pinecone",
                compaction_threshold=50000,
                compaction_strategy="importance",
            ),
            default_tier="session",
            enable_promotion=True,
            enable_demotion=False,
        )

        # Serialize to JSON and back
        json_str = original.to_json()
        restored = MemoryConfig.from_json(json_str)

        # Verify all fields match
        assert restored.default_tier == original.default_tier
        assert restored.enable_promotion == original.enable_promotion
        assert restored.enable_demotion == original.enable_demotion
        assert restored.ephemeral.ttl_seconds == original.ephemeral.ttl_seconds
        assert restored.session.max_entries == original.session.max_entries
        assert restored.persistent.compaction_threshold == original.persistent.compaction_threshold


class TestMemoryConfigUtilities:
    """Test MemoryConfig utility methods."""

    def test_get_tier_names(self):
        """Test getting list of configured tier names."""
        # Persistent only
        config1 = MemoryConfig(
            persistent=PersistentPolicy(adapter_type="chroma"), default_tier="persistent"
        )
        assert config1.get_tier_names() == ["persistent"]

        # Session + persistent
        config2 = MemoryConfig(
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
        )
        assert set(config2.get_tier_names()) == {"session", "persistent"}

        # All tiers
        config3 = MemoryConfig(
            ephemeral=EphemeralPolicy(adapter_type="redis"),
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
        )
        assert set(config3.get_tier_names()) == {"ephemeral", "session", "persistent"}

    def test_get_policy(self):
        """Test getting policy for specific tier."""
        config = MemoryConfig(
            ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
            session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
            persistent=PersistentPolicy(adapter_type="chroma"),
        )

        # Get existing policies
        eph = config.get_policy("ephemeral")
        assert eph is not None
        assert eph.tier_name == "ephemeral"

        sess = config.get_policy("session")
        assert sess is not None
        assert sess.tier_name == "session"

        pers = config.get_policy("persistent")
        assert pers is not None
        assert pers.tier_name == "persistent"

        # Get non-existent tier
        invalid = config.get_policy("invalid")
        assert invalid is None

    def test_str_representation(self):
        """Test string representation of config."""
        config = MemoryConfig(
            session=SessionPolicy(adapter_type="redis"),
            persistent=PersistentPolicy(adapter_type="chroma"),
            enable_promotion=True,
        )

        s = str(config)
        assert "MemoryConfig" in s
        assert "session" in s
        assert "persistent" in s
        assert "promotion=True" in s
