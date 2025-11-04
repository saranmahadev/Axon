"""Unit tests for Axon data models."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from axon import (
    DateRange,
    Filter,
    MemoryEntry,
    MemoryEntryType,
    MemoryMetadata,
    MemoryTier,
    PrivacyLevel,
    ProvenanceEvent,
    SourceType,
)


class TestProvenanceEvent:
    """Test cases for ProvenanceEvent model."""

    def test_provenance_event_creation(self):
        """Test creating a provenance event."""
        event = ProvenanceEvent(action="store", by="memory_system", metadata={"tier": "persistent"})
        assert event.action == "store"
        assert event.by == "memory_system"
        assert event.metadata["tier"] == "persistent"
        assert isinstance(event.timestamp, datetime)

    def test_provenance_event_json_serialization(self):
        """Test JSON serialization of provenance event."""
        event = ProvenanceEvent(action="recall", by="test_module")
        json_data = event.model_dump()
        assert json_data["action"] == "recall"
        assert json_data["by"] == "test_module"


class TestMemoryMetadata:
    """Test cases for MemoryMetadata model."""

    def test_metadata_defaults(self):
        """Test metadata creation with defaults."""
        meta = MemoryMetadata()
        assert meta.user_id is None
        assert meta.session_id is None
        assert meta.source == "app"
        assert meta.privacy_level == "public"
        assert isinstance(meta.created_at, datetime)
        assert meta.last_accessed_at is None
        assert meta.tags == []
        assert meta.importance == 0.5
        assert meta.version == ""
        assert meta.provenance == []

    def test_metadata_with_values(self):
        """Test metadata creation with explicit values."""
        meta = MemoryMetadata(
            user_id="user123",
            session_id="session456",
            source="agent",
            tags=["important", "urgent"],
            importance=0.9,
            privacy_level="private",
        )
        assert meta.user_id == "user123"
        assert meta.session_id == "session456"
        assert meta.source == "agent"
        assert meta.tags == ["important", "urgent"]
        assert meta.importance == 0.9
        assert meta.privacy_level == "private"

    def test_importance_validation(self):
        """Test importance score validation."""
        # Valid importance
        meta = MemoryMetadata(importance=0.0)
        assert meta.importance == 0.0

        meta = MemoryMetadata(importance=1.0)
        assert meta.importance == 1.0

        # Invalid importance - too low
        with pytest.raises(ValidationError):
            MemoryMetadata(importance=-0.1)

        # Invalid importance - too high
        with pytest.raises(ValidationError):
            MemoryMetadata(importance=1.1)

    def test_metadata_custom_fields(self):
        """Test that metadata allows custom fields."""
        meta = MemoryMetadata(custom_field="custom_value", another_field=123)
        # Pydantic v2 stores extra fields in __pydantic_extra__
        assert hasattr(meta, "custom_field") or "custom_field" in meta.__pydantic_extra__


class TestMemoryEntry:
    """Test cases for MemoryEntry model."""

    def test_entry_creation_minimal(self):
        """Test creating entry with minimal required fields."""
        entry = MemoryEntry(text="Test memory")
        assert entry.text == "Test memory"
        assert entry.type == "note"
        assert entry.embedding is None
        assert isinstance(entry.metadata, MemoryMetadata)
        assert len(entry.id) > 0  # UUID generated

    def test_entry_creation_full(self):
        """Test creating entry with all fields."""
        meta = MemoryMetadata(user_id="user123", tags=["test"], importance=0.8)
        entry = MemoryEntry(
            text="Full test memory",
            type="conversation_turn",
            embedding=[0.1, 0.2, 0.3],
            metadata=meta,
        )
        assert entry.text == "Full test memory"
        assert entry.type == "conversation_turn"
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.metadata.user_id == "user123"

    def test_entry_text_validation(self):
        """Test that text field must not be empty."""
        with pytest.raises(ValidationError):
            MemoryEntry(text="")

    def test_add_provenance(self):
        """Test adding provenance events to entry."""
        entry = MemoryEntry(text="Test")
        assert len(entry.metadata.provenance) == 0

        entry.add_provenance("store", "memory_system", tier="persistent")
        assert len(entry.metadata.provenance) == 1
        assert entry.metadata.provenance[0].action == "store"
        assert entry.metadata.provenance[0].by == "memory_system"
        assert entry.metadata.provenance[0].metadata["tier"] == "persistent"

    def test_update_accessed(self):
        """Test updating last accessed timestamp."""
        entry = MemoryEntry(text="Test")
        assert entry.metadata.last_accessed_at is None

        entry.update_accessed()
        assert entry.metadata.last_accessed_at is not None
        assert isinstance(entry.metadata.last_accessed_at, datetime)

    def test_has_embedding(self):
        """Test has_embedding property."""
        entry_no_embed = MemoryEntry(text="No embedding")
        assert not entry_no_embed.has_embedding

        entry_with_embed = MemoryEntry(text="With embedding", embedding=[0.1, 0.2, 0.3])
        assert entry_with_embed.has_embedding

    def test_embedding_dim(self):
        """Test embedding_dim property."""
        entry_no_embed = MemoryEntry(text="No embedding")
        assert entry_no_embed.embedding_dim is None

        entry_with_embed = MemoryEntry(text="With embedding", embedding=[0.1, 0.2, 0.3, 0.4, 0.5])
        assert entry_with_embed.embedding_dim == 5

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = MemoryEntry(
            text="Test entry",
            type="note",
            metadata=MemoryMetadata(user_id="user123", tags=["test"]),
        )

        # Serialize
        json_data = original.model_dump()
        assert json_data["text"] == "Test entry"
        assert json_data["metadata"]["user_id"] == "user123"

        # Deserialize
        reconstructed = MemoryEntry(**json_data)
        assert reconstructed.text == original.text
        assert reconstructed.metadata.user_id == original.metadata.user_id


class TestDateRange:
    """Test cases for DateRange model."""

    def test_date_range_creation(self):
        """Test creating a date range."""
        start = datetime(2025, 11, 1)
        end = datetime(2025, 11, 4)
        range_obj = DateRange(start=start, end=end)
        assert range_obj.start == start
        assert range_obj.end == end

    def test_date_range_validation(self):
        """Test that end must be after start."""
        with pytest.raises(ValidationError):
            DateRange(start=datetime(2025, 11, 4), end=datetime(2025, 11, 1))

    def test_date_range_optional(self):
        """Test that both start and end are optional."""
        range_obj = DateRange()
        assert range_obj.start is None
        assert range_obj.end is None

        range_obj = DateRange(start=datetime(2025, 11, 1))
        assert range_obj.start is not None
        assert range_obj.end is None


class TestFilter:
    """Test cases for Filter model."""

    def test_filter_creation_empty(self):
        """Test creating an empty filter."""
        filter_obj = Filter()
        assert filter_obj.user_id is None
        assert filter_obj.session_id is None
        assert filter_obj.tags == []
        assert filter_obj.privacy_level is None
        assert filter_obj.min_importance is None
        assert filter_obj.max_importance is None

    def test_filter_creation_with_values(self):
        """Test creating filter with values."""
        filter_obj = Filter(
            user_id="user123", tags=["important"], min_importance=0.5, privacy_level="public"
        )
        assert filter_obj.user_id == "user123"
        assert filter_obj.tags == ["important"]
        assert filter_obj.min_importance == 0.5
        assert filter_obj.privacy_level == "public"

    def test_importance_range_validation(self):
        """Test importance range validation."""
        # Valid range
        filter_obj = Filter(min_importance=0.3, max_importance=0.8)
        assert filter_obj.min_importance == 0.3
        assert filter_obj.max_importance == 0.8

        # Invalid range (max < min)
        with pytest.raises(ValidationError):
            Filter(min_importance=0.8, max_importance=0.3)

    def test_filter_matches_user_id(self):
        """Test filter matching by user_id."""
        filter_obj = Filter(user_id="user123")

        matching = MemoryEntry(text="Test", metadata=MemoryMetadata(user_id="user123"))
        assert filter_obj.matches(matching)

        non_matching = MemoryEntry(text="Test", metadata=MemoryMetadata(user_id="user456"))
        assert not filter_obj.matches(non_matching)

    def test_filter_matches_tags(self):
        """Test filter matching by tags."""
        filter_obj = Filter(tags=["important", "urgent"])

        matching = MemoryEntry(
            text="Test", metadata=MemoryMetadata(tags=["important", "urgent", "extra"])
        )
        assert filter_obj.matches(matching)

        partial_match = MemoryEntry(text="Test", metadata=MemoryMetadata(tags=["important"]))
        assert not filter_obj.matches(partial_match)

    def test_filter_matches_importance(self):
        """Test filter matching by importance range."""
        filter_obj = Filter(min_importance=0.5, max_importance=0.8)

        matching = MemoryEntry(text="Test", metadata=MemoryMetadata(importance=0.7))
        assert filter_obj.matches(matching)

        too_low = MemoryEntry(text="Test", metadata=MemoryMetadata(importance=0.3))
        assert not filter_obj.matches(too_low)

        too_high = MemoryEntry(text="Test", metadata=MemoryMetadata(importance=0.9))
        assert not filter_obj.matches(too_high)

    def test_filter_matches_older_than_days(self):
        """Test filter matching by age in days."""
        filter_obj = Filter(older_than_days=7)

        old_entry = MemoryEntry(
            text="Old",
            metadata=MemoryMetadata(created_at=datetime.now(timezone.utc) - timedelta(days=10)),
        )
        assert filter_obj.matches(old_entry)

        recent_entry = MemoryEntry(
            text="Recent",
            metadata=MemoryMetadata(created_at=datetime.now(timezone.utc) - timedelta(days=3)),
        )
        assert not filter_obj.matches(recent_entry)

    def test_filter_matches_combined(self):
        """Test filter with multiple criteria."""
        filter_obj = Filter(
            user_id="user123", tags=["important"], min_importance=0.6, privacy_level="public"
        )

        matching = MemoryEntry(
            text="Match all",
            metadata=MemoryMetadata(
                user_id="user123",
                tags=["important", "extra"],
                importance=0.8,
                privacy_level="public",
            ),
        )
        assert filter_obj.matches(matching)

        wrong_user = MemoryEntry(
            text="Wrong user",
            metadata=MemoryMetadata(
                user_id="user456", tags=["important"], importance=0.8, privacy_level="public"
            ),
        )
        assert not filter_obj.matches(wrong_user)


class TestEnums:
    """Test cases for enum types."""

    def test_memory_tier_enum(self):
        """Test MemoryTier enum values."""
        assert MemoryTier.EPHEMERAL.value == "ephemeral"
        assert MemoryTier.SESSION.value == "session"
        assert MemoryTier.PERSISTENT.value == "persistent"
        assert MemoryTier.ARCHIVE.value == "archive"

    def test_privacy_level_enum(self):
        """Test PrivacyLevel enum values."""
        assert PrivacyLevel.PUBLIC.value == "public"
        assert PrivacyLevel.SENSITIVE.value == "sensitive"
        assert PrivacyLevel.PRIVATE.value == "private"

    def test_source_type_enum(self):
        """Test SourceType enum values."""
        assert SourceType.APP.value == "app"
        assert SourceType.SYSTEM.value == "system"
        assert SourceType.AGENT.value == "agent"

    def test_memory_entry_type_enum(self):
        """Test MemoryEntryType enum values."""
        assert MemoryEntryType.NOTE.value == "note"
        assert MemoryEntryType.EVENT.value == "event"
        assert MemoryEntryType.CONVERSATION_TURN.value == "conversation_turn"
        assert MemoryEntryType.PROFILE.value == "profile"
        assert MemoryEntryType.EMBEDDING_SUMMARY.value == "embedding_summary"
