"""
Ephemeral Policy for short-lived memories.

This module provides the EphemeralPolicy class for configuring
the ephemeral tier, which stores very short-lived memories that
auto-expire within seconds to minutes.
"""

from typing import Literal

from pydantic import Field, field_validator

from ..policy import Policy


class EphemeralPolicy(Policy):
    """
    Policy for ephemeral (short-lived) memories.

    The ephemeral tier is designed for very temporary data that should
    expire quickly. It uses in-memory storage (Redis or Memory adapter)
    and always relies on TTL-based expiration.

    Constraints:
        - Only Redis or Memory adapters allowed
        - TTL must be between 5 seconds and 1 hour
        - Eviction strategy is always TTL-based
        - Vector search is disabled (not needed for short-lived data)

    Use Cases:
        - Rate limiting tokens
        - One-time verification codes
        - Temporary feature flags
        - Recent activity tracking
        - Short-term cache warming

    Example:
        >>> policy = EphemeralPolicy(
        ...     adapter_type="redis",
        ...     ttl_seconds=60  # 1 minute
        ... )
    """

    tier_name: Literal["ephemeral"] = Field(
        default="ephemeral", description="Tier name is always 'ephemeral'"
    )

    adapter_type: Literal["redis", "memory"] = Field(
        "redis", description="Only in-memory adapters allowed for ephemeral tier"
    )

    ttl_seconds: int = Field(
        60, description="TTL between 5 seconds and 1 hour (default: 60s)", ge=5, le=3600
    )

    eviction_strategy: Literal["ttl"] = Field(
        default="ttl", description="Always TTL-based for ephemeral tier"
    )

    enable_vector_search: Literal[False] = Field(
        default=False, description="Vector search disabled for ephemeral tier"
    )

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ephemeral_ttl(cls, v: int) -> int:
        """
        Validate that TTL is appropriate for ephemeral tier.

        Ephemeral memories should expire quickly (5s to 1hr).
        """
        if v < 5:
            raise ValueError("Ephemeral TTL must be at least 5 seconds")
        if v > 3600:
            raise ValueError("Ephemeral TTL should not exceed 1 hour (3600s)")
        return v

    @field_validator("adapter_type")
    @classmethod
    def validate_ephemeral_adapter(cls, v: str) -> str:
        """
        Validate that adapter type is suitable for ephemeral tier.

        Only in-memory adapters (Redis, Memory) are allowed.
        """
        if v not in ["redis", "memory"]:
            raise ValueError(f"Ephemeral tier requires in-memory adapter, got '{v}'")
        return v
