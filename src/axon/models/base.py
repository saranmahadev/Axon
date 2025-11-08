"""Base types, enums, and schemas for Axon Memory SDK.

This module defines the fundamental types used throughout the SDK including
enums for memory tiers, privacy levels, and provenance tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryTier(str, Enum):
    """Memory storage tiers with different persistence and access characteristics.

    Attributes:
        EPHEMERAL: Short-lived in-memory storage (minutes)
        SESSION: Session-scoped storage (hours to days)
        PERSISTENT: Long-term vector-indexed storage (indefinite)
        ARCHIVE: Cold storage for infrequent access (years)
    """

    EPHEMERAL = "ephemeral"
    SESSION = "session"
    PERSISTENT = "persistent"
    ARCHIVE = "archive"


class PrivacyLevel(str, Enum):
    """Privacy classification levels for memory entries.

    Levels ordered from least to most restrictive:
    PUBLIC < INTERNAL < SENSITIVE < RESTRICTED

    Attributes:
        PUBLIC: Non-sensitive information, shareable publicly
        INTERNAL: Internal use only (emails, phone numbers, IP addresses)
        SENSITIVE: Requires careful handling, limited sharing
        RESTRICTED: Highly confidential (SSN, credit cards), maximum security
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class SourceType(str, Enum):
    """Origin source of a memory entry.

    Attributes:
        APP: Created by the application
        SYSTEM: Created by system/automation
        AGENT: Created by an AI agent
    """

    APP = "app"
    SYSTEM = "system"
    AGENT = "agent"


class MemoryEntryType(str, Enum):
    """Type classification for memory entries.

    Attributes:
        NOTE: Simple text note
        EVENT: Time-bound event or action
        CONVERSATION_TURN: Chat message or dialogue turn
        PROFILE: User profile or preference data
        EMBEDDING_SUMMARY: Summarized/compacted embedding
    """

    NOTE = "note"
    EVENT = "event"
    CONVERSATION_TURN = "conversation_turn"
    PROFILE = "profile"
    EMBEDDING_SUMMARY = "embedding_summary"


class ProvenanceEvent(BaseModel):
    """Record of an action taken on a memory entry for audit trail.

    Attributes:
        action: Type of action (store, recall, compact, forget, etc.)
        by: Module or component that performed the action
        timestamp: When the action occurred (ISO8601)
        metadata: Optional additional context about the action
    """

    action: str = Field(..., description="Action performed (store, recall, compact, forget)")
    by: str = Field(..., description="Module or component that performed the action")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="When action occurred"
    )
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "store",
                "by": "memory_system",
                "timestamp": "2025-11-04T12:34:56Z",
                "metadata": {"tier": "persistent"},
            }
        }
    )


# Type aliases for cleaner code
SourceLiteral = Literal["app", "system", "agent"]
PrivacyLiteral = Literal["public", "internal", "sensitive", "restricted"]
MemoryTypeLiteral = Literal["note", "event", "conversation_turn", "profile", "embedding_summary"]
