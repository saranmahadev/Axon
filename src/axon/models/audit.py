"""Audit trail data models for operation tracking and compliance.

This module provides structured audit logging capabilities for tracking all
operations performed on the memory system, including stores, recalls, deletions,
and compactions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    """Types of operations that can be audited."""

    STORE = "store"
    RECALL = "recall"
    FORGET = "forget"
    COMPACT = "compact"
    EXPORT = "export"
    BULK_STORE = "bulk_store"
    REINDEX = "reindex"


class EventStatus(str, Enum):
    """Status of an audited operation."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditEvent(BaseModel):
    """Represents a single auditable event in the memory system.

    Attributes:
        event_id: Unique identifier for this audit event
        timestamp: ISO 8601 timestamp when the event occurred
        operation: Type of operation performed
        user_id: Optional identifier for the user who triggered the operation
        session_id: Optional identifier for the session context
        entry_ids: List of memory entry IDs affected by this operation
        metadata: Operation-specific metadata (e.g., query parameters, filters)
        status: Outcome of the operation
        error_message: Optional error details if status is FAILURE
        duration_ms: Optional duration of the operation in milliseconds
    """

    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation: OperationType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    entry_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: EventStatus = EventStatus.SUCCESS
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None

    # Pydantic v2 handles datetime and UUID serialization automatically
    # Custom serialization is handled in to_dict() method below
    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary with proper serialization.

        Returns:
            Dictionary representation of the audit event
        """
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "entry_ids": self.entry_ids,
            "metadata": self.metadata,
            "status": self.status.value,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }
