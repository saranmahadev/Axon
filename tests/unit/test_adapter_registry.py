"""
Tests for AdapterRegistry.

Tests adapter registration, lazy initialization, lifecycle management,
and error handling.
"""

import pytest

from axon.adapters.base import StorageAdapter
from axon.adapters.memory import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry


class MockAdapter(StorageAdapter):
    """Mock adapter for testing."""

    def __init__(self, name: str = "mock", fail_init: bool = False):
        self.name = name
        self.fail_init = fail_init
        self.initialized = False
        self.closed = False
        self.init_count = 0

    async def initialize(self):
        """Initialize adapter."""
        if self.fail_init:
            raise RuntimeError(f"Mock initialization failure for {self.name}")
        self.init_count += 1
        self.initialized = True

    async def close(self):
        """Close adapter."""
        self.closed = True

    # Minimal StorageAdapter interface implementation
    async def save(self, entry):
        """Save a single memory entry."""
        return "mock-id"

    async def bulk_save(self, entries):
        """Save multiple memory entries."""
        return [f"mock-id-{i}" for i in range(len(entries))]

    async def store(self, entry):
        return "mock-id"

    async def query(self, query_text, k=5, filter=None):
        return []

    async def get(self, entry_id):
        return None

    async def delete(self, entry_id=None, filter=None):
        return 0

    async def count(self, filter=None):
        return 0

    async def list_ids(self, filter=None, limit=100):
        return []

    async def reindex(self, new_embedder=None):
        """Reindex entries with new embedder."""
        pass


