"""
MemorySystem: Central interface for intelligent memory management.

This module provides the main user-facing API for storing and retrieving
memories across multiple tiers with automatic tier selection, promotion/
demotion, and observability.

The MemorySystem coordinates Router, PolicyEngine, ScoringEngine, and
AdapterRegistry to provide seamless memory operations.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from axon.core.adapter_registry import AdapterRegistry
from axon.core.audit import AuditLogger
from axon.core.config import MemoryConfig
from axon.core.policy_engine import PolicyEngine
from axon.core.privacy import PIIDetector
from axon.core.router import Router
from axon.core.scoring import ScoringEngine
from axon.core.transaction import IsolationLevel, TransactionCoordinator
from axon.models.audit import EventStatus, OperationType
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter

logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """
    Trace event for operation tracking and debugging.

    Captures key information about memory operations for observability,
    debugging, and performance monitoring.

    Attributes:
        timestamp: When the operation occurred
        operation: Type of operation ("store", "recall", "forget", etc.)
        duration_ms: How long the operation took in milliseconds
        entry_id: Memory entry ID (for store/forget operations)
        query: Search query (for recall operations)
        tier: Target tier (if specified)
        result_count: Number of results (for recall operations)
        success: Whether the operation succeeded
        error: Error message if operation failed
    """

    timestamp: datetime
    operation: str
    duration_ms: float
    entry_id: str | None = None
    query: str | None = None
    tier: str | None = None
    result_count: int | None = None
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MemorySystem:
    """
    Central interface for memory storage and retrieval.

    MemorySystem provides a high-level API for managing memories across
    multiple storage tiers. It automatically handles tier selection,
    promotion/demotion, and provides observability through tracing.

    Key features:
    - Automatic tier selection based on importance
    - Multi-tier search with intelligent result merging
    - Access pattern tracking and automatic promotion/demotion
    - Input validation and error handling
    - Operation tracing for debugging and monitoring

    Example:
        ```python
        config = MemoryConfig(...)
        system = MemorySystem(config)

        # Store a memory
        entry_id = await system.store(
            "User prefers dark mode",
            importance=0.8
        )

        # Recall memories
        results = await system.recall("user preferences", k=5)
        ```

    Attributes:
        config: Memory system configuration
        router: Router for tier management
        registry: Adapter registry for storage backends
        policy_engine: Policy engine for promotion/demotion decisions
        scoring_engine: Scoring engine for importance calculation
    """

    def __init__(
        self,
        config: MemoryConfig,
        router: Router | None = None,
        registry: AdapterRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        scoring_engine: ScoringEngine | None = None,
        embedder: Any | None = None,
        audit_logger: Optional[AuditLogger] = None,
        pii_detector: Optional[PIIDetector] = None,
        enable_pii_detection: bool = True,
    ):
        """
        Initialize MemorySystem with configuration and optional components.

        If components are not provided, they will be created with default
        configurations. This allows for both simple initialization and
        advanced customization.

        Args:
            config: Memory system configuration with tier definitions
            router: Optional pre-configured Router instance
            registry: Optional pre-configured AdapterRegistry instance
            policy_engine: Optional pre-configured PolicyEngine instance
            scoring_engine: Optional pre-configured ScoringEngine instance
            embedder: Optional Embedder instance for generating embeddings (required for vector adapters)
            audit_logger: Optional AuditLogger instance for audit trail tracking
            pii_detector: Optional PIIDetector instance for privacy detection
            enable_pii_detection: Whether to enable automatic PII detection (default: True)

        Raises:
            ValueError: If config is invalid or missing required tiers
        """
        if not config:
            raise ValueError("config is required")

        # At least persistent tier must be configured
        if not config.persistent:
            raise ValueError("config must define at least a persistent tier")

        self.config = config
        self.embedder = embedder
        self.audit_logger = audit_logger
        self.enable_pii_detection = enable_pii_detection
        self.pii_detector = pii_detector or (PIIDetector() if enable_pii_detection else None)

        # Initialize or use provided components
        self.registry = registry or AdapterRegistry()
        self.scoring_engine = scoring_engine or ScoringEngine()

        # Register adapters from config if registry was created new
        if registry is None:
            self._register_adapters_from_config()

        # Build tiers dict from config
        tiers_dict = {}
        if config.ephemeral:
            tiers_dict["ephemeral"] = config.ephemeral
        if config.session:
            tiers_dict["session"] = config.session
        tiers_dict["persistent"] = config.persistent

        # Initialize policy engine with tier policies
        if policy_engine is None:
            self.policy_engine = PolicyEngine(
                registry=self.registry, scoring_engine=self.scoring_engine, tier_policies=tiers_dict
            )
        else:
            self.policy_engine = policy_engine

        # Initialize router
        if router is None:
            self.router = Router(
                config=config,
                registry=self.registry,
                policy_engine=self.policy_engine,
                embedder=self.embedder,
            )
        else:
            self.router = router

        # Tracing
        self._trace_events: list[TraceEvent] = []
        self._enable_tracing = True

        # Transaction coordinator
        self._transaction_coordinator: TransactionCoordinator | None = None

    def _register_adapters_from_config(self):
        """Register adapters from configuration."""
        # Build tiers dict from config
        tiers = {}
        if self.config.ephemeral:
            tiers["ephemeral"] = self.config.ephemeral
        if self.config.session:
            tiers["session"] = self.config.session
        tiers["persistent"] = self.config.persistent

        for tier_name, policy in tiers.items():
            # Register adapter with config
            # The registry will handle lazy initialization
            self.registry.register(
                tier=tier_name, adapter_type=policy.adapter_type, adapter_config=policy
            )

    async def store(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
        tier: str | None = None,
    ) -> str:
        """
        Store a memory with automatic tier selection.

        Creates a new memory entry and stores it in the appropriate tier
        based on importance or explicit tier specification. The entry is
        automatically assigned a unique ID and timestamped.

        Args:
            content: Text content to store (required, non-empty)
            metadata: Additional key-value metadata (optional)
            importance: Importance score 0.0-1.0 (optional, default: 0.5)
            tags: List of tags for categorization (optional)
            tier: Explicit tier override (optional, bypasses auto-selection)

        Returns:
            str: Unique entry ID (UUID format)

        Raises:
            ValueError: If content is empty, importance out of range, or tier invalid
            RuntimeError: If storage operation fails

        Example:
            ```python
            # Store with automatic tier selection
            id1 = await system.store("User likes pizza", importance=0.8)

            # Store with metadata and tags
            id2 = await system.store(
                "API key: abc123",
                importance=0.9,
                metadata={"service": "openai"},
                tags=["credentials", "api"]
            )

            # Store with explicit tier
            id3 = await system.store(
                "Temporary cache data",
                tier="ephemeral"
            )
            ```
        """
        start_time = datetime.now()
        entry_id = None

        try:
            # Validate inputs
            if not content or not content.strip():
                raise ValueError("content cannot be empty")

            if importance is not None:
                if not 0.0 <= importance <= 1.0:
                    raise ValueError(f"importance must be between 0.0 and 1.0, got {importance}")
            else:
                importance = 0.5  # Default importance

            if tier is not None:
                if tier not in self.config.tiers:
                    valid_tiers = list(self.config.tiers.keys())
                    raise ValueError(f"Invalid tier '{tier}'. Valid tiers: {valid_tiers}")

            # Generate unique ID
            entry_id = str(uuid.uuid4())

            # Detect PII if enabled
            pii_result = None
            if self.enable_pii_detection and self.pii_detector:
                pii_result = self.pii_detector.detect(content)

            # Build metadata
            entry_metadata = MemoryMetadata(
                importance=importance,
                tags=tags or [],
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
            )

            # Set privacy level from PII detection if not provided in metadata
            if pii_result and not metadata:
                entry_metadata.privacy_level = pii_result.recommended_privacy_level
            elif pii_result and metadata and "privacy_level" not in metadata:
                entry_metadata.privacy_level = pii_result.recommended_privacy_level

            # Merge user metadata if provided
            if metadata:
                # Apply custom metadata fields directly to entry_metadata
                for key, value in metadata.items():
                    setattr(entry_metadata, key, value)

            # Store PII detection results in metadata as a custom field
            if pii_result and pii_result.has_pii:
                entry_metadata.pii_detection = {
                    "detected_types": list(pii_result.detected_types),
                    "has_pii": pii_result.has_pii,
                    "details": pii_result.details,
                }

            # Create memory entry
            entry = MemoryEntry(id=entry_id, text=content, metadata=entry_metadata)

            # Generate embedding if embedder is available
            if self.embedder:
                embedding = await self.embedder.embed(content)
                entry.embedding = embedding

            # Store via router (handles tier selection if tier not specified)
            await self.router.route_store(entry, tier=tier)

            # Log trace event
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._log_trace(
                TraceEvent(
                    timestamp=start_time,
                    operation="store",
                    duration_ms=duration_ms,
                    entry_id=entry_id,
                    tier=tier,
                    success=True,
                    metadata={"importance": importance, "tags": tags or []},
                )
            )

            # Log audit event
            if self.audit_logger:
                audit_metadata = {
                    "importance": importance,
                    "tags": tags or [],
                    "tier": tier,
                    "has_embedding": entry.embedding is not None,
                    "privacy_level": (
                        entry.metadata.privacy_level.value if entry.metadata.privacy_level else None
                    ),
                }
                # Add PII detection info if available
                if pii_result and pii_result.has_pii:
                    audit_metadata["pii_detected"] = True
                    audit_metadata["pii_types"] = list(pii_result.detected_types)

                await self.audit_logger.log_event(
                    operation=OperationType.STORE,
                    user_id=entry.metadata.user_id,
                    session_id=entry.metadata.session_id,
                    entry_ids=[entry_id],
                    metadata=audit_metadata,
                    status=EventStatus.SUCCESS,
                    duration_ms=duration_ms,
                )

            return entry_id

        except Exception as e:
            # Log failed operation
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._log_trace(
                TraceEvent(
                    timestamp=start_time,
                    operation="store",
                    duration_ms=duration_ms,
                    entry_id=entry_id,
                    tier=tier,
                    success=False,
                    error=str(e),
                )
            )

            # Log audit event for failure
            if self.audit_logger:
                await self.audit_logger.log_event(
                    operation=OperationType.STORE,
                    entry_ids=[entry_id] if entry_id else [],
                    metadata={"tier": tier, "error_type": type(e).__name__},
                    status=EventStatus.FAILURE,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )

            raise

    async def recall(
        self,
        query: str,
        k: int = 5,
        filter: Filter | None = None,
        tiers: list[str] | None = None,
        min_importance: float | None = None,
    ) -> list[MemoryEntry]:
        """
        Search and retrieve memories across tiers.

        Searches for memories matching the query across specified tiers
        (or all tiers by default). Results are automatically deduplicated,
        sorted by relevance, and limited to k entries.

        Args:
            query: Search query text (required, non-empty)
            k: Maximum number of results to return (default: 5, must be > 0)
            filter: Optional filter for metadata/tags (optional)
            tiers: Specific tiers to search (optional, default: all tiers)
            min_importance: Minimum importance threshold (optional, 0.0-1.0)

        Returns:
            List[MemoryEntry]: Matching memory entries, sorted by relevance

        Raises:
            ValueError: If query is empty, k <= 0, or tiers invalid

        Example:
            ```python
            # Basic search
            results = await system.recall("user preferences")

            # Search with limit and importance filter
            results = await system.recall(
                "important settings",
                k=10,
                min_importance=0.7
            )

            # Search specific tiers with filter
            results = await system.recall(
                "api credentials",
                tiers=["persistent"],
                filter=Filter(tags=["credentials"])
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Validate inputs
            if query is None:
                raise ValueError("query cannot be None")

            # Allow empty query for "get all" semantics
            query = query.strip()

            if k <= 0:
                raise ValueError(f"k must be greater than 0, got {k}")

            if tiers is not None:
                # Validate all specified tiers exist
                invalid_tiers = [t for t in tiers if t not in self.config.tiers]
                if invalid_tiers:
                    valid_tiers = list(self.config.tiers.keys())
                    raise ValueError(f"Invalid tiers: {invalid_tiers}. Valid tiers: {valid_tiers}")

            if min_importance is not None:
                if not 0.0 <= min_importance <= 1.0:
                    raise ValueError(
                        f"min_importance must be between 0.0 and 1.0, got {min_importance}"
                    )

            # Search via router
            results = await self.router.route_recall(
                query_text=query, k=k, filter=filter, tiers=tiers
            )

            # Apply importance filter if specified
            if min_importance is not None:
                results = [
                    entry for entry in results if entry.metadata.importance >= min_importance
                ]

            # Log trace event
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._log_trace(
                TraceEvent(
                    timestamp=start_time,
                    operation="recall",
                    duration_ms=duration_ms,
                    query=query,
                    tier=tiers[0] if tiers and len(tiers) == 1 else None,
                    result_count=len(results),
                    success=True,
                    metadata={"k": k, "min_importance": min_importance, "tiers": tiers or "all"},
                )
            )

            # Log audit event
            if self.audit_logger:
                # Extract user_id and session_id from filter if available
                user_id = filter.user_id if filter else None
                session_id = filter.session_id if filter else None

                await self.audit_logger.log_event(
                    operation=OperationType.RECALL,
                    user_id=user_id,
                    session_id=session_id,
                    entry_ids=[entry.id for entry in results],
                    metadata={
                        "query": query,
                        "k": k,
                        "result_count": len(results),
                        "tiers": tiers or "all",
                        "min_importance": min_importance,
                        "has_filter": filter is not None,
                    },
                    status=EventStatus.SUCCESS,
                    duration_ms=duration_ms,
                )

            return results

        except Exception as e:
            # Log failed operation
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._log_trace(
                TraceEvent(
                    timestamp=start_time,
                    operation="recall",
                    duration_ms=duration_ms,
                    query=query,
                    success=False,
                    error=str(e),
                )
            )

            # Log audit event for failure
            if self.audit_logger:
                user_id = filter.user_id if filter else None
                session_id = filter.session_id if filter else None

                await self.audit_logger.log_event(
                    operation=OperationType.RECALL,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "query": query,
                        "k": k,
                        "tiers": tiers or "all",
                        "error_type": type(e).__name__,
                    },
                    status=EventStatus.FAILURE,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )

            raise

    def _log_trace(self, event: TraceEvent):
        """
        Log a trace event.

        Args:
            event: Trace event to log
        """
        if self._enable_tracing:
            self._trace_events.append(event)

    def get_trace_events(
        self, operation: str | None = None, limit: int | None = None
    ) -> list[TraceEvent]:
        """
        Get trace events for debugging and monitoring.

        Args:
            operation: Filter by operation type (optional)
            limit: Maximum number of events to return (optional)

        Returns:
            List of trace events, most recent first
        """
        events = self._trace_events.copy()
        events.reverse()  # Most recent first

        if operation:
            events = [e for e in events if e.operation == operation]

        if limit:
            events = events[:limit]

        return events

    def clear_trace_events(self):
        """Clear all trace events."""
        self._trace_events.clear()

    def enable_tracing(self, enabled: bool = True):
        """
        Enable or disable operation tracing.

        Args:
            enabled: Whether to enable tracing
        """
        self._enable_tracing = enabled

    def transaction(self, isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED):
        """
        Create a transactional context for atomic multi-tier operations.

        This enables Two-Phase Commit (2PC) for operations that span multiple
        tiers, ensuring either all changes succeed or all are rolled back.

        Args:
            isolation_level: Transaction isolation level

        Returns:
            Async context manager for the transaction

        Example:
            >>> async with system.transaction() as txn:
            ...     await system.store("entry 1", tier="ephemeral")
            ...     await system.store("entry 2", tier="persistent")
            ...     # Commits automatically on exit, rolls back on exception

        Raises:
            RuntimeError: If transaction fails to prepare or commit
        """
        # Lazy initialize transaction coordinator
        # Note: We'll collect adapters when the context manager is entered,
        # since get_adapter() is async
        if self._transaction_coordinator is None:
            self._transaction_coordinator = TransactionCoordinator(
                adapters={}, isolation_level=isolation_level  # Will be populated on first use
            )

        return self._transaction_coordinator.transaction()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with statistics including:
            - tier_stats: Per-tier operation counts
            - total_operations: Total store/recall/forget operations
            - trace_events: Number of trace events
        """
        tier_stats = self.router.get_tier_stats()

        total_stores = sum(stats.get("stores", 0) for stats in tier_stats.values())
        total_recalls = sum(stats.get("recalls", 0) for stats in tier_stats.values())
        total_forgets = sum(stats.get("forgets", 0) for stats in tier_stats.values())

        return {
            "tier_stats": tier_stats,
            "total_operations": {
                "stores": total_stores,
                "recalls": total_recalls,
                "forgets": total_forgets,
            },
            "trace_events": len(self._trace_events),
        }

    async def export(
        self,
        tier: str | None = None,
        filter: Filter | None = None,
        include_embeddings: bool = True,
    ) -> dict[str, Any]:
        """
        Export memories to a portable JSON-serializable format.

        Exports all memories or a filtered subset to a dictionary that can be
        serialized to JSON for backup, migration, or archival purposes.

        Args:
            tier: Export only from specific tier (None = all tiers)
            filter: Filter to apply when selecting memories to export
            include_embeddings: Whether to include embedding vectors (can be large)

        Returns:
            Dictionary containing:
            - version: Export format version
            - exported_at: ISO timestamp of export
            - config: Tier configuration summary
            - entries: List of memory entries
            - statistics: Export statistics

        Example:
            ```python
            # Export all memories
            data = await system.export()

            # Export specific tier
            data = await system.export(tier="persistent")

            # Export filtered memories
            data = await system.export(
                filter=Filter(tags=["important"], min_importance=0.8)
            )

            # Save to file
            import json
            with open("backup.json", "w") as f:
                json.dump(data, f, indent=2)
            ```

        Raises:
            ValueError: If tier is invalid
        """
        start_time = datetime.now()

        # Validate tier if specified
        if tier and tier not in self.config.tiers:
            valid_tiers = list(self.config.tiers.keys())
            raise ValueError(f"Invalid tier '{tier}'. Valid tiers: {valid_tiers}")

        # Determine tiers to export from
        tiers_to_export = [tier] if tier else list(self.config.tiers.keys())

        # Collect all entries
        all_entries = []
        stats_by_tier = {}

        for tier_name in tiers_to_export:
            adapter = await self.registry.get_adapter(tier_name)

            # Query all entries from this tier
            # Try query first, but if it returns nothing, fall back to listing all IDs
            entries = []
            try:
                entries = await adapter.query(
                    vector=[0.0] * 384,  # Dummy vector - InMemory falls back to text search
                    k=100000,  # Very large number to get all
                    filter=filter,
                )
            except Exception:
                pass  # Will fall through to list_ids approach

            # If query returned nothing (e.g., no embeddings), try listing all IDs
            if not entries:
                try:
                    entry_ids = adapter.list_ids()  # Note: list_ids is sync, not async
                    for entry_id in entry_ids:
                        try:
                            entry = await adapter.get(entry_id)
                            # Apply filter if provided
                            if filter is None or filter.matches(entry):
                                entries.append(entry)
                        except KeyError:
                            continue
                except Exception:
                    # If list_ids also fails, just use empty list
                    pass

            stats_by_tier[tier_name] = len(entries)

            # Add tier information to each entry
            for entry in entries:
                entry_dict = {
                    "id": entry.id,
                    "type": entry.type,
                    "text": entry.text,
                    "metadata": {
                        "user_id": entry.metadata.user_id,
                        "session_id": entry.metadata.session_id,
                        "source": entry.metadata.source,
                        "privacy_level": entry.metadata.privacy_level,
                        "created_at": entry.metadata.created_at.isoformat(),
                        "last_accessed_at": (
                            entry.metadata.last_accessed_at.isoformat()
                            if entry.metadata.last_accessed_at
                            else None
                        ),
                        "tags": entry.metadata.tags,
                        "importance": entry.metadata.importance,
                        "version": entry.metadata.version,
                    },
                    "tier": tier_name,
                }

                # Optionally include embedding
                if include_embeddings and entry.embedding:
                    entry_dict["embedding"] = entry.embedding

                # Include provenance if present
                if entry.metadata.provenance:
                    entry_dict["provenance"] = [
                        {
                            "action": p.action,
                            "by": p.by,
                            "timestamp": p.timestamp.isoformat(),
                            "metadata": p.metadata,
                        }
                        for p in entry.metadata.provenance
                    ]

                all_entries.append(entry_dict)

        # Build export data structure
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "config": {
                "tiers": list(self.config.tiers.keys()),
                "default_tier": self.config.default_tier,
            },
            "entries": all_entries,
            "statistics": {
                "total_entries": len(all_entries),
                "by_tier": stats_by_tier,
                "include_embeddings": include_embeddings,
            },
        }

        # Trace the operation
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        if self._enable_tracing:
            self._trace_events.append(
                TraceEvent(
                    timestamp=datetime.now(),
                    operation="EXPORT",
                    duration_ms=duration_ms,
                    tier=tier,
                    result_count=len(all_entries),
                    metadata={"filter": str(filter) if filter else None},
                )
            )

        # Log audit event
        if self.audit_logger:
            # Extract user_id and session_id from filter if available
            user_id = filter.user_id if filter else None
            session_id = filter.session_id if filter else None

            await self.audit_logger.log_event(
                operation=OperationType.EXPORT,
                user_id=user_id,
                session_id=session_id,
                entry_ids=[entry["id"] for entry in all_entries],
                metadata={
                    "tier": tier or "all",
                    "total_entries": len(all_entries),
                    "by_tier": stats_by_tier,
                    "include_embeddings": include_embeddings,
                    "has_filter": filter is not None,
                },
                status=EventStatus.SUCCESS,
                duration_ms=duration_ms,
            )

        return export_data

    async def import_from(
        self,
        data: dict[str, Any],
        overwrite: bool = False,
        tier_mapping: dict[str, str] | None = None,
    ) -> dict[str, int]:
        """
        Import memories from exported data.

        Imports memory entries from a previously exported backup. Handles
        tier mapping, conflict resolution, and validation.

        Args:
            data: Export data dictionary (from export() method)
            overwrite: If True, overwrite existing entries with same ID.
                      If False, skip entries that already exist.
            tier_mapping: Optional mapping of {old_tier: new_tier} to change
                         tier assignments during import. Example:
                         {"ephemeral": "session"} moves ephemeral to session.

        Returns:
            Dictionary with statistics:
            - imported: Number of entries successfully imported
            - skipped: Number of entries skipped (already exist, overwrite=False)
            - errors: Number of entries that failed to import
            - by_tier: Breakdown by target tier

        Example:
            ```python
            # Import from backup
            import json
            with open("backup.json") as f:
                data = json.load(f)

            stats = await system.import_from(data)
            print(f"Imported {stats['imported']} entries")

            # Import with tier remapping
            stats = await system.import_from(
                data,
                tier_mapping={"ephemeral": "session"}  # Move ephemeral→session
            )

            # Import with overwrite
            stats = await system.import_from(data, overwrite=True)
            ```

        Raises:
            ValueError: If data format is invalid or tiers don't exist
        """
        start_time = datetime.now()

        # Validate export data
        self._validate_export_data(data)

        # Track statistics
        imported = 0
        skipped = 0
        errors = 0
        by_tier = {}

        # Process each entry
        for entry_data in data.get("entries", []):
            try:
                # Determine target tier
                original_tier = entry_data.get("tier", self.config.default_tier)
                target_tier = original_tier

                # Apply tier mapping if provided
                if tier_mapping and original_tier in tier_mapping:
                    target_tier = tier_mapping[original_tier]

                # Validate target tier exists
                if target_tier not in self.config.tiers:
                    errors += 1
                    continue

                # Check if entry already exists
                adapter = await self.registry.get_adapter(target_tier)
                entry_id = entry_data["id"]

                exists = False
                try:
                    await adapter.get(entry_id)
                    exists = True
                except KeyError:
                    exists = False

                if exists and not overwrite:
                    skipped += 1
                    continue

                # Reconstruct MemoryEntry
                from axon.models.base import ProvenanceEvent

                metadata_dict = entry_data["metadata"]
                provenance_list = []

                if "provenance" in entry_data:
                    for p in entry_data["provenance"]:
                        provenance_list.append(
                            ProvenanceEvent(
                                action=p["action"],
                                by=p["by"],
                                timestamp=datetime.fromisoformat(p["timestamp"]),
                                metadata=p.get("metadata", {}),
                            )
                        )

                metadata = MemoryMetadata(
                    user_id=metadata_dict.get("user_id"),
                    session_id=metadata_dict.get("session_id"),
                    source=metadata_dict.get("source", "app"),
                    privacy_level=metadata_dict.get("privacy_level", "public"),
                    created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                    last_accessed_at=(
                        datetime.fromisoformat(metadata_dict["last_accessed_at"])
                        if metadata_dict.get("last_accessed_at")
                        else None
                    ),
                    tags=metadata_dict.get("tags", []),
                    importance=metadata_dict.get("importance", 0.5),
                    version=metadata_dict.get("version", ""),
                    provenance=provenance_list,
                )

                entry = MemoryEntry(
                    id=entry_id,
                    type=entry_data.get("type", "note"),
                    text=entry_data["text"],
                    embedding=entry_data.get("embedding"),
                    metadata=metadata,
                )

                # Store in target tier
                await adapter.save(entry)
                imported += 1

                # Update tier stats
                by_tier[target_tier] = by_tier.get(target_tier, 0) + 1

            except Exception:
                errors += 1
                continue

        # Build result statistics
        result = {"imported": imported, "skipped": skipped, "errors": errors, "by_tier": by_tier}

        # Trace the operation
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        if self._enable_tracing:
            self._trace_events.append(
                TraceEvent(
                    timestamp=datetime.now(),
                    operation="IMPORT",
                    duration_ms=duration_ms,
                    result_count=imported,
                    metadata={
                        "total_entries": len(data.get("entries", [])),
                        "overwrite": overwrite,
                        "tier_mapping": tier_mapping,
                    },
                )
            )

        return result

    async def sync(
        self,
        source_tier: str,
        target_tier: str,
        filter: Filter | None = None,
        delete_source: bool = False,
        conflict_resolution: str = "newer",
    ) -> dict[str, int]:
        """
        Synchronize memories between tiers.

        Copies or moves memories from one tier to another. Useful for:
        - Promoting important session data to persistent storage
        - Archiving old data to cold storage
        - Replicating data across adapters
        - Tier rebalancing

        Args:
            source_tier: Tier to copy/move from
            target_tier: Tier to copy/move to
            filter: Optional filter to select which memories to sync
            delete_source: If True, delete from source after copying (move operation)
            conflict_resolution: How to handle existing entries in target:
                - "newer": Keep newer entry (by last_accessed_at)
                - "source": Always use source entry
                - "target": Keep target entry (skip)
                - "merge": Merge metadata (not yet implemented)

        Returns:
            Dictionary with statistics:
            - synced: Number of entries successfully synced
            - skipped: Number of entries skipped (conflicts, errors)
            - deleted: Number of entries deleted from source
            - conflicts: Number of conflicts encountered

        Example:
            ```python
            # Promote important session memories to persistent
            stats = await system.sync(
                source_tier="session",
                target_tier="persistent",
                filter=Filter(min_importance=0.8)
            )

            # Archive old persistent data (move operation)
            stats = await system.sync(
                source_tier="persistent",
                target_tier="archive",
                filter=Filter(older_than_days=365),
                delete_source=True  # Delete from persistent after archiving
            )
            ```

        Raises:
            ValueError: If tiers are invalid or conflict_resolution is unknown
        """
        start_time = datetime.now()

        # Validate tiers
        if source_tier not in self.config.tiers:
            valid_tiers = list(self.config.tiers.keys())
            raise ValueError(f"Invalid source tier '{source_tier}'. Valid tiers: {valid_tiers}")

        if target_tier not in self.config.tiers:
            valid_tiers = list(self.config.tiers.keys())
            raise ValueError(f"Invalid target tier '{target_tier}'. Valid tiers: {valid_tiers}")

        if source_tier == target_tier:
            raise ValueError("Source and target tiers must be different")

        # Validate conflict resolution
        valid_resolutions = ["newer", "source", "target"]
        if conflict_resolution not in valid_resolutions:
            raise ValueError(
                f"Invalid conflict_resolution '{conflict_resolution}'. Valid: {valid_resolutions}"
            )

        # Get adapters
        source_adapter = await self.registry.get_adapter(source_tier)
        target_adapter = await self.registry.get_adapter(target_tier)

        # Track statistics
        synced = 0
        skipped = 0
        deleted = 0
        conflicts = 0

        # Get entries from source
        try:
            # Try query first
            entries = await source_adapter.query(vector=[0.0] * 384, k=100000, filter=filter)
        except Exception:
            # Fall back to listing IDs
            entry_ids = await source_adapter.list_ids()
            entries = []
            for entry_id in entry_ids:
                try:
                    entry = await source_adapter.get(entry_id)
                    if filter is None or filter.matches(entry):
                        entries.append(entry)
                except KeyError:
                    continue

        # Process each entry
        to_delete = []
        for entry in entries:
            try:
                # Check if entry exists in target
                target_entry = None
                try:
                    target_entry = await target_adapter.get(entry.id)
                except KeyError:
                    pass

                should_sync = True

                if target_entry:
                    conflicts += 1

                    # Apply conflict resolution
                    if conflict_resolution == "target":
                        should_sync = False
                    elif conflict_resolution == "newer":
                        # Compare last_accessed_at or created_at
                        source_time = entry.metadata.last_accessed_at or entry.metadata.created_at
                        target_time = (
                            target_entry.metadata.last_accessed_at
                            or target_entry.metadata.created_at
                        )
                        should_sync = source_time > target_time
                    # "source" always syncs

                if should_sync:
                    # Copy to target
                    await target_adapter.save(entry)
                    synced += 1

                    # Mark for deletion if move operation
                    if delete_source:
                        to_delete.append(entry.id)
                else:
                    skipped += 1

            except Exception:
                skipped += 1
                continue

        # Delete from source if move operation
        if delete_source:
            for entry_id in to_delete:
                try:
                    await source_adapter.delete(entry_id)
                    deleted += 1
                except Exception:
                    pass

        # Build result
        result = {"synced": synced, "skipped": skipped, "deleted": deleted, "conflicts": conflicts}

        # Trace the operation
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        if self._enable_tracing:
            self._trace_events.append(
                TraceEvent(
                    timestamp=datetime.now(),
                    operation="SYNC",
                    duration_ms=duration_ms,
                    result_count=synced,
                    metadata={
                        "source_tier": source_tier,
                        "target_tier": target_tier,
                        "delete_source": delete_source,
                        "conflict_resolution": conflict_resolution,
                        "filter": str(filter) if filter else None,
                    },
                )
            )

        return result

    def _validate_export_data(self, data: dict[str, Any]):
        """
        Validate export data format.

        Args:
            data: Export data to validate

        Raises:
            ValueError: If data format is invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Export data must be a dictionary")

        if "version" not in data:
            raise ValueError("Export data missing 'version' field")

        if "entries" not in data:
            raise ValueError("Export data missing 'entries' field")

        if not isinstance(data["entries"], list):
            raise ValueError("Export data 'entries' must be a list")

        # Validate each entry has required fields
        for i, entry in enumerate(data["entries"]):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {i} is not a dictionary")

            required_fields = ["id", "text", "metadata"]
            for field_name in required_fields:
                if field_name not in entry:
                    raise ValueError(f"Entry {i} missing required field '{field_name}'")

    async def compact(
        self,
        tier: str | None = None,
        strategy: str | Any = "count",
        threshold: int | None = None,
        dry_run: bool = False,
        summarizer: Any | None = None,
        embedder: Any | None = None,
    ) -> dict[str, Any]:
        """
        Compact memories in a tier by summarizing groups of entries.

        Compaction reduces the number of entries in a tier by grouping
        similar or related entries and replacing them with LLM-generated
        summaries. This helps manage storage costs and query performance.

        The compaction process:
        1. Check if tier needs compaction (via threshold)
        2. Select entries to compact using strategy
        3. Group entries into batches using strategy
        4. Summarize each group using an LLM
        5. Replace original entries with summary entries
        6. Update provenance to track what was summarized

        Args:
            tier: Tier to compact (None = check all tiers and compact as needed)
            strategy: Compaction strategy to use. Can be:
                - String: "count", "semantic", "importance", "time", or "hybrid"
                - CompactionStrategy instance for custom strategies
                Strategy behaviors:
                - "count": Legacy count-based compaction
                - "semantic": Group by embedding similarity
                - "importance": Compact low-importance entries first
                - "time": Compact old entries first
            threshold: Entry count threshold override (None = use policy default)
            dry_run: If True, return what would be compacted without doing it
            summarizer: Summarizer instance to use (None = create default LLMSummarizer)
            embedder: Embedder instance for generating summary embeddings (optional)

        Returns:
            Dictionary with compaction results:
            {
                "tier": "persistent",
                "entries_before": 15000,
                "entries_after": 1500,
                "summaries_created": 135,
                "groups_compacted": 135,
                "reduction_ratio": 0.9,  # 90% reduction
                "dry_run": false,
                "execution_time": 45.2,
                "strategy": "count"
            }

        Raises:
            ValueError: If tier is invalid
            ValueError: If strategy is not supported
            RuntimeError: If compaction fails

        Example:
            >>> # Compact persistent tier when over 10,000 entries
            >>> result = await memory_system.compact(
            ...     tier="persistent",
            ...     strategy="count",
            ...     threshold=10000
            ... )
            >>> print(f"Reduced from {result['entries_before']} to {result['entries_after']}")
            >>> print(f"Created {result['summaries_created']} summaries")
            >>> print(f"Reduction: {result['reduction_ratio']*100:.1f}%")

            >>> # Semantic compaction with similarity clustering
            >>> result = await memory_system.compact(
            ...     tier="persistent",
            ...     strategy="semantic"
            ... )

            >>> # Custom strategy instance
            >>> from axon.core.compaction_strategies import SemanticCompactionStrategy
            >>> custom_strategy = SemanticCompactionStrategy(similarity_threshold=0.9)
            >>> result = await memory_system.compact(
            ...     tier="persistent",
            ...     strategy=custom_strategy
            ... )

            >>> # Dry run to see what would happen
            >>> result = await memory_system.compact(tier="session", dry_run=True)
            >>> if result['entries_before'] > result['entries_after']:
            ...     print(f"Would compact {result['groups_compacted']} groups")

            >>> # Auto-compact all tiers that need it
            >>> result = await memory_system.compact()  # None = all tiers
        """
        from ..models.base import MemoryEntryType, ProvenanceEvent
        from .summarizer import LLMSummarizer
        from .compaction_strategies import CompactionStrategy, get_strategy

        start_time = datetime.now()

        # Use self.embedder if no embedder provided
        if embedder is None:
            embedder = self.embedder

        # Get strategy instance
        if isinstance(strategy, str):
            # Get strategy by name
            strategy_instance = get_strategy(strategy)
            strategy_name = strategy
        elif isinstance(strategy, CompactionStrategy):
            # Use custom strategy instance
            strategy_instance = strategy
            strategy_name = strategy_instance.name
        else:
            raise ValueError(
                f"Invalid strategy type: {type(strategy)}. "
                "Must be a string name or CompactionStrategy instance."
            )

        # Validate tier if specified
        if tier is not None and tier not in self.config.tiers:
            raise ValueError(
                f"Invalid tier: '{tier}'. Available tiers: {list(self.config.tiers.keys())}"
            )

        # Determine which tiers to compact
        tiers_to_compact = []
        if tier is not None:
            tiers_to_compact = [tier]
        else:
            # Check all tiers
            for tier_name in self.config.tiers.keys():
                adapter = await self.registry.get_adapter(tier_name)
                current_count = adapter.count()
                should_compact, details = self.policy_engine.should_compact(
                    tier_name, current_count
                )
                if should_compact:
                    tiers_to_compact.append(tier_name)

        # If no tiers need compaction
        if not tiers_to_compact:
            result = {
                "tier": tier or "all",
                "entries_before": 0,
                "entries_after": 0,
                "summaries_created": 0,
                "groups_compacted": 0,
                "reduction_ratio": 0.0,
                "dry_run": dry_run,
                "execution_time": 0.0,
                "strategy": strategy_name,
                "reason": "No tiers need compaction (below threshold)",
            }

            # Create trace event
            if self._enable_tracing:
                self._trace_events.append(
                    TraceEvent(
                        timestamp=datetime.now(),
                        operation="compact",
                        duration_ms=0.0,
                        tier=tier or "all",
                        result_count=0,
                        success=True,
                        metadata={
                            "strategy": strategy_name,
                            "tiers_checked": list(self.config.tiers.keys()),
                            "tiers_compacted": 0,
                            "dry_run": dry_run,
                        },
                    )
                )

            return result

        # Initialize summarizer if not provided (skip for dry run since we won't actually summarize)
        if summarizer is None and not dry_run:
            summarizer = LLMSummarizer()

        # Compact each tier
        total_before = 0
        total_after = 0
        total_summaries = 0
        total_groups = 0

        for tier_name in tiers_to_compact:
            # Get adapter and current entries
            adapter = await self.registry.get_adapter(tier_name)

            # Get compaction threshold
            tier_threshold = threshold
            if tier_threshold is None:
                policy = self.policy_engine._policies.get(tier_name)
                if (
                    policy
                    and hasattr(policy, "compaction_threshold")
                    and policy.compaction_threshold
                ):
                    tier_threshold = policy.compaction_threshold
                else:
                    continue  # Skip if no threshold

            # Get current count
            current_count = adapter.count()
            total_before += current_count

            # Check if compaction is needed
            if current_count < tier_threshold:
                total_after += current_count
                continue

            # Query all entries
            all_entries = await adapter.query(
                vector=[0.0] * 1536, k=current_count, filter=None  # Dummy vector
            )

            if not all_entries:
                total_after += current_count
                continue

            # Use strategy to select entries to compact
            entries_to_compact = strategy_instance.select_entries_to_compact(
                all_entries, threshold=tier_threshold
            )

            if not entries_to_compact:
                total_after += current_count
                continue

            # Determine entries to keep (those not selected for compaction)
            entries_to_compact_ids = {e.id for e in entries_to_compact}
            entries_to_keep = [e for e in all_entries if e.id not in entries_to_compact_ids]

            # Use strategy to group entries for summarization
            groups = strategy_instance.group_entries(entries_to_compact, batch_size=100)

            total_groups += len(groups)

            # If dry run, just calculate statistics
            if dry_run:
                total_after += len(entries_to_keep) + len(groups)
                total_summaries += len(groups)
                continue

            # Summarize each group
            summary_entries = []
            for group in groups:
                try:
                    # Create summary text
                    summary_text = await summarizer.summarize(
                        group, context=f"{tier_name} tier compaction"
                    )

                    # Calculate aggregate importance (weighted average)
                    total_importance = sum(e.metadata.importance for e in group)
                    avg_importance = total_importance / len(group)

                    # Create provenance event
                    provenance = ProvenanceEvent(
                        timestamp=datetime.now(),
                        action="compact",
                        by="memory_system",
                        metadata={
                            "strategy": strategy,
                            "tier": tier_name,
                            "summarized_count": str(len(group)),
                            "summarized_ids": ",".join([e.id for e in group]),
                            "original_importance_avg": str(avg_importance),
                        },
                    )

                    # Create summary entry
                    summary_entry = MemoryEntry(
                        id=str(uuid.uuid4()),
                        type=MemoryEntryType.EMBEDDING_SUMMARY,  # Correct field name
                        text=summary_text,
                        embedding=None,  # No embedding yet (will be generated below)
                        metadata=MemoryMetadata(
                            user_id=group[0].metadata.user_id,
                            session_id=group[0].metadata.session_id,
                            source="system",  # Compaction is a system operation
                            privacy_level=group[0].metadata.privacy_level,
                            created_at=group[0].metadata.created_at,  # Use oldest date
                            last_accessed_at=datetime.now(),
                            tags=list({tag for e in group for tag in e.metadata.tags}),
                            importance=avg_importance,
                            version="1.0",
                            provenance=[provenance],
                        ),
                    )

                    # Generate embedding for summary (if embedder provided)
                    if embedder:
                        summary_embedding = await embedder.embed(summary_text)
                        summary_entry.embedding = summary_embedding

                    summary_entries.append(summary_entry)
                    total_summaries += 1

                except Exception as e:
                    # Log error but continue with other groups
                    logger.error(f"Failed to summarize group in {tier_name}: {e}")
                    # Keep original entries instead
                    entries_to_keep.extend(group)

            # Delete old entries and save summaries
            if summary_entries:
                # Delete entries that were summarized
                for entry in entries_to_compact:
                    try:
                        await adapter.delete(entry.id)
                    except Exception as e:
                        logger.warning(f"Failed to delete entry {entry.id}: {e}")

                # Save summary entries
                for summary_entry in summary_entries:
                    try:
                        await adapter.save(summary_entry)
                    except Exception as e:
                        logger.error(f"Failed to save summary entry: {e}")

            # Update count
            new_count = adapter.count()
            total_after += new_count

        # Calculate statistics
        execution_time = (datetime.now() - start_time).total_seconds()
        reduction_ratio = 0.0
        if total_before > 0:
            reduction_ratio = (total_before - total_after) / total_before

        result = {
            "tier": tier or "multiple",
            "tiers_compacted": tiers_to_compact,
            "entries_before": total_before,
            "entries_after": total_after,
            "summaries_created": total_summaries,
            "groups_compacted": total_groups,
            "reduction_ratio": reduction_ratio,
            "dry_run": dry_run,
            "execution_time": execution_time,
            "strategy": strategy_name,
        }

        # Create trace event
        if self._enable_tracing:
            self._trace_events.append(
                TraceEvent(
                    timestamp=datetime.now(),
                    operation="compact",
                    duration_ms=execution_time * 1000,  # Convert to milliseconds
                    tier=tier or "multiple",
                    result_count=total_summaries,
                    success=True,
                    metadata={
                        "tiers_compacted": tiers_to_compact,
                        "strategy": strategy_name,
                        "threshold": threshold,
                        "dry_run": dry_run,
                        "summaries_created": total_summaries,
                        "groups_compacted": total_groups,
                    },
                )
            )

        # Log audit event
        if self.audit_logger:
            await self.audit_logger.log_event(
                operation=OperationType.COMPACT,
                metadata={
                    "tier": tier or "multiple",
                    "tiers_compacted": tiers_to_compact,
                    "strategy": strategy_name,
                    "threshold": threshold,
                    "entries_before": total_before,
                    "entries_after": total_after,
                    "summaries_created": total_summaries,
                    "groups_compacted": total_groups,
                    "reduction_ratio": reduction_ratio,
                    "dry_run": dry_run,
                },
                status=EventStatus.SUCCESS,
                duration_ms=execution_time * 1000,
            )

        return result

    async def get_provenance_chain(self, entry_id: str) -> list[MemoryEntry]:
        """
        Get the complete provenance chain for an entry, tracing back to source.

        Retrieves an entry and all its ancestor entries by following the
        provenance metadata. This shows the complete lineage from the original
        entry through all transformations (compactions, summarizations, etc.).

        Args:
            entry_id: ID of the entry to trace

        Returns:
            List of entries in chronological order (oldest first), including
            the requested entry and all ancestors

        Raises:
            KeyError: If entry_id not found in any tier

        Example:
            ```python
            # Get full lineage of a summarized entry
            chain = await system.get_provenance_chain("summary_id")
            for entry in chain:
                print(f"{entry.id}: {entry.type} - {entry.text[:50]}")
            ```
        """
        chain = []
        current_id = entry_id

        # Follow the chain backwards
        visited = set()  # Prevent infinite loops

        while current_id and current_id not in visited:
            visited.add(current_id)

            # Find the entry in any tier
            entry = None
            for tier_name in self.config.tiers.keys():
                adapter = await self.registry.get_adapter(tier_name)
                try:
                    entry = await adapter.get(current_id)
                    break
                except KeyError:
                    continue

            if not entry:
                # Entry not found - may have been deleted
                break

            chain.append(entry)

            # Look for source entry IDs in provenance
            if entry.metadata.provenance:
                # Get the last provenance event (most recent action)
                last_prov = entry.metadata.provenance[-1]

                # Extract source IDs from metadata
                if "summarized_ids" in last_prov.metadata:
                    # This is a summary - get the first source ID
                    source_ids = last_prov.metadata["summarized_ids"].split(",")
                    if source_ids:
                        current_id = source_ids[0].strip()
                    else:
                        break
                else:
                    # No more ancestors
                    break
            else:
                # No provenance - this is the source
                break

        # Return in chronological order (oldest first)
        return list(reversed(chain))

    async def find_derived_entries(self, entry_id: str) -> list[MemoryEntry]:
        """
        Find all entries derived from a source entry.

        Searches across all tiers for entries that have the given entry_id
        in their provenance chain (i.e., summaries or transformations of
        this entry).

        Args:
            entry_id: ID of the source entry

        Returns:
            List of entries that were derived from the source entry

        Example:
            ```python
            # Find all summaries that include a specific entry
            derived = await system.find_derived_entries("original_id")
            print(f"Found {len(derived)} derived entries")
            ```
        """
        derived = []

        # Search all tiers
        for tier_name in self.config.tiers.keys():
            adapter = await self.registry.get_adapter(tier_name)

            # Get all entries from this tier
            try:
                # Query with dummy vector to get all
                all_entries = await adapter.query(vector=[0.0] * 384, k=100000, filter=None)

                # Check each entry's provenance
                for entry in all_entries:
                    if entry.metadata.provenance:
                        for prov_event in entry.metadata.provenance:
                            # Check if entry_id is in the summarized IDs
                            if "summarized_ids" in prov_event.metadata:
                                source_ids = prov_event.metadata["summarized_ids"].split(",")
                                source_ids = [sid.strip() for sid in source_ids]

                                if entry_id in source_ids:
                                    derived.append(entry)
                                    break  # Don't add same entry twice

            except Exception:
                # If query fails, try listing IDs
                try:
                    entry_ids = await adapter.list_ids()
                    for eid in entry_ids:
                        try:
                            entry = await adapter.get(eid)
                            if entry.metadata.provenance:
                                for prov_event in entry.metadata.provenance:
                                    if "summarized_ids" in prov_event.metadata:
                                        source_ids = prov_event.metadata["summarized_ids"].split(
                                            ","
                                        )
                                        source_ids = [sid.strip() for sid in source_ids]

                                        if entry_id in source_ids:
                                            derived.append(entry)
                                            break
                        except KeyError:
                            continue
                except Exception:
                    # Skip this tier
                    continue

        return derived

    async def export_audit_log(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation: Optional[OperationType] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Export audit events for compliance or analysis.

        Args:
            start_time: Filter events after this timestamp
            end_time: Filter events before this timestamp
            operation: Filter by operation type
            user_id: Filter by user ID
            session_id: Filter by session ID

        Returns:
            List of audit events as dictionaries

        Raises:
            RuntimeError: If no audit logger is configured

        Example:
            ```python
            # Export all audit events
            events = await system.export_audit_log()

            # Export events for a specific user
            events = await system.export_audit_log(user_id="user_123")

            # Export recent events
            from datetime import datetime, timedelta
            events = await system.export_audit_log(
                start_time=datetime.now() - timedelta(days=7)
            )
            ```
        """
        if not self.audit_logger:
            raise RuntimeError(
                "No audit logger configured. Initialize MemorySystem with audit_logger parameter."
            )

        events = await self.audit_logger.get_events(
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
        )

        return [event.to_dict() for event in events]

    async def close(self):
        """
        Close all adapters and clean up resources.

        Should be called when the MemorySystem is no longer needed.
        """
        await self.registry.close_all()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        tier_names = list(self.config.tiers.keys())
        return f"MemorySystem(tiers={tier_names}, tracing={self._enable_tracing})"
