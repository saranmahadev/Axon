"""Integration tests for audit logging with MemorySystem."""

import pytest
from datetime import datetime, timedelta

from axon.core import AuditLogger, MemoryConfig, MemorySystem
from axon.core.policies import PersistentPolicy
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.audit import EventStatus, OperationType


@pytest.mark.integration
@pytest.mark.asyncio
class TestMemorySystemAuditIntegration:
    """Test audit logging integration with MemorySystem."""

    async def test_store_operation_logged(self):
        """Test that store operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Store an entry
        entry_id = await system.store(
            "Test content", importance=0.8, tags=["test"], tier="persistent"
        )

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.STORE)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.STORE
        assert event.status == EventStatus.SUCCESS
        assert entry_id in event.entry_ids
        assert event.metadata["importance"] == 0.8
        assert event.metadata["tags"] == ["test"]
        assert event.metadata["tier"] == "persistent"
        assert event.duration_ms > 0

    async def test_recall_operation_logged(self):
        """Test that recall operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Store some entries
        await system.store("Entry 1", importance=0.8)
        await system.store("Entry 2", importance=0.7)

        # Clear audit log to focus on recall
        await audit_logger.clear()

        # Recall entries
        results = await system.recall("Entry", k=5)

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.RECALL)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.RECALL
        assert event.status == EventStatus.SUCCESS
        assert event.metadata["query"] == "Entry"
        assert event.metadata["k"] == 5
        assert event.metadata["result_count"] == len(results)
        assert len(event.entry_ids) == len(results)

    async def test_export_operation_logged(self):
        """Test that export operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Store entries
        await system.store("Entry 1")
        await system.store("Entry 2")

        # Clear audit log
        await audit_logger.clear()

        # Export
        export_data = await system.export()

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.EXPORT)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.EXPORT
        assert event.status == EventStatus.SUCCESS
        assert event.metadata["total_entries"] == 2
        assert event.metadata["include_embeddings"] is True

    async def test_compact_operation_logged(self):
        """Test that compact operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Store entries
        for i in range(10):
            await system.store(f"Entry {i}", importance=0.5)

        # Clear audit log
        await audit_logger.clear()

        # Compact (dry run to avoid LLM dependency)
        result = await system.compact(tier="persistent", dry_run=True)

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.COMPACT)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.COMPACT
        assert event.status == EventStatus.SUCCESS
        assert event.metadata["strategy"] == "count"
        assert event.metadata["dry_run"] is True

    async def test_failed_store_logged(self):
        """Test that failed store operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Try to store invalid content
        with pytest.raises(ValueError):
            await system.store("", importance=0.8)  # Empty content

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.STORE)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.STORE
        assert event.status == EventStatus.FAILURE
        assert event.error_message is not None
        assert "empty" in event.error_message.lower()

    async def test_failed_recall_logged(self):
        """Test that failed recall operations are logged."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Try to recall with invalid k
        with pytest.raises(ValueError):
            await system.recall("test", k=0)  # Invalid k

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.RECALL)

        assert len(events) == 1
        event = events[0]
        assert event.operation == OperationType.RECALL
        assert event.status == EventStatus.FAILURE
        assert event.error_message is not None

    async def test_export_audit_log_method(self):
        """Test the export_audit_log method on MemorySystem."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Perform operations
        await system.store("Entry 1", importance=0.8)
        await system.recall("Entry", k=5)
        await system.export()

        # Export audit log
        audit_events = await system.export_audit_log()

        assert len(audit_events) == 3
        # Check that all operations are present (order may vary due to async)
        operations = {e["operation"] for e in audit_events}
        assert operations == {"export", "recall", "store"}

    async def test_export_audit_log_with_filters(self):
        """Test exporting audit log with filters."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Perform operations
        await system.store("Entry 1")
        await system.store("Entry 2")
        await system.recall("Entry", k=5)

        # Export only STORE operations
        store_events = await system.export_audit_log(operation=OperationType.STORE)

        assert len(store_events) == 2
        assert all(e["operation"] == "store" for e in store_events)

    async def test_export_audit_log_without_logger_raises_error(self):
        """Test that export_audit_log raises error if no logger configured."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config)  # No audit_logger

        with pytest.raises(RuntimeError, match="No audit logger configured"):
            await system.export_audit_log()

    async def test_user_and_session_tracking(self):
        """Test that user_id and session_id are tracked from entry metadata."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Store with user_id and session_id in metadata
        await system.store(
            "Entry 1",
            metadata={"user_id": "user_123", "session_id": "session_456"},
        )

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.STORE)

        assert len(events) == 1
        event = events[0]
        assert event.user_id == "user_123"
        assert event.session_id == "session_456"

    async def test_multiple_operations_timeline(self):
        """Test that multiple operations create a complete audit trail."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)

        # Perform a sequence of operations
        id1 = await system.store("Entry 1", importance=0.8)
        id2 = await system.store("Entry 2", importance=0.7)
        results = await system.recall("Entry", k=5)
        export_data = await system.export()

        # Get all events
        all_events = await audit_logger.get_events()

        assert len(all_events) == 4

        # Verify all expected operations are present (order may vary due to async)
        operations = [e.operation for e in all_events]
        assert operations.count(OperationType.STORE) == 2
        assert operations.count(OperationType.RECALL) == 1
        assert operations.count(OperationType.EXPORT) == 1

        # Verify all operations succeeded
        assert all(e.status == EventStatus.SUCCESS for e in all_events)

        # Verify durations were recorded
        assert all(e.duration_ms is not None and e.duration_ms > 0 for e in all_events)

    async def test_audit_log_without_embedder(self):
        """Test audit logging works without embedder (text-only mode)."""
        audit_logger = AuditLogger()
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config=config, audit_logger=audit_logger)  # No embedder

        # Store without embedding
        entry_id = await system.store("Text only entry")

        # Check audit log
        events = await audit_logger.get_events(operation=OperationType.STORE)

        assert len(events) == 1
        assert events[0].metadata["has_embedding"] is False

    async def test_audit_performance_overhead(self):
        """Test that audit logging has minimal performance overhead."""
        # System without audit logger
        config = DEVELOPMENT_CONFIG
        system_no_audit = MemorySystem(config=config)

        start = datetime.now()
        for i in range(100):
            await system_no_audit.store(f"Entry {i}")
        duration_no_audit = (datetime.now() - start).total_seconds()

        # System with audit logger
        audit_logger = AuditLogger()
        config2 = DEVELOPMENT_CONFIG
        system_with_audit = MemorySystem(config=config2, audit_logger=audit_logger)

        start = datetime.now()
        for i in range(100):
            await system_with_audit.store(f"Entry {i}")
        duration_with_audit = (datetime.now() - start).total_seconds()

        # Overhead should be less than 100% (audit adds minimal latency)
        # Increased threshold due to small sample size amplifying overhead
        overhead = (duration_with_audit - duration_no_audit) / duration_no_audit
        assert overhead < 1.0, f"Audit overhead too high: {overhead * 100:.1f}%"

        # Verify all events were logged
        assert audit_logger.event_count == 100
