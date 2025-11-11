# Custom Storage Adapters

Build your own storage adapter to integrate any database or backend with Axon.

---

## Overview

Axon's adapter architecture allows you to **integrate any storage backend** by implementing the `StorageAdapter` interface. Whether you want to use a specific database, cloud service, or custom storage solution, creating a custom adapter is straightforward.

**Common Use Cases:**
- Integrate proprietary databases
- Use specialized vector stores
- Connect to cloud storage (S3, Azure Blob)
- Implement custom caching strategies
- Add domain-specific features
- Comply with enterprise requirements

---

## StorageAdapter Interface

All adapters must implement the `StorageAdapter` abstract base class:

```python
from axon.adapters.base import StorageAdapter
from axon.models import MemoryEntry, Filter

class CustomAdapter(StorageAdapter):
    """Custom storage adapter implementation."""
    
    async def save(self, entry: MemoryEntry) -> str:
        """Save entry and return ID."""
        pass
    
    async def query(
        self, 
        vector: list[float], 
        k: int = 5,
        filter: Filter | None = None
    ) -> list[MemoryEntry]:
        """Query by vector similarity with optional filtering."""
        pass
    
    async def get(self, id: str) -> MemoryEntry:
        """Retrieve entry by ID."""
        pass
    
    async def delete(self, id: str) -> bool:
        """Delete entry by ID."""
        pass
    
    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Save multiple entries efficiently."""
        pass
    
    async def reindex(self) -> None:
        """Rebuild index for vector search."""
        pass
```

---

## Required Methods

### 1. save()

Store a single memory entry:

```python
async def save(self, entry: MemoryEntry) -> str:
    """Save entry and return its ID.
    
    Args:
        entry: MemoryEntry with text, embedding, metadata
    
    Returns:
        Unique ID string for the saved entry
    
    Raises:
        ValueError: If entry is invalid
    """
    # Validate entry
    if not entry.text:
        raise ValueError("Entry must have text")
    
    # Generate ID if needed
    if not entry.id:
        entry.id = str(uuid.uuid4())
    
    # Store in your backend
    await self.backend.insert(entry.dict())
    
    return entry.id
```

### 2. query()

Search by vector similarity:

```python
async def query(
    self,
    vector: list[float],
    k: int = 5,
    filter: Filter | None = None
) -> list[MemoryEntry]:
    """Query by vector similarity.
    
    Args:
        vector: Query embedding (e.g., 1536-dim for OpenAI)
        k: Number of results to return (top-k)
        filter: Optional metadata filter
    
    Returns:
        List of MemoryEntry objects, ordered by similarity (highest first)
    
    Raises:
        ValueError: If vector is empty or k is invalid
    """
    # Validate inputs
    if not vector:
        raise ValueError("Query vector cannot be empty")
    if k <= 0:
        raise ValueError("k must be positive")
    
    # Perform similarity search in your backend
    results = await self.backend.similarity_search(
        vector=vector,
        limit=k,
        filters=filter.dict() if filter else None
    )
    
    # Convert to MemoryEntry objects
    return [MemoryEntry(**r) for r in results]
```

### 3. get()

Retrieve by ID:

```python
async def get(self, id: str) -> MemoryEntry:
    """Retrieve entry by ID.
    
    Args:
        id: Unique identifier
    
    Returns:
        MemoryEntry object
    
    Raises:
        KeyError: If entry not found
    """
    result = await self.backend.get(id)
    
    if not result:
        raise KeyError(f"Entry not found: {id}")
    
    return MemoryEntry(**result)
```

### 4. delete()

Remove an entry:

```python
async def delete(self, id: str) -> bool:
    """Delete entry by ID.
    
    Args:
        id: Unique identifier
    
    Returns:
        True if deleted, False if not found
    """
    return await self.backend.delete(id)
```

### 5. bulk_save()

Batch insert for efficiency:

```python
async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
    """Save multiple entries efficiently.
    
    Args:
        entries: List of MemoryEntry objects
    
    Returns:
        List of IDs (in same order as entries)
    
    Raises:
        ValueError: If entries is empty or invalid
    """
    if not entries:
        raise ValueError("Entries list cannot be empty")
    
    # Generate IDs if needed
    for entry in entries:
        if not entry.id:
            entry.id = str(uuid.uuid4())
    
    # Batch insert in your backend
    await self.backend.bulk_insert([e.dict() for e in entries])
    
    return [e.id for e in entries]
```

### 6. reindex()

Rebuild indexes:

```python
async def reindex(self) -> None:
    """Rebuild vector search index.
    
    For vector stores, rebuild similarity index.
    For other stores, this may be a no-op.
    
    Raises:
        RuntimeError: If reindexing fails
    """
    await self.backend.rebuild_index()
```

---

## Optional Methods

### Transaction Support

If your backend supports transactions:

