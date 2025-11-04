"""Pytest configuration and shared fixtures for Axon tests."""

from datetime import datetime

import pytest

from axon import DateRange, Filter, MemoryEntry, MemoryMetadata


@pytest.fixture
def sample_metadata() -> MemoryMetadata:
    """Create sample metadata for testing."""
    return MemoryMetadata(
        user_id="test_user_123",
        session_id="test_session_456",
        source="app",
        tags=["test", "sample"],
        importance=0.7,
        privacy_level="public",
        version="test-embedder-v1",
    )


@pytest.fixture
def sample_entry(sample_metadata: MemoryMetadata) -> MemoryEntry:
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        text="This is a test memory entry about science fiction movies.",
        type="note",
        metadata=sample_metadata,
    )


@pytest.fixture
def sample_entry_with_embedding(sample_metadata: MemoryMetadata) -> MemoryEntry:
    """Create a sample memory entry with an embedding vector."""
    return MemoryEntry(
        text="This entry has an embedding vector.",
        type="note",
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        metadata=sample_metadata,
    )


@pytest.fixture
def sample_filter() -> Filter:
    """Create a sample filter for testing."""
    return Filter(
        user_id="test_user_123",
        tags=["test"],
        min_importance=0.5,
        privacy_level="public",
    )


@pytest.fixture
def date_range() -> DateRange:
    """Create a sample date range for testing."""
    return DateRange(
        start=datetime(2025, 11, 1),
        end=datetime(2025, 11, 4),
    )
