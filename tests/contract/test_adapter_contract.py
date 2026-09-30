"""StorageAdapter contract suite.

Every adapter must behave identically for the operations Axon's core relies on. If a
test here fails for one backend, either that adapter has a bug or the contract in
``axon.adapters.base`` is under-specified; fix one or the other, never skip the test.

The contract, in short:
    save(entry)      -> entry.id; saving an existing id overwrites (upsert)
    get(id)          -> the entry, or raises KeyError if absent
    delete(id)       -> True if something was deleted, False if the id was absent
    bulk_save(list)  -> ids in order; an empty list raises ValueError
    query(vec, k, f) -> at most k entries, best match first, honoring the filter
    count_async()    -> exact number of stored entries
    list_ids_async() -> ALL stored ids (never a truncated list)
"""

from __future__ import annotations

import uuid

import pytest

from axon.errors import EntryNotFoundError
from axon.models.base import ProvenanceEvent
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter

pytestmark = [pytest.mark.contract, pytest.mark.asyncio]

DIM = 8

# Redis is a key-value tier without vector search: query() filters and sorts by recency
NO_VECTOR_SEARCH = {"redis"}


def vec(i: int) -> list[float]:
    """Deterministic, distinguishable unit-ish vectors: one hot dimension per index."""
    v = [0.01] * DIM
    v[i % DIM] = 1.0
    return v


def make_entry(
    n: int = 0,
    *,
    entry_id: str | None = None,
    user_id: str = "alice",
    session_id: str | None = "s1",
    tags: list[str] | None = None,
    importance: float = 0.5,
    text: str | None = None,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id or str(uuid.uuid4()),
        text=text or f"memory number {n}",
        embedding=vec(n),
        metadata=MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
            importance=importance,
        ),
    )


# --------------------------------------------------------------------------- save / get


async def test_save_returns_entry_id(adapter):
    entry = make_entry()

    assert await adapter.save(entry) == entry.id


async def test_get_round_trips_text_and_metadata(adapter):
    entry = make_entry(
        3, user_id="alice", session_id="sess-9", tags=["a", "b"], importance=0.9, text="hello"
    )
    await adapter.save(entry)

    got = await adapter.get(entry.id)

    assert got.id == entry.id
    assert got.text == "hello"
    assert got.metadata.user_id == "alice"
    assert got.metadata.session_id == "sess-9"
    assert sorted(got.metadata.tags) == ["a", "b"]
    assert got.metadata.importance == pytest.approx(0.9)
    assert got.metadata.privacy_level == entry.metadata.privacy_level


async def test_get_missing_raises_entry_not_found(adapter):
    """A miss is an EntryNotFoundError (still a KeyError) carrying the requested id."""
    missing = str(uuid.uuid4())

    with pytest.raises(EntryNotFoundError) as exc_info:
        await adapter.get(missing)

    assert isinstance(exc_info.value, KeyError)
    assert exc_info.value.entry_id == missing


async def test_save_same_id_overwrites(adapter):
    entry = make_entry(text="first")
    await adapter.save(entry)

    updated = make_entry(entry_id=entry.id, text="second")
    await adapter.save(updated)

    assert (await adapter.get(entry.id)).text == "second"
    assert await adapter.count_async() == 1


async def test_save_none_raises_value_error(adapter):
    with pytest.raises(ValueError):
        await adapter.save(None)


async def test_non_uuid_string_ids_are_supported(adapter):
    """Users may pass their own ids (MemorySystem/forget docs use them)."""
    entry = make_entry(entry_id="user-supplied-id-1")
    await adapter.save(entry)

    assert (await adapter.get("user-supplied-id-1")).id == "user-supplied-id-1"
    assert "user-supplied-id-1" in await adapter.list_ids_async()
    assert await adapter.delete("user-supplied-id-1") is True


# ------------------------------------------------------------------- data fidelity
# A memory store must not silently drop data. Axon depends on all of these fields:
# `type` (entry kind), `version` (embedder-change detection), provenance (audit lineage
# and compaction), custom metadata (e.g. PII detection results) and the embedding itself.


async def test_round_trips_entry_type(adapter):
    entry = make_entry()
    entry.type = "event"
    await adapter.save(entry)

    assert (await adapter.get(entry.id)).type == "event"


