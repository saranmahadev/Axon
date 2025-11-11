# Embedders API Reference

Embedders convert text into dense vector embeddings for semantic search and similarity matching.

---

## Overview

Axon supports multiple embedding providers:

- **OpenAI**: GPT embeddings (text-embedding-3-small, text-embedding-3-large)
- **Voyage AI**: Specialized embeddings for various domains
- **Sentence Transformers**: Local open-source models
- **HuggingFace**: Hundreds of pre-trained models
- **Custom**: Implement your own embedder

All embedders implement the `Embedder` interface for consistency.

---

## Base Embedder Interface

```python
from axon.embedders import Embedder
```

### Abstract Methods

All embedders must implement these methods:

#### embed()

Generate embedding for a single text.

```python
async def embed(text: str) -> list[float]
```

**Parameters:**

- `text` (`str`): Text to embed

**Returns:**

- `list[float]`: Embedding vector

**Example:**
```python
embedding = await embedder.embed("Hello world")
print(f"Dimension: {len(embedding)}")
```

---

#### embed_batch()

Generate embeddings for multiple texts efficiently.

```python
async def embed_batch(texts: list[str]) -> list[list[float]]
```

**Parameters:**

- `texts` (`list[str]`): List of texts to embed

**Returns:**

- `list[list[float]]`: List of embedding vectors

