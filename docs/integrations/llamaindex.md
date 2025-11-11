# LlamaIndex Integration

Use Axon as a vector store backend for LlamaIndex RAG applications.

---

## Overview

Axon provides **native LlamaIndex integration** through `AxonLlamaIndexVectorStore`, enabling you to use Axon's multi-tier memory system as a vector store for LlamaIndex applications.

**Key Features:**
- ✓ LlamaIndex VectorStore compatible
- ✓ Multi-tier document storage
- ✓ Semantic search over indexed documents
- ✓ Policy-driven lifecycle management
- ✓ Automatic persistence
- ✓ Metadata support

---

## Installation

```bash
# Install LlamaIndex and Axon
pip install llama-index llama-index-core axon-sdk

# Or with all dependencies
pip install "axon-sdk[all]" llama-index
```

---

## Basic Usage

### Quick Start

```python
from llama_index.core import VectorStoreIndex, Document
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from axon.core.templates import DEVELOPMENT_CONFIG

# Create Axon vector store
vector_store = AxonLlamaIndexVectorStore(config=DEVELOPMENT_CONFIG)

# Create documents
documents = [
    Document(text="Axon is a memory SDK for Python"),
    Document(text="It supports multiple storage tiers"),
    Document(text="Axon integrates with LangChain and LlamaIndex")
]

# Build index
index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is Axon?")
print(response)
```

---

## Configuration

### Using Templates

```python
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from axon.core.templates import (
    DEVELOPMENT_CONFIG,
    STANDARD_CONFIG,
    PRODUCTION_CONFIG
)

# Development (in-memory)
vector_store = AxonLlamaIndexVectorStore(config=DEVELOPMENT_CONFIG)

# Standard (Redis + ChromaDB)
vector_store = AxonLlamaIndexVectorStore(config=STANDARD_CONFIG)

# Production (Redis + Qdrant)
vector_store = AxonLlamaIndexVectorStore(config=PRODUCTION_CONFIG)
```

### Custom Configuration

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

# Custom configuration
config = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        compaction_threshold=50000
    )
)

system = MemorySystem(config)
vector_store = AxonLlamaIndexVectorStore(
    system,
    tier="persistent",  # Explicit tier selection
    collection_name="my_documents"
)
```

---

## Features

### Document Indexing

```python
from llama_index.core import VectorStoreIndex, Document

# Create vector store
vector_store = AxonLlamaIndexVectorStore(config=config)

# Index documents
documents = [
    Document(
        text="Python is a programming language",
        metadata={"category": "programming", "importance": "high"}
    ),
    Document(
        text="Machine learning uses Python extensively",
        metadata={"category": "AI", "importance": "high"}
    ),
    Document(
        text="Python has a rich ecosystem",
        metadata={"category": "programming", "importance": "medium"}
    )
]

# Build index
index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)
```

### Semantic Search

```python
# Query the index
query_engine = index.as_query_engine(similarity_top_k=5)

response = query_engine.query("What is Python used for?")
print(f"Answer: {response}")
print(f"Source nodes: {len(response.source_nodes)}")

# Access source documents
for node in response.source_nodes:
    print(f"- {node.text[:100]}... (score: {node.score:.2f})")
```

### Metadata Filtering

```python
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

# Query with metadata filters
query_engine = index.as_query_engine(
    filters=MetadataFilters(
        filters=[
            MetadataFilter(key="category", value="AI"),
            MetadataFilter(key="importance", value="high")
        ]
    ),
    similarity_top_k=3
)

response = query_engine.query("Tell me about AI")
# Only returns documents matching filters
```

---

## Examples

### RAG Application

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from axon.core.templates import PRODUCTION_CONFIG

async def build_rag_system(document_path: str):
    """Build RAG system with Axon."""
    
    # Create vector store
    vector_store = AxonLlamaIndexVectorStore(
        config=PRODUCTION_CONFIG,
        collection_name="knowledge_base"
    )
    
    # Load documents
    documents = SimpleDirectoryReader(document_path).load_data()
    
    print(f"Loaded {len(documents)} documents")
    
    # Build index
    index = VectorStoreIndex.from_documents(
        documents,
        vector_store=vector_store,
        show_progress=True
    )
    
    # Create query engine
    query_engine = index.as_query_engine(
        similarity_top_k=5,
        response_mode="tree_summarize"
    )
    
    return query_engine

# Use the RAG system
query_engine = await build_rag_system("./docs")

response = query_engine.query("How do I install Axon?")
print(f"Answer: {response}")
```

### Multi-Collection System