class TestAdapterRegistration:
    """Test adapter registration."""

    def test_register_with_instance(self):
        """Test registering with pre-configured adapter instance."""
        registry = AdapterRegistry()
        adapter = MockAdapter("test-adapter")

        registry.register("ephemeral", "memory", adapter_instance=adapter)

        assert registry.is_registered("ephemeral")
        assert registry.get_adapter_type("ephemeral") == "memory"
        assert "ephemeral" in registry.get_all_tiers()

    def test_register_with_config(self):
        """Test registering with adapter configuration."""
        registry = AdapterRegistry()
        config = {"collection_name": "test"}

        registry.register("session", "memory", adapter_config=config)

        assert registry.is_registered("session")
        assert registry.get_adapter_type("session") == "memory"

    def test_register_multiple_tiers(self):
        """Test registering adapters for multiple tiers."""
        registry = AdapterRegistry()

        registry.register("ephemeral", "memory", adapter_instance=MockAdapter("eph"))
        registry.register("session", "memory", adapter_instance=MockAdapter("sess"))
        registry.register("persistent", "memory", adapter_instance=MockAdapter("pers"))

        tiers = registry.get_all_tiers()
        assert len(tiers) == 3
        assert set(tiers) == {"ephemeral", "session", "persistent"}

    def test_register_duplicate_tier_overrides(self):
        """Test that registering same tier twice overrides previous."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("first")
        adapter2 = MockAdapter("second")

        registry.register("ephemeral", "memory", adapter_instance=adapter1)
        registry.register("ephemeral", "redis", adapter_instance=adapter2)

        assert registry.get_adapter_type("ephemeral") == "redis"

    def test_register_without_instance_or_config_raises(self):
        """Test that registration requires either instance or config."""
        registry = AdapterRegistry()

        with pytest.raises(
            ValueError, match="Must provide either adapter_instance or adapter_config"
        ):
            registry.register("ephemeral", "memory")

    def test_register_invalid_adapter_type_raises(self):
        """Test that invalid adapter type raises error."""
        registry = AdapterRegistry()

        with pytest.raises(ValueError, match="Invalid adapter_type"):
            registry.register("ephemeral", "invalid_type", adapter_config={})

    def test_is_registered(self):
        """Test is_registered check."""
        registry = AdapterRegistry()

        assert not registry.is_registered("ephemeral")

        registry.register("ephemeral", "memory", adapter_instance=MockAdapter())

        assert registry.is_registered("ephemeral")
        assert not registry.is_registered("session")

    def test_get_all_tiers(self):
        """Test get_all_tiers returns all registered tiers."""
        registry = AdapterRegistry()

        assert registry.get_all_tiers() == []

        registry.register("ephemeral", "memory", adapter_instance=MockAdapter())
        registry.register("session", "memory", adapter_instance=MockAdapter())

        tiers = registry.get_all_tiers()
        assert len(tiers) == 2
        assert "ephemeral" in tiers
        assert "session" in tiers


@pytest.mark.asyncio
class TestAdapterResolution:
    """Test adapter resolution and lazy initialization."""

    async def test_get_adapter_with_instance(self):
        """Test getting adapter when registered with instance."""
        registry = AdapterRegistry()
        adapter = MockAdapter("test")
        registry.register("ephemeral", "memory", adapter_instance=adapter)

        result = await registry.get_adapter("ephemeral")

        assert result is adapter
        assert adapter.initialized
        assert adapter.init_count == 1

    async def test_get_adapter_lazy_initialization(self):
        """Test lazy initialization on first access."""
        registry = AdapterRegistry()
        registry.register("ephemeral", "memory", adapter_config={})

        # Should create and initialize on first access
        adapter = await registry.get_adapter("ephemeral")

        assert adapter is not None
        assert isinstance(adapter, InMemoryAdapter)

    async def test_get_adapter_cached(self):
        """Test that adapter is cached after first access."""
        registry = AdapterRegistry()
        adapter = MockAdapter("test")
        registry.register("ephemeral", "memory", adapter_instance=adapter)

        result1 = await registry.get_adapter("ephemeral")
        result2 = await registry.get_adapter("ephemeral")

        assert result1 is result2
        assert adapter.init_count == 1  # Initialized only once

    async def test_get_adapter_unregistered_tier_raises(self):
        """Test that getting unregistered tier raises KeyError."""
        registry = AdapterRegistry()

        with pytest.raises(KeyError, match="Tier 'unknown' not registered"):
            await registry.get_adapter("unknown")

    async def test_get_adapter_initialization_failure_raises(self):
        """Test that initialization failure raises RuntimeError."""
        registry = AdapterRegistry()
        adapter = MockAdapter("failing", fail_init=True)
        registry.register("ephemeral", "memory", adapter_instance=adapter)

        with pytest.raises(RuntimeError, match="Failed to initialize adapter"):
            await registry.get_adapter("ephemeral")

    async def test_get_adapter_type(self):
        """Test getting adapter type for tier."""
        registry = AdapterRegistry()
        registry.register("ephemeral", "redis", adapter_instance=MockAdapter())
        registry.register("session", "chroma", adapter_instance=MockAdapter())

        assert registry.get_adapter_type("ephemeral") == "redis"
        assert registry.get_adapter_type("session") == "chroma"
        assert registry.get_adapter_type("unknown") is None


@pytest.mark.asyncio
class TestAdapterLifecycle:
    """Test adapter lifecycle management."""

    async def test_initialize_all(self):
        """Test initializing all registered adapters."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("adapter1")
        adapter2 = MockAdapter("adapter2")

        registry.register("ephemeral", "memory", adapter_instance=adapter1)
        registry.register("session", "memory", adapter_instance=adapter2)

        await registry.initialize_all()

        assert adapter1.initialized
        assert adapter2.initialized

    async def test_close_all(self):
        """Test closing all adapters."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("adapter1")
        adapter2 = MockAdapter("adapter2")

        registry.register("ephemeral", "memory", adapter_instance=adapter1)
        registry.register("session", "memory", adapter_instance=adapter2)

        await registry.initialize_all()
        await registry.close_all()

        assert adapter1.closed
        assert adapter2.closed

    async def test_close_all_with_uninitialized_adapters(self):
        """Test close_all handles uninitialized adapters gracefully."""
        registry = AdapterRegistry()
        adapter = MockAdapter("adapter")
        registry.register("ephemeral", "memory", adapter_instance=adapter)

        # Don't initialize, just close
        await registry.close_all()

        # Should not raise, adapter not closed since not initialized
        assert not adapter.closed

    async def test_context_manager(self):
        """Test using registry as async context manager."""
        adapter = MockAdapter("adapter")
        registry = AdapterRegistry()
        registry.register("ephemeral", "memory", adapter_instance=adapter)

        async with registry:
            # initialize_all called on entry
            assert adapter.initialized

        # close_all called on exit
        assert adapter.closed

    async def test_repr(self):
        """Test string representation."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("adapter1")
        adapter2 = MockAdapter("adapter2")

        registry.register("ephemeral", "redis", adapter_instance=adapter1)
        registry.register("session", "chroma", adapter_instance=adapter2)

        repr_str = repr(registry)

        assert "AdapterRegistry" in repr_str
        assert "ephemeral=redis" in repr_str
        assert "session=chroma" in repr_str
        assert "pending" in repr_str

        # After initialization
        await registry.initialize_all()
        repr_str = repr(registry)

        assert "initialized" in repr_str
