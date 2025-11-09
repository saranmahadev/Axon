"""Unit tests for transaction management."""

import pytest
from datetime import datetime, timezone

from axon.core.transaction import (
    IsolationLevel,
    TransactionCoordinator,
    TransactionState,
)
from axon.adapters import InMemoryAdapter
from axon.models.entry import MemoryEntry, MemoryMetadata


@pytest.fixture
def sample_entry():
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        text="Test entry",
        embedding=[0.1] * 128,
        metadata=MemoryMetadata(importance=0.5),
    )


@pytest.fixture
def coordinator():
    """Create a transaction coordinator with in-memory adapters."""
    adapters = {
        "ephemeral": InMemoryAdapter(),
        "persistent": InMemoryAdapter(),
    }
    return TransactionCoordinator(adapters=adapters)


class TestTransactionCoordinator:
    """Test transaction coordinator functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test coordinator initialization with different isolation levels."""
        coordinator = TransactionCoordinator(isolation_level=IsolationLevel.SERIALIZABLE)
        assert coordinator.isolation_level == IsolationLevel.SERIALIZABLE
        assert coordinator.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_initialization_custom_timeout(self):
        """Test coordinator with custom timeout."""
        coordinator = TransactionCoordinator(timeout_seconds=60.0)
        assert coordinator.timeout_seconds == 60.0

    @pytest.mark.asyncio
    async def test_begin_transaction(self, coordinator):
        """Test starting a new transaction."""
        txn_id = await coordinator.begin()

        assert txn_id is not None
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

    @pytest.mark.asyncio
    async def test_begin_with_explicit_id(self, coordinator):
        """Test starting transaction with explicit ID."""
        txn_id = await coordinator.begin(transaction_id="test-txn-123")

        assert txn_id == "test-txn-123"
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

    @pytest.mark.asyncio
    async def test_begin_duplicate_id_fails(self, coordinator):
        """Test that duplicate transaction ID raises error."""
        txn_id = await coordinator.begin(transaction_id="test-txn-123")

        with pytest.raises(ValueError, match="already exists"):
            await coordinator.begin(transaction_id="test-txn-123")

    @pytest.mark.asyncio
    async def test_add_operation(self, coordinator, sample_entry):
        """Test adding operations to a transaction."""
        txn_id = await coordinator.begin()

        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )

        # Transaction should still be active
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

    @pytest.mark.asyncio
    async def test_add_operation_to_nonexistent_transaction(self, coordinator, sample_entry):
        """Test adding operation to non-existent transaction fails."""
        with pytest.raises(ValueError, match="not found"):
            await coordinator.add_operation(
                "nonexistent-txn", operation_type="save", tier="ephemeral", entry=sample_entry
            )

    @pytest.mark.asyncio
    async def test_add_operation_to_invalid_tier(self, coordinator, sample_entry):
        """Test adding operation to unregistered tier fails."""
        txn_id = await coordinator.begin()

        with pytest.raises(KeyError, match="No adapter registered"):
            await coordinator.add_operation(
                txn_id, operation_type="save", tier="invalid_tier", entry=sample_entry
            )

    @pytest.mark.asyncio
    async def test_prepare_phase_success(self, coordinator, sample_entry):
        """Test successful prepare phase."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )

        prepared = await coordinator.prepare(txn_id)

        assert prepared is True
        assert coordinator.get_state(txn_id) == TransactionState.PREPARED

    @pytest.mark.asyncio
    async def test_prepare_empty_transaction(self, coordinator):
        """Test preparing empty transaction succeeds."""
        txn_id = await coordinator.begin()

        prepared = await coordinator.prepare(txn_id)

        assert prepared is True
        assert coordinator.get_state(txn_id) == TransactionState.PREPARED

    @pytest.mark.asyncio
    async def test_prepare_invalid_state_fails(self, coordinator, sample_entry):
        """Test that prepare fails from invalid state."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        await coordinator.prepare(txn_id)

        # Try to prepare again
        with pytest.raises(ValueError, match="cannot prepare from this state"):
            await coordinator.prepare(txn_id)

    @pytest.mark.asyncio
    async def test_commit_phase_success(self, coordinator, sample_entry):
        """Test successful commit phase."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        await coordinator.prepare(txn_id)

        committed = await coordinator.commit(txn_id)

        assert committed is True
        assert coordinator.get_state(txn_id) == TransactionState.COMMITTED

    @pytest.mark.asyncio
    async def test_commit_without_prepare_fails(self, coordinator, sample_entry):
        """Test that commit fails if not prepared."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )

        with pytest.raises(ValueError, match="must be prepared"):
            await coordinator.commit(txn_id)

    @pytest.mark.asyncio
    async def test_abort_transaction(self, coordinator, sample_entry):
        """Test aborting a transaction."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )

        aborted = await coordinator.abort(txn_id)

        assert aborted is True
        assert coordinator.get_state(txn_id) == TransactionState.ABORTED

    @pytest.mark.asyncio
    async def test_abort_after_prepare(self, coordinator, sample_entry):
        """Test aborting after prepare phase."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        await coordinator.prepare(txn_id)

        aborted = await coordinator.abort(txn_id)

        assert aborted is True
        assert coordinator.get_state(txn_id) == TransactionState.ABORTED

    @pytest.mark.asyncio
    async def test_abort_committed_transaction_fails(self, coordinator, sample_entry):
        """Test that aborting committed transaction fails."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        await coordinator.prepare(txn_id)
        await coordinator.commit(txn_id)

        aborted = await coordinator.abort(txn_id)
        assert aborted is False  # Cannot abort committed transaction

    @pytest.mark.asyncio
    async def test_cleanup_transaction(self, coordinator, sample_entry):
        """Test cleaning up transaction state."""
        txn_id = await coordinator.begin()
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        await coordinator.prepare(txn_id)
        await coordinator.commit(txn_id)

        await coordinator.cleanup(txn_id)

        # State should be None after cleanup
        assert coordinator.get_state(txn_id) is None

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_transaction_fails(self, coordinator):
        """Test cleanup of non-existent transaction fails."""
        with pytest.raises(ValueError, match="not found"):
            await coordinator.cleanup("nonexistent-txn")

    @pytest.mark.asyncio
    async def test_multi_tier_operations(self, coordinator, sample_entry):
        """Test transaction with operations across multiple tiers."""
        txn_id = await coordinator.begin()

        entry1 = sample_entry
        entry2 = MemoryEntry(
            text="Second entry", embedding=[0.2] * 128, metadata=MemoryMetadata(importance=0.7)
        )

        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=entry1
        )
        await coordinator.add_operation(
            txn_id, operation_type="save", tier="persistent", entry=entry2
        )

        prepared = await coordinator.prepare(txn_id)
        assert prepared is True

        committed = await coordinator.commit(txn_id)
        assert committed is True

    @pytest.mark.asyncio
    async def test_transaction_context_manager_success(self, coordinator, sample_entry):
        """Test transaction context manager with successful commit."""
        async with coordinator.transaction() as txn_id:
            await coordinator.add_operation(
                txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
            )

        # Transaction should be automatically cleaned up
        assert coordinator.get_state(txn_id) is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self, coordinator, sample_entry):
        """Test transaction context manager with exception (should abort)."""
        with pytest.raises(RuntimeError, match="Test error"):
            async with coordinator.transaction() as txn_id:
                await coordinator.add_operation(
                    txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
                )
                raise RuntimeError("Test error")

        # Transaction should be aborted and cleaned up
        assert coordinator.get_state(txn_id) is None

    @pytest.mark.asyncio
    async def test_delete_operation(self, coordinator):
        """Test delete operation in transaction."""
        txn_id = await coordinator.begin()

        await coordinator.add_operation(
            txn_id, operation_type="delete", tier="ephemeral", entry_id="test-entry-id"
        )

        prepared = await coordinator.prepare(txn_id)
        assert prepared is True

        committed = await coordinator.commit(txn_id)
        assert committed is True


class TestIsolationLevels:
    """Test transaction isolation level configurations."""

    @pytest.mark.asyncio
    async def test_read_uncommitted(self):
        """Test READ_UNCOMMITTED isolation level."""
        coordinator = TransactionCoordinator(isolation_level=IsolationLevel.READ_UNCOMMITTED)
        assert coordinator.isolation_level == IsolationLevel.READ_UNCOMMITTED

    @pytest.mark.asyncio
    async def test_read_committed(self):
        """Test READ_COMMITTED isolation level."""
        coordinator = TransactionCoordinator(isolation_level=IsolationLevel.READ_COMMITTED)
        assert coordinator.isolation_level == IsolationLevel.READ_COMMITTED

    @pytest.mark.asyncio
    async def test_repeatable_read(self):
        """Test REPEATABLE_READ isolation level."""
        coordinator = TransactionCoordinator(isolation_level=IsolationLevel.REPEATABLE_READ)
        assert coordinator.isolation_level == IsolationLevel.REPEATABLE_READ

    @pytest.mark.asyncio
    async def test_serializable(self):
        """Test SERIALIZABLE isolation level."""
        coordinator = TransactionCoordinator(isolation_level=IsolationLevel.SERIALIZABLE)
        assert coordinator.isolation_level == IsolationLevel.SERIALIZABLE


class TestTransactionState:
    """Test transaction state transitions."""

    @pytest.mark.asyncio
    async def test_state_transition_success_path(self, coordinator, sample_entry):
        """Test state transitions in successful transaction."""
        txn_id = await coordinator.begin()
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

        await coordinator.prepare(txn_id)
        assert coordinator.get_state(txn_id) == TransactionState.PREPARED

        await coordinator.commit(txn_id)
        assert coordinator.get_state(txn_id) == TransactionState.COMMITTED

    @pytest.mark.asyncio
    async def test_state_transition_abort_path(self, coordinator, sample_entry):
        """Test state transitions when aborting."""
        txn_id = await coordinator.begin()
        assert coordinator.get_state(txn_id) == TransactionState.ACTIVE

        await coordinator.add_operation(
            txn_id, operation_type="save", tier="ephemeral", entry=sample_entry
        )

        await coordinator.abort(txn_id)
        assert coordinator.get_state(txn_id) == TransactionState.ABORTED

    @pytest.mark.asyncio
    async def test_get_state_nonexistent_transaction(self, coordinator):
        """Test getting state of non-existent transaction returns None."""
        state = coordinator.get_state("nonexistent-txn")
        assert state is None
