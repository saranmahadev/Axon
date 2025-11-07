"""
Base Policy class for memory tier configuration.

This module provides the foundational Policy class that defines
common configuration options for all memory tiers.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Policy(BaseModel):
    """
    Base policy configuration for a memory tier.

    A Policy defines how a specific tier of the memory system behaves,
    including which storage adapter to use, how long memories persist,
    capacity limits, and eviction strategies.

    Attributes:
        tier_name: Unique name for this tier (e.g., "ephemeral", "session")
        adapter_type: Type of storage adapter ("redis", "chroma", "qdrant", etc.)
        ttl_seconds: Time-to-live in seconds (None = no expiration)
        max_entries: Maximum number of entries before eviction (None = unlimited)
        compaction_threshold: Entry count that triggers compaction (None = disabled)
        eviction_strategy: Strategy for removing entries when at capacity
        enable_vector_search: Whether this tier supports vector similarity search

    Example:
        >>> policy = Policy(
        ...     tier_name="session",
        ...     adapter_type="redis",
        ...     ttl_seconds=600,
        ...     max_entries=1000,
        ...     eviction_strategy="ttl"
        ... )
    """

    tier_name: str = Field(
        ...,
        description="Name of the tier (e.g., 'ephemeral', 'session', 'persistent')",
        min_length=1,
        max_length=50,
    )

    adapter_type: Literal["redis", "chroma", "qdrant", "pinecone", "memory"] = Field(
        ..., description="Storage adapter to use for this tier"
    )

    ttl_seconds: int | None = Field(
        None, description="Time-to-live in seconds (None = no expiration)", ge=0
    )

    max_entries: int | None = Field(
        None, description="Maximum entries before eviction (None = unlimited)", gt=0
    )

    compaction_threshold: int | None = Field(
        None, description="Entry count that triggers compaction (None = disabled)", gt=0
    )

    eviction_strategy: Literal["ttl", "lru", "fifo", "importance"] = Field(
        "ttl", description="Strategy for removing entries when at capacity"
    )

    enable_vector_search: bool = Field(
        True, description="Whether this tier supports vector similarity search"
    )

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl_positive(cls, v: int | None) -> int | None:
        """Validate that TTL is non-negative if specified."""
        if v is not None and v < 0:
            raise ValueError("TTL must be non-negative or None")
        return v

    @field_validator("compaction_threshold")
    @classmethod
    def validate_compaction_reasonable(cls, v: int | None) -> int | None:
        """Validate that compaction threshold is reasonable if specified."""
        if v is not None and v < 10:
            raise ValueError("Compaction threshold should be at least 10 entries")
        return v

    def to_dict(self) -> dict[str, Any]:
        """
        Convert policy to dictionary.

        Returns:
            Dictionary representation of the policy
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Policy":
        """
        Create policy from dictionary.

        Args:
            data: Dictionary containing policy configuration

        Returns:
            Policy instance

        Raises:
            ValidationError: If data doesn't match policy schema
        """
        return cls(**data)

    def __str__(self) -> str:
        """String representation of the policy."""
        ttl_str = f"{self.ttl_seconds}s" if self.ttl_seconds else "∞"
        max_str = str(self.max_entries) if self.max_entries else "∞"
        return (
            f"Policy(tier={self.tier_name}, adapter={self.adapter_type}, "
            f"ttl={ttl_str}, max={max_str}, eviction={self.eviction_strategy})"
        )
