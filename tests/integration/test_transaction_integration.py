"""Integration tests for transaction functionality across adapters."""

import pytest
from datetime import datetime, timezone

from axon.core import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, PersistentPolicy
from axon.core.transaction import IsolationLevel, TransactionCoordinator
from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry
from axon.models.entry import MemoryEntry, MemoryMetadata


@pytest.fixture
def memory_system():
    """Create a MemorySystem with in-memory adapters for testing."""
    registry = AdapterRegistry()
    registry.register("ephemeral", adapter_type="memory", adapter_instance=InMemoryAdapter())
    registry.register("persistent", adapter_type="memory", adapter_instance=InMemoryAdapter())

    config = MemoryConfig(
        ephemeral=EphemeralPolicy(backend="memory"),
        persistent=PersistentPolicy(backend="memory"),
        default_tier="persistent",
    )

    return MemorySystem(config, registry=registry)


@pytest.fixture
def coordinator_with_adapters():
    """Create a transaction coordinator with in-memory adapters."""
    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    return TransactionCoordinator(adapters=adapters)


class TestMultiTierTransactions:
    """Test transactions spanning multiple storage tiers."""

    @pytest.mark.asyncio
    async def test_commit_across_tiers(self, coordinator_with_adapters):
        """Test successful commit across multiple tiers."""
        coordinator = coordinator_with_adapters

        entry1 = MemoryEntry(
            text="Ephemeral entry", embedding=[0.1] * 128, metadata=MemoryMetadata(importance=0.3)
        )

        entry2 = MemoryEntry(
            text="Persistent entry",
            embedding=[0.2] * 128,
            metadata=MemoryMetadata(importance=0.9),
        )

        # Begin transaction
        txn_id = await coordinator.begin()

        # Add operations to both tiers
        await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
        await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)

        # Prepare and commit
        prepared = await coordinator.prepare(txn_id)
        assert prepared is True

        committed = await coordinator.commit(txn_id)
        assert committed is True

        # Verify both entries were saved
        ephemeral_adapter = coordinator.adapters["ephemeral"]
        persistent_adapter = coordinator.adapters["persistent"]

        saved_entry1 = await ephemeral_adapter.get(entry1.id)
        assert saved_entry1.text == "Ephemeral entry"

        saved_entry2 = await persistent_adapter.get(entry2.id)
        assert saved_entry2.text == "Persistent entry"

    @pytest.mark.asyncio
    async def test_abort_across_tiers(self, coordinator_with_adapters):
        """Test that abort prevents changes across all tiers."""
        coordinator = coordinator_with_adapters

        entry1 = MemoryEntry(
            text="Should not be saved", embedding=[0.1] * 128, metadata=MemoryMetadata()
        )

        entry2 = MemoryEntry(
            text="Also should not be saved", embedding=[0.2] * 128, metadata=MemoryMetadata()
        )

        # Begin transaction
        txn_id = await coordinator.begin()

        # Add operations
        await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
        await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)

        # Abort before commit
        aborted = await coordinator.abort(txn_id)
        assert aborted is True

        # Verify entries were NOT saved
        ephemeral_adapter = coordinator.adapters["ephemeral"]
        persistent_adapter = coordinator.adapters["persistent"]

        with pytest.raises(KeyError):
            await ephemeral_adapter.get(entry1.id)

        with pytest.raises(KeyError):
            await persistent_adapter.get(entry2.id)

    @pytest.mark.asyncio
    async def test_transaction_context_manager_multi_tier(self, coordinator_with_adapters):
        """Test context manager with multi-tier operations."""
        coordinator = coordinator_with_adapters

        entry1 = MemoryEntry(text="Entry 1", embedding=[0.1] * 128, metadata=MemoryMetadata())

        entry2 = MemoryEntry(text="Entry 2", embedding=[0.2] * 128, metadata=MemoryMetadata())

        # Use context manager
        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
            await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)

        # Both should be saved
        ephemeral_adapter = coordinator.adapters["ephemeral"]
        persistent_adapter = coordinator.adapters["persistent"]

        saved_entry1 = await ephemeral_adapter.get(entry1.id)
        assert saved_entry1.text == "Entry 1"

        saved_entry2 = await persistent_adapter.get(entry2.id)
        assert saved_entry2.text == "Entry 2"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, coordinator_with_adapters):
        """Test that exception triggers rollback."""
        coordinator = coordinator_with_adapters

        entry1 = MemoryEntry(text="Entry 1", embedding=[0.1] * 128, metadata=MemoryMetadata())

        entry2 = MemoryEntry(text="Entry 2", embedding=[0.2] * 128, metadata=MemoryMetadata())

        # Exception should trigger rollback
        with pytest.raises(RuntimeError, match="Simulated error"):
            async with coordinator.transaction() as txn_id:
                await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry1)
                await coordinator.add_operation(txn_id, "save", "persistent", entry=entry2)
                raise RuntimeError("Simulated error")

        # Verify nothing was saved
        ephemeral_adapter = coordinator.adapters["ephemeral"]
        persistent_adapter = coordinator.adapters["persistent"]

        with pytest.raises(KeyError):
            await ephemeral_adapter.get(entry1.id)

        with pytest.raises(KeyError):
            await persistent_adapter.get(entry2.id)


