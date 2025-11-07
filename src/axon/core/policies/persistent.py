"""
Persistent Policy for long-term memories.

This module provides the PersistentPolicy class for configuring
the persistent tier, which stores memories indefinitely with
optional compaction and archival.
"""

from typing import Literal

from pydantic import Field, field_validator

from ..policy import Policy


class PersistentPolicy(Policy):
    """
    Policy for persistent (long-term) memories.

    The persistent tier stores memories indefinitely, typically using
    vector databases for semantic search. It supports compaction to
    manage storage costs and optional archival for cold storage.

    Constraints:
        - Must use vector-capable adapters (Chroma, Qdrant, Pinecone)
        - TTL is usually None (no expiration) or very long
        - Compaction threshold should be reasonable (≥100 entries)
        - Vector search is always enabled

    Use Cases:
        - Long-term knowledge base
        - User history and preferences
        - Learned facts and insights
        - Important conversations
        - Permanent records

    Attributes:
        compaction_strategy: How to compact when threshold is reached
        archive_adapter: Optional adapter for archived/cold memories (e.g., S3)

    Example:
        >>> policy = PersistentPolicy(
        ...     adapter_type="pinecone",
        ...     compaction_threshold=10000,
        ...     compaction_strategy="importance"
        ... )
    """

    tier_name: Literal["persistent"] = Field(
        default="persistent", description="Tier name is always 'persistent'"
    )

    adapter_type: Literal["chroma", "qdrant", "pinecone", "memory"] = Field(
        "chroma", description="Vector database for persistent storage"
    )

    ttl_seconds: int | None = Field(
        None, description="Usually None (no expiration) or very long (days/months)"
    )

    compaction_threshold: int | None = Field(
        10000, description="Compact after N entries (default: 10,000)", gt=0
    )

    compaction_strategy: Literal["count", "semantic", "importance", "time"] = Field(
        "count", description="Strategy for compacting memories"
    )

    enable_vector_search: Literal[True] = Field(
        default=True, description="Always enabled for persistent tier"
    )

    archive_adapter: str | None = Field(
        None, description="Adapter for archived memories (e.g., 's3', 'gcs')"
    )

    @field_validator("compaction_threshold")
    @classmethod
    def validate_compaction_threshold(cls, v: int | None) -> int | None:
        """
        Validate that compaction threshold is reasonable.

        Should be high enough to avoid frequent compaction but
        low enough to prevent unbounded growth.
        """
        if v is not None and v < 100:
            raise ValueError(
                "Compaction threshold should be at least 100 entries "
                "to avoid excessive compaction overhead"
            )
        return v

    @field_validator("adapter_type")
    @classmethod
    def validate_persistent_adapter(cls, v: str) -> str:
        """
        Validate that adapter supports vector search.

        Persistent tier requires vector capabilities for semantic recall.
        Memory adapter is allowed for testing only.
        """
        if v not in ["chroma", "qdrant", "pinecone", "memory"]:
            raise ValueError(f"Persistent tier requires vector-capable adapter, got '{v}'")
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def validate_persistent_ttl(cls, v: int | None) -> int | None:
        """
        Validate that TTL is appropriate for persistent tier.

        Persistent memories usually don't expire, but if TTL is set,
        it should be long (at least 1 day).
        """
        if v is not None and v < 86400:  # 1 day
            raise ValueError(
                "Persistent tier TTL should be at least 1 day (86400s) " "or None for no expiration"
            )
        return v
