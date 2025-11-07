"""
Memory System Configuration.

This module provides the MemoryConfig class for configuring
the complete multi-tier memory system with policies for each tier.
"""

import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .policies.ephemeral import EphemeralPolicy
from .policies.persistent import PersistentPolicy
from .policies.session import SessionPolicy


class MemoryConfig(BaseModel):
    """
    Complete memory system configuration.

    Defines the multi-tier memory architecture by specifying policies
    for ephemeral, session, and persistent tiers. At minimum, the
    persistent tier must be configured.

    Attributes:
        ephemeral: Policy for ephemeral tier (optional, short-lived)
        session: Policy for session tier (optional, medium-lived)
        persistent: Policy for persistent tier (required, long-lived)
        default_tier: Tier where new memories are stored by default
        enable_promotion: Auto-promote important memories to higher tiers
        enable_demotion: Auto-demote old/unimportant memories to lower tiers

    Example:
        >>> config = MemoryConfig(
        ...     session=SessionPolicy(adapter_type="redis", ttl_seconds=600),
        ...     persistent=PersistentPolicy(adapter_type="chroma"),
        ...     default_tier="session"
        ... )
    """

    ephemeral: EphemeralPolicy | None = Field(
        None, description="Ephemeral tier policy (optional)"
    )

    session: SessionPolicy | None = Field(None, description="Session tier policy (optional)")

    persistent: PersistentPolicy = Field(..., description="Persistent tier policy (required)")

    default_tier: Literal["ephemeral", "session", "persistent"] = Field(
        "session", description="Default tier for new memories"
    )

    enable_promotion: bool = Field(
        False, description="Auto-promote important memories to higher tiers"
    )

    enable_demotion: bool = Field(
        False, description="Auto-demote old/unimportant memories to lower tiers"
    )

    @property
    def tiers(self) -> dict:
        """
        Get configured tiers as a dictionary.

        Returns:
            Dictionary mapping tier names to their policy configurations
        """
        result = {}
        if self.ephemeral:
            result["ephemeral"] = self.ephemeral
        if self.session:
            result["session"] = self.session
        result["persistent"] = self.persistent
        return result

    @model_validator(mode="after")
    def validate_default_tier_exists(self):
        """
        Validate that the default tier is actually configured.

        If default_tier is set to "ephemeral" or "session", those
        tiers must be configured.
        """
        if self.default_tier == "ephemeral" and self.ephemeral is None:
            raise ValueError("default_tier is 'ephemeral' but ephemeral policy is not configured")
        if self.default_tier == "session" and self.session is None:
            raise ValueError("default_tier is 'session' but session policy is not configured")
        return self

    @model_validator(mode="after")
    def validate_promotion_requires_tiers(self):
        """
        Validate that promotion/demotion is only enabled with multiple tiers.

        Can't promote if there's no higher tier, or demote if no lower tier.
        """
        if self.enable_promotion:
            # Need at least 2 tiers for promotion to make sense
            tier_count = sum(
                [
                    self.ephemeral is not None,
                    self.session is not None,
                    True,  # persistent always exists
                ]
            )
            if tier_count < 2:
                raise ValueError("enable_promotion requires at least 2 tiers configured")

        if self.enable_demotion:
            # Need at least 2 tiers for demotion to make sense
            tier_count = sum(
                [
                    self.ephemeral is not None,
                    self.session is not None,
                    True,  # persistent always exists
                ]
            )
            if tier_count < 2:
                raise ValueError("enable_demotion requires at least 2 tiers configured")

        return self

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation with all policies
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Dictionary containing configuration

        Returns:
            MemoryConfig instance

        Raises:
            ValidationError: If data doesn't match schema
        """
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """
        Export configuration as JSON string.

        Args:
            indent: JSON indentation level (default: 2)

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "MemoryConfig":
        """
        Load configuration from JSON string.

        Args:
            json_str: JSON string containing configuration

        Returns:
            MemoryConfig instance

        Raises:
            ValidationError: If JSON doesn't match schema
            JSONDecodeError: If JSON is malformed
        """
        return cls.from_dict(json.loads(json_str))

    def get_tier_names(self) -> list[str]:
        """
        Get list of configured tier names.

        Returns:
            List of tier names that are configured
        """
        tiers = []
        if self.ephemeral is not None:
            tiers.append("ephemeral")
        if self.session is not None:
            tiers.append("session")
        tiers.append("persistent")  # Always configured
        return tiers

    def get_policy(
        self, tier_name: str
    ) -> EphemeralPolicy | SessionPolicy | PersistentPolicy | None:
        """
        Get policy for a specific tier.

        Args:
            tier_name: Name of tier ("ephemeral", "session", "persistent")

        Returns:
            Policy instance or None if tier not configured
        """
        if tier_name == "ephemeral":
            return self.ephemeral
        elif tier_name == "session":
            return self.session
        elif tier_name == "persistent":
            return self.persistent
        else:
            return None

    def __str__(self) -> str:
        """String representation of configuration."""
        tiers = self.get_tier_names()
        return (
            f"MemoryConfig(tiers={tiers}, default={self.default_tier}, "
            f"promotion={self.enable_promotion}, demotion={self.enable_demotion})"
        )
