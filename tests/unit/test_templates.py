"""
Tests for configuration templates.

Tests that all pre-configured templates are valid
and can be serialized/deserialized correctly.
"""

from axon.core import templates
from axon.core.config import MemoryConfig


class TestTemplateValidation:
    """Test that all templates are valid."""

    def test_minimal_config(self):
        """Test MINIMAL_CONFIG template."""
        config = templates.MINIMAL_CONFIG

        assert isinstance(config, MemoryConfig)
        assert config.persistent is not None
        assert config.session is None
        assert config.ephemeral is None
        assert config.default_tier == "persistent"
        assert config.persistent.adapter_type == "chroma"

    def test_lightweight_config(self):
        """Test LIGHTWEIGHT_CONFIG template."""
        config = templates.LIGHTWEIGHT_CONFIG

        assert config.session is not None
        assert config.persistent is not None
        assert config.default_tier == "session"
        assert config.session.adapter_type == "redis"
        assert config.persistent.adapter_type == "memory"

    def test_standard_config(self):
        """Test STANDARD_CONFIG template."""
        config = templates.STANDARD_CONFIG

        assert config.ephemeral is not None
        assert config.session is not None
        assert config.persistent is not None
        assert config.default_tier == "session"
        assert config.enable_promotion is True
        assert config.ephemeral.adapter_type == "redis"
        assert config.session.adapter_type == "redis"
        assert config.persistent.adapter_type == "chroma"

    def test_production_config(self):
        """Test PRODUCTION_CONFIG template."""
        config = templates.PRODUCTION_CONFIG

        assert config.ephemeral is not None
        assert config.session is not None
        assert config.persistent is not None
        assert config.enable_promotion is True
        assert config.enable_demotion is True
        assert config.persistent.adapter_type == "pinecone"
        assert config.persistent.archive_adapter == "s3"

    def test_development_config(self):
        """Test DEVELOPMENT_CONFIG template."""
        config = templates.DEVELOPMENT_CONFIG

        assert config.ephemeral is not None
        assert config.session is not None
        assert config.persistent is not None
        assert config.ephemeral.adapter_type == "memory"
        assert config.session.adapter_type == "memory"
        assert config.persistent.adapter_type == "memory"

    def test_qdrant_config(self):
        """Test QDRANT_CONFIG template."""
        config = templates.QDRANT_CONFIG

        assert config.ephemeral is not None
        assert config.session is not None
        assert config.persistent is not None
        assert config.persistent.adapter_type == "qdrant"


class TestTemplateSerialization:
    """Test that templates can be serialized/deserialized."""

    def test_all_templates_serialize_to_json(self):
        """Test that all templates can convert to JSON."""
        template_names = [
            "MINIMAL_CONFIG",
            "LIGHTWEIGHT_CONFIG",
            "STANDARD_CONFIG",
            "PRODUCTION_CONFIG",
            "DEVELOPMENT_CONFIG",
            "QDRANT_CONFIG",
        ]

        for name in template_names:
            template = getattr(templates, name)
            json_str = template.to_json()

            # Verify JSON is valid and non-empty
            assert isinstance(json_str, str)
            assert len(json_str) > 100  # Should have substantial content
            assert "{" in json_str
            assert "}" in json_str

    def test_all_templates_roundtrip(self):
        """Test that all templates can roundtrip through JSON."""
        template_names = [
            "MINIMAL_CONFIG",
            "LIGHTWEIGHT_CONFIG",
            "STANDARD_CONFIG",
            "PRODUCTION_CONFIG",
            "DEVELOPMENT_CONFIG",
            "QDRANT_CONFIG",
        ]

        for name in template_names:
            original = getattr(templates, name)
            json_str = original.to_json()
            restored = MemoryConfig.from_json(json_str)

            # Verify tier configuration matches
            assert restored.default_tier == original.default_tier
            assert set(restored.get_tier_names()) == set(original.get_tier_names())


class TestTemplateMetadata:
    """Test template metadata."""

    def test_metadata_exists_for_all_templates(self):
        """Test that metadata exists for each template."""
        template_names = [
            "MINIMAL_CONFIG",
            "LIGHTWEIGHT_CONFIG",
            "STANDARD_CONFIG",
            "PRODUCTION_CONFIG",
            "DEVELOPMENT_CONFIG",
            "QDRANT_CONFIG",
        ]

        for name in template_names:
            assert name in templates.TEMPLATE_METADATA
            metadata = templates.TEMPLATE_METADATA[name]

            # Verify required metadata fields
            assert "name" in metadata
            assert "description" in metadata
            assert "use_case" in metadata
            assert "dependencies" in metadata
            assert "tiers" in metadata

    def test_metadata_tier_count_matches_config(self):
        """Test that metadata tier count matches actual config."""
        template_names = [
            "MINIMAL_CONFIG",
            "LIGHTWEIGHT_CONFIG",
            "STANDARD_CONFIG",
            "PRODUCTION_CONFIG",
            "DEVELOPMENT_CONFIG",
            "QDRANT_CONFIG",
        ]

        for name in template_names:
            config = getattr(templates, name)
            metadata = templates.TEMPLATE_METADATA[name]

            actual_tier_count = len(config.get_tier_names())
            expected_tier_count = metadata["tiers"]

            assert (
                actual_tier_count == expected_tier_count
            ), f"{name}: expected {expected_tier_count} tiers, got {actual_tier_count}"
