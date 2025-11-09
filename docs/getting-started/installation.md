# Installation

## Requirements

- **Python**: 3.9 or higher
- **Operating System**: Windows, macOS, Linux
- **Optional**: Docker (for running backend services like Redis, Qdrant)

---

## Installation Methods

### Using pip (Recommended)

=== "Minimal Installation"

    Install Axon with core dependencies only:

    ```bash
    pip install axon
    ```

    This includes:

    - Core memory system
    - In-memory adapter
    - Basic embedders

=== "Full Installation"

    Install with all storage adapters and embedders:

    ```bash
    pip install "axon[all]"
    ```

    This includes:

    - All core features
    - ChromaDB, Qdrant, Pinecone, Redis adapters
    - OpenAI, HuggingFace, Voyage AI embedders
    - LangChain and LlamaIndex integrations

=== "Custom Installation"

    Install only the adapters you need:

    ```bash
    # Install with specific adapters
    pip install "axon[chromadb,redis]"

    # Install with specific integrations
    pip install "axon[langchain,llamaindex]"

    # Combine multiple extras
    pip install "axon[qdrant,openai,langchain]"
    ```

### From Source

For development or the latest features:

```bash
# Clone the repository
git clone https://github.com/yourusername/Axon.git
cd Axon

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Optional Dependencies

### Storage Backends

| Backend | Install Command | Use Case |
|---------|----------------|----------|
| **Redis** | `pip install "axon[redis]"` | Ephemeral/session caching with TTL |
| **ChromaDB** | `pip install "axon[chromadb]"` | Local vector storage, development |
| **Qdrant** | `pip install "axon[qdrant]"` | Production vector database |
| **Pinecone** | `pip install "axon[pinecone]"` | Managed vector database |

### Embedders

| Provider | Install Command | Models |
|----------|----------------|--------|
| **OpenAI** | `pip install "axon[openai]"` | text-embedding-3-small/large |
| **Voyage AI** | `pip install "axon[voyageai]"` | voyage-2, voyage-code-2 |
| **HuggingFace** | `pip install "axon[huggingface]"` | Any HF embedding model |
| **Sentence Transformers** | `pip install "axon[sentence-transformers]"` | Local embeddings |

### Integrations

| Framework | Install Command | Description |
|-----------|----------------|-------------|
| **LangChain** | `pip install "axon[langchain]"` | Memory and VectorStore adapters |
| **LlamaIndex** | `pip install "axon[llamaindex]"` | VectorStore integration |

---

## Verifying Installation

After installation, verify Axon is working:

```python
import axon
print(f"Axon version: {axon.__version__}")

from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

# Create a simple memory system
system = MemorySystem(config=DEVELOPMENT_CONFIG)
print("Axon installed successfully!")
```

Expected output:

```
Axon version: 1.0.0-beta
Axon installed successfully!
```

---

## Environment Setup

### API Keys

If using cloud services, set up environment variables:

```bash
# OpenAI (for embeddings or LLM summarization)
export OPENAI_API_KEY="sk-..."

# Pinecone (for vector storage)
export PINECONE_API_KEY="..."
export PINECONE_ENVIRONMENT="us-east-1-aws"

# Voyage AI (for embeddings)
export VOYAGE_API_KEY="..."
```

### Configuration File

Create a `.env` file in your project root:

```bash
# .env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east-1-aws
VOYAGE_API_KEY=...

# Logging
AXON_LOG_LEVEL=INFO
AXON_STRUCTURED_LOGGING=true
```

Load environment variables in your code:

```python
from dotenv import load_dotenv
load_dotenv()

# Now Axon can access API keys
```

---

## Setting Up Storage Backends

### Redis (Local)

Using Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

Using Redis locally (Windows):

1. Download Redis for Windows
2. Run `redis-server`

### ChromaDB (Local)

No setup required - ChromaDB runs embedded:

```python
from axon.adapters import ChromaAdapter

adapter = ChromaAdapter(
    collection_name="my_collection",
    persist_directory="./chroma_db"  # Auto-created
)
```

### Qdrant (Local)

Using Docker:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
```

Or use Qdrant Cloud (managed).

### Pinecone (Cloud)

1. Sign up at [pinecone.io](https://www.pinecone.io/)
2. Create an index
3. Set environment variables (API key, environment)

---

## Next Steps

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Quick Start**

    ---

    Build your first memory-enabled app in 5 minutes.

    [:octicons-arrow-right-24: Quickstart](quickstart.md)

-   :fontawesome-solid-gear:{ .lg .middle } **Configuration**

    ---

    Learn how to configure Axon for your use case.

    [:octicons-arrow-right-24: Configuration](configuration.md)

</div>

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'chromadb'`

**Solution**: Install the required adapter:

```bash
pip install "axon[chromadb]"
```

### Version Conflicts

**Problem**: Dependency conflicts with existing packages

**Solution**: Use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install "axon[all]"
```

### Slow Imports

**Problem**: Importing Axon takes a long time

**Solution**: Axon uses lazy imports. Only install what you need:

```bash
# Instead of axon[all]
pip install "axon[chromadb,openai]"  # Only what you use
```

---

## Getting Help

- **Documentation**: [https://axon.readthedocs.io](https://axon.readthedocs.io)
- **GitHub Issues**: [Report a bug](https://github.com/yourusername/Axon/issues)
- **Discussions**: [Ask questions](https://github.com/yourusername/Axon/discussions)
