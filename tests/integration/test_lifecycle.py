"""End-to-end lifecycle tests: promotion, demotion, TTL expiry and capacity.

These run the real MemorySystem -> Router -> PolicyEngine -> adapters stack (no mocks) on
two backends: the in-memory adapter, and Redis (a real server), which - unlike the
in-memory adapter - returns copies, so it catches bugs hidden by shared object references.

Redis: AXON_TEST_REDIS_URL (default redis://localhost:6379/0); those cases skip if unreachable.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest
import pytest_asyncio

from axon.adapters.memory import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry
from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.errors import AdapterError, TierNotFoundError
from axon.models.entry import MemoryEntry, MemoryMetadata

TIERS = ["ephemeral", "session", "persistent"]


async def _make_adapter(kind: str):
    if kind == "memory":
        return InMemoryAdapter(), None

    from axon.adapters.redis import RedisAdapter

    parsed = urlparse(os.environ.get("AXON_TEST_REDIS_URL", "redis://localhost:6379/0"))
    adapter = RedisAdapter(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        namespace=f"axon_lifecycle_{uuid.uuid4().hex[:10]}",
    )
    try:
        await adapter.redis.ping()
    except Exception as e:
        pytest.skip(f"Redis not reachable ({e}); set AXON_TEST_REDIS_URL")

    async def cleanup():
        await adapter.clear_async()
        await adapter.close()

    return adapter, cleanup


@pytest_asyncio.fixture(params=["memory", "redis"])
async def make_system(request):
    """Factory: build a MemorySystem whose three tiers use the parametrized backend."""
    cleanups = []

    async def build(**policy_overrides) -> MemorySystem:
        adapters = {}
        registry = AdapterRegistry()
        for tier in TIERS:
            adapter, cleanup = await _make_adapter(request.param)
            adapters[tier] = adapter
            registry.register(tier, request.param, adapter_instance=adapter)
            if cleanup:
                cleanups.append(cleanup)

        config = MemoryConfig(
            ephemeral=EphemeralPolicy(
                adapter_type=request.param, **policy_overrides.get("ephemeral", {})
            ),
            session=SessionPolicy(
                adapter_type=request.param, **policy_overrides.get("session", {})
            ),
            # PersistentPolicy only allows vector-store types as a label; the registry above
            # already holds the real adapter instances
            persistent=PersistentPolicy(
                adapter_type="memory", **policy_overrides.get("persistent", {})
            ),
            default_tier="ephemeral",
        )
        return MemorySystem(config, registry=registry, enable_pii_detection=False)

    yield build

    for cleanup in cleanups:
        await cleanup()


def hot_entry(entry_id: str, text: str = "promote me") -> MemoryEntry:
    """An entry whose score comfortably exceeds the promotion threshold."""
    entry = MemoryEntry(
        id=entry_id, text=text, embedding=[0.1] * 8, metadata=MemoryMetadata(importance=1.0)
    )
    entry.metadata.access_count = 50
    return entry


def cold_entry(entry_id: str, text: str = "leave me") -> MemoryEntry:
    """An entry that does not qualify for promotion."""
    return MemoryEntry(
        id=entry_id, text=text, embedding=[0.1] * 8, metadata=MemoryMetadata(importance=0.1)
    )


async def ids_in(system: MemorySystem, tier: str) -> list[str]:
    return sorted(await (await system.registry.get_adapter(tier)).list_ids_async())


async def total_entries(system: MemorySystem) -> int:
    return sum([len(await ids_in(system, t)) for t in TIERS])


async def seed(system: MemorySystem, tier: str, entry: MemoryEntry) -> None:
    await (await system.registry.get_adapter(tier)).save(entry)


# ------------------------------------------------------------------------------ promotion


@pytest.mark.asyncio
async def test_recall_moves_a_qualifying_entry_up_one_tier(make_system):
    system = await make_system()
    await seed(system, "ephemeral", hot_entry("x"))

    results = await system.recall("promote me", k=5)

    assert [r.id for r in results] == ["x"]
    assert await ids_in(system, "ephemeral") == []
    assert await ids_in(system, "session") == ["x"]


@pytest.mark.asyncio
async def test_promotion_never_duplicates_an_entry_across_tiers(make_system):
    system = await make_system()
    await seed(system, "ephemeral", hot_entry("x"))

    for _ in range(3):
        await system.recall("promote me", k=5)

    assert await total_entries(system) == 1


@pytest.mark.asyncio
async def test_non_qualifying_entry_stays_put(make_system):
    system = await make_system()
    await seed(system, "ephemeral", cold_entry("x"))

    await system.recall("leave me", k=5)

    assert await ids_in(system, "ephemeral") == ["x"]
    assert await ids_in(system, "session") == []


@pytest.mark.asyncio
async def test_top_tier_entries_are_never_promoted(make_system):
    system = await make_system()
    await seed(system, "persistent", hot_entry("x"))

    await system.recall("promote me", k=5)

    assert await ids_in(system, "persistent") == ["x"]
    assert await total_entries(system) == 1


@pytest.mark.asyncio
async def test_promotion_is_counted_in_tier_stats(make_system):
    system = await make_system()
    await seed(system, "ephemeral", hot_entry("x"))

    await system.recall("promote me", k=5)

    assert system.router.get_tier_stats("ephemeral")["promotions"] == 1


@pytest.mark.asyncio
async def test_promoted_entry_keeps_its_text_and_metadata(make_system):
    system = await make_system()
    entry = hot_entry("x", text="keep my content")
    entry.metadata.user_id = "alice"
    entry.metadata.tags = ["a", "b"]
    await seed(system, "ephemeral", entry)

    await system.recall("keep my content", k=5)

    moved = await (await system.registry.get_adapter("session")).get("x")
    assert moved.text == "keep my content"
    assert moved.metadata.user_id == "alice"
    assert sorted(moved.metadata.tags) == ["a", "b"]
    assert moved.metadata.importance == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_failed_promotion_rolls_back_and_recall_still_succeeds(make_system):
    """If the source copy cannot be removed, the target copy must not be left behind."""
    system = await make_system()
    await seed(system, "ephemeral", hot_entry("x"))
    source = await system.registry.get_adapter("ephemeral")

    async def broken_delete(id):
        raise ConnectionError("source tier unavailable")

    source.delete = broken_delete

    results = await system.recall("promote me", k=5)

    assert [r.id for r in results] == ["x"]  # recall is not failed by a promotion problem
    assert await ids_in(system, "ephemeral") == ["x"]
    assert await ids_in(system, "session") == []  # no duplicate left in the target tier


# ------------------------------------------------------------------------ access tracking


@pytest.mark.asyncio
async def test_recall_persists_access_count_and_timestamp(make_system):
    """Promotion is driven by access frequency, so counts must survive between recalls."""
    system = await make_system()
    await seed(system, "session", cold_entry("x"))

    for _ in range(3):
        await system.recall("leave me", k=5)

    stored = await (await system.registry.get_adapter("session")).get("x")
    assert stored.metadata.access_count == 3
    assert stored.metadata.last_accessed_at is not None


@pytest.mark.asyncio
async def test_access_count_accumulates_from_existing_value(make_system):
    system = await make_system()
    entry = cold_entry("x")
    entry.metadata.access_count = 4
    await seed(system, "session", entry)

    await system.recall("leave me", k=5)

    stored = await (await system.registry.get_adapter("session")).get("x")
    assert stored.metadata.access_count == 5


# ------------------------------------------------------------------------------------ TTL


class Clock:
    """Controllable time source injected into the router (no sleeping in tests)."""

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest_asyncio.fixture
async def ttl_system(make_system):
    """System with ephemeral TTL 60s, session TTL 600s, persistent TTL none."""
    system = await make_system(ephemeral={"ttl_seconds": 60}, session={"ttl_seconds": 600})
    system.router._clock = Clock()
    return system


async def stored(system: MemorySystem, tier: str, entry_id: str) -> MemoryEntry:
    return await (await system.registry.get_adapter(tier)).get(entry_id)


@pytest.mark.asyncio
async def test_store_stamps_expiry_from_the_tier_ttl(ttl_system):
    clock = ttl_system.router._clock

    entry_id = await ttl_system.store("short lived", tier="ephemeral")

    entry = await stored(ttl_system, "ephemeral", entry_id)
    assert entry.metadata.expires_at == pytest.approx(clock.now + 60)


@pytest.mark.asyncio
async def test_tier_without_ttl_never_gets_an_expiry(ttl_system):
    entry_id = await ttl_system.store("keep forever", tier="persistent")

    entry = await stored(ttl_system, "persistent", entry_id)
    assert getattr(entry.metadata, "expires_at", None) is None


@pytest.mark.asyncio
async def test_entry_is_recalled_until_its_ttl_elapses(ttl_system):
    await ttl_system.store("short lived", tier="ephemeral")

    ttl_system.router._clock.advance(59)
    assert len(await ttl_system.recall("short lived", k=5)) == 1


@pytest.mark.asyncio
async def test_expired_entry_is_not_recalled_and_is_removed(ttl_system):
    await ttl_system.store("short lived", tier="ephemeral")

    ttl_system.router._clock.advance(61)
    results = await ttl_system.recall("short lived", k=5)

    assert results == []
    assert await ids_in(ttl_system, "ephemeral") == []
    assert ttl_system.router.get_tier_stats("ephemeral")["expired"] == 1


@pytest.mark.asyncio
async def test_expired_copy_does_not_hide_a_live_copy_in_another_tier(ttl_system):
    stale = cold_entry("x", text="same memory")
    stale.metadata.expires_at = ttl_system.router._clock.now - 1
    await seed(ttl_system, "ephemeral", stale)
    await seed(ttl_system, "persistent", cold_entry("x", text="same memory"))

    results = await ttl_system.recall("same memory", k=5)

    assert [r.id for r in results] == ["x"]
    assert await ids_in(ttl_system, "ephemeral") == []
    assert await ids_in(ttl_system, "persistent") == ["x"]


@pytest.mark.asyncio
async def test_purge_expired_removes_only_expired_entries(ttl_system):
    await ttl_system.store("old one", tier="ephemeral")
    await ttl_system.store("old two", tier="ephemeral")
    keep_id = await ttl_system.store("kept forever", tier="persistent")
    ttl_system.router._clock.advance(61)
    fresh_id = await ttl_system.store("fresh", tier="ephemeral")

    purged = await ttl_system.purge_expired()

    assert purged == 2
    assert await ids_in(ttl_system, "ephemeral") == [fresh_id]
    assert await ids_in(ttl_system, "persistent") == [keep_id]


@pytest.mark.asyncio
async def test_purge_expired_can_target_one_tier(ttl_system):
    await ttl_system.store("eph", tier="ephemeral")
    await ttl_system.store("ses", tier="session")
    ttl_system.router._clock.advance(601)  # both expired

    assert await ttl_system.purge_expired(tier="ephemeral") == 1
    assert len(await ids_in(ttl_system, "session")) == 1


@pytest.mark.asyncio
async def test_purge_expired_unknown_tier_raises(ttl_system):
    with pytest.raises(TierNotFoundError):
        await ttl_system.purge_expired(tier="nope")


@pytest.mark.asyncio
async def test_promotion_resets_expiry_to_the_target_tiers_ttl(ttl_system):
    clock = ttl_system.router._clock
    await seed(ttl_system, "ephemeral", hot_entry("x"))

    await ttl_system.recall("promote me", k=5)

    entry = await stored(ttl_system, "session", "x")
    assert entry.metadata.expires_at == pytest.approx(clock.now + 600)


@pytest.mark.asyncio
async def test_promotion_into_a_tier_without_ttl_clears_the_expiry(ttl_system):
    entry = hot_entry("x")
    entry.metadata.expires_at = ttl_system.router._clock.now + 100
    await seed(ttl_system, "session", entry)

    await ttl_system.recall("promote me", k=5)

    moved = await stored(ttl_system, "persistent", "x")
    assert getattr(moved.metadata, "expires_at", None) is None


# ------------------------------------------------------------------------------ demotion


def idle_entry(
    entry_id: str, *, importance: float = 0.1, days_idle: int = 90, accesses: int = 0
) -> MemoryEntry:
    """An entry nobody has touched for ``days_idle`` days."""
    then = datetime.now(timezone.utc) - timedelta(days=days_idle)
    entry = MemoryEntry(
        id=entry_id,
        text=f"idle memory {entry_id}",
        embedding=[0.1] * 8,
        metadata=MemoryMetadata(importance=importance, created_at=then, last_accessed_at=then),
    )
    entry.metadata.access_count = accesses
    return entry


@pytest.mark.asyncio
async def test_rebalance_demotes_a_stale_low_value_entry_one_tier(make_system):
    system = await make_system()
    await seed(system, "persistent", idle_entry("x"))

    result = await system.rebalance()

    assert result == {"expired": 0, "demoted": 1}
    assert await ids_in(system, "persistent") == []
    assert await ids_in(system, "session") == ["x"]


@pytest.mark.asyncio
async def test_rebalance_moves_entries_one_tier_per_pass_without_duplicating(make_system):
    system = await make_system()
    await seed(system, "persistent", idle_entry("x"))

    await system.rebalance()
    assert await total_entries(system) == 1
    await system.rebalance()

    assert await ids_in(system, "ephemeral") == ["x"]
    assert await total_entries(system) == 1


@pytest.mark.asyncio
async def test_rebalance_keeps_recently_used_and_valuable_entries(make_system):
    system = await make_system()
    await seed(system, "persistent", hot_entry("hot"))
    await seed(system, "persistent", idle_entry("fresh", days_idle=0))

    result = await system.rebalance()

    assert result["demoted"] == 0
    assert await ids_in(system, "persistent") == ["fresh", "hot"]


@pytest.mark.asyncio
async def test_lowest_tier_entries_are_never_demoted(make_system):
    system = await make_system()
    await seed(system, "ephemeral", idle_entry("x"))

    assert (await system.rebalance())["demoted"] == 0
    assert await ids_in(system, "ephemeral") == ["x"]


@pytest.mark.asyncio
async def test_important_old_entry_is_only_demoted_under_capacity_pressure(make_system):
    """Score of an old-but-important entry sits just under the threshold until the tier fills."""
    roomy = await make_system(session={"max_entries": 1000})
    await seed(roomy, "session", idle_entry("x", importance=0.9, accesses=2))
    assert (await roomy.rebalance(tier="session"))["demoted"] == 0

    full = await make_system(session={"max_entries": 10})
    for i in range(10):
        await seed(full, "session", idle_entry(f"x{i}", importance=0.9, accesses=2))
    assert (await full.rebalance(tier="session"))["demoted"] == 10


@pytest.mark.asyncio
async def test_demotion_is_counted_in_tier_stats(make_system):
    system = await make_system()
    await seed(system, "persistent", idle_entry("x"))

    await system.rebalance()

    assert system.router.get_tier_stats("persistent")["demotions"] == 1


@pytest.mark.asyncio
async def test_rebalance_unknown_tier_raises(make_system):
    system = await make_system()

    with pytest.raises(TierNotFoundError):
        await system.rebalance(tier="nope")


@pytest.mark.asyncio
async def test_failed_demotion_is_reported_and_leaves_no_duplicate(make_system):
    system = await make_system()
    await seed(system, "persistent", idle_entry("x"))
    source = await system.registry.get_adapter("persistent")

    async def broken_delete(id):
        raise ConnectionError("source tier unavailable")

    source.delete = broken_delete

    with pytest.raises(AdapterError, match="Demotion incomplete"):
        await system.rebalance()

    assert await ids_in(system, "persistent") == ["x"]
    assert await ids_in(system, "session") == []


@pytest.mark.asyncio
async def test_rebalance_also_purges_expired_entries(ttl_system):
    await ttl_system.store("gone soon", tier="ephemeral")
    ttl_system.router._clock.advance(61)

    result = await ttl_system.rebalance()

    assert result["expired"] == 1
    assert await ids_in(ttl_system, "ephemeral") == []


# ---------------------------------------------------------------- capacity enforcement


@pytest.mark.asyncio
async def test_store_over_capacity_demotes_stale_entries_to_make_room(make_system):
    system = await make_system(session={"max_entries": 10})
    for i in range(10):
        await seed(system, "session", idle_entry(f"old{i}"))

    await system.store("brand new", tier="session", importance=0.9)

    assert len(await ids_in(system, "session")) == 10  # back at the limit
    assert len(await ids_in(system, "ephemeral")) == 1  # the least recently used moved down
    assert await total_entries(system) == 11  # nothing deleted


@pytest.mark.asyncio
async def test_store_over_capacity_purges_expired_before_demoting(make_system):
    system = await make_system(session={"max_entries": 10, "ttl_seconds": 60})
    clock = system.router._clock = Clock()
    for i in range(10):
        entry = idle_entry(f"old{i}", importance=0.9, accesses=2)
        entry.metadata.expires_at = clock.now - 1  # already expired
        await seed(system, "session", entry)

    await system.store("brand new", tier="session")

    assert len(await ids_in(system, "session")) == 1  # only the new entry remains
    assert await ids_in(system, "ephemeral") == []  # expiry made room; nothing was demoted


@pytest.mark.asyncio
async def test_store_over_capacity_never_deletes_live_entries_that_do_not_qualify(
    make_system, caplog
):
    system = await make_system(session={"max_entries": 10})
    for i in range(10):
        await seed(system, "session", hot_entry(f"hot{i}"))

    with caplog.at_level(logging.WARNING):
        await system.store("one more", tier="session", importance=0.9)

    assert len(await ids_in(system, "session")) == 11  # over capacity, but nothing was lost
    assert "still over capacity" in caplog.text