```python
async def supports_transactions(self) -> bool:
    """Check if adapter supports transactions."""
    return True

async def prepare_transaction(self, transaction_id: str) -> bool:
    """Prepare for transaction commit (2PC Phase 1)."""
    return await self.backend.prepare(transaction_id)

async def commit_transaction(self, transaction_id: str) -> bool:
    """Commit transaction (2PC Phase 2)."""
    return await self.backend.commit(transaction_id)

async def abort_transaction(self, transaction_id: str) -> bool:
    """Abort transaction and rollback."""
    return await self.backend.rollback(transaction_id)
```

---

## Complete Example: MongoDB Adapter

```python
"""MongoDB storage adapter for Axon."""

from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np
from typing import Optional
import uuid

from axon.adapters.base import StorageAdapter
from axon.models import MemoryEntry, Filter


class MongoDBAdapter(StorageAdapter):
    """MongoDB storage adapter with vector search."""
    
    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        database: str = "axon",
        collection: str = "memories"
    ):
        """Initialize MongoDB adapter.
        
        Args:
            connection_string: MongoDB connection URI
            database: Database name
            collection: Collection name
        """
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[database]
        self.collection = self.db[collection]
    
    async def save(self, entry: MemoryEntry) -> str:
        """Save entry to MongoDB."""
        if not entry.id:
            entry.id = str(uuid.uuid4())
        
        doc = entry.dict()
        await self.collection.update_one(
            {"_id": entry.id},
            {"$set": doc},
            upsert=True
        )
        
        return entry.id
    
    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Optional[Filter] = None
    ) -> list[MemoryEntry]:
        """Query by vector similarity."""
        # Build filter query
        query = {}
        if filter:
            if filter.tags:
                query["tags"] = {"$all": filter.tags}
            if filter.min_importance is not None:
                query["importance"] = {"$gte": filter.min_importance}
            if filter.metadata:
                for key, value in filter.metadata.items():
                    query[f"metadata.{key}"] = value
        
        # Get all matching documents
        cursor = self.collection.find(query)
        docs = await cursor.to_list(length=None)
        
        if not docs:
            return []
        
        # Compute similarities (in-memory for simplicity)
        query_vec = np.array(vector)
        similarities = []
        
        for doc in docs:
            if "embedding" in doc and doc["embedding"]:
                doc_vec = np.array(doc["embedding"])
                # Cosine similarity
                similarity = np.dot(query_vec, doc_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
                )
                similarities.append((similarity, doc))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Take top k
        top_docs = [doc for _, doc in similarities[:k]]
        
        # Convert to MemoryEntry
        return [MemoryEntry(**doc) for doc in top_docs]
    
    async def get(self, id: str) -> MemoryEntry:
        """Retrieve entry by ID."""
        doc = await self.collection.find_one({"_id": id})
        
        if not doc:
            raise KeyError(f"Entry not found: {id}")
        
        return MemoryEntry(**doc)
    
    async def delete(self, id: str) -> bool:
        """Delete entry by ID."""
        result = await self.collection.delete_one({"_id": id})
        return result.deleted_count > 0
    
    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Bulk save entries."""
        if not entries:
            raise ValueError("Entries list cannot be empty")
        
        # Generate IDs
        for entry in entries:
            if not entry.id:
                entry.id = str(uuid.uuid4())
        
        # Bulk upsert
        operations = [
            {
                "update_one": {
                    "filter": {"_id": entry.id},
                    "update": {"$set": entry.dict()},
                    "upsert": True
                }
            }
            for entry in entries
        ]
        
        await self.collection.bulk_write(operations)
        
        return [entry.id for entry in entries]
    
    async def reindex(self) -> None:
        """Create indexes for MongoDB."""
        # Create indexes for common queries
        await self.collection.create_index("tags")
        await self.collection.create_index("importance")
        await self.collection.create_index("created_at")
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()


# Usage
async def main():
    # Create adapter
    adapter = MongoDBAdapter(
        connection_string="mongodb://localhost:27017",
        database="axon",
        collection="memories"
    )
    
    # Use with MemorySystem
    from axon import MemorySystem
    from axon.core.config import MemoryConfig
    from axon.core.policies import PersistentPolicy
    
    config = MemoryConfig(
        persistent=PersistentPolicy(adapter=adapter)
    )
    
    memory = MemorySystem(config)
    
    # Store and query
    await memory.store("Hello MongoDB!", importance=0.8)
    results = await memory.recall("MongoDB", k=5)
    
    print(f"Found {len(results)} results")
```

---

## Example: S3 Archive Adapter

For long-term archival storage:

