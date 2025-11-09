"""Unit tests for AuditLogger."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from axon.core.audit import AuditLogger
from axon.models.audit import AuditEvent, EventStatus, OperationType


@pytest.mark.asyncio
class TestAuditLoggerBasics:
    """Test basic AuditLogger functionality."""

    async def test_create_logger(self):
        """Test creating an audit logger."""
        logger = AuditLogger()

        assert logger.event_count == 0
        assert logger.total_events_logged == 0
        assert logger._max_events == 10000
        assert logger._enable_rotation is True

    async def test_create_logger_with_custom_max_events(self):
        """Test creating logger with custom max_events."""
        logger = AuditLogger(max_events=5000)

        assert logger._max_events == 5000

    async def test_log_simple_event(self):
        """Test logging a simple event."""
        logger = AuditLogger()

        event = await logger.log_event(operation=OperationType.STORE)

        assert logger.event_count == 1
        assert logger.total_events_logged == 1
        assert isinstance(event, AuditEvent)
        assert event.operation == OperationType.STORE
        assert event.status == EventStatus.SUCCESS

    async def test_log_event_with_full_details(self):
        """Test logging event with all details."""
        logger = AuditLogger()

        event = await logger.log_event(
            operation=OperationType.RECALL,
            user_id="user_123",
            session_id="session_456",
            entry_ids=["entry_1", "entry_2"],
            metadata={"query": "test", "k": 5},
            status=EventStatus.SUCCESS,
            duration_ms=12.5,
        )

        assert event.operation == OperationType.RECALL
        assert event.user_id == "user_123"
        assert event.session_id == "session_456"
        assert event.entry_ids == ["entry_1", "entry_2"]
        assert event.metadata["query"] == "test"
        assert event.duration_ms == 12.5

    async def test_log_failed_event(self):
        """Test logging a failed event."""
        logger = AuditLogger()

        event = await logger.log_event(
            operation=OperationType.STORE,
            status=EventStatus.FAILURE,
            error_message="ValueError: Invalid input",
        )

        assert event.status == EventStatus.FAILURE
        assert event.error_message == "ValueError: Invalid input"

    async def test_multiple_events(self):
        """Test logging multiple events."""
        logger = AuditLogger()

        for i in range(10):
            await logger.log_event(operation=OperationType.STORE, entry_ids=[f"entry_{i}"])

        assert logger.event_count == 10
        assert logger.total_events_logged == 10


@pytest.mark.asyncio
class TestAuditLoggerQuerying:
    """Test querying audit events."""

    async def test_get_all_events(self):
        """Test getting all events."""
        logger = AuditLogger()

        # Log some events
        await logger.log_event(operation=OperationType.STORE)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await logger.log_event(operation=OperationType.RECALL)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await logger.log_event(operation=OperationType.COMPACT)

        events = await logger.get_events()

        assert len(events) == 3
        # Should be newest first
        assert events[0].operation == OperationType.COMPACT
        assert events[2].operation == OperationType.STORE

    async def test_filter_by_operation(self):
        """Test filtering events by operation type."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE)
        await logger.log_event(operation=OperationType.STORE)
        await logger.log_event(operation=OperationType.RECALL)
        await logger.log_event(operation=OperationType.COMPACT)

        store_events = await logger.get_events(operation=OperationType.STORE)
        recall_events = await logger.get_events(operation=OperationType.RECALL)

        assert len(store_events) == 2
        assert len(recall_events) == 1
        assert all(e.operation == OperationType.STORE for e in store_events)

    async def test_filter_by_user_id(self):
        """Test filtering events by user_id."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE, user_id="user_1")
        await logger.log_event(operation=OperationType.STORE, user_id="user_1")
        await logger.log_event(operation=OperationType.STORE, user_id="user_2")

        user1_events = await logger.get_events(user_id="user_1")
        user2_events = await logger.get_events(user_id="user_2")

        assert len(user1_events) == 2
        assert len(user2_events) == 1

    async def test_filter_by_session_id(self):
        """Test filtering events by session_id."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE, session_id="session_1")
        await logger.log_event(operation=OperationType.RECALL, session_id="session_1")
        await logger.log_event(operation=OperationType.STORE, session_id="session_2")

        session1_events = await logger.get_events(session_id="session_1")

        assert len(session1_events) == 2
        assert all(e.session_id == "session_1" for e in session1_events)

    async def test_filter_by_status(self):
        """Test filtering events by status."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE, status=EventStatus.SUCCESS)
        await logger.log_event(operation=OperationType.STORE, status=EventStatus.SUCCESS)
        await logger.log_event(operation=OperationType.STORE, status=EventStatus.FAILURE)

        success_events = await logger.get_events(status=EventStatus.SUCCESS)
        failure_events = await logger.get_events(status=EventStatus.FAILURE)

        assert len(success_events) == 2
        assert len(failure_events) == 1

    async def test_filter_by_time_range(self):
        """Test filtering events by time range."""
        logger = AuditLogger()

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Log events
        await logger.log_event(operation=OperationType.STORE)
        await asyncio.sleep(0.01)  # Small delay
        await logger.log_event(operation=OperationType.RECALL)

        # Get events from yesterday
        events_since_yesterday = await logger.get_events(start_time=yesterday)
        assert len(events_since_yesterday) == 2

        # Get events until tomorrow
        events_until_tomorrow = await logger.get_events(end_time=tomorrow)
        assert len(events_until_tomorrow) == 2

        # Get events in narrow range (should be empty if range is in past)
        past_start = yesterday - timedelta(days=1)
        past_end = yesterday
        past_events = await logger.get_events(start_time=past_start, end_time=past_end)
        assert len(past_events) == 0

    async def test_filter_with_limit(self):
        """Test limiting number of returned events."""
        logger = AuditLogger()

        # Log 10 events
        for i in range(10):
            await logger.log_event(operation=OperationType.STORE)

        events = await logger.get_events(limit=5)

        assert len(events) == 5

    async def test_combined_filters(self):
        """Test combining multiple filters."""
        logger = AuditLogger()

        await logger.log_event(
            operation=OperationType.STORE, user_id="user_1", status=EventStatus.SUCCESS
        )
        await logger.log_event(
            operation=OperationType.STORE, user_id="user_1", status=EventStatus.FAILURE
        )
        await logger.log_event(
            operation=OperationType.RECALL, user_id="user_1", status=EventStatus.SUCCESS
        )

        # Filter by operation AND user_id AND status
        events = await logger.get_events(
            operation=OperationType.STORE,
            user_id="user_1",
            status=EventStatus.SUCCESS,
        )

        assert len(events) == 1
        assert events[0].operation == OperationType.STORE
        assert events[0].user_id == "user_1"
        assert events[0].status == EventStatus.SUCCESS


@pytest.mark.asyncio
class TestAuditLoggerExport:
    """Test audit log export functionality."""

    async def test_export_to_json(self):
        """Test exporting events to JSON file."""
        logger = AuditLogger()

        # Log some events
        await logger.log_event(operation=OperationType.STORE, user_id="user_1")
        await logger.log_event(operation=OperationType.RECALL, user_id="user_2")

        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "audit_log.json"

            count = await logger.export_to_json(file_path)

            assert count == 2
            assert file_path.exists()

            # Read and verify JSON
            with open(file_path, "r") as f:
                data = json.load(f)

            assert len(data) == 2
            # Check that both operations are present (order may vary)
            operations = {e["operation"] for e in data}
            assert operations == {"recall", "store"}

    async def test_export_with_time_filter(self):
        """Test exporting events with time filter."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE)
        await asyncio.sleep(0.01)
        cutoff = datetime.utcnow()
        await asyncio.sleep(0.01)
        await logger.log_event(operation=OperationType.RECALL)

        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "filtered_log.json"

            # Export only events after cutoff
            count = await logger.export_to_json(file_path, start_time=cutoff)

            assert count == 1

            with open(file_path, "r") as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["operation"] == "recall"

    async def test_export_creates_parent_directories(self):
        """Test that export creates parent directories if needed."""
        logger = AuditLogger()

        await logger.log_event(operation=OperationType.STORE)

        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested" / "deep" / "audit.json"

            count = await logger.export_to_json(file_path)

            assert count == 1
            assert file_path.exists()
            assert file_path.parent.exists()


