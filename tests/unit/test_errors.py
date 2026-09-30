"""Tests for the Axon exception hierarchy and the places that raise it."""

import pytest

import axon
from axon import errors
from axon.adapters.memory import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry
from axon.core.audit import AuditLogger
from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import PersistentPolicy
from axon.errors import (
    AdapterError,
    AuditError,
    AxonError,
    ConfigurationError,
    EmbeddingError,
    EntryNotFoundError,
    ForgetIncompleteError,
    SummarizationError,
    TierNotFoundError,
    TransactionError,
)

ALL_ERRORS = [
    ConfigurationError,
    TierNotFoundError,
    EntryNotFoundError,
    AdapterError,
    ForgetIncompleteError,
    EmbeddingError,
    SummarizationError,
    TransactionError,
    AuditError,
]


class TestHierarchy:
    @pytest.mark.parametrize("cls", ALL_ERRORS)
    def test_every_error_derives_from_axon_error(self, cls):
        assert issubclass(cls, AxonError)

    @pytest.mark.parametrize(
        "cls, builtin",
        [
            (ConfigurationError, ValueError),
            (TierNotFoundError, KeyError),
            (EntryNotFoundError, KeyError),
            (AdapterError, RuntimeError),
            (ForgetIncompleteError, RuntimeError),
            (EmbeddingError, RuntimeError),
            (SummarizationError, RuntimeError),
            (TransactionError, RuntimeError),
            (AuditError, RuntimeError),
        ],
    )
    def test_errors_stay_catchable_as_the_builtin_they_replaced(self, cls, builtin):
        assert issubclass(cls, builtin)

    def test_forget_incomplete_is_an_adapter_error(self):
        assert issubclass(ForgetIncompleteError, AdapterError)

    def test_errors_are_exported_from_the_package_root(self):
        for cls in ALL_ERRORS + [AxonError]:
            assert getattr(axon, cls.__name__) is cls
            assert cls.__name__ in axon.__all__

    def test_errors_module_all_lists_every_error(self):
        assert set(errors.__all__) == {c.__name__ for c in ALL_ERRORS} | {"AxonError"}


class TestNotFoundErrors:
    def test_key_errors_render_without_repr_quoting(self):
        assert str(EntryNotFoundError("e1")) == "Entry 'e1' not found"
        assert str(TierNotFoundError("nope")) == "Tier 'nope' not found"

    def test_tier_not_found_lists_available_tiers(self):
        err = TierNotFoundError("nope", ["ephemeral", "persistent"])

        assert err.tier == "nope"
        assert err.available == ["ephemeral", "persistent"]
        assert "ephemeral, persistent" in str(err)

    def test_tier_not_found_accepts_a_custom_message(self):
        assert str(TierNotFoundError("x", message="custom")) == "custom"

    def test_entry_not_found_carries_the_id(self):
        assert EntryNotFoundError("abc").entry_id == "abc"


class TestForgetIncompleteError:
    def test_carries_counts_and_per_tier_failures(self):
        boom = ConnectionError("down")

        err = ForgetIncompleteError(3, {"session": boom})

        assert err.deleted_count == 3
        assert err.failures == {"session": boom}
        assert "3 entries deleted" in str(err)
        assert "session: down" in str(err)


class TestRaiseSites:
    @pytest.mark.asyncio
    async def test_registry_raises_tier_not_found_with_available_tiers(self):
        registry = AdapterRegistry()
        registry.register("persistent", "memory", adapter_instance=InMemoryAdapter())

        with pytest.raises(TierNotFoundError) as exc_info:
            await registry.get_adapter("session")

        assert exc_info.value.tier == "session"
        assert exc_info.value.available == ["persistent"]

    def test_registry_rejects_unknown_adapter_type_as_configuration_error(self):
        with pytest.raises(ConfigurationError, match="Invalid adapter_type"):
            AdapterRegistry().register("persistent", "no-such-backend", adapter_config={})

    def test_registry_requires_instance_or_config(self):
        with pytest.raises(ConfigurationError, match="Must provide either"):
            AdapterRegistry().register("persistent", "memory")

    def test_memory_system_requires_config(self):
        with pytest.raises(ConfigurationError, match="config is required"):
            MemorySystem(config=None)

    @pytest.mark.asyncio
    async def test_registry_wraps_adapter_creation_failure(self, monkeypatch):
        registry = AdapterRegistry()
        registry.register("persistent", "memory", adapter_config={})

        def broken_factory(adapter_type, config):
            raise OSError("disk unavailable")

        monkeypatch.setattr(registry, "_create_adapter", broken_factory)

        with pytest.raises(AdapterError) as exc_info:
            await registry.get_adapter("persistent")

        assert exc_info.value.tier == "persistent"

    @pytest.mark.asyncio
    async def test_memory_adapter_get_raises_entry_not_found(self):
        with pytest.raises(EntryNotFoundError) as exc_info:
            await InMemoryAdapter().get("missing")

        assert exc_info.value.entry_id == "missing"

    @pytest.mark.asyncio
    async def test_forget_unknown_tier_raises_tier_not_found(self):
        system = MemorySystem(
            config=MemoryConfig(
                persistent=PersistentPolicy(adapter_type="memory"), default_tier="persistent"
            ),
            enable_pii_detection=False,
        )

        with pytest.raises(TierNotFoundError) as exc_info:
            await system.forget("e1", tier="nope")

        assert exc_info.value.tier == "nope"
        assert "persistent" in exc_info.value.available

    @pytest.mark.asyncio
    async def test_export_audit_log_without_logger_raises_audit_error(self):
        system = MemorySystem(
            config=MemoryConfig(
                persistent=PersistentPolicy(adapter_type="memory"), default_tier="persistent"
            ),
            enable_pii_detection=False,
        )

        with pytest.raises(AuditError, match="No audit logger configured"):
            await system.export_audit_log()

    @pytest.mark.asyncio
    async def test_audit_export_append_to_corrupt_file_raises_audit_error(self, tmp_path):
        export = tmp_path / "audit.json"
        export.write_text("{not json")
        logger = AuditLogger(max_events=2, auto_export_path=export, enable_rotation=True)

        with pytest.raises(AuditError, match="Cannot append"):
            for _ in range(2):
                await logger.log_event(operation=axon.core.audit.OperationType.STORE)
