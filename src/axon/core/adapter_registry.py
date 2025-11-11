"""
Adapter Registry for managing storage adapter instances.

Provides centralized management of storage adapters across memory tiers
with lazy initialization, caching, and lifecycle management.
"""

import asyncio
from typing import Any

from axon.adapters.base import StorageAdapter


class AdapterRegistry:
    """
    Registry for managing storage adapter instances across tiers.

    Responsibilities:
    - Register adapters for each memory tier
    - Lazy initialization (create adapter on first access)
    - Singleton pattern (one adapter instance per tier)
    - Lifecycle management (initialize_all, close_all)

    Thread Safety:
        Assumes single-threaded execution per request.
        Concurrent get_adapter() calls for same tier will initialize once.

    Example:
        >>> registry = AdapterRegistry()
        >>> registry.register("ephemeral", "redis", adapter_config={...})
        >>> registry.register("session", "redis", adapter_instance=my_adapter)
        >>> adapter = await registry.get_adapter("ephemeral")
    """

    def __init__(self):
        """Initialize empty registry."""
        self._adapters: dict[str, StorageAdapter] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self._adapter_types: dict[str, str] = {}
        self._initialized: dict[str, bool] = {}
        self._init_locks: dict[str, asyncio.Lock] = {}

    def register(
        self,
        tier: str,
        adapter_type: str,
        adapter_instance: StorageAdapter | None = None,
        adapter_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Register an adapter for a memory tier.

        Args:
            tier: Tier name ("ephemeral", "session", "persistent")
            adapter_type: Adapter type ("memory", "redis", "chroma", "qdrant", "pinecone")
            adapter_instance: Pre-configured adapter instance (if provided, used directly)
            adapter_config: Configuration dict for creating adapter (if no instance provided)

        Raises:
            ValueError: If neither adapter_instance nor adapter_config provided
            ValueError: If adapter_type is invalid

        Note:
            If tier already registered, this will override the previous registration.
        """
        if adapter_instance is None and adapter_config is None:
            raise ValueError(
                f"Must provide either adapter_instance or adapter_config for tier '{tier}'"
            )

        # Validate adapter_type
        valid_types = {"memory", "redis", "chroma", "qdrant", "pinecone"}
        if adapter_type not in valid_types:
            raise ValueError(
                f"Invalid adapter_type '{adapter_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

        self._adapter_types[tier] = adapter_type

        if adapter_instance is not None:
            # Use pre-configured instance
            self._adapters[tier] = adapter_instance
            self._initialized[tier] = False  # Will check if needs initialization
            self._configs[tier] = {}
        else:
            # Store config for lazy initialization
            self._adapters[tier] = None  # type: ignore
            self._initialized[tier] = False
            self._configs[tier] = adapter_config or {}

        # Create lock for thread-safe initialization
        if tier not in self._init_locks:
            self._init_locks[tier] = asyncio.Lock()

    async def get_adapter(self, tier: str) -> StorageAdapter:
        """
        Get adapter instance for tier.

        Performs lazy initialization on first access. Subsequent calls
        return the cached instance.

        Args:
            tier: Tier name

        Returns:
            StorageAdapter instance for the tier

        Raises:
            KeyError: If tier not registered
            RuntimeError: If adapter initialization fails

        Note:
            Thread-safe through asyncio.Lock. Multiple concurrent calls
            for same tier will initialize only once.
        """
        if tier not in self._adapter_types:
            raise KeyError(
                f"Tier '{tier}' not registered. "
                f"Registered tiers: {', '.join(self.get_all_tiers())}"
            )

        # Fast path: already initialized
        if self._initialized.get(tier, False) and self._adapters[tier] is not None:
            return self._adapters[tier]

        # Slow path: need initialization (with lock for thread safety)
        async with self._init_locks[tier]:
            # Double-check after acquiring lock
            if self._initialized.get(tier, False) and self._adapters[tier] is not None:
                return self._adapters[tier]

            # Initialize adapter
            await self._initialize_adapter(tier)
            return self._adapters[tier]

    async def _initialize_adapter(self, tier: str) -> None:
        """
        Initialize adapter for tier.

        Args:
            tier: Tier name

        Raises:
            RuntimeError: If initialization fails
        """
        adapter = self._adapters[tier]

        if adapter is None:
            # Need to create adapter from config
            adapter_type = self._adapter_types[tier]
            config = self._configs[tier]

            try:
                adapter = self._create_adapter(adapter_type, config)
                self._adapters[tier] = adapter
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create adapter for tier '{tier}' " f"(type: {adapter_type}): {e}"
                ) from e

        # Initialize the adapter if it has an initialize method
        if hasattr(adapter, "initialize") and callable(adapter.initialize):
            try:
                await adapter.initialize()
                self._initialized[tier] = True
            except Exception as e:
                raise RuntimeError(f"Failed to initialize adapter for tier '{tier}': {e}") from e
        else:
            # No initialize method, mark as initialized
            self._initialized[tier] = True

    def _create_adapter(self, adapter_type: str, config: dict[str, Any]) -> StorageAdapter:
        """
        Create adapter instance from type and config.

        Args:
            adapter_type: Adapter type
            config: Configuration dict or Policy object

        Returns:
            StorageAdapter instance

        Raises:
            ValueError: If adapter_type not supported
        """
        # Convert Policy object to dict if needed
        if hasattr(config, "model_dump"):
            config = config.model_dump()

        # Filter out policy-specific fields that adapters don't need
        policy_fields = {
            "tier_name",
            "adapter_type",
            "ttl_seconds",
            "max_entries",
            "compaction_threshold",
            "eviction_strategy",
            "enable_vector_search",
            "compaction_strategy",
            "archive_adapter",
        }
        config = {k: v for k, v in config.items() if k not in policy_fields}

        if adapter_type == "memory":
            from axon.adapters.memory import InMemoryAdapter

            # InMemoryAdapter doesn't take any constructor params
            return InMemoryAdapter()
        elif adapter_type == "redis":
            from axon.adapters.redis import RedisAdapter

            return RedisAdapter(**config)
        elif adapter_type == "chroma":
            from axon.adapters.chroma import ChromaAdapter

            return ChromaAdapter(**config)
        elif adapter_type == "qdrant":
            from axon.adapters.qdrant import QdrantAdapter

            return QdrantAdapter(**config)
        elif adapter_type == "pinecone":
            from axon.adapters.pinecone import PineconeAdapter

            return PineconeAdapter(**config)
        else:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")

    async def initialize_all(self) -> None:
        """
        Initialize all registered adapters.

        Useful for warming up connections at application startup.

        Raises:
            RuntimeError: If any adapter fails to initialize
        """
        for tier in self.get_all_tiers():
            await self.get_adapter(tier)  # Triggers lazy initialization

    async def close_all(self) -> None:
        """
        Close all adapter connections.

        Should be called during application shutdown.
        Errors during close are logged but not raised.
        """
        for tier, adapter in self._adapters.items():
            if adapter is not None and self._initialized.get(tier, False):
                try:
                    if hasattr(adapter, "close") and callable(adapter.close):
                        await adapter.close()
                except Exception as e:
                    # Log error but continue closing other adapters
                    print(f"Warning: Error closing adapter for tier '{tier}': {e}")

        # Reset state
        self._initialized = dict.fromkeys(self._initialized, False)

    def is_registered(self, tier: str) -> bool:
        """
        Check if tier has registered adapter.

        Args:
            tier: Tier name

        Returns:
            True if tier is registered
        """
        return tier in self._adapter_types

    def get_all_tiers(self) -> list[str]:
        """
        Get list of all registered tier names.

        Returns:
            List of tier names (e.g., ["ephemeral", "session", "persistent"])
        """
        return list(self._adapter_types.keys())

    def get_adapter_type(self, tier: str) -> str | None:
        """
        Get adapter type for tier.

        Args:
            tier: Tier name

        Returns:
            Adapter type string or None if tier not registered
        """
        return self._adapter_types.get(tier)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all()
        return False

    def __repr__(self) -> str:
        """String representation for debugging."""
        tiers_info = []
        for tier in sorted(self.get_all_tiers()):
            adapter_type = self._adapter_types[tier]
            initialized = self._initialized.get(tier, False)
            status = "initialized" if initialized else "pending"
            tiers_info.append(f"{tier}={adapter_type}({status})")

        return f"AdapterRegistry({', '.join(tiers_info)})"
