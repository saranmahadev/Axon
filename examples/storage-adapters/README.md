# Storage Adapter Examples

Examples for different storage backends.

## Examples

- `01_qdrant_basic.py` - Qdrant vector store basics
- `04_pinecone_basic.py` - Pinecone basic operations
- `05_pinecone_serverless_demo.py` - Pinecone serverless setup
- `06_pinecone_multi_namespace.py` - Multi-namespace organization
- `07_redis_session_cache.py` - Redis for session caching
- `08_redis_ttl_demo.py` - TTL-based expiration
- `13_redis_multi_tenant.py` - Multi-tenant Redis setup

## Prerequisites

- **Qdrant:** Requires Qdrant server running (Docker: `docker run -p 6333:6333 qdrant/qdrant`)
- **Pinecone:** Requires API key (`export PINECONE_API_KEY=...`)
- **Redis:** Requires Redis server (Docker: `docker run -p 6379:6379 redis`)

## Quick Start

```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Run example
python examples/storage-adapters/07_redis_session_cache.py
```
