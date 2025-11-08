"""Unit tests for audit data models."""

import pytest
from datetime import datetime, timedelta
from uuid import UUID

from axon.models.audit import AuditEvent, EventStatus, OperationType


class TestOperationType:
    """Test OperationType enum."""

    def test_operation_types_exist(self):
        """Test that all operation types are defined."""
        assert OperationType.STORE == "store"
        assert OperationType.RECALL == "recall"
        assert OperationType.FORGET == "forget"
        assert OperationType.COMPACT == "compact"
        assert OperationType.EXPORT == "export"
        assert OperationType.BULK_STORE == "bulk_store"
        assert OperationType.REINDEX == "reindex"

    def test_operation_type_string_values(self):
        """Test that operation types have correct string values."""
        assert OperationType.STORE.value == "store"
        assert OperationType.RECALL.value == "recall"


class TestEventStatus:
    """Test EventStatus enum."""

    def test_status_types_exist(self):
        """Test that all status types are defined."""
        assert EventStatus.SUCCESS == "success"
        assert EventStatus.FAILURE == "failure"
        assert EventStatus.PARTIAL == "partial"


class TestAuditEvent:
    """Test AuditEvent model."""

    def test_minimal_audit_event(self):
        """Test creating audit event with minimal fields."""
        event = AuditEvent(operation=OperationType.STORE)

        assert isinstance(event.event_id, UUID)
        assert isinstance(event.timestamp, datetime)
        assert event.operation == OperationType.STORE
        assert event.user_id is None
        assert event.session_id is None
        assert event.entry_ids == []
        assert event.metadata == {}
        assert event.status == EventStatus.SUCCESS
        assert event.error_message is None
        assert event.duration_ms is None

    def test_full_audit_event(self):
        """Test creating audit event with all fields."""
        timestamp = datetime.now()
        event = AuditEvent(
            operation=OperationType.RECALL,
            user_id="user_123",
            session_id="session_456",
            entry_ids=["entry_1", "entry_2", "entry_3"],
            metadata={"query": "test query", "k": 5},
            status=EventStatus.SUCCESS,
            duration_ms=15.7,
        )

        assert event.operation == OperationType.RECALL
        assert event.user_id == "user_123"
        assert event.session_id == "session_456"
        assert len(event.entry_ids) == 3
        assert event.metadata["query"] == "test query"
        assert event.metadata["k"] == 5
        assert event.status == EventStatus.SUCCESS
        assert event.duration_ms == 15.7
        assert event.error_message is None

    def test_failed_event_with_error(self):
        """Test creating failed event with error message."""
        event = AuditEvent(
            operation=OperationType.STORE,
            status=EventStatus.FAILURE,
            error_message="ValueError: Invalid content",
            duration_ms=2.3,
        )

        assert event.status == EventStatus.FAILURE
        assert event.error_message == "ValueError: Invalid content"
        assert event.duration_ms == 2.3

    def test_to_dict_serialization(self):
        """Test to_dict method serializes correctly."""
        event = AuditEvent(
            operation=OperationType.COMPACT,
            user_id="user_123",
            entry_ids=["entry_1"],
            metadata={"tier": "persistent"},
            status=EventStatus.SUCCESS,
            duration_ms=125.6,
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert isinstance(event_dict["event_id"], str)
        assert isinstance(event_dict["timestamp"], str)
        assert event_dict["operation"] == "compact"
        assert event_dict["user_id"] == "user_123"
        assert event_dict["entry_ids"] == ["entry_1"]
        assert event_dict["metadata"]["tier"] == "persistent"
        assert event_dict["status"] == "success"
        assert event_dict["duration_ms"] == 125.6

    def test_to_dict_with_none_values(self):
        """Test to_dict handles None values correctly."""
        event = AuditEvent(operation=OperationType.STORE)
        event_dict = event.to_dict()

        assert event_dict["user_id"] is None
        assert event_dict["session_id"] is None
        assert event_dict["error_message"] is None
        assert event_dict["duration_ms"] is None

    def test_timestamp_iso_format(self):
        """Test timestamp is serialized to ISO format."""
        event = AuditEvent(operation=OperationType.EXPORT)
        event_dict = event.to_dict()

        # Should be ISO 8601 format
        timestamp_str = event_dict["timestamp"]
        assert "T" in timestamp_str
        # Should be parseable
        parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_event_id_is_uuid(self):
        """Test event_id is valid UUID."""
        event = AuditEvent(operation=OperationType.STORE)

        assert isinstance(event.event_id, UUID)
        # Should be able to convert to string
        event_id_str = str(event.event_id)
        # Should be able to parse back
        parsed_uuid = UUID(event_id_str)
        assert parsed_uuid == event.event_id

    def test_metadata_can_be_complex(self):
        """Test metadata can hold complex nested structures."""
        event = AuditEvent(
            operation=OperationType.RECALL,
            metadata={
                "query": "test",
                "filters": {"tags": ["important"], "min_importance": 0.8},
                "result_count": 5,
                "nested": {"level1": {"level2": "value"}},
            },
        )

        assert event.metadata["query"] == "test"
        assert event.metadata["filters"]["tags"] == ["important"]
        assert event.metadata["nested"]["level1"]["level2"] == "value"

    def test_entry_ids_list(self):
        """Test entry_ids can hold multiple IDs."""
        entry_ids = [f"entry_{i}" for i in range(100)]
        event = AuditEvent(operation=OperationType.BULK_STORE, entry_ids=entry_ids)

        assert len(event.entry_ids) == 100
        assert event.entry_ids[0] == "entry_0"
        assert event.entry_ids[99] == "entry_99"

    def test_default_timestamp_is_recent(self):
        """Test default timestamp is close to current time."""
        before = datetime.utcnow()
        event = AuditEvent(operation=OperationType.STORE)
        after = datetime.utcnow()

        assert before <= event.timestamp <= after

    def test_partial_status(self):
        """Test PARTIAL status for operations that partially succeed."""
        event = AuditEvent(
            operation=OperationType.COMPACT,
            status=EventStatus.PARTIAL,
            metadata={"completed": 5, "failed": 2},
        )

        assert event.status == EventStatus.PARTIAL
        assert event.metadata["completed"] == 5
        assert event.metadata["failed"] == 2