```python
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

class DocumentManager:
    """Manage multiple document collections."""
    
    def __init__(self, config):
        self.config = config
        self.indexes = {}
    
    def create_collection(self, name: str) -> VectorStoreIndex:
        """Create a new document collection."""
        vector_store = AxonLlamaIndexVectorStore(
            config=self.config,
            collection_name=name
        )
        
        index = VectorStoreIndex([], vector_store=vector_store)
        self.indexes[name] = index
        return index
    
    def add_documents(self, collection: str, documents: list):
        """Add documents to collection."""
        index = self.indexes.get(collection)
        if not index:
            index = self.create_collection(collection)
        
        for doc in documents:
            index.insert(doc)
    
    def query(self, collection: str, query: str) -> str:
        """Query a collection."""
        index = self.indexes[collection]
        query_engine = index.as_query_engine()
        response = query_engine.query(query)
        return str(response)

# Usage
manager = DocumentManager(STANDARD_CONFIG)

# Create collections
manager.create_collection("technical_docs")
manager.create_collection("user_guides")

# Add documents
manager.add_documents("technical_docs", [
    Document(text="API documentation for memory system"),
    Document(text="Architecture overview")
])

manager.add_documents("user_guides", [
    Document(text="Getting started guide"),
    Document(text="Configuration tutorial")
])

# Query specific collections
tech_answer = manager.query("technical_docs", "How does the API work?")
user_answer = manager.query("user_guides", "How do I get started?")
```

### Incremental Updates

```python
from llama_index.core import VectorStoreIndex, Document
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

# Create index with vector store
vector_store = AxonLlamaIndexVectorStore(config=config)
index = VectorStoreIndex([], vector_store=vector_store)

# Add documents incrementally
new_doc = Document(
    text="New product feature released",
    metadata={"date": "2025-01-15", "type": "announcement"}
)

index.insert(new_doc)

# Update existing document
updated_doc = Document(
    text="Updated product information",
    id_="existing_doc_id",
    metadata={"date": "2025-01-16", "type": "update"}
)

index.update(updated_doc)

# Delete document
index.delete("old_doc_id")
```

---

## Advanced Features

### Custom Storage Context

```python
from llama_index.core import StorageContext, VectorStoreIndex

# Create storage context
vector_store = AxonLlamaIndexVectorStore(config=config)
storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

# Use with index
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)
```

### Hybrid Search

```python
# Combine semantic search with metadata filtering
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

query_engine = index.as_query_engine(
    similarity_top_k=10,  # Semantic search for 10 results
    filters=MetadataFilters(
        filters=[
            MetadataFilter(key="importance", value="high")
        ]
    )
)

# Returns top 10 semantically similar, high-importance documents
response = query_engine.query("Important information about Python")
```

---

## Integration with LangChain

Combine both integrations for powerful RAG chatbots:

```python
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from llama_index.core import VectorStoreIndex
from axon.integrations.langchain import AxonChatMemory
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore

# Setup document store (LlamaIndex)
vector_store = AxonLlamaIndexVectorStore(config=config)
index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

# Setup conversation memory (LangChain)
chat_memory = AxonChatMemory(
    config=config,
    session_id="user_123"
)

# Create retriever from LlamaIndex
retriever = index.as_retriever(similarity_top_k=5)

# Build conversational RAG chain
llm = ChatOpenAI(temperature=0)
chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=chat_memory
)

# Query with conversation context
result = chain({"question": "What is Axon?"})
print(result["answer"])

# Follow-up questions use conversation history
result = chain({"question": "How do I use it?"})
print(result["answer"])
```

---

## Best Practices

### 1. Use Collections for Organization

```python
# ✓ Good: Organized collections
tech_docs = AxonLlamaIndexVectorStore(
    config=config,
    collection_name="technical_docs"
)

user_guides = AxonLlamaIndexVectorStore(
    config=config,
    collection_name="user_guides"
)

# ✗ Bad: Everything in one collection
all_docs = AxonLlamaIndexVectorStore(config=config)
# Harder to manage and query
```

### 2. Set Appropriate Tier

```python
# ✓ Good: Persistent tier for documents
vector_store = AxonLlamaIndexVectorStore(
    config=config,
    tier="persistent"  # Documents need persistence
)

# ✗ Bad: Ephemeral tier
vector_store = AxonLlamaIndexVectorStore(
    config=config,
    tier="ephemeral"  # Documents lost on restart!
)
```

### 3. Use Metadata Effectively

```python
# ✓ Good: Rich metadata
Document(
    text="Content",
    metadata={
        "category": "technical",
        "importance": "high",
        "date": "2025-01-15",
        "author": "john",
        "version": "1.0"
    }
)

# ✗ Bad: No metadata
Document(text="Content")  # Harder to filter and organize
```

---

## Performance Tips

### Batch Indexing

```python
# Index documents in batches for better performance
batch_size = 100

for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]
    
    for doc in batch:
        index.insert(doc)
    
    print(f"Indexed {min(i + batch_size, len(documents))} / {len(documents)}")
```

### Optimize Query Parameters

```python
# Balance between quality and performance
query_engine = index.as_query_engine(
    similarity_top_k=5,  # Fewer results = faster
    response_mode="compact"  # Faster than "tree_summarize"
)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-chat:{ .lg .middle } **LangChain Integration**

    ---

    Combine with LangChain for chat.

    [:octicons-arrow-right-24: LangChain Guide](langchain.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Advanced vector store configuration.

    [:octicons-arrow-right-24: Configuration Guide](../getting-started/configuration.md)

-   :material-rocket-launch:{ .lg .middle } **Production**

    ---

    Deploy LlamaIndex apps with Axon.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
