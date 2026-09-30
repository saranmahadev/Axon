"""Adapter factories for the StorageAdapter contract suite.

Every adapter listed here must pass the same behavioral tests. Backends that need
external services are skipped (with a visible reason) when the service is unreachable:

    AXON_TEST_REDIS_URL     redis://host:port/db   (default: redis://localhost:6379/0)
    AXON_TEST_QDRANT_URL    http://host:6333       (default: in-process Qdrant, no server)
    PINECONE_API_KEY        enables the Pinecone adapter (needs network + a real index)

CI should run Redis and Qdrant as service containers so nothing is skipped there.
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlparse

import pytest
import pytest_asyncio

DIM = 8


def _unique(prefix: str = "axon_contract") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _make_memory(tmp_path):
    from axon.adapters.memory import InMemoryAdapter

    return InMemoryAdapter(), None


async def _make_chroma(tmp_path):
    pytest.importorskip("chromadb")
    from axon.adapters.chroma import ChromaAdapter

    adapter = ChromaAdapter(collection_name=_unique(), persist_directory=str(tmp_path / "chroma"))
    return adapter, None


async def _make_qdrant(tmp_path):
    pytest.importorskip("qdrant_client")
    from axon.adapters.qdrant import QdrantAdapter

    url = os.environ.get("AXON_TEST_QDRANT_URL")
    if url:
        adapter = QdrantAdapter(url=url, collection_name=_unique())
    else:
        # In-process Qdrant: same client API, no server required
        adapter = QdrantAdapter(url=None, location=":memory:", collection_name=_unique())

    async def cleanup():
        await adapter.client.delete_collection(adapter.collection_name)

    return adapter, cleanup


async def _make_redis(tmp_path):
    pytest.importorskip("redis")
    from axon.adapters.redis import RedisAdapter

    parsed = urlparse(os.environ.get("AXON_TEST_REDIS_URL", "redis://localhost:6379/0"))
    adapter = RedisAdapter(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        db=int((parsed.path or "/0").lstrip("/") or 0),
        namespace=_unique(),
    )
    try:
        await adapter.redis.ping()
    except Exception as e:
        pytest.skip(f"Redis not reachable ({e}); set AXON_TEST_REDIS_URL")

    async def cleanup():
        await adapter.clear_async()
        await adapter.close()

    return adapter, cleanup


async def _make_pinecone(tmp_path):
    if not os.environ.get("PINECONE_API_KEY"):
        pytest.skip("PINECONE_API_KEY not set")
    pytest.importorskip("pinecone")
    from axon.adapters.pinecone import PineconeAdapter

    adapter = PineconeAdapter(
        api_key=os.environ["PINECONE_API_KEY"], index_name=_unique("axon-contract").replace("_", "-")
    )

    async def cleanup():
        await adapter.clear_async()

    return adapter, cleanup


ADAPTER_FACTORIES = {
    "memory": _make_memory,
    "chroma": _make_chroma,
    "qdrant": _make_qdrant,
    "redis": _make_redis,
    "pinecone": _make_pinecone,
}


@pytest_asyncio.fixture(params=list(ADAPTER_FACTORIES), ids=list(ADAPTER_FACTORIES))
async def adapter(request, tmp_path):
    """A fresh, empty adapter for each backend under test."""
    instance, cleanup = await ADAPTER_FACTORIES[request.param](tmp_path)
    instance.contract_name = request.param
    try:
        yield instance
    finally:
        if cleanup is not None:
            try:
                await cleanup()
            except Exception:
                pass
