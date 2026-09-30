"""
End-to-end tests for MemorySystem.forget().

These use real in-memory adapters (no mocks) because forget() previously reported
success while deleting nothing: mocks encoded the wrong adapter contract and hid it.
"""

import pytest

from axon.core.audit import AuditLogger
from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.errors import ForgetIncompleteError
from axon.models.audit import EventStatus, OperationType
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter

TIERS = ["ephemeral", "session", "persistent"]


@pytest.fixture
def audit_logger():
    return AuditLogger()


@pytest.fixture
def system(audit_logger):
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(adapter_type="memory"),
        session=SessionPolicy(adapter_type="memory"),
        persistent=PersistentPolicy(adapter_type="memory"),
        default_tier="persistent",
    )
    return MemorySystem(config=config, audit_logger=audit_logger, enable_pii_detection=False)


def make_entry(entry_id: str, user_id: str = "alice", text: str | None = None) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        text=text or f"memory {entry_id}",
        metadata=MemoryMetadata(user_id=user_id),
    )


async def seed(system: MemorySystem, tier: str, *entries: MemoryEntry) -> None:
    adapter = await system.registry.get_adapter(tier)
    for entry in entries:
        await adapter.save(entry)


async def count(system: MemorySystem, tier: str) -> int:
    return await (await system.registry.get_adapter(tier)).count_async()


@pytest.mark.asyncio
async def test_forget_by_id_removes_entry_from_storage(system):
    await seed(system, "persistent", make_entry("e1"), make_entry("e2"))

    deleted = await system.forget("e1")

    assert deleted == 1
    persistent = await system.registry.get_adapter("persistent")
    assert await persistent.list_ids_async() == ["e2"]
    with pytest.raises(KeyError):
        await persistent.get("e1")


@pytest.mark.asyncio
async def test_forget_by_id_removes_entry_from_every_tier(system):
    await seed(system, "session", make_entry("dup"))
    await seed(system, "persistent", make_entry("dup"))

    deleted = await system.forget("dup")

    assert deleted == 2
    assert await count(system, "session") == 0
    assert await count(system, "persistent") == 0


@pytest.mark.asyncio
async def test_forget_specific_tier_leaves_other_tiers_untouched(system):
    await seed(system, "session", make_entry("dup"))
    await seed(system, "persistent", make_entry("dup"))

    deleted = await system.forget("dup", tier="session")

    assert deleted == 1
    assert await count(system, "session") == 0
    assert await count(system, "persistent") == 1


@pytest.mark.asyncio
async def test_forget_by_filter_removes_only_matching_user_across_tiers(system):
    for tier in TIERS:
        await seed(
            system,
            tier,
            make_entry(f"{tier}-alice", user_id="alice"),
            make_entry(f"{tier}-bob", user_id="bob"),
        )

    deleted = await system.forget(filter=Filter(user_id="alice"))

    assert deleted == 3
    for tier in TIERS:
        adapter = await system.registry.get_adapter(tier)
        assert await adapter.list_ids_async() == [f"{tier}-bob"]


@pytest.mark.asyncio
async def test_forget_id_and_filter_requires_both_to_match(system):
    await seed(system, "persistent", make_entry("e1", user_id="alice"))

    assert await system.forget("e1", filter=Filter(user_id="bob")) == 0
    assert await count(system, "persistent") == 1

    assert await system.forget("e1", filter=Filter(user_id="alice")) == 1
    assert await count(system, "persistent") == 0


@pytest.mark.asyncio
async def test_forget_unknown_id_returns_zero(system):
    await seed(system, "persistent", make_entry("e1"))

    assert await system.forget("does-not-exist") == 0
    assert await count(system, "persistent") == 1


@pytest.mark.asyncio
async def test_forget_requires_id_or_filter(system):
    with pytest.raises(ValueError, match="Must provide either"):
        await system.forget()


@pytest.mark.asyncio
async def test_forget_unknown_tier_raises(system):
    with pytest.raises(KeyError):
        await system.forget("e1", tier="nope")


@pytest.mark.asyncio
async def test_forget_failure_in_one_tier_still_clears_others_then_raises(system):
    """A failing tier must not stop erasure elsewhere, nor be reported as success."""
    for tier in TIERS:
        await seed(system, tier, make_entry("dup"))

    session = await system.registry.get_adapter("session")

    async def broken_delete(id):
        raise ConnectionError("session backend down")

    session.delete = broken_delete

    with pytest.raises(ForgetIncompleteError, match="Forget incomplete") as exc_info:
        await system.forget("dup")

    assert exc_info.value.deleted_count == 2
    assert list(exc_info.value.failures) == ["session"]
    assert isinstance(exc_info.value.failures["session"], ConnectionError)
    assert await count(system, "ephemeral") == 0
    assert await count(system, "persistent") == 0
    assert await count(system, "session") == 1  # the failed tier is the one left behind


@pytest.mark.asyncio
async def test_forget_is_audit_logged(system, audit_logger):
    await seed(system, "persistent", make_entry("e1", user_id="alice"))

    await system.forget(filter=Filter(user_id="alice"))

    events = await audit_logger.get_events(operation=OperationType.FORGET)
    assert len(events) == 1
    assert events[0].status == EventStatus.SUCCESS
    assert events[0].user_id == "alice"
    assert events[0].metadata["deleted_count"] == 1
    assert events[0].metadata["filter"] == {"user_id": "alice"}


@pytest.mark.asyncio
async def test_forget_failure_is_audit_logged(system, audit_logger):
    session = await system.registry.get_adapter("session")

    async def broken_delete(id):
        raise ConnectionError("down")

    session.delete = broken_delete

    with pytest.raises(RuntimeError):
        await system.forget("e1")

    events = await audit_logger.get_events(operation=OperationType.FORGET)
    assert len(events) == 1
    assert events[0].status == EventStatus.FAILURE
    assert events[0].entry_ids == ["e1"]


@pytest.mark.asyncio
async def test_forgotten_entry_is_no_longer_recalled(system):
    entry_id = await system.store("my secret launch code is 1234", importance=0.9)
    assert await system.recall("secret launch code", k=5)

    assert await system.forget(entry_id) >= 1

    assert await system.recall("secret launch code", k=5) == []


@pytest.mark.asyncio
async def test_store_with_audit_logging_and_string_privacy_level(system, audit_logger):
    """Regression: store() crashed after writing when privacy_level was a plain string."""
    entry_id = await system.store("plain note", metadata={"privacy_level": "restricted"})

    events = await audit_logger.get_events(operation=OperationType.STORE)
    assert events[0].status == EventStatus.SUCCESS
    assert events[0].metadata["privacy_level"] == "restricted"
    assert entry_id