class TestTransactionIsolation:
    """Test transaction isolation levels."""

    @pytest.mark.asyncio
    async def test_read_committed_isolation(self):
        """Test READ_COMMITTED isolation level."""
        adapters = {
            "ephemeral": InMemoryAdapter(),
            "persistent": InMemoryAdapter(),
        }
        coordinator = TransactionCoordinator(
            adapters=adapters, isolation_level=IsolationLevel.READ_COMMITTED
        )

        entry = MemoryEntry(text="Test entry", embedding=[0.1] * 128, metadata=MemoryMetadata())

        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(txn_id, "save", "ephemeral", entry=entry)

        # Entry should be saved
        saved = await adapters["ephemeral"].get(entry.id)
        assert saved.text == "Test entry"

    @pytest.mark.asyncio
    async def test_serializable_isolation(self):
        """Test SERIALIZABLE isolation level."""
        adapters = {
            "ephemeral": InMemoryAdapter(),
            "persistent": InMemoryAdapter(),
        }
        coordinator = TransactionCoordinator(
            adapters=adapters, isolation_level=IsolationLevel.SERIALIZABLE
        )

        entry = MemoryEntry(text="Test entry", embedding=[0.1] * 128, metadata=MemoryMetadata())

        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(txn_id, "save", "persistent", entry=entry)

        # Entry should be saved
        saved = await adapters["persistent"].get(entry.id)
        assert saved.text == "Test entry"


class TestMemorySystemTransactionIntegration:
    """Test MemorySystem transaction integration."""

    @pytest.mark.asyncio
    async def test_memory_system_has_transaction_method(self, memory_system):
        """Test that MemorySystem has transaction() method."""
        assert hasattr(memory_system, "transaction")
        assert callable(memory_system.transaction)

    @pytest.mark.asyncio
    async def test_memory_system_transaction_context(self, memory_system):
        """Test MemorySystem transaction context manager."""
        # The transaction() method should return an async context manager
        ctx = memory_system.transaction()
        assert hasattr(ctx, "__aenter__")
        assert hasattr(ctx, "__aexit__")


class TestTransactionPerformance:
    """Test transaction performance characteristics."""

    @pytest.mark.asyncio
    async def test_many_operations_single_transaction(self, coordinator_with_adapters):
        """Test transaction with many operations."""
        coordinator = coordinator_with_adapters

        # Create 100 entries
        entries = [
            MemoryEntry(
                text=f"Entry {i}", embedding=[float(i % 10) / 10.0] * 128, metadata=MemoryMetadata()
            )
            for i in range(100)
        ]

        async with coordinator.transaction() as txn_id:
            for i, entry in enumerate(entries):
                tier = "ephemeral" if i % 2 == 0 else "persistent"
                await coordinator.add_operation(txn_id, "save", tier, entry=entry)

        # Verify some entries were saved
        ephemeral_adapter = coordinator.adapters["ephemeral"]
        persistent_adapter = coordinator.adapters["persistent"]

        # Check first entry in each tier
        saved_0 = await ephemeral_adapter.get(entries[0].id)
        assert saved_0.text == "Entry 0"

        saved_1 = await persistent_adapter.get(entries[1].id)
        assert saved_1.text == "Entry 1"

    @pytest.mark.asyncio
    async def test_delete_operations_in_transaction(self, coordinator_with_adapters):
        """Test delete operations within a transaction."""
        coordinator = coordinator_with_adapters
        ephemeral_adapter = coordinator.adapters["ephemeral"]

        # First save some entries
        entry1 = MemoryEntry(text="Entry 1", embedding=[0.1] * 128, metadata=MemoryMetadata())
        entry2 = MemoryEntry(text="Entry 2", embedding=[0.2] * 128, metadata=MemoryMetadata())

        await ephemeral_adapter.save(entry1)
        await ephemeral_adapter.save(entry2)

        # Verify they exist
        assert await ephemeral_adapter.get(entry1.id)
        assert await ephemeral_adapter.get(entry2.id)

        # Delete in transaction
        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(txn_id, "delete", "ephemeral", entry_id=entry1.id)
            await coordinator.add_operation(txn_id, "delete", "ephemeral", entry_id=entry2.id)

        # Verify they were deleted
        with pytest.raises(KeyError):
            await ephemeral_adapter.get(entry1.id)

        with pytest.raises(KeyError):
            await ephemeral_adapter.get(entry2.id)
