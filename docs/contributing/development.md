# Development Guide

Welcome to Axon development! This guide will help you set up your environment and understand the development workflow.

---

## Prerequisites

- **Python:** 3.9 or higher
- **Git:** For version control
- **pip:** Python package installer
- **Virtual Environment:** venv or conda

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/saranmahadev/AxonMemoryCore.git
cd AxonMemoryCore
```

### 2. Create Virtual Environment

=== "Windows"
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

=== "macOS/Linux"
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

### 3. Install Dependencies

```bash
# Install package in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black ruff mypy

# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]
```

---

## Development Workflow

### 1. Planning Phase

Before writing code:

- **Define objectives**: Clear success criteria
- **Break down tasks**: Manageable chunks
- **Identify dependencies**: What else needs to change?
- **Create plan**: Implementation strategy

### 2. Implementation Phase

Follow test-driven development (TDD):

1. **Write test** for new feature
2. **Run test** (should fail)
3. **Write code** to make test pass
4. **Refactor** if needed
5. **Commit** changes

**Example:**
```python
# 1. Write test first
def test_store_memory():
    memory = MemorySystem()
    entry_id = await memory.store("Test content")
    assert entry_id is not None

# 2. Implement feature
async def store(self, content: str) -> str:
    # Implementation here
    pass
```

### 3. Testing Phase

Run tests frequently:

```bash
# All tests
pytest

# With coverage
pytest --cov=axon --cov-report=html

# Specific test file
pytest tests/unit/test_memory_system.py
```

### 4. Review Phase

Before committing:

- [ ] All tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Type hints added
- [ ] No linting errors

### 5. Commit & Push

```bash
# Format code
black src/ tests/

# Run linter
ruff check src/ tests/

# Type check
mypy src/

# Commit
git add .
git commit -m "feat(core): add new feature"
git push origin feature-branch
```

---

## Project Structure

```
AxonMemoryCore/
├── src/axon/              # Source code
│   ├── core/              # Core memory system
│   ├── adapters/          # Storage adapters
│   ├── embedders/         # Embedding providers
│   ├── models/            # Data models
│   └── utils/             # Utilities
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
├── examples/              # Example code
└── pyproject.toml         # Project configuration
```

---

## Code Organization

### Core Modules

| Module | Purpose |
|--------|---------|
| `memory_system.py` | Main MemorySystem API |
| `router.py` | Tier routing logic |
| `policy_engine.py` | Policy evaluation |
| `adapter_registry.py` | Adapter management |

### Adding New Features

#### 1. New Adapter

```python
# src/axon/adapters/my_adapter.py
from axon.adapters.base import StorageAdapter

class MyAdapter(StorageAdapter):
    """Custom storage adapter."""
    
    async def store(self, entry: MemoryEntry) -> str:
        # Implementation
        pass
```

#### 2. New Embedder

```python
# src/axon/embedders/my_embedder.py
from axon.embedders.base import Embedder

class MyEmbedder(Embedder):
    """Custom embedder."""
    
    async def embed(self, text: str) -> list[float]:
        # Implementation
        pass
```

#### 3. New Policy

```python
# src/axon/core/policies/my_policy.py
from axon.core.policy import Policy

class MyPolicy(Policy):
    """Custom policy."""
    
    def evaluate(self, entry: MemoryEntry) -> bool:
        # Implementation
        pass
```

---

## Development Tools

### Code Formatting

Use Black with 100-character line length:

```bash
# Format all code
black src/ tests/ --line-length 100

# Check without modifying
black src/ tests/ --check
```

### Linting

Use Ruff for fast linting:

```bash
# Check all files
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/
```

### Type Checking

Use mypy in strict mode:

```bash
# Type check source code
mypy src/

# Type check with error codes
mypy src/ --show-error-codes
```

---

## Building Documentation

### Local Preview

```bash
# Serve docs locally
mkdocs serve

# Open http://127.0.0.1:8000
```

### Build Static Site

```bash
# Build to site/ directory
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

---

## Debugging

### Using pdb

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

### Pytest Debugging

```bash
# Drop into pdb on failure
pytest --pdb

# Show print statements
pytest -s

# Verbose output
pytest -vv
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Use logger
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

---

## Working with Git

### Branch Strategy

- **main** - Stable production code
- **feature/** - New features
- **fix/** - Bug fixes
- **docs/** - Documentation updates

### Creating Feature Branch

```bash
# Create and checkout
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "feat: add my feature"

# Push to remote
git push origin feature/my-feature
```

### Commit Messages

Follow conventional commits:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting
- `refactor` - Code restructuring
- `test` - Tests
- `chore` - Maintenance

**Examples:**
```
feat(adapters): add Qdrant batch operations
fix(router): handle empty tier list
docs(api): update router documentation
test(core): add memory system unit tests
```

---

## Performance Profiling

### Using cProfile

```bash
python -m cProfile -o output.prof script.py
python -m pstats output.prof
```

### Memory Profiling

```bash
pip install memory_profiler

# Add @profile decorator
python -m memory_profiler script.py
```

### Async Profiling

```python
import asyncio
import cProfile

async def main():
    # Your async code
    pass

cProfile.run('asyncio.run(main())')
```

---

## Continuous Integration

### GitHub Actions (Planned)

The project will use GitHub Actions for:

- **Test Suite**: Run on every PR
- **Code Quality**: Linting and type checking
- **Coverage**: Track test coverage
- **Documentation**: Build and deploy docs

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/saranmahadev/AxonMemoryCore/issues)
- **Discussions**: [GitHub Discussions](https://github.com/saranmahadev/AxonMemoryCore/discussions)
- **Documentation**: [Official Docs](http://axon.saranmahadev.in)

---

## Next Steps

- Read the [Testing Guide](testing.md)
- Review the [Code Style Guide](style.md)
- Check out [existing issues](https://github.com/saranmahadev/AxonMemoryCore/issues)
- Join the discussion!

---

**Happy coding! 🚀**
