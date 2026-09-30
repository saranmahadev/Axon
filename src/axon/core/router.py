"""
Router for intelligent tier selection and memory routing.

The Router orchestrates memory operations across multiple tiers,
handling tier selection, routing, and automatic promotion/demotion
based on policy evaluation and scoring.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.policy_engine import PolicyEngine
from axon.errors import AdapterError, ForgetIncompleteError, TierNotFoundError
from axon.models.entry import MemoryEntry
from axon.models.filter import Filter

logger = logging.getLogger(__name__)

# Metadata field holding an entry's absolute expiry time (epoch seconds), set from the
# tier's ttl_seconds. Stored as a regular extra metadata field, so it works on every backend.
EXPIRES_AT = "expires_at"


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

        # Time source for TTL decisions (epoch seconds); replaceable in tests
        self._clock = time.time

        # Track tier statistics for monitoring
        self._tier_stats: dict[str, dict[str, int]] = {
            "ephemeral": {"stores": 0, "recalls": 0, "forgets": 0, "promotions": 0, "expired": 0},
            "session": {
                "stores": 0,
                "recalls": 0,
                "forgets": 0,
                "promotions": 0,
                "demotions": 0,
                "expired": 0,
            },
            "persistent": {
                "stores": 0,
                "recalls": 0,
                "forgets": 0,
                "demotions": 0,
                "expired": 0,
            },
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
            raise TierNotFoundError(
                tier, list(self.config.tiers), f"Tier '{tier}' not found in configuration"
            )

        # Stamp the tier's TTL, then get adapter and store entry
        self._apply_ttl(entry, tier)
        adapter = await self.registry.get_adapter(tier)
        entry_id = await adapter.save(entry)

        # Update statistics
        self._tier_stats[tier]["stores"] += 1

        # Keep the tier within its capacity (best effort; never fails the store)
        await self._enforce_capacity(tier)

        logger.debug(f"Stored entry {entry_id} in tier '{tier}'")
        return entry_id

    async def _enforce_capacity(self, tier: str) -> None:
        """Bring an over-capacity tier back under ``max_entries`` without deleting live data.

        First sweeps expired entries; if the tier is still over its limit, demotes the
        least recently used entries that qualify for demotion. Entries that do not qualify
        stay, so the tier may remain over capacity (a warning is logged): Axon does not
        hard-evict live memories.

        Note: this scans the tier, so it runs only while the tier is over capacity.
        """
        if not self.policy_engine:
            return

        try:
            is_overflow, details = await self.policy_engine.check_overflow_async(tier)
            if not is_overflow:
                return

            logger.warning(
                f"Tier '{tier}' overflow detected: {details['overflow_amount']} entries over limit"
            )
            await self.purge_expired(tier)

            is_overflow, details = await self.policy_engine.check_overflow_async(tier)
            if not is_overflow:
                return

            demoted = await self.demote_entries(tier, limit=details["overflow_amount"])
            if demoted < details["overflow_amount"]:
                logger.warning(
                    f"Tier '{tier}' is still over capacity: demoted {demoted} of "
                    f"{details['overflow_amount']} excess entries; the rest do not qualify"
                )
        except Exception as e:
            # A failing capacity check must not block writes, but it must be visible
            logger.warning(f"Could not enforce capacity for tier '{tier}': {e}")

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

                # Expired entries must not be returned (or shadow a live copy elsewhere)
                results = await self._drop_expired(results, adapter, tier)

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
        moved_ids: set[str] = set()
        for entry, from_tier, to_tier in promoted_entries:
            try:
                await self._promote_entry(entry, from_tier, to_tier)
                moved_ids.add(entry.id)
                self._tier_stats[from_tier]["promotions"] += 1
                if "promotions" in self._tier_stats[to_tier]:
                    self._tier_stats[to_tier]["promotions"] += 1
                logger.info(f"Promoted entry {entry.id}: {from_tier} → {to_tier}")
            except Exception as e:
                logger.error(f"Failed to promote entry {entry.id}: {e}")
                # Continue without failing the recall

        # Persist the updated access metadata for entries that stayed where they are.
        # Backends return copies, so without this the counts that drive promotion are lost.
        for entry in all_results:
            source_tier = tier_sources.get(entry.id)
            if source_tier and entry.id not in moved_ids:
                await self._persist_access_metadata(entry, source_tier)

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
                raise TierNotFoundError(
                    tier, list(self.config.tiers), f"Tier '{tier}' not found in configuration"
                )
            tiers = [tier]
        else:
            tiers = list(self.config.tiers.keys())

        total_deleted = 0
        failures: dict[str, Exception] = {}

        # Delete from every tier even if one fails, so a single bad backend cannot
        # leave data behind in the others; failures are reported after the sweep.
        for t in tiers:
            try:
                deleted = await self._forget_in_tier(t, entry_id, filter)
            except Exception as e:
                logger.error(f"Error deleting from tier '{t}': {e}")
                failures[t] = e
                continue

            total_deleted += deleted
            self._tier_stats[t]["forgets"] += deleted
            if deleted > 0:
                logger.debug(f"Deleted {deleted} entries from tier '{t}'")

        logger.info(
            f"Forget complete: {total_deleted} entries deleted "
            f"(entry_id={entry_id}, tiers={tiers}, failed_tiers={list(failures)})"
        )

        if failures:
            raise ForgetIncompleteError(total_deleted, failures)

        return total_deleted

    async def _forget_in_tier(self, tier: str, entry_id: str | None, filter: Filter | None) -> int:
        """Delete matching entries from one tier and return how many were removed.

        With ``entry_id`` only that entry is a candidate; with only ``filter`` every entry
        in the tier is. When both are given, the entry must also match the filter.
        """
        adapter = await self.registry.get_adapter(tier)

        if entry_id is not None:
            candidate_ids = [entry_id]
        else:
            candidate_ids = await adapter.list_ids_async()

        deleted = 0
        for candidate_id in candidate_ids:
            if filter is not None:
                try:
                    entry = await adapter.get(candidate_id)
                except KeyError:
                    continue  # Not in this tier (or removed concurrently)
                if not filter.matches(entry):
                    continue

            if await adapter.delete(candidate_id):
                deleted += 1

        return deleted

    async def demote_entries(self, tier: str, limit: int | None = None) -> int:
        """
        Demote entries of ``tier`` that qualify for demotion to the next lower tier.

        Qualification is decided by the policy engine (low importance, no recent access,
        and rising capacity pressure make an entry more likely to qualify). Entries are
        demoted least-recently-used first, at most ``limit`` of them.

        Returns:
            Number of entries demoted

        Raises:
            TierNotFoundError: If ``tier`` is not configured
            AdapterError: If some entries could not be moved (the others still were)
        """
        if tier not in self.config.tiers:
            raise TierNotFoundError(
                tier, list(self.config.tiers), f"Tier '{tier}' not found in configuration"
            )
        if not self.policy_engine:
            return 0

        adapter = await self.registry.get_adapter(tier)
        pressure = await self._capacity_pressure(tier)

        candidates: list[tuple[MemoryEntry, str]] = []
        for entry_id in await adapter.list_ids_async():
            try:
                entry = await adapter.get(entry_id)
            except KeyError:
                continue
            if self._is_expired(entry):
                continue  # handled by purge_expired, not demoted
            target = self.policy_engine.get_demotion_path(entry, tier, capacity_pressure=pressure)
            if target is not None and target in self.config.tiers:
                candidates.append((entry, target))

        def last_use(item: tuple[MemoryEntry, str]) -> datetime:
            meta = item[0].metadata
            when = meta.last_accessed_at or meta.created_at
            return when if when.tzinfo else when.replace(tzinfo=timezone.utc)

        candidates.sort(key=last_use)
        if limit is not None:
            candidates = candidates[:limit]

        demoted = 0
        failures: list[str] = []
        for entry, target in candidates:
            try:
                await self._demote_entry(entry, tier, target)
            except Exception as e:
                logger.error(f"Failed to demote entry {entry.id} {tier} → {target}: {e}")
                failures.append(f"{entry.id}: {e}")
                continue
            demoted += 1
            self._tier_stats[tier]["demotions"] += 1
            logger.info(f"Demoted entry {entry.id}: {tier} → {target}")

        if failures:
            raise AdapterError(
                f"Demotion incomplete in tier '{tier}': {demoted} demoted, "
                f"{len(failures)} failed ({'; '.join(failures)})",
                tier=tier,
            )
        return demoted

    async def _capacity_pressure(self, tier: str) -> float:
        """Fraction of ``max_entries`` in use (0.0 when the tier is unlimited), capped at 1."""
        max_entries = getattr(self.config.tiers.get(tier), "max_entries", None)
        if not max_entries:
            return 0.0
        count = (await self.registry.get_statistics(tier))["entry_count"]
        return min(1.0, count / max_entries)

    def _tier_ttl(self, tier: str) -> int | None:
        """The tier policy's ttl_seconds (None = entries never expire)."""
        return getattr(self.config.tiers.get(tier), "ttl_seconds", None)

    def _apply_ttl(self, entry: MemoryEntry, tier: str) -> None:
        """Set (or clear) the entry's expiry according to the tier it is being written to."""
        ttl = self._tier_ttl(tier)
        if ttl is not None:
            setattr(entry.metadata, EXPIRES_AT, self._clock() + ttl)
        elif getattr(entry.metadata, EXPIRES_AT, None) is not None:
            setattr(entry.metadata, EXPIRES_AT, None)  # moved to a tier without a TTL

    def _is_expired(self, entry: MemoryEntry) -> bool:
        expires_at = getattr(entry.metadata, EXPIRES_AT, None)
        return expires_at is not None and expires_at <= self._clock()

    async def _drop_expired(self, entries: list[MemoryEntry], adapter: Any, tier: str) -> list:
        """Return only live entries, lazily deleting the expired ones from ``adapter``."""
        live = []
        for entry in entries:
            if not self._is_expired(entry):
                live.append(entry)
                continue
            try:
                await adapter.delete(entry.id)
                self._tier_stats[tier]["expired"] += 1
            except Exception as e:
                logger.warning(f"Could not delete expired entry {entry.id} from '{tier}': {e}")
        return live

    async def purge_expired(self, tier: str | None = None) -> int:
        """
        Delete every expired entry from ``tier`` (default: all tiers).

        Recall already hides and lazily removes expired entries it encounters; this sweeps
        the ones that were never recalled, so they stop counting against capacity.

        Returns:
            Number of entries deleted

        Raises:
            TierNotFoundError: If ``tier`` is not configured
            AdapterError: If a tier could not be swept (other tiers are still swept)
        """
        if tier is not None:
            if tier not in self.config.tiers:
                raise TierNotFoundError(
                    tier, list(self.config.tiers), f"Tier '{tier}' not found in configuration"
                )
            tiers = [tier]
        else:
            tiers = list(self.config.tiers)

        purged = 0
        failures: dict[str, Exception] = {}
        for t in tiers:
            try:
                adapter = await self.registry.get_adapter(t)
                for entry_id in await adapter.list_ids_async():
                    try:
                        entry = await adapter.get(entry_id)
                    except KeyError:
                        continue  # removed concurrently, or expired natively (Redis)
                    if self._is_expired(entry) and await adapter.delete(entry_id):
                        purged += 1
                        self._tier_stats[t]["expired"] += 1
            except Exception as e:
                logger.error(f"Error purging expired entries from tier '{t}': {e}")
                failures[t] = e

        if failures:
            details = "; ".join(f"{t}: {e}" for t, e in failures.items())
            raise AdapterError(
                f"Purge incomplete: {purged} expired entries deleted, but {len(failures)} "
                f"tier(s) failed ({details})"
            )
        return purged

    def _update_access_metadata(self, entry: MemoryEntry) -> None:
        """
        Update entry metadata to track access patterns.

        Updates:
        - last_accessed_at: Current timestamp
        - access_count: Increment counter

        Args:
            entry: Memory entry to update (modified in-place)
        """
        entry.metadata.last_accessed_at = datetime.now(timezone.utc)

        # access_count lives in the metadata's extra fields
        current_count = getattr(entry.metadata, "access_count", 0)
        entry.metadata.access_count = current_count + 1

        logger.debug(f"Updated access metadata for entry {entry.id}: " f"count={current_count + 1}")

    async def _persist_access_metadata(self, entry: MemoryEntry, tier: str) -> None:
        """Write updated access metadata back to the tier the entry was read from.

        Best effort: a failed write is logged and never fails the recall.
        """
        try:
            adapter = await self.registry.get_adapter(tier)
            await adapter.save(entry)
        except Exception as e:
            logger.warning(f"Could not persist access metadata for entry {entry.id}: {e}")

    async def _promote_entry(self, entry: MemoryEntry, from_tier: str, to_tier: str) -> None:
        """Move an entry to a higher tier (see :meth:`_move_entry`)."""
        await self._move_entry(entry, from_tier, to_tier)
        logger.debug(f"Promoted entry {entry.id}: {from_tier} → {to_tier}")

    async def _demote_entry(self, entry: MemoryEntry, from_tier: str, to_tier: str) -> None:
        """Move an entry to a lower tier (see :meth:`_move_entry`)."""
        await self._move_entry(entry, from_tier, to_tier)
        logger.debug(f"Demoted entry {entry.id}: {from_tier} → {to_tier}")

    async def _move_entry(self, entry: MemoryEntry, from_tier: str, to_tier: str) -> None:
        """
        Move an entry between tiers without ever leaving it in both.

        Steps: save to the target tier, then delete from the source. If the source delete
        fails, the target copy is removed again so the entry is not duplicated.

        Args:
            entry: Memory entry to move
            from_tier: Source tier name
            to_tier: Target tier name

        Raises:
            AdapterError: If the move fails (the entry then remains in the source tier)
        """
        to_adapter = await self.registry.get_adapter(to_tier)
        from_adapter = await self.registry.get_adapter(from_tier)

        # Record the tier hint in the metadata's extra fields; the target tier's TTL applies
        entry.metadata.tier = to_tier
        self._apply_ttl(entry, to_tier)

        await to_adapter.save(entry)

        try:
            await from_adapter.delete(entry.id)
        except Exception as e:
            try:
                await to_adapter.delete(entry.id)
            except Exception as rollback_error:
                logger.error(
                    f"Entry {entry.id} is now in both '{from_tier}' and '{to_tier}': "
                    f"source delete failed ({e}) and rollback failed ({rollback_error})"
                )
                raise AdapterError(
                    f"Moving entry {entry.id} {from_tier} → {to_tier} failed and could not be "
                    f"rolled back; it exists in both tiers: {e}",
                    tier=from_tier,
                ) from e
            raise AdapterError(
                f"Moving entry {entry.id} {from_tier} → {to_tier} failed; it remains in "
                f"'{from_tier}': {e}",
                tier=from_tier,
            ) from e

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