```python
"""S3 storage adapter for archival."""

import boto3
import json
from typing import Optional

from axon.adapters.base import StorageAdapter
from axon.models import MemoryEntry, Filter


class S3Adapter(StorageAdapter):
    """S3 storage adapter for archival."""
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "memories/",
        region: str = "us-east-1"
    ):
        """Initialize S3 adapter.
        
        Args:
            bucket: S3 bucket name
            prefix: Key prefix for memories
            region: AWS region
        """
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket
        self.prefix = prefix
    
    async def save(self, entry: MemoryEntry) -> str:
        """Save entry to S3."""
        if not entry.id:
            entry.id = str(uuid.uuid4())
        
        key = f"{self.prefix}{entry.id}.json"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(entry.dict()),
            ContentType='application/json'
        )
        
        return entry.id
    
    async def get(self, id: str) -> MemoryEntry:
        """Retrieve entry from S3."""
        key = f"{self.prefix}{id}.json"
        
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            data = json.loads(response['Body'].read())
            return MemoryEntry(**data)
        except self.s3.exceptions.NoSuchKey:
            raise KeyError(f"Entry not found: {id}")
    
    async def delete(self, id: str) -> bool:
        """Delete entry from S3."""
        key = f"{self.prefix}{id}.json"
        
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False
    
    async def query(
        self,
        vector: list[float],
        k: int = 5,
        filter: Optional[Filter] = None
    ) -> list[MemoryEntry]:
        """S3 doesn't support efficient vector search."""
        raise NotImplementedError(
            "S3 adapter doesn't support vector search. "
            "Use for archival only."
        )
    
    async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
        """Bulk save to S3."""
        ids = []
        for entry in entries:
            id = await self.save(entry)
            ids.append(id)
        return ids
    
    async def reindex(self) -> None:
        """No-op for S3."""
        pass
```

---

## Testing Your Adapter

### Unit Tests

```python
# test_custom_adapter.py
import pytest
from axon.models import MemoryEntry

@pytest.mark.asyncio
async def test_save_and_get():
    """Test save and retrieve."""
    adapter = CustomAdapter()
    
    # Create entry
    entry = MemoryEntry(
        text="Test memory",
        embedding=[0.1] * 1536,
        importance=0.8
    )
    
    # Save
    id = await adapter.save(entry)
    assert id
    
    # Retrieve
    retrieved = await adapter.get(id)
    assert retrieved.text == "Test memory"
    assert retrieved.importance == 0.8

@pytest.mark.asyncio
async def test_query():
    """Test vector search."""
    adapter = CustomAdapter()
    
    # Store entries
    for i in range(10):
        await adapter.save(MemoryEntry(
            text=f"Entry {i}",
            embedding=[i/10] * 1536,
            importance=0.5
        ))
    
    # Query
    results = await adapter.query(
        vector=[0.5] * 1536,
        k=3
    )
    
    assert len(results) == 3
    assert all(isinstance(r, MemoryEntry) for r in results)

@pytest.mark.asyncio
async def test_delete():
    """Test deletion."""
    adapter = CustomAdapter()
    
    # Save and delete
    entry = MemoryEntry(text="Delete me", embedding=[0.1] * 1536)
    id = await adapter.save(entry)
    
    deleted = await adapter.delete(id)
    assert deleted
    
    # Verify deleted
    with pytest.raises(KeyError):
        await adapter.get(id)
```

---

## Best Practices

### 1. Handle Errors Gracefully

```python
async def save(self, entry: MemoryEntry) -> str:
    try:
        # Your save logic
        return entry.id
    except ConnectionError as e:
        raise RuntimeError(f"Failed to connect to backend: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to save entry: {e}")
```

### 2. Implement Efficient Batching

```python
async def bulk_save(self, entries: list[MemoryEntry]) -> list[str]:
    # Process in batches for better performance
    batch_size = 100
    all_ids = []
    
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i + batch_size]
        # Batch insert logic
        ids = await self._insert_batch(batch)
        all_ids.extend(ids)
    
    return all_ids
```

### 3. Add Connection Pooling

```python
class CustomAdapter(StorageAdapter):
    def __init__(self, connection_string: str, pool_size: int = 10):
        self.pool = ConnectionPool(
            connection_string,
            max_connections=pool_size
        )
```

### 4. Support Filtering

```python
async def query(self, vector, k, filter=None):
    query_params = {}
    
    if filter:
        if filter.tags:
            query_params['tags'] = filter.tags
        if filter.min_importance:
            query_params['importance__gte'] = filter.min_importance
        # Add more filter support
    
    return await self.backend.search(vector, k, **query_params)
```

---

## Registering Your Adapter

```python
from axon.core.adapter_registry import AdapterRegistry

# Register your adapter
AdapterRegistry.register("mongodb", MongoDBAdapter)
AdapterRegistry.register("s3", S3Adapter)

# Use in configuration
config = MemoryConfig(
    persistent=PersistentPolicy(adapter_type="mongodb")
)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-test-tube:{ .lg .middle } **Testing Guide**

    ---

    Learn to test your custom adapter.

    [:octicons-arrow-right-24: Testing Guide](../contributing/testing.md)

-   :material-book-open-variant:{ .lg .middle } **API Reference**

    ---

    Full StorageAdapter API documentation.

    [:octicons-arrow-right-24: Adapter API](../api/adapters.md)

-   :material-rocket-launch:{ .lg .middle } **Production Deployment**

    ---

    Deploy custom adapters to production.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
