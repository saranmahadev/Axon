"""MemoryEntry - The canonical data structure for all memory in Axon.

This module defines the core MemoryEntry model that represents a single unit
of memory with optional embeddings, metadata, and provenance tracking.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import (
    MemoryTypeLiteral,
    PrivacyLiteral,
    ProvenanceEvent,
    SourceLiteral,
)


class MemoryMetadata(BaseModel):
    """Metadata associated with a memory entry.

    This includes both reserved fields used by the SDK and support for
    arbitrary custom key-value pairs.

    Reserved fields:
        user_id: User identifier for multi-tenant scenarios
        session_id: Session identifier for session-scoped memory
        source: Origin of the memory (app, system, agent)
        created_at: When the memory was created
        last_accessed_at: When the memory was last retrieved
        tags: Categorization tags for filtering
        importance: Importance score (0.0 to 1.0)
        privacy_level: Privacy classification
        version: Embedder model version/signature
        provenance: Audit trail of actions
    """

    # Core identifiers
    user_id: str | None = Field(None, description="User identifier for multi-tenant scenarios")
    session_id: str | None = Field(None, description="Session identifier")

    # Source and classification
    source: SourceLiteral = Field("app", description="Origin: app, system, or agent")
    privacy_level: PrivacyLiteral = Field("public", description="Privacy classification")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (ISO8601)",
    )
    last_accessed_at: datetime | None = Field(None, description="Last access timestamp (ISO8601)")

    # Categorization and scoring
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score (0.0-1.0)")

    # Versioning and audit
    version: str = Field(default="", description="Embedder signature (model name + version)")
    provenance: list[ProvenanceEvent] = Field(
        default_factory=list, description="Audit trail of actions"
    )

    # Allow additional custom metadata
    model_config = ConfigDict(extra="allow")  # Allow arbitrary additional fields

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v: float) -> float:
        """Ensure importance is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Importance must be between 0.0 and 1.0, got {v}")
        return v


class MemoryEntry(BaseModel):
    """The canonical data structure for a memory entry in Axon.

    Represents a single unit of memory that can be stored across different tiers.
    Supports optional vector embeddings for semantic search and rich metadata.

    Attributes:
        id: Unique identifier (UUID)
        type: Classification of memory type
        text: Raw text content or serialized data
        embedding: Optional vector embedding for semantic search
        metadata: Rich metadata including provenance and custom fields

    Example:
        >>> entry = MemoryEntry(
        ...     text="User prefers science fiction movies",
        ...     type=MemoryEntryType.NOTE,
        ...     metadata=MemoryMetadata(
        ...         user_id="user123",
        ...         tags=["preferences", "movies"],
        ...         importance=0.8
        ...     )
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier (UUID)")

    type: MemoryTypeLiteral = Field(default="note", description="Type of memory entry")

    text: str = Field(..., min_length=1, description="Raw text content or serialized data")

    embedding: list[float] | None = Field(
        None, description="Vector embedding (null for ephemeral text-only entries)"
    )

    metadata: MemoryMetadata = Field(
        default_factory=MemoryMetadata,
        description="Rich metadata including identifiers, tags, and provenance",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "conversation_turn",
                "text": "User: I really enjoy science fiction movies, especially ones with time travel.",
                "embedding": None,
                "metadata": {
                    "user_id": "user123",
                    "session_id": "session456",
                    "source": "app",
                    "tags": ["conversation", "preferences"],
                    "importance": 0.7,
                    "privacy_level": "public",
                    "created_at": "2025-11-04T12:00:00Z",
                },
            }
        }
    )

    def add_provenance(self, action: str, by: str, **metadata: str) -> None:
        """Add a provenance event to the audit trail.

        Args:
            action: Action performed (e.g., 'store', 'recall', 'compact')
            by: Module or component performing the action
            **metadata: Additional context as key-value pairs
        """
        event = ProvenanceEvent(action=action, by=by, metadata=metadata)
        self.metadata.provenance.append(event)

    def update_accessed(self) -> None:
        """Update the last_accessed_at timestamp to now."""
        self.metadata.last_accessed_at = datetime.now(timezone.utc)

    @property
    def has_embedding(self) -> bool:
        """Check if this entry has a vector embedding."""
        return self.embedding is not None and len(self.embedding) > 0

    @property
    def embedding_dim(self) -> int | None:
        """Get the dimensionality of the embedding vector."""
        return len(self.embedding) if self.has_embedding else None
