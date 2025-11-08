"""Audit logging system for tracking memory operations.

This module provides audit trail functionality for compliance, debugging,
and observability. All operations on the memory system can be logged with
structured metadata.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.audit import AuditEvent, EventStatus, OperationType


class AuditLogger:
    """Thread-safe audit logger for tracking memory system operations.

    The audit logger captures all significant operations (store, recall, forget,
    compact, export) with structured metadata for compliance and observability.

    Features:
    - Structured event logging with timestamps
    - Async-safe operation
    - In-memory storage with optional file export
    - Automatic rotation when max events reached
    - Query/filter capabilities

    Example:
        >>> audit_logger = AuditLogger(max_events=10000)
        >>> await audit_logger.log_event(
        ...     operation=OperationType.STORE,
        ...     user_id="user_123",
        ...     entry_ids=["entry_1"],
        ...     status=EventStatus.SUCCESS
        ... )
    """

    def __init__(
        self,
        max_events: int = 10000,
        auto_export_path: Optional[Path] = None,
        enable_rotation: bool = True,
    ):
        """Initialize the audit logger.

        Args:
            max_events: Maximum number of events to keep in memory before rotation
            auto_export_path: Optional path to auto-export events on rotation
            enable_rotation: Whether to enable automatic rotation when max_events reached
        """
        self._events: List[AuditEvent] = []
        self._max_events = max_events
        self._auto_export_path = auto_export_path
        self._enable_rotation = enable_rotation
        self._lock = asyncio.Lock()
        self._total_events_logged = 0

    async def log_event(
        self,
        operation: OperationType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        entry_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: EventStatus = EventStatus.SUCCESS,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> AuditEvent:
        """Log an audit event for a memory operation.

        Args:
            operation: Type of operation being logged
            user_id: Optional user identifier
            session_id: Optional session identifier
            entry_ids: List of memory entry IDs affected
            metadata: Operation-specific metadata (query params, filters, etc.)
            status: Outcome of the operation
            error_message: Error details if status is FAILURE
            duration_ms: Duration of the operation in milliseconds

        Returns:
            The created AuditEvent instance
        """
        event = AuditEvent(
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            entry_ids=entry_ids or [],
            metadata=metadata or {},
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        async with self._lock:
            self._events.append(event)
            self._total_events_logged += 1

            # Check if rotation is needed
            if self._enable_rotation and len(self._events) >= self._max_events:
                await self._rotate_events()

        return event

    async def _rotate_events(self) -> None:
        """Rotate events when max_events is reached.

        If auto_export_path is set, exports events to file before clearing.
        Otherwise, removes oldest half of events to make room.
        """
        if self._auto_export_path:
            # Export to file
            await self._export_to_file(self._auto_export_path)
            self._events.clear()
        else:
            # Keep newest half
            keep_count = self._max_events // 2
            self._events = self._events[-keep_count:]

    async def get_events(
        self,
        operation: Optional[OperationType] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[EventStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Query audit events with optional filters.

        Args:
            operation: Filter by operation type
            user_id: Filter by user ID
            session_id: Filter by session ID
            status: Filter by event status
            start_time: Filter events after this timestamp
            end_time: Filter events before this timestamp
            limit: Maximum number of events to return

        Returns:
            List of matching audit events (newest first)
        """
        async with self._lock:
            # Start with all events
            results = list(self._events)

            # Apply filters
            if operation is not None:
                results = [e for e in results if e.operation == operation]

            if user_id is not None:
                results = [e for e in results if e.user_id == user_id]

            if session_id is not None:
                results = [e for e in results if e.session_id == session_id]

            if status is not None:
                results = [e for e in results if e.status == status]

            if start_time is not None:
                results = [e for e in results if e.timestamp >= start_time]

            if end_time is not None:
                results = [e for e in results if e.timestamp <= end_time]

            # Sort by timestamp (newest first)
            results.sort(key=lambda e: e.timestamp, reverse=True)

            # Apply limit
            if limit is not None:
                results = results[:limit]

            return results

    async def export_to_json(
        self,
        file_path: Path,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Export audit events to JSON file.

        Args:
            file_path: Path to output JSON file
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Number of events exported
        """
        events = await self.get_events(start_time=start_time, end_time=end_time)
        await self._export_to_file(file_path, events)
        return len(events)

    async def _export_to_file(
        self, file_path: Path, events: Optional[List[AuditEvent]] = None
    ) -> None:
        """Internal method to export events to file.

        Args:
            file_path: Path to output file
            events: Events to export (defaults to all events)
        """
        if events is None:
            async with self._lock:
                events = list(self._events)

        # Convert to dict format
        events_dict = [event.to_dict() for event in events]

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(events_dict, f, indent=2, ensure_ascii=False)

    async def clear(self) -> None:
        """Clear all audit events from memory."""
        async with self._lock:
            self._events.clear()

    @property
    def event_count(self) -> int:
        """Get current number of events in memory."""
        return len(self._events)

    @property
    def total_events_logged(self) -> int:
        """Get total number of events logged since initialization."""
        return self._total_events_logged

    def get_stats(self) -> Dict[str, Any]:
        """Get audit logger statistics.

        Returns:
            Dictionary with statistics about logged events
        """
        return {
            "events_in_memory": len(self._events),
            "total_events_logged": self._total_events_logged,
            "max_events": self._max_events,
            "rotation_enabled": self._enable_rotation,
            "auto_export_enabled": self._auto_export_path is not None,
        }
