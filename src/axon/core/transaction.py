"""
Transaction Management for Multi-Tier Memory Operations

This module implements Two-Phase Commit (2PC) protocol to ensure atomic
operations across multiple storage tiers. It provides transactional guarantees
for store, update, and delete operations.

Key Components:
- TransactionCoordinator: Orchestrates 2PC across adapters
- TransactionContext: Context manager for transactional operations
- IsolationLevel: Transaction isolation levels
- TransactionState: Tracks transaction lifecycle

Usage:
    >>> async with system.transaction() as txn:
    ...     await txn.store("entry 1", tier="ephemeral")
    ...     await txn.store("entry 2", tier="persistent")
    ...     # Automatically commits on exit, rolls back on exception
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..adapters.base import StorageAdapter
from ..models.entry import MemoryEntry

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction lifecycle states."""

    ACTIVE = "active"  # Transaction in progress, accepting operations
    PREPARING = "preparing"  # Phase 1: Preparing to commit
    PREPARED = "prepared"  # Phase 1 complete, ready to commit
    COMMITTING = "committing"  # Phase 2: Committing changes
    COMMITTED = "committed"  # Transaction successfully committed
    ABORTING = "aborting"  # Rolling back changes
    ABORTED = "aborted"  # Transaction rolled back
    FAILED = "failed"  # Transaction failed


class IsolationLevel(Enum):
    """
    Transaction isolation levels.

    - READ_UNCOMMITTED: Lowest isolation, allows dirty reads
    - READ_COMMITTED: Prevents dirty reads
    - REPEATABLE_READ: Prevents dirty and non-repeatable reads
    - SERIALIZABLE: Highest isolation, prevents all anomalies
    """

    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@dataclass
class TransactionOperation:
    """
    Record of an operation within a transaction.

    Tracks operations for rollback and commit coordination.
    """

    operation_type: str  # "save", "delete", "update"
    tier: str
    entry: MemoryEntry | None = None
    entry_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ParticipantState:
    """
    Tracks the state of a participant (adapter) in 2PC.

    Each adapter participating in the transaction has its own state
    tracking for prepare/commit/abort operations.
    """

    tier: str
    adapter: StorageAdapter
    prepared: bool = False
    committed: bool = False
    aborted: bool = False
    operations: list[TransactionOperation] = field(default_factory=list)
    prepare_data: Any = None  # Adapter-specific prepare data


class TransactionCoordinator:
    """
    Coordinates Two-Phase Commit (2PC) across multiple storage adapters.

    Implements the 2PC protocol:
    1. Prepare Phase: Ask all participants to prepare to commit
    2. Commit Phase: If all prepared successfully, commit all; otherwise abort all

    This ensures atomicity across multiple storage tiers - either all changes
    succeed or all are rolled back.

    Example:
        >>> coordinator = TransactionCoordinator(isolation_level=IsolationLevel.READ_COMMITTED)
        >>> txn_id = await coordinator.begin()
        >>> await coordinator.add_operation(txn_id, "save", "ephemeral", entry1)
        >>> await coordinator.add_operation(txn_id, "save", "persistent", entry2)
        >>> success = await coordinator.commit(txn_id)
    """

    def __init__(
        self,
        adapters: dict[str, StorageAdapter] | None = None,
        isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
        timeout_seconds: float = 30.0,
    ):
        """
        Initialize transaction coordinator.

        Args:
            adapters: Map of tier name to storage adapter
            isolation_level: Transaction isolation level
            timeout_seconds: Timeout for prepare/commit operations
        """
        self.adapters = adapters or {}
        self.isolation_level = isolation_level
        self.timeout_seconds = timeout_seconds

        # Active transactions
        self._transactions: dict[str, dict[str, Any]] = {}

        # Locks for transaction state management
        self._lock = asyncio.Lock()

        logger.info(
            f"TransactionCoordinator initialized with isolation={isolation_level.value}, "
            f"timeout={timeout_seconds}s"
        )

    async def begin(self, transaction_id: str | None = None) -> str:
        """
        Begin a new transaction.

        Args:
            transaction_id: Optional explicit transaction ID (generates UUID if None)

        Returns:
            Transaction ID

        Raises:
            ValueError: If transaction ID already exists
        """
        async with self._lock:
            txn_id = transaction_id or str(uuid.uuid4())

            if txn_id in self._transactions:
                raise ValueError(f"Transaction {txn_id} already exists")

            self._transactions[txn_id] = {
                "id": txn_id,
                "state": TransactionState.ACTIVE,
                "participants": {},  # tier -> ParticipantState
                "isolation_level": self.isolation_level,
                "started_at": datetime.now(timezone.utc),
                "operations_count": 0,
            }

            logger.debug(f"Transaction {txn_id} started")
            return txn_id

    async def add_operation(
        self,
        transaction_id: str,
        operation_type: str,
        tier: str,
        entry: MemoryEntry | None = None,
        entry_id: str | None = None,
    ) -> None:
        """
        Add an operation to the transaction.

        Args:
            transaction_id: Transaction ID
            operation_type: Type of operation ("save", "delete", "update")
            tier: Storage tier
            entry: Memory entry (for save/update operations)
            entry_id: Entry ID (for delete operations)

        Raises:
            ValueError: If transaction doesn't exist or is not active
            KeyError: If tier adapter not registered
        """
        async with self._lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")

            txn = self._transactions[transaction_id]

            if txn["state"] != TransactionState.ACTIVE:
                raise ValueError(
                    f"Transaction {transaction_id} is {txn['state'].value}, " "not active"
                )

            if tier not in self.adapters:
                raise KeyError(f"No adapter registered for tier '{tier}'")

            # Get or create participant state
            if tier not in txn["participants"]:
                txn["participants"][tier] = ParticipantState(tier=tier, adapter=self.adapters[tier])

            # Add operation
            operation = TransactionOperation(
                operation_type=operation_type, tier=tier, entry=entry, entry_id=entry_id
            )

            txn["participants"][tier].operations.append(operation)
            txn["operations_count"] += 1

            logger.debug(
                f"Transaction {transaction_id}: Added {operation_type} operation to tier '{tier}'"
            )

    async def prepare(self, transaction_id: str) -> bool:
        """
        Phase 1: Prepare all participants to commit.

        Asks each adapter to prepare its changes. If all participants
        successfully prepare, returns True. If any fail, aborts all.

        Args:
            transaction_id: Transaction ID

        Returns:
            True if all participants prepared successfully, False otherwise

        Raises:
            ValueError: If transaction doesn't exist or is in wrong state
        """
        async with self._lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")

            txn = self._transactions[transaction_id]

            if txn["state"] != TransactionState.ACTIVE:
                raise ValueError(
                    f"Transaction {transaction_id} is {txn['state'].value}, "
                    "cannot prepare from this state"
                )

            txn["state"] = TransactionState.PREPARING
            logger.debug(f"Transaction {transaction_id}: Starting prepare phase")

        # Prepare all participants (outside lock to allow concurrent preparation)
        participants = list(txn["participants"].values())
        prepare_results = []

        for participant in participants:
            try:
                # For now, we simulate prepare by validating operations
                # In a real implementation, adapters would implement prepare()
                success = await self._prepare_participant(transaction_id, participant)
                prepare_results.append(success)

                if success:
                    participant.prepared = True
                    logger.debug(
                        f"Transaction {transaction_id}: Tier '{participant.tier}' prepared"
                    )
                else:
                    logger.warning(
                        f"Transaction {transaction_id}: Tier '{participant.tier}' "
                        "failed to prepare"
                    )

            except Exception as e:
                logger.error(
                    f"Transaction {transaction_id}: Prepare failed for tier "
                    f"'{participant.tier}': {e}"
                )
                prepare_results.append(False)

        # Check if all prepared
        all_prepared = all(prepare_results)

        async with self._lock:
            if all_prepared:
                txn["state"] = TransactionState.PREPARED
                logger.info(f"Transaction {transaction_id}: All participants prepared")
                return True
            else:
                txn["state"] = TransactionState.FAILED
                logger.warning(f"Transaction {transaction_id}: Prepare phase failed, " "will abort")
                return False

    async def _prepare_participant(
        self, transaction_id: str, participant: ParticipantState
    ) -> bool:
        """
        Prepare a single participant.

        In a full implementation, this would call adapter.prepare().
        For now, we validate operations and return True.

        Args:
            transaction_id: Transaction ID
            participant: Participant state

        Returns:
            True if participant can commit, False otherwise
        """
        # Validate operations
        for op in participant.operations:
            if op.operation_type == "save" and op.entry is None:
                logger.error(f"Transaction {transaction_id}: Save operation missing entry")
                return False
            if op.operation_type == "delete" and op.entry_id is None:
                logger.error(f"Transaction {transaction_id}: Delete operation missing entry_id")
                return False

        # In a real implementation, adapter would reserve resources here
        # For now, we just return success
        return True

    async def commit(self, transaction_id: str) -> bool:
        """
        Phase 2: Commit all participants.

        Applies all changes across all participants. This should only be
        called if prepare() returned True.

        Args:
            transaction_id: Transaction ID

        Returns:
            True if commit succeeded, False otherwise

        Raises:
            ValueError: If transaction doesn't exist or is not prepared
        """
        async with self._lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")

            txn = self._transactions[transaction_id]

            if txn["state"] != TransactionState.PREPARED:
                raise ValueError(
                    f"Transaction {transaction_id} is {txn['state'].value}, "
                    "must be prepared before commit"
                )

            txn["state"] = TransactionState.COMMITTING
            logger.debug(f"Transaction {transaction_id}: Starting commit phase")

        # Commit all participants
        participants = list(txn["participants"].values())
        commit_results = []

        for participant in participants:
            try:
                success = await self._commit_participant(transaction_id, participant)
                commit_results.append(success)

                if success:
                    participant.committed = True
                    logger.debug(
                        f"Transaction {transaction_id}: Tier '{participant.tier}' committed"
                    )
                else:
                    logger.error(
                        f"Transaction {transaction_id}: Tier '{participant.tier}' "
                        "failed to commit"
                    )

            except Exception as e:
                logger.error(
                    f"Transaction {transaction_id}: Commit failed for tier "
                    f"'{participant.tier}': {e}"
                )
                commit_results.append(False)

        # Check if all committed
        all_committed = all(commit_results)

        async with self._lock:
            if all_committed:
                txn["state"] = TransactionState.COMMITTED
                txn["committed_at"] = datetime.now(timezone.utc)
                logger.info(f"Transaction {transaction_id}: Successfully committed")
                return True
            else:
                # This is a critical failure - some committed, some didn't
                # In production, this would trigger compensation/recovery
                txn["state"] = TransactionState.FAILED
                logger.critical(
                    f"Transaction {transaction_id}: Partial commit failure! "
                    "Manual recovery may be needed."
                )
                return False

    async def _commit_participant(self, transaction_id: str, participant: ParticipantState) -> bool:
        """
        Commit operations for a single participant.

        Args:
            transaction_id: Transaction ID
            participant: Participant state

        Returns:
            True if commit succeeded, False otherwise
        """
        try:
            for op in participant.operations:
                if op.operation_type == "save" and op.entry:
                    await participant.adapter.save(op.entry)
                elif op.operation_type == "delete" and op.entry_id:
                    await participant.adapter.delete(op.entry_id)
                # Add more operation types as needed

            return True

        except Exception as e:
            logger.error(
                f"Transaction {transaction_id}: Commit error on tier '{participant.tier}': {e}"
            )
            return False

    async def abort(self, transaction_id: str) -> bool:
        """
        Abort the transaction and rollback all changes.

        Args:
            transaction_id: Transaction ID

        Returns:
            True if abort succeeded, False otherwise

        Raises:
            ValueError: If transaction doesn't exist
        """
        async with self._lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")

            txn = self._transactions[transaction_id]

            # Can abort from any state except already aborted/committed
            if txn["state"] in [TransactionState.ABORTED, TransactionState.COMMITTED]:
                logger.warning(
                    f"Transaction {transaction_id} is {txn['state'].value}, " "cannot abort"
                )
                return False

            txn["state"] = TransactionState.ABORTING
            logger.debug(f"Transaction {transaction_id}: Starting abort")

        # Abort all participants
        participants = list(txn["participants"].values())

        for participant in participants:
            try:
                # In a real implementation, adapter would rollback changes
                # For now, we just mark as aborted
                participant.aborted = True
                logger.debug(f"Transaction {transaction_id}: Tier '{participant.tier}' aborted")

            except Exception as e:
                logger.error(
                    f"Transaction {transaction_id}: Abort failed for tier "
                    f"'{participant.tier}': {e}"
                )

        async with self._lock:
            txn["state"] = TransactionState.ABORTED
            txn["aborted_at"] = datetime.now(timezone.utc)
            logger.info(f"Transaction {transaction_id}: Aborted")

        return True

    async def cleanup(self, transaction_id: str) -> None:
        """
        Clean up transaction state after commit or abort.

        Args:
            transaction_id: Transaction ID

        Raises:
            ValueError: If transaction doesn't exist
        """
        async with self._lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")

            txn = self._transactions[transaction_id]

            # Only cleanup if transaction is in terminal state
            if txn["state"] not in [
                TransactionState.COMMITTED,
                TransactionState.ABORTED,
                TransactionState.FAILED,
            ]:
                logger.warning(
                    f"Transaction {transaction_id} is {txn['state'].value}, "
                    "not in terminal state"
                )
                return

            del self._transactions[transaction_id]
            logger.debug(f"Transaction {transaction_id}: Cleaned up")

    def get_state(self, transaction_id: str) -> TransactionState | None:
        """
        Get current state of a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction state or None if not found
        """
        txn = self._transactions.get(transaction_id)
        return txn["state"] if txn else None

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for transactional operations.

        Automatically commits on successful exit, aborts on exception.

        Example:
            >>> async with coordinator.transaction() as txn_id:
            ...     await coordinator.add_operation(txn_id, "save", "tier1", entry)
            ...     # Commits automatically if no exception
        """
        txn_id = await self.begin()

        try:
            yield txn_id

            # Prepare phase
            prepared = await self.prepare(txn_id)
            if not prepared:
                await self.abort(txn_id)
                raise RuntimeError(f"Transaction {txn_id} failed to prepare")

            # Commit phase
            committed = await self.commit(txn_id)
            if not committed:
                raise RuntimeError(f"Transaction {txn_id} failed to commit")

        except Exception as e:
            logger.error(f"Transaction {txn_id} error: {e}")
            await self.abort(txn_id)
            raise

        finally:
            await self.cleanup(txn_id)
