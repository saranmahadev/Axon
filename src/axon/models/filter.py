"""Filter - Declarative query filtering for memory retrieval.

This module defines the Filter model for constructing queries across
memory tiers with support for temporal, categorical, and privacy filters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import PrivacyLiteral

if TYPE_CHECKING:
    from .entry import MemoryEntry


class DateRange(BaseModel):
    """Date range filter for temporal queries.

    Attributes:
        start: Start of the range (inclusive)
        end: End of the range (inclusive)
    """

    start: datetime | None = Field(None, description="Start of range (inclusive)")
    end: datetime | None = Field(None, description="End of range (inclusive)")

    @field_validator("end")
    @classmethod
    def validate_range(cls, v: datetime | None, info) -> datetime | None:
        """Ensure end is after start if both are provided."""
        if v is not None and info.data.get("start") is not None:
            if v < info.data["start"]:
                raise ValueError("End date must be after start date")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"start": "2025-11-01T00:00:00Z", "end": "2025-11-04T23:59:59Z"}
        }
    )


class Filter(BaseModel):
    """Declarative filter for memory queries.

    Supports filtering by user, session, tags, date ranges, privacy levels,
    and custom metadata fields. All filters are AND-ed together.

    Attributes:
        user_id: Filter by user identifier
        session_id: Filter by session identifier
        tags: Filter by tags (entry must have all specified tags)
        date_range: Filter by creation date range
        privacy_level: Filter by privacy classification
        min_importance: Minimum importance score (0.0-1.0)
        max_importance: Maximum importance score (0.0-1.0)
        older_than_days: Filter entries older than N days
        custom: Additional custom metadata filters

    Example:
        >>> filter = Filter(
        ...     user_id="user123",
        ...     tags=["preferences", "movies"],
        ...     min_importance=0.5,
        ...     privacy_level="public"
        ... )
    """

    # Identity filters
    user_id: str | None = Field(None, description="Filter by user identifier")
    session_id: str | None = Field(None, description="Filter by session identifier")

    # Tag filters
    tags: list[str] = Field(
        default_factory=list, description="Filter by tags (AND - must have all)"
    )

    # Temporal filters
    date_range: DateRange | None = Field(None, description="Filter by date range")
    older_than_days: int | None = Field(None, ge=0, description="Filter entries older than N days")

    # Classification filters
    privacy_level: PrivacyLiteral | None = Field(None, description="Filter by privacy level")

    # Importance filters
    min_importance: float | None = Field(
        None, ge=0.0, le=1.0, description="Minimum importance score"
    )
    max_importance: float | None = Field(
        None, ge=0.0, le=1.0, description="Maximum importance score"
    )

    # Custom metadata filters
    custom: dict[str, str] = Field(
        default_factory=dict, description="Custom metadata key-value filters"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "tags": ["preferences"],
                "min_importance": 0.5,
                "privacy_level": "public",
                "older_than_days": 30,
            }
        }
    )

    @field_validator("max_importance")
    @classmethod
    def validate_importance_range(cls, v: float | None, info) -> float | None:
        """Ensure max_importance is greater than min_importance if both set."""
        if v is not None and info.data.get("min_importance") is not None:
            if v < info.data["min_importance"]:
                raise ValueError("max_importance must be >= min_importance")
        return v

    def matches(self, entry: MemoryEntry) -> bool:
        """Check if a MemoryEntry matches this filter.

        Args:
            entry: The memory entry to check

        Returns:
            True if the entry matches all filter criteria
        """

        # User ID filter
        if self.user_id and entry.metadata.user_id != self.user_id:
            return False

        # Session ID filter
        if self.session_id and entry.metadata.session_id != self.session_id:
            return False

        # Tags filter (must have all specified tags)
        if self.tags and not all(tag in entry.metadata.tags for tag in self.tags):
            return False

        # Privacy level filter
        if self.privacy_level and entry.metadata.privacy_level != self.privacy_level:
            return False

        # Importance range filter
        if self.min_importance is not None and entry.metadata.importance < self.min_importance:
            return False
        if self.max_importance is not None and entry.metadata.importance > self.max_importance:
            return False

        # Date range filter
        if self.date_range:
            if self.date_range.start and entry.metadata.created_at < self.date_range.start:
                return False
            if self.date_range.end and entry.metadata.created_at > self.date_range.end:
                return False

        # Older than days filter
        if self.older_than_days is not None:
            age_days = (datetime.now(timezone.utc) - entry.metadata.created_at).days
            if age_days < self.older_than_days:
                return False

        # Custom metadata filters
        for key, value in self.custom.items():
            if not hasattr(entry.metadata, key) or getattr(entry.metadata, key) != value:
                return False

        return True