async def test_round_trips_embedder_version(adapter):
    entry = make_entry()
    entry.metadata.version = "text-embedding-3-small:2025-01"
    await adapter.save(entry)

    assert (await adapter.get(entry.id)).metadata.version == "text-embedding-3-small:2025-01"


async def test_round_trips_provenance(adapter):
    entry = make_entry()
    entry.metadata.provenance = [
        ProvenanceEvent(action="store", by="memory_system", metadata={"tier": "persistent"}),
        ProvenanceEvent(action="compact", by="compactor", metadata={"source": "a,b"}),
    ]
    await adapter.save(entry)

    got = (await adapter.get(entry.id)).metadata.provenance

    assert [(p.action, p.by, p.metadata) for p in got] == [
        ("store", "memory_system", {"tier": "persistent"}),
        ("compact", "compactor", {"source": "a,b"}),
    ]


async def test_round_trips_custom_metadata(adapter):
    entry = make_entry()
    entry.metadata.topic = "billing"
    entry.metadata.attempts = 3
    entry.metadata.pii_detection = {"detected_types": ["email"], "has_pii": True}
    await adapter.save(entry)

    got = (await adapter.get(entry.id)).metadata

    assert got.topic == "billing"
    assert got.attempts == 3
    assert got.pii_detection == {"detected_types": ["email"], "has_pii": True}


@pytest.mark.parametrize("level", ["public", "internal", "sensitive", "restricted"])
async def test_round_trips_every_privacy_level(adapter, level):
    entry = make_entry()
    entry.metadata.privacy_level = level
    await adapter.save(entry)

    assert (await adapter.get(entry.id)).metadata.privacy_level == level


async def test_round_trips_created_at(adapter):
    entry = make_entry()
    await adapter.save(entry)

    got = (await adapter.get(entry.id)).metadata.created_at

    assert got.tzinfo is not None
    assert abs((got - entry.metadata.created_at).total_seconds()) < 0.01


async def test_round_trips_embedding(adapter):
    entry = make_entry(5)
    await adapter.save(entry)

    got = (await adapter.get(entry.id)).embedding

    if adapter.contract_name in NO_VECTOR_SEARCH and got is None:
        pytest.skip("redis stores no embedding for its tier")
    # Vector stores may normalize on write (Qdrant does for cosine), so compare direction
    dot = sum(a * b for a, b in zip(got, entry.embedding))
    norm = (sum(a * a for a in got) ** 0.5) * (sum(b * b for b in entry.embedding) ** 0.5)
    assert dot / norm == pytest.approx(1.0, abs=1e-5)


async def test_query_results_carry_the_same_fields_as_get(adapter):
    entry = make_entry(2, tags=["t"], importance=0.8)
    entry.type = "event"
    await adapter.save(entry)

    (result,) = await adapter.query(vec(2), k=1)

    assert result.id == entry.id
    assert result.type == "event"
    assert result.metadata.tags == ["t"]


# ------------------------------------------------------------------------------ delete


async def test_delete_existing_returns_true_and_removes(adapter):
    entry = make_entry()
    await adapter.save(entry)

    assert await adapter.delete(entry.id) is True

    with pytest.raises(KeyError):
        await adapter.get(entry.id)
    assert await adapter.count_async() == 0


async def test_delete_missing_returns_false(adapter):
    assert await adapter.delete(str(uuid.uuid4())) is False


async def test_delete_leaves_other_entries(adapter):
    keep, drop = make_entry(1), make_entry(2)
    await adapter.save(keep)
    await adapter.save(drop)

    await adapter.delete(drop.id)

    assert await adapter.list_ids_async() == [keep.id]


# ------------------------------------------------------------------- count / list_ids


async def test_count_empty_is_zero(adapter):
    assert await adapter.count_async() == 0


async def test_count_tracks_saves_and_deletes(adapter):
    entries = [make_entry(i) for i in range(5)]
    for e in entries:
        await adapter.save(e)
    assert await adapter.count_async() == 5

    await adapter.delete(entries[0].id)
    assert await adapter.count_async() == 4


async def test_list_ids_empty(adapter):
    assert await adapter.list_ids_async() == []