@pytest.mark.asyncio
class TestAuditLoggerRotation:
    """Test audit log rotation."""

    async def test_rotation_when_max_reached(self):
        """Test that rotation occurs when max_events is reached."""
        logger = AuditLogger(max_events=10, enable_rotation=True)

        # Log more than max_events
        for i in range(15):
            await logger.log_event(operation=OperationType.STORE)

        # Should have rotated, keeping newest 5 (half of max)
        assert logger.event_count == 5
        assert logger.total_events_logged == 15

    async def test_rotation_with_auto_export(self):
        """Test rotation with auto-export to file."""
        with TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "auto_export.json"
            logger = AuditLogger(max_events=5, auto_export_path=export_path, enable_rotation=True)

            # Log events to trigger rotation
            for i in range(6):
                await logger.log_event(operation=OperationType.STORE, entry_ids=[f"entry_{i}"])

            # Should have exported and cleared
            assert logger.event_count == 0  # Cleared after export
            assert export_path.exists()

            # Verify exported data
            with open(export_path, "r") as f:
                data = json.load(f)

            assert len(data) == 5  # First 5 events before rotation

    async def test_no_rotation_when_disabled(self):
        """Test that rotation doesn't occur when disabled."""
        logger = AuditLogger(max_events=5, enable_rotation=False)

        # Log more than max_events
        for i in range(10):
            await logger.log_event(operation=OperationType.STORE)

        # Should keep all events (no rotation)
        assert logger.event_count == 10


