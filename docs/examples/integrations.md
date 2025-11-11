# Integration Examples

Integrate Axon with popular frameworks: LangChain and LlamaIndex from `examples/04-integrations/`.

---

## Overview

These examples show how to integrate Axon with leading AI frameworks for enhanced memory capabilities.

**Examples Covered:**
- Embedder Integrations (2 examples)
- LangChain Integration (2 examples)
- LlamaIndex Integration (2 examples)

**What You'll Learn:**
- Custom embedder integration
- LangChain chat memory
- LangChain retriever
- LlamaIndex storage
- LlamaIndex RAG

**Prerequisites:**
- Completed basic examples
- `pip install langchain` (for LangChain)
- `pip install llama-index` (for LlamaIndex)
- OpenAI API key

**Location:** `examples/04-integrations/`

---

## Embedder Integrations

### 01_embedder_integrations.py

**Pre-built embedders** - Use popular embedding models.

**File:** `examples/04-integrations/01_embedder_integrations.py`

**What it demonstrates:**
- OpenAI embeddings
- Sentence Transformers
- Voyage AI embeddings
- HuggingFace embeddings
- Custom embedder creation

**OpenAI Embedder:**

```python
from axon.embedders import OpenAIEmbedder

embedder = OpenAIEmbedder(
    model="text-embedding-ada-002",
    api_key="your-api-key"
)

memory = MemorySystem(config, embedder=embedder)
```

**Sentence Transformers:**

```python
from axon.embedders import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder(
    model_name="all-MiniLM-L6-v2"  # Local, fast
)

memory = MemorySystem(config, embedder=embedder)
```

**Voyage AI:**

```python
from axon.embedders import VoyageEmbedder

embedder = VoyageEmbedder(
    api_key="your-voyage-key",
    model="voyage-01"
)

memory = MemorySystem(config, embedder=embedder)
```

---

### 02_custom_embedder.py

**Build custom embedder** - Integrate any embedding model.

**File:** `examples/04-integrations/02_custom_embedder.py`

**What it demonstrates:**
- Embedder interface
- Custom implementation
- Batch processing
- Caching strategies

**Custom embedder:**

```python
from axon.embedders.base import Embedder

class MyCustomEmbedder(Embedder):
    def __init__(self, model):
        self.model = model
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return self.model.encode(text).tolist()
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for batch."""
        return [await self.embed(text) for text in texts]
    
    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return 384

# Use custom embedder
embedder = MyCustomEmbedder(my_model)
memory = MemorySystem(config, embedder=embedder)
```

---

## LangChain Integration

### 01_langchain_memory.py

**LangChain chat memory** - Use Axon as LangChain memory backend.

**File:** `examples/04-integrations/langchain/01_langchain_memory.py`

**What it demonstrates:**
- AxonChatMemory wrapper
- Conversation history
- Multi-turn dialogue
- Context management
- LangChain chains

**Setup:**

```python
from axon.integrations.langchain import AxonChatMemory
from langchain.chains import ConversationChain
from langchain.llms import OpenAI

# Create Axon memory backend
memory = AxonChatMemory(
    config=config,
    user_id="user_123",
    session_id="chat_session"
)

# Use with LangChain
conversation = ConversationChain(
    llm=OpenAI(temperature=0),
    memory=memory
)

# Chat
response = conversation.predict(input="Hi, my name is Alice")
print(response)

response = conversation.predict(input="What's my name?")
print(response)  # "Your name is Alice"
```

**Features:**
- Automatic conversation history
- Multi-tier storage (recent in session, old in persistent)
- Semantic search for context
- Privacy-aware storage

---

### 02_langchain_retriever.py

**LangChain retriever** - Use Axon for retrieval-augmented generation.

**File:** `examples/04-integrations/langchain/02_langchain_retriever.py`

**What it demonstrates:**
- AxonRetriever wrapper
- Document storage
- Semantic retrieval
- RAG patterns
- LangChain retrievers

**Setup:**

```python
from axon.integrations.langchain import AxonRetriever
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

# Create retriever
retriever = AxonRetriever(
    memory=memory,
    search_kwargs={"k": 5}
)

# Use in RAG chain
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(temperature=0),
    retriever=retriever,
    chain_type="stuff"
)

# Store documents
await memory.store("Python is a programming language", importance=0.8)
await memory.store("JavaScript is used for web development", importance=0.8)

# Query
result = qa_chain.run("What is Python?")
print(result)
```

**Use cases:**
- Document Q&A
- Knowledge base search
- Context-aware responses
- Semantic search