async def test_list_ids_returns_every_id(adapter):
    entries = [make_entry(i) for i in range(12)]
    await adapter.bulk_save(entries)

    assert sorted(await adapter.list_ids_async()) == sorted(e.id for e in entries)


@pytest.mark.slow
async def test_list_ids_is_complete_beyond_one_page(adapter):
    """forget(filter=...) enumerates via list_ids; a truncated list leaves data behind."""
    if adapter.contract_name == "pinecone":
        pytest.skip("Pinecone cannot page IDs; it raises instead of truncating (see its docs)")
    entries = [make_entry(i) for i in range(1100)]
    await adapter.bulk_save(entries)

    ids = await adapter.list_ids_async()

    assert len(ids) == 1100
    assert set(ids) == {e.id for e in entries}


# ---------------------------------------------------------------------------- bulk_save


async def test_bulk_save_returns_ids_in_order(adapter):
    entries = [make_entry(i) for i in range(4)]

    assert await adapter.bulk_save(entries) == [e.id for e in entries]
    assert await adapter.count_async() == 4


async def test_bulk_save_empty_raises_value_error(adapter):
    with pytest.raises(ValueError):
        await adapter.bulk_save([])


# ------------------------------------------------------------------------------- query


async def test_query_returns_best_match_first(adapter):
    if adapter.contract_name in NO_VECTOR_SEARCH:
        pytest.skip(f"{adapter.contract_name} does not rank by vector similarity")
    entries = [make_entry(i) for i in range(4)]  # entry i is "hot" in dimension i
    await adapter.bulk_save(entries)

    results = await adapter.query(vec(2), k=4)

    assert results[0].id == entries[2].id


async def test_query_respects_k(adapter):
    await adapter.bulk_save([make_entry(i) for i in range(6)])

    assert len(await adapter.query(vec(0), k=3)) == 3


async def test_query_k_larger_than_size_returns_everything(adapter):
    await adapter.bulk_save([make_entry(i) for i in range(3)])

    assert len(await adapter.query(vec(0), k=50)) == 3


async def test_query_empty_store_returns_empty_list(adapter):
    assert await adapter.query(vec(0), k=5) == []


async def test_query_filters_by_user_id(adapter):
    mine = [make_entry(i, user_id="alice") for i in range(3)]
    theirs = [make_entry(i + 3, user_id="bob") for i in range(3)]
    await adapter.bulk_save(mine + theirs)

    results = await adapter.query(vec(0), k=10, filter=Filter(user_id="alice"))

    assert {r.id for r in results} == {e.id for e in mine}


async def test_query_filters_by_tag(adapter):
    tagged = make_entry(1, tags=["keep"])
    other = make_entry(2, tags=["other"])
    await adapter.bulk_save([tagged, other])

    results = await adapter.query(vec(1), k=10, filter=Filter(tags=["keep"]))

    assert [r.id for r in results] == [tagged.id]


async def test_query_filters_by_min_importance(adapter):
    high = make_entry(1, importance=0.9)
    low = make_entry(2, importance=0.1)
    await adapter.bulk_save([high, low])

    results = await adapter.query(vec(1), k=10, filter=Filter(min_importance=0.5))

    assert [r.id for r in results] == [high.id]


async def test_query_filter_matching_nothing_returns_empty(adapter):
    await adapter.save(make_entry(user_id="alice"))

    assert await adapter.query(vec(0), k=5, filter=Filter(user_id="nobody")) == []


# ------------------------------------------------------------------------------ reindex


async def test_reindex_preserves_data(adapter):
    entries = [make_entry(i) for i in range(3)]
    await adapter.bulk_save(entries)

    await adapter.reindex()

    assert sorted(await adapter.list_ids_async()) == sorted(e.id for e in entries)


async def test_query_rejects_empty_vector(adapter):
    if adapter.contract_name in NO_VECTOR_SEARCH:
        pytest.skip(f"{adapter.contract_name} ignores the query vector (filter-only lookups)")
    with pytest.raises(ValueError):
        await adapter.query([], k=5)


async def test_query_rejects_non_positive_k(adapter):
    with pytest.raises(ValueError):
        await adapter.query(vec(0), k=0)
