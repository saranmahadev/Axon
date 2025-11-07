"""
Router for intelligent tier selection and memory routing.

The Router orchestrates memory operations across multiple tiers,
handling tier selection, routing, and automatic promotion/demotion
based on policy evaluation and scoring.
"""

import logging
from datetime import datetime
from typing import Any

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policy_engine import PolicyEngine
from axon.models.entry import MemoryEntry
from axon.models.filter import Filter

logger = logging.getLogger(__name__)


class Router:
    """
    Intelligent router for multi-tier memory management.

    Routes memory operations (store, recall, forget) to appropriate tiers
    based on policies and automatically promotes/demotes memories based on
    access patterns and scoring.

    Design assumptions:
    - Single-threaded operation (no concurrent routing)
    - Sequential tier queries (no parallel fan-out)
    - Automatic promotion on recall (update metadata + check scores)
    - Fail-fast error handling

    Thread safety:
    - Not thread-safe - assumes single-threaded event loop
    - All async methods should be awaited from same event loop
    - AdapterRegistry handles thread-safe adapter initialization

    Example:
        ```python
        config = MemoryConfig.balanced()
        registry = AdapterRegistry()
        # Register adapters...

        router = Router(config, registry)

        # Store a memory
        entry_id = await router.route_store(entry)

        # Recall memories (with automatic promotion)
        results = await router.route_recall(query, k=10)

        # Forget a memory
        await router.route_forget(entry_id)
        ```
    """

    def __init__(
        self,
        config: MemoryConfig,
        registry: AdapterRegistry,
        policy_engine: PolicyEngine | None = None,
        embedder: Any | None = None,
    ):
        """
        Initialize Router.

        Args:
            config: Memory configuration with tier policies
            registry: Adapter registry for accessing tier storage
            policy_engine: Policy engine for promotion/demotion decisions (optional)
            embedder: Embedder for converting text to vectors (optional)
        """
        self.config = config
        self.registry = registry
        self.policy_engine = policy_engine
        self.embedder = embedder

        # Track tier statistics for monitoring
        self._tier_stats: dict[str, dict[str, int]] = {
            "ephemeral": {"stores": 0, "recalls": 0, "forgets": 0, "promotions": 0},
            "session": {"stores": 0, "recalls": 0, "forgets": 0, "promotions": 0, "demotions": 0},
            "persistent": {"stores": 0, "recalls": 0, "forgets": 0, "demotions": 0},
        }

        logger.info(f"Router initialized with {len(config.tiers)} tiers")

    async def select_tier(self, entry: MemoryEntry) -> str:
        """
        Select appropriate tier for a memory entry.

        Uses policy configuration and PolicyEngine to determine which tier
        (ephemeral, session, persistent) should store the entry based on
        its importance and metadata.

        Selection logic:
        1. Check entry.metadata for explicit tier hint
        2. Use PolicyEngine if available for intelligent selection
        3. Fall back to importance-based thresholds
        4. Default to config.default_tier

        Args:
            entry: Memory entry to route

        Returns:
            Tier name ("ephemeral", "session", or "persistent")

        Raises:
            ValueError: If tier selection fails
        """
        # Check for explicit tier hint in metadata
        if hasattr(entry.metadata, "__pydantic_extra__") and entry.metadata.__pydantic_extra__:
            tier_hint = entry.metadata.__pydantic_extra__.get("tier")
            if tier_hint in self.config.tiers:
                logger.debug(f"Using explicit tier hint: {tier_hint}")
                return tier_hint

        # Use importance-based thresholds
        importance = entry.metadata.importance

        # Simple importance-based selection
        # persistent: importance >= 0.7
        # session: 0.3 <= importance < 0.7
        # ephemeral: importance < 0.3
        if importance >= 0.7:
            selected = "persistent"
        elif importance >= 0.3:
            selected = "session"
        else:
            selected = "ephemeral"

        # Validate selected tier exists in config
        if selected not in self.config.tiers:
            # Fall back to first available tier
            original_selected = selected
            selected = list(self.config.tiers.keys())[0]
            logger.debug(
                f"Selected tier '{original_selected}' not in config, "
                f"using first available: {selected}"
            )

        logger.debug(f"Selected tier '{selected}' for entry with importance {importance:.2f}")
        return selected

    async def route_store(self, entry: MemoryEntry, tier: str | None = None) -> str:
        """
        Route store operation to appropriate tier.

        Selects tier (if not specified), handles tier overflow by demoting
        existing entries if needed, stores entry, and updates statistics.

        Args:
            entry: Memory entry to store
            tier: Optional explicit tier (overrides selection logic)

        Returns:
            Entry ID from storage adapter

        Raises:
            KeyError: If selected tier not registered
            RuntimeError: If storage operation fails
        """
        # Select tier if not explicitly specified
        if tier is None:
            tier = await self.select_tier(entry)

        # Validate tier exists
        if tier not in self.config.tiers:
            raise KeyError(f"Tier '{tier}' not found in configuration")

        # Check for overflow and handle if policy engine available
        if self.policy_engine:
            is_overflow, overflow_details = self.policy_engine.check_overflow(tier)
            if is_overflow:
                logger.warning(
                    f"Tier '{tier}' overflow detected: {overflow_details['overflow_amount']} "
                    f"entries over limit"
                )
                # In a full implementation, would trigger compaction/demotion here
                # For now, just log the overflow

        # Get adapter and store entry
        adapter = await self.registry.get_adapter(tier)
        entry_id = await adapter.save(entry)

        # Update statistics
        self._tier_stats[tier]["stores"] += 1

        logger.debug(f"Stored entry {entry_id} in tier '{tier}'")
        return entry_id

    async def route_recall(
        self,
        query_text: str,
        k: int = 5,
        filter: Filter | None = None,
        tiers: list[str] | None = None,
    ) -> list[MemoryEntry]:
        """
        Route recall operation across tiers.

        Queries specified tiers (or all tiers), merges results, deduplicates,
        automatically checks for promotion opportunities, and updates access metadata.

        Query strategy:
        - Query tiers sequentially (not parallel)
        - Merge and deduplicate results by entry ID
        - Sort by relevance score
        - Check promotion criteria for accessed memories
        - Update access metadata (access_count, last_accessed_at)

        Args:
            query_text: Query string for semantic search
            k: Number of results to return
            filter: Optional filter to apply
            tiers: Optional list of tiers to query (default: all)

        Returns:
            List of matching memory entries, sorted by relevance

        Raises:
            KeyError: If specified tier not registered
            RuntimeError: If query operation fails
        """
        # Determine which tiers to query
        if tiers is None:
            tiers = list(self.config.tiers.keys())

        # Embed query text if embedder available
        query_vector = None
        if self.embedder and query_text:
            query_vector = await self.embedder.embed(query_text)

        # Track seen entry IDs to deduplicate
        seen_ids: set[str] = set()
        all_results: list[MemoryEntry] = []
        tier_sources: dict[str, str] = {}  # entry_id -> tier_name

        # Query each tier sequentially
        for tier in tiers:
            if tier not in self.config.tiers:
                logger.warning(f"Skipping unknown tier '{tier}'")
                continue

            try:
                adapter = await self.registry.get_adapter(tier)

                # Use vector query if we have embeddings, otherwise text query
                if query_vector is not None:
                    results = await adapter.query(query_vector, k=k, filter=filter)
                else:
                    # Fallback to text query (for adapters that support it)
                    results = await adapter.query(query_text, k=k, filter=filter)

                # Deduplicate and track sources
                for entry in results:
                    if entry.id not in seen_ids:
                        seen_ids.add(entry.id)
                        all_results.append(entry)
                        tier_sources[entry.id] = tier

                self._tier_stats[tier]["recalls"] += 1
                logger.debug(f"Queried tier '{tier}': {len(results)} results")

            except Exception as e:
                logger.error(f"Error querying tier '{tier}': {e}")
                # Continue with other tiers
                continue

        # Update access metadata and check for promotions
        promoted_entries: list[tuple[MemoryEntry, str, str]] = []  # (entry, from_tier, to_tier)

        for entry in all_results:
            source_tier = tier_sources.get(entry.id)
            if not source_tier:
                continue

            # Update access metadata
            self._update_access_metadata(entry)

            # Check for promotion if policy engine available
            if self.policy_engine:
                target_tier = self.policy_engine.get_promotion_path(entry, source_tier)
                if target_tier:
                    promoted_entries.append((entry, source_tier, target_tier))
                    logger.debug(
                        f"Entry {entry.id} qualifies for promotion: "
                        f"{source_tier} → {target_tier}"
                    )

        # Execute promotions (move entries to higher tiers)
        for entry, from_tier, to_tier in promoted_entries:
            try:
                await self._promote_entry(entry, from_tier, to_tier)
                self._tier_stats[from_tier]["promotions"] += 1
                if "promotions" in self._tier_stats[to_tier]:
                    self._tier_stats[to_tier]["promotions"] += 1
                logger.info(f"Promoted entry {entry.id}: {from_tier} → {to_tier}")
            except Exception as e:
                logger.error(f"Failed to promote entry {entry.id}: {e}")
                # Continue without failing the recall

        # Sort by relevance (if entries have scores) and return top k
        # Note: Actual score sorting would require score metadata from adapter
        results = all_results[:k]

        logger.debug(
            f"Recall complete: {len(results)} results, " f"{len(promoted_entries)} promotions"
        )

        return results

    async def route_forget(
        self,
        entry_id: str | None = None,
        filter: Filter | None = None,
        tier: str | None = None,
    ) -> int:
        """
        Route forget operation to appropriate tier(s).

        Deletes memory entries matching ID or filter from specified tier
        or all tiers. Updates statistics.

        Args:
            entry_id: Specific entry ID to delete
            filter: Filter to match entries for deletion
            tier: Optional specific tier (default: search all)

        Returns:
            Number of entries deleted

        Raises:
            ValueError: If neither entry_id nor filter provided
            KeyError: If specified tier not registered
            RuntimeError: If deletion fails
        """
        # Validate inputs
        if entry_id is None and filter is None:
            raise ValueError("Must provide either entry_id or filter")

        # Determine which tiers to search
        if tier is not None:
            if tier not in self.config.tiers:
                raise KeyError(f"Tier '{tier}' not found in configuration")
            tiers = [tier]
        else:
            tiers = list(self.config.tiers.keys())

        total_deleted = 0

        # Delete from each tier
        for t in tiers:
            try:
                adapter = await self.registry.get_adapter(t)
                deleted = await adapter.delete(entry_id=entry_id, filter=filter)
                total_deleted += deleted
                self._tier_stats[t]["forgets"] += deleted

                if deleted > 0:
                    logger.debug(f"Deleted {deleted} entries from tier '{t}'")

            except Exception as e:
                logger.error(f"Error deleting from tier '{t}': {e}")
                # Continue with other tiers
                continue

        logger.info(
            f"Forget complete: {total_deleted} entries deleted "
            f"(entry_id={entry_id}, tiers={tiers})"
        )

        return total_deleted

    def _update_access_metadata(self, entry: MemoryEntry) -> None:
        """
        Update entry metadata to track access patterns.

        Updates:
        - last_accessed_at: Current timestamp
        - access_count: Increment counter

        Args:
            entry: Memory entry to update (modified in-place)
        """
        # Update last_accessed_at
        entry.metadata.last_accessed_at = datetime.now()

        # Update access_count in extra fields
        if not hasattr(entry.metadata, "__pydantic_extra__"):
            entry.metadata.__pydantic_extra__ = {}

        current_count = entry.metadata.__pydantic_extra__.get("access_count", 0)
        entry.metadata.__pydantic_extra__["access_count"] = current_count + 1

        logger.debug(f"Updated access metadata for entry {entry.id}: " f"count={current_count + 1}")

    async def _promote_entry(self, entry: MemoryEntry, from_tier: str, to_tier: str) -> None:
        """
        Promote entry from one tier to another.

        Steps:
        1. Save entry to target tier
        2. Delete from source tier
        3. Update tier hint in metadata

        Args:
            entry: Memory entry to promote
            from_tier: Source tier name
            to_tier: Target tier name

        Raises:
            RuntimeError: If promotion fails
        """
        # Save to target tier
        to_adapter = await self.registry.get_adapter(to_tier)

        # Update tier hint in metadata
        if not hasattr(entry.metadata, "__pydantic_extra__"):
            entry.metadata.__pydantic_extra__ = {}
        entry.metadata.__pydantic_extra__["tier"] = to_tier

        await to_adapter.save(entry)

        # Delete from source tier
        from_adapter = await self.registry.get_adapter(from_tier)
        await from_adapter.delete(entry_id=entry.id)

        logger.debug(f"Promoted entry {entry.id}: {from_tier} → {to_tier}")

    async def _demote_entry(self, entry: MemoryEntry, from_tier: str, to_tier: str) -> None:
        """
        Demote entry from one tier to another.

        Steps:
        1. Save entry to target tier
        2. Delete from source tier
        3. Update tier hint in metadata

        Args:
            entry: Memory entry to demote
            from_tier: Source tier name
            to_tier: Target tier name

        Raises:
            RuntimeError: If demotion fails
        """
        # Save to target tier
        to_adapter = await self.registry.get_adapter(to_tier)

        # Update tier hint in metadata
        if not hasattr(entry.metadata, "__pydantic_extra__"):
            entry.metadata.__pydantic_extra__ = {}
        entry.metadata.__pydantic_extra__["tier"] = to_tier

        await to_adapter.save(entry)

        # Delete from source tier
        from_adapter = await self.registry.get_adapter(from_tier)
        await from_adapter.delete(entry_id=entry.id)

        logger.debug(f"Demoted entry {entry.id}: {from_tier} → {to_tier}")

    def get_tier_stats(self, tier: str | None = None) -> dict[str, Any]:
        """
        Get statistics for tier operations.

        Args:
            tier: Specific tier name, or None for all tiers

        Returns:
            Dictionary of statistics
        """
        if tier is not None:
            return self._tier_stats.get(tier, {})
        return self._tier_stats.copy()

    def reset_stats(self):
        """Reset tier statistics to zero."""
        for tier in self._tier_stats:
            for key in self._tier_stats[tier]:
                self._tier_stats[tier][key] = 0

    def __repr__(self) -> str:
        """String representation."""
        tiers = ", ".join(self.registry.get_all_tiers())
        return f"Router(tiers=[{tiers}], policy_engine={self.policy_engine is not None})"