@pytest.mark.asyncio
class TestAuditLoggerClear:
    """Test clearing audit log."""

    async def test_clear_removes_all_events(self):
        """Test that clear removes all events."""
        logger = AuditLogger()

        # Log events
        for i in range(5):
            await logger.log_event(operation=OperationType.STORE)

        assert logger.event_count == 5
        assert logger.total_events_logged == 5

        # Clear
        await logger.clear()

        assert logger.event_count == 0
        assert logger.total_events_logged == 5  # Total is preserved


@pytest.mark.asyncio
class TestAuditLoggerStats:
    """Test audit logger statistics."""

    async def test_get_stats(self):
        """Test getting logger statistics."""
        logger = AuditLogger(max_events=1000, enable_rotation=True)

        # Log some events
        for i in range(5):
            await logger.log_event(operation=OperationType.STORE)

        stats = logger.get_stats()

        assert stats["events_in_memory"] == 5
        assert stats["total_events_logged"] == 5
        assert stats["max_events"] == 1000
        assert stats["rotation_enabled"] is True
        assert stats["auto_export_enabled"] is False

    async def test_stats_with_auto_export(self):
        """Test stats with auto_export enabled."""
        with TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.json"
            logger = AuditLogger(auto_export_path=export_path)

            stats = logger.get_stats()

            assert stats["auto_export_enabled"] is True


@pytest.mark.asyncio
class TestAuditLoggerThreadSafety:
    """Test audit logger thread safety."""

    async def test_concurrent_logging(self):
        """Test logging from multiple concurrent tasks."""
        logger = AuditLogger()

        # Create tasks that log concurrently
        async def log_events(count: int):
            for i in range(count):
                await logger.log_event(operation=OperationType.STORE)

        # Run 5 tasks concurrently, each logging 10 events
        tasks = [log_events(10) for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should have all 50 events
        assert logger.event_count == 50
        assert logger.total_events_logged == 50

    async def test_concurrent_query_and_log(self):
        """Test querying while logging concurrently."""
        logger = AuditLogger()

        async def log_continuously():
            for i in range(20):
                await logger.log_event(operation=OperationType.STORE)
                await asyncio.sleep(0.001)

        async def query_continuously():
            for i in range(10):
                events = await logger.get_events()
                await asyncio.sleep(0.002)

        # Run logging and querying concurrently
        await asyncio.gather(log_continuously(), query_continuously())

        # Should complete without errors
        assert logger.event_count > 0