---

## LlamaIndex Integration

### 01_llamaindex_storage.py

**LlamaIndex storage** - Use Axon as LlamaIndex vector store.

**File:** `examples/04-integrations/llamaindex/01_llamaindex_storage.py`

**What it demonstrates:**
- AxonLlamaIndexVectorStore wrapper
- Document indexing
- Query engine
- Storage context
- LlamaIndex patterns

**Setup:**

```python
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from llama_index import VectorStoreIndex, ServiceContext
from llama_index.schema import Document

# Create vector store
vector_store = AxonLlamaIndexVectorStore(
    memory=memory,
    tier="persistent"
)

# Create index
service_context = ServiceContext.from_defaults()
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    service_context=service_context
)

# Index documents
documents = [
    Document(text="Python is a programming language"),
    Document(text="JavaScript is used for web development")
]

for doc in documents:
    index.insert(doc)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is Python?")
print(response)
```

---

### 02_llamaindex_rag.py

**LlamaIndex RAG** - Build RAG systems with LlamaIndex and Axon.

**File:** `examples/04-integrations/llamaindex/02_llamaindex_rag.py`

**What it demonstrates:**
- Complete RAG pipeline
- Document ingestion
- Query processing
- Response generation
- Multi-tier storage

**RAG pipeline:**

```python
from axon.integrations.llamaindex import AxonLlamaIndexVectorStore
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext,
    set_global_service_context
)

# Setup
vector_store = AxonLlamaIndexVectorStore(memory=memory)
service_context = ServiceContext.from_defaults()
set_global_service_context(service_context)

# Load documents
documents = SimpleDirectoryReader("./data").load_data()

# Create index
index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# Query with RAG
query_engine = index.as_query_engine(
    similarity_top_k=5,
    streaming=True
)

response = query_engine.query("Summarize the main points")
print(response)
```

**Features:**
- Automatic chunking
- Semantic retrieval
- Multi-tier storage
- Streaming responses

---

## Embedding Providers

Axon supports multiple embedding providers:

### OpenAI

```python
from axon.embedders import OpenAIEmbedder

embedder = OpenAIEmbedder(
    model="text-embedding-ada-002",  # or text-embedding-3-small
    api_key="sk-..."
)
```

**Specs:**
- Dimensions: 1536
- Cost: $0.0001 per 1K tokens
- Speed: ~200ms per request

### Sentence Transformers (Local)

```python
from axon.embedders import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder(
    model_name="all-MiniLM-L6-v2"
)
```

**Specs:**
- Dimensions: 384
- Cost: Free (local)
- Speed: ~10ms per request (GPU), ~50ms (CPU)

### Voyage AI

```python
from axon.embedders import VoyageEmbedder

embedder = VoyageEmbedder(
    api_key="pa-...",
    model="voyage-01"
)
```

**Specs:**
- Dimensions: 1024
- Cost: $0.0001 per 1K tokens
- Speed: ~150ms per request

### HuggingFace

```python
from axon.embedders import HuggingFaceEmbedder

embedder = HuggingFaceEmbedder(
    model_name="sentence-transformers/all-mpnet-base-v2"
)
```

---

## Summary

Integration examples demonstrate:

**Embedders:**
- OpenAI embeddings
- Sentence Transformers (local)
- Voyage AI
- Custom embedders

**LangChain:**
- Chat memory backend
- Retriever for RAG
- Conversation chains
- Document Q&A

**LlamaIndex:**
- Vector store backend
- Document indexing
- Query engine
- RAG pipelines

**Run All Integration Examples:**

```bash
cd examples/04-integrations

# Embedders
python 01_embedder_integrations.py
python 02_custom_embedder.py

# LangChain
python langchain/01_langchain_memory.py
python langchain/02_langchain_retriever.py

# LlamaIndex
python llamaindex/01_llamaindex_storage.py
python llamaindex/02_llamaindex_rag.py
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-application:{ .lg .middle } **Real-World Examples**

    ---

    Complete applications and use cases.

    [:octicons-arrow-right-24: Real-World Examples](real-world.md)

-   :material-book-open-variant:{ .lg .middle } **Integration Docs**

    ---

    Detailed integration guides.

    [:octicons-arrow-right-24: LangChain Guide](../integrations/langchain.md)
    
    [:octicons-arrow-right-24: LlamaIndex Guide](../integrations/llamaindex.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation.

    [:octicons-arrow-right-24: API Reference](../api/memory-system.md)

</div>
