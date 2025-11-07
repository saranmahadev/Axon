"""
Session Policy for medium-lived memories.

This module provides the SessionPolicy class for configuring
the session tier, which stores memories for the duration of a
user session (minutes to hours).
"""

from typing import Literal

from pydantic import Field, field_validator

from ..policy import Policy


class SessionPolicy(Policy):
    """
    Policy for session-scoped memories.

    The session tier stores memories for the duration of a user session,
    typically minutes to hours. It's designed for conversation context,
    active workspaces, and temporary user state.

    Constraints:
        - Typically uses Redis or in-memory adapters, optionally vector DBs
        - TTL should be at least 60 seconds if specified
        - Supports optional overflow to persistent tier
        - Vector search can be enabled if using vector adapter

    Use Cases:
        - Conversation history (chatbots)
        - Active workspace state
        - Recent user interactions
        - Temporary project data
        - Session-specific preferences

    Attributes:
        overflow_to_persistent: If True, promote to persistent when max_entries reached

    Example:
        >>> policy = SessionPolicy(
        ...     adapter_type="redis",
        ...     ttl_seconds=1800,  # 30 minutes
        ...     max_entries=1000,
        ...     overflow_to_persistent=True
        ... )
    """

    tier_name: Literal["session"] = Field(
        default="session", description="Tier name is always 'session'"
    )

    adapter_type: Literal["redis", "memory", "chroma", "qdrant", "pinecone"] = Field(
        "redis", description="Adapter for session storage (typically Redis)"
    )

    ttl_seconds: int | None = Field(
        600, description="TTL in seconds (default: 10 minutes, min: 60s if set)", ge=60
    )

    max_entries: int | None = Field(
        1000, description="Maximum entries per session (default: 1000)", gt=0
    )

    overflow_to_persistent: bool = Field(
        False, description="Promote to persistent tier when max_entries reached"
    )

    enable_vector_search: bool = Field(
        True, description="Enable vector search if adapter supports it"
    )

    @field_validator("ttl_seconds")
    @classmethod
    def validate_session_ttl(cls, v: int | None) -> int | None:
        """
        Validate that TTL is appropriate for session tier.

        Session TTL should be at least 60 seconds to avoid
        premature expiration during active use.
        """
        if v is not None and v < 60:
            raise ValueError(
                "Session TTL should be at least 60 seconds " "(use ephemeral tier for shorter TTLs)"
            )
        return v

    @field_validator("max_entries")
    @classmethod
    def validate_max_entries(cls, v: int | None) -> int | None:
        """
        Validate that max_entries is reasonable.

        Should have some headroom for active sessions.
        """
        if v is not None and v < 10:
            raise ValueError("Session max_entries should be at least 10")
        return v

    @field_validator("enable_vector_search")
    @classmethod
    def validate_vector_search_with_adapter(cls, v: bool, info) -> bool:
        """
        Warn if vector search enabled but adapter doesn't support it.

        This is a soft validation - we allow it but it won't work.
        """
        # Get adapter_type from field values if available
        adapter = info.data.get("adapter_type")
        if v and adapter in ["redis", "memory"]:
            # Note: We don't raise an error, just document the limitation
            # Vector search will simply not be available at runtime
            pass
        return v