**Example:**
```python
texts = ["First text", "Second text", "Third text"]
embeddings = await embedder.embed_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

---

#### get_dimension()

Get the dimensionality of embeddings.

```python
def get_dimension() -> int
```

**Returns:**

- `int`: Embedding dimension

**Example:**
```python
dim = embedder.get_dimension()
print(f"Embedding dimension: {dim}")
```

---

#### model_name

Property returning the model identifier.

```python
@property
def model_name() -> str
```

**Returns:**

- `str`: Model name

---

## OpenAI Embedder

Use OpenAI's embedding models.

```python
from axon.embedders import OpenAIEmbedder
```

### Constructor

```python
def __init__(
    api_key: str | None = None,
    model: str = "text-embedding-3-small",
    cache_embeddings: bool = False
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | OpenAI API key (uses env var if None) |
| `model` | `str` | `"text-embedding-3-small"` | Model name |
| `cache_embeddings` | `bool` | `False` | Enable caching |

**Supported Models:**

| Model | Dimension | Cost (per 1M tokens) |
|-------|-----------|---------------------|
| `text-embedding-3-small` | 1536 | $0.02 |
| `text-embedding-3-large` | 3072 | $0.13 |
| `text-embedding-ada-002` | 1536 | $0.10 |

**Example:**
```python
import os
from axon.embedders import OpenAIEmbedder

# From environment variable
embedder = OpenAIEmbedder()

# Explicit API key
embedder = OpenAIEmbedder(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="text-embedding-3-large"
)

# Generate embeddings
embedding = await embedder.embed("Semantic search example")
```

---

## Voyage AI Embedder

Use Voyage AI's specialized embeddings.

```python
from axon.embedders import VoyageEmbedder
```

### Constructor

```python
def __init__(
    api_key: str | None = None,
    model: str = "voyage-2",
    cache_embeddings: bool = False
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | Voyage API key |
| `model` | `str` | `"voyage-2"` | Model name |
| `cache_embeddings` | `bool` | `False` | Enable caching |

**Supported Models:**

- `voyage-2`: General purpose (1024 dim)
- `voyage-code-2`: Code search (1536 dim)
- `voyage-large-2`: High performance (1536 dim)

**Example:**
```python
from axon.embedders import VoyageEmbedder

embedder = VoyageEmbedder(
    api_key=os.getenv("VOYAGE_API_KEY"),
    model="voyage-2"
)

embeddings = await embedder.embed_batch([
    "First document",
    "Second document"
])
```

---

## Sentence Transformer Embedder

Use local open-source models via sentence-transformers.

```python
from axon.embedders import SentenceTransformerEmbedder
```

### Constructor

```python
def __init__(
    model_name: str = "all-MiniLM-L6-v2",
    device: str | None = None,
    cache_embeddings: bool = False
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | `"all-MiniLM-L6-v2"` | Model identifier |
| `device` | `str \| None` | `None` | Device (cuda/cpu, auto-detected if None) |
| `cache_embeddings` | `bool` | `False` | Enable caching |

**Popular Models:**

| Model | Dimension | Speed | Quality |
|-------|-----------|-------|---------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good |
| `all-mpnet-base-v2` | 768 | Medium | Better |
| `multi-qa-mpnet-base-dot-v1` | 768 | Medium | Best for QA |

**Example:**
```python
from axon.embedders import SentenceTransformerEmbedder

# Fast, lightweight model
embedder = SentenceTransformerEmbedder(
    model_name="all-MiniLM-L6-v2",
    device="cuda"  # Use GPU
)

# High-quality model
embedder = SentenceTransformerEmbedder(
    model_name="all-mpnet-base-v2"
)

embedding = await embedder.embed("Local embedding generation")
```

---

## HuggingFace Embedder

Use any HuggingFace model for embeddings.

```python
from axon.embedders import HuggingFaceEmbedder
```

### Constructor

```python
def __init__(
    model_name: str,
    api_key: str | None = None,
    cache_embeddings: bool = False
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | `str` | HuggingFace model ID |
| `api_key` | `str \| None` | HF API token (optional) |
| `cache_embeddings` | `bool` | Enable caching |

**Example:**
```python
from axon.embedders import HuggingFaceEmbedder

embedder = HuggingFaceEmbedder(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    api_key=os.getenv("HF_TOKEN")
)

embedding = await embedder.embed("HuggingFace embeddings")
```

---

## Caching

Enable embedding caching to avoid regenerating embeddings for repeated text.

### EmbeddingCache

```python
from axon.embedders import EmbeddingCache
```

**Features:**

- **In-memory caching**: Fast lookup
- **LRU eviction**: Automatic cache management
- **Hash-based keys**: Efficient storage

**Example:**
```python
from axon.embedders import OpenAIEmbedder

# Enable caching
embedder = OpenAIEmbedder(cache_embeddings=True)

# First call - generates embedding
embedding1 = await embedder.embed("Repeated text")

# Second call - uses cache (much faster)
embedding2 = await embedder.embed("Repeated text")

assert embedding1 == embedding2  # Identical results
```

---

## Custom Embedder

Implement your own embedder:

```python
from axon.embedders import Embedder

class CustomEmbedder(Embedder):
    def __init__(self, model_path: str):
        self.model_path = model_path
        # Load your model...
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        # Your implementation
        return [0.1, 0.2, 0.3, ...]  # Return embedding vector
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding generation."""
        return [await self.embed(text) for text in texts]
    
    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return 384
    
    @property
    def model_name(self) -> str:
        """Return model name."""
        return "custom-embedder-v1"

# Use your custom embedder
embedder = CustomEmbedder("/path/to/model")
memory = MemorySystem(embedder=embedder)
```

---

## Synchronous Wrappers

All embedders provide sync wrappers:

```python
# Async (recommended)
embedding = await embedder.embed("text")

# Sync (for non-async contexts)
embedding = embedder.embed_sync("text")

# Batch sync
embeddings = embedder.embed_batch_sync(["text1", "text2"])
```

---

## Integration with MemorySystem

```python
from axon import MemorySystem
from axon.embedders import OpenAIEmbedder

# Configure embedder
embedder = OpenAIEmbedder(model="text-embedding-3-small")

# Pass to MemorySystem
memory = MemorySystem(
    config=config,
    embedder=embedder
)

# Embeddings generated automatically
await memory.store("This will be embedded automatically")

# Semantic search
results = await memory.search("similar to this", k=10)
```

---

## Performance Considerations

### Model Selection

| Priority | Recommended Model | Reason |
|----------|-------------------|--------|
| Speed | `all-MiniLM-L6-v2` | Fastest local model |
| Quality | `text-embedding-3-large` | Best semantic understanding |
| Cost | `all-MiniLM-L6-v2` | Free, local inference |
| Balance | `text-embedding-3-small` | Good quality, low cost |

### Batch Processing

Always use `embed_batch()` for multiple texts:

```python
# ❌ Inefficient
embeddings = [await embedder.embed(text) for text in texts]

# ✅ Efficient
embeddings = await embedder.embed_batch(texts)
```

### Caching

Enable caching for repeated embeddings:

```python
embedder = OpenAIEmbedder(cache_embeddings=True)
```

---

## Error Handling

```python
from axon.embedders import OpenAIEmbedder

embedder = OpenAIEmbedder()

try:
    embedding = await embedder.embed("text")
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Embedding generation failed: {e}")
```

---

## See Also

- [Memory System API](memory-system.md) - Using embedders with memory
- [Configuration API](config.md) - Configuring embedders
- [Storage Adapters](adapters.md) - Vector storage
- [Sentence Transformers Docs](https://www.sbert.net/) - Local models
