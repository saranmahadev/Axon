# Installation

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows, macOS, Linux
- **Optional**: Docker (for running backend services like Redis, Qdrant)

---

## Installation Methods

### Using pip (Recommended)

=== "Basic Installation"

    Install Axon SDK with core dependencies:

    ```bash
    pip install axon-sdk
    ```

    This includes:

    - Core memory system (`MemorySystem`, `MemoryEntry`, etc.)
    - In-memory adapter (for development and testing)
    - OpenAI embedder support
    - NumPy for vector operations
    - Pydantic for data validation

=== "Full Installation"

    Install with all storage adapters and optional dependencies:

    ```bash
    pip install "axon-sdk[all]"
    ```

    This adds:

    - **Storage Adapters**: ChromaDB, Qdrant, Pinecone, Redis
    - All vector database clients
    - Additional backend dependencies

=== "Development Installation"

    Install with development tools (testing, linting, type checking):

    ```bash
    pip install "axon-sdk[dev]"
    ```

    This adds:

    - pytest, pytest-cov, pytest-asyncio (testing)
    - black (code formatting)
    - ruff (linting)
    - mypy (type checking)

### From Source

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/saranmahadev/Axon.git
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

## Additional Dependencies

### Storage Backends

Axon core includes the in-memory adapter by default. For production use, install additional storage backends:

| Backend | Install Command | Use Case |
|---------|----------------|----------|
| **Redis** | `pip install redis>=5.0.0` | Ephemeral/session caching with TTL support |
| **ChromaDB** | `pip install chromadb>=0.4.0` | Local vector storage, good for development |
| **Qdrant** | `pip install qdrant-client>=1.6.0` | Production-grade vector database |
| **Pinecone** | `pip install pinecone-client>=2.0.0` | Managed cloud vector database |

**Or install all at once:**
```bash
pip install "axon-sdk[all]"
```

### Embedders

OpenAI embedder is included with core dependencies. For other providers:

| Provider | Install Command | Models |
|----------|----------------|--------|
| **OpenAI** | Included by default | text-embedding-3-small, text-embedding-3-large, ada-002 |
| **Voyage AI** | `pip install voyageai` | voyage-2, voyage-code-2, voyage-law-2 |
| **HuggingFace** | `pip install transformers sentence-transformers` | Any HuggingFace embedding model |
| **Sentence Transformers** | `pip install sentence-transformers` | Local SBERT models |

### Integrations

| Framework | Install Command | Description |
|-----------|----------------|-------------|
| **LangChain** | `pip install langchain langchain-community` | Memory and retriever adapters |
| **LlamaIndex** | `pip install llama-index` | VectorStore integration |

---

## Verifying Installation

After installation, verify Axon is working:

```python
import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

async def verify_installation():
    """Verify Axon is installed and working."""
    # Create a memory system
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    
    # Store a test memory
    entry_id = await memory.store("Hello, Axon!")
    
    # Recall the memory
    results = await memory.recall("Axon", k=1)
    
    if results and results[0].text == "Hello, Axon!":
        print("✓ Axon installed successfully!")
        print(f"✓ Memory stored and recalled correctly")
        return True
    return False

# Run verification
asyncio.run(verify_installation())
```

Expected output:

```
✓ Axon installed successfully!
✓ Memory stored and recalled correctly
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

**Solution**: Install the required backend separately:

```bash
pip install chromadb>=0.4.0
```

Or install all backends at once:

```bash
pip install "axon-sdk[all]"
```

### Version Conflicts

**Problem**: Dependency conflicts with existing packages

**Solution**: Use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install axon-sdk
```

### Python Version

**Problem**: `requires python>=3.10`

**Solution**: Upgrade your Python version. Axon requires Python 3.10 or higher:

```bash
python --version  # Check your version
```

Download Python 3.10+ from [python.org](https://www.python.org/downloads/)

---

## Getting Help

- **Documentation**: [http://axon.saranmahadev.in](http://axon.saranmahadev.in)
- **GitHub Issues**: [Report a bug](https://github.com/saranmahadev/Axon/issues)
- **Discussions**: [Ask questions](https://github.com/saranmahadev/Axon/discussions)
- **PyPI Package**: [axon-sdk](https://pypi.org/project/axon-sdk/)
