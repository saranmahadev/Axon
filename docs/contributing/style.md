# Code Style Guide

Axon follows strict code quality standards to ensure maintainability, readability, and consistency.

---

## Overview

- **Formatter**: Black (100-character line length)
- **Linter**: Ruff (fast Python linter)
- **Type Checker**: mypy (strict mode)
- **Docstrings**: Google style
- **Import Order**: isort-compatible

---

## Code Formatting

### Black

Axon uses Black with 100-character line length.

**Configuration:**
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py39']
```

**Usage:**
```bash
# Format all files
black src/ tests/

# Check without modifying
black --check src/ tests/

# Show diff
black --diff src/ tests/
```

**Example:**
```python
# ✅ Good - Black formatted
def long_function_name(
    parameter_one: str,
    parameter_two: int,
    parameter_three: list[str],
) -> dict[str, Any]:
    """Properly formatted function."""
    return {
        "key1": parameter_one,
        "key2": parameter_two,
        "key3": parameter_three,
    }
```

---

## Linting

### Ruff

Fast Python linter replacing Flake8, isort, and more.

**Configuration:**
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]
```

**Usage:**
```bash
# Check all files
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Show all violations
ruff check --output-format=full src/
```

---

## Type Hints

### mypy

Strict type checking with mypy.

**Configuration:**
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Required Type Hints:**

```python
# ✅ Good - Full type hints
from typing import List, Dict, Optional

def process_entries(
    entries: List[MemoryEntry],
    filter: Optional[MemoryFilter] = None
) -> Dict[str, Any]:
    """Process memory entries."""
    result: Dict[str, Any] = {}
    return result

# ❌ Bad - Missing type hints
def process_entries(entries, filter=None):
    result = {}
    return result
```

**Usage:**
```bash
# Type check source code
mypy src/

# Check specific file
mypy src/axon/core/memory_system.py
```

---

## Naming Conventions

### Files

Use `snake_case` for file names:

```
✅ memory_system.py
✅ redis_adapter.py
✅ policy_engine.py

❌ MemorySystem.py
❌ RedisAdapter.py
❌ PolicyEngine.py
```

### Classes

Use `PascalCase` for class names:

```python
# ✅ Good
class MemorySystem:
    pass

class RedisAdapter:
    pass

class PolicyEngine:
    pass

# ❌ Bad
class memory_system:
    pass

class redisAdapter:
    pass
```

### Functions & Methods

Use `snake_case` for functions and methods:

```python
# ✅ Good
def store_memory():
    pass

def get_entry_by_id():
    pass

async def recall_memories():
    pass

# ❌ Bad
def storeMemory():
    pass

def GetEntryById():
    pass
```

### Variables

Use `snake_case` for variables:

```python
# ✅ Good
user_name = "John"
entry_count = 10
memory_tier = MemoryTier.PERSISTENT

# ❌ Bad
userName = "John"
entryCount = 10
MemoryTier = MemoryTier.PERSISTENT
```

### Constants

Use `UPPER_SNAKE_CASE` for constants:

```python
# ✅ Good
MAX_BATCH_SIZE = 1000
DEFAULT_TIMEOUT = 30
API_VERSION = "v1"

# ❌ Bad
max_batch_size = 1000
defaultTimeout = 30
apiVersion = "v1"
```

### Private Members

Use `_leading_underscore` for private:

```python
class MemorySystem:
    def __init__(self):
        # ✅ Good - private attributes
        self._adapter = None
        self._config = None
    
    def _internal_method(self):
        """Private method."""
        pass
    
    # ✅ Good - public interface
    def store(self, content: str):
        """Public method."""
        pass
```

---

## Docstrings

### Google Style

Axon uses Google-style docstrings.

**Module Docstring:**
```python
"""Memory system core implementation.

This module provides the main MemorySystem class which orchestrates
multi-tier memory storage, retrieval, and lifecycle management.
"""
```

**Class Docstring:**
```python
class MemorySystem:
    """Unified memory system for LLM applications.
    
    Provides multi-tier memory storage with automatic routing,
    policy-based lifecycle management, and semantic search.
    
    Attributes:
        config: Memory configuration
        embedder: Text embedding provider
        
    Example:
        ```python
        memory = MemorySystem()
        entry_id = await memory.store("Important note")
        results = await memory.search("note", k=5)
        ```
    """
```

**Function Docstring:**
```python
async def store(
    self,
    content: str,
    tier: MemoryTier | None = None,
    metadata: dict[str, Any] | None = None
) -> str:
    """Store a memory entry.
    
    Args:
        content: Text content to store
        tier: Target tier (auto-selected if None)
        metadata: Optional metadata dict
        
    Returns:
        Entry ID (UUID string)
        
    Raises:
        ValueError: If content is empty
        RuntimeError: If storage fails
        
    Example:
        ```python
        entry_id = await memory.store(
            "User prefers dark mode",
            tier=MemoryTier.PERSISTENT,
            metadata={"user_id": "user123"}
        )
        ```
    """
```

---

## Import Organization

### Import Order

1. Standard library
2. Third-party packages
3. Local imports

**Example:**
```python
# Standard library
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party
import pytest
from pydantic import BaseModel, Field

# Local
from axon.adapters import StorageAdapter
from axon.core.config import MemoryConfig
from axon.models.entry import MemoryEntry
```

### Absolute vs Relative

Use absolute imports:

```python
# ✅ Good - absolute
from axon.core.memory_system import MemorySystem
from axon.adapters.redis import RedisAdapter

# ❌ Bad - relative
from ..core.memory_system import MemorySystem
from .redis import RedisAdapter
```

---

## Code Organization

### File Structure

```python
"""Module docstring."""

# Imports
import asyncio
from typing import Any

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Classes
class MyClass:
    """Class docstring."""
    pass

# Functions
def my_function():
    """Function docstring."""
    pass

# Main execution
if __name__ == "__main__":
    main()
```

### Method Order in Classes

1. `__init__` and special methods
2. Class methods (`@classmethod`)
3. Static methods (`@staticmethod`)
4. Properties (`@property`)
5. Public methods
6. Private methods (`_method`)

**Example:**
```python
class MemorySystem:
    def __init__(self, config: MemoryConfig):
        """Initialize."""
        self.config = config
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MemorySystem(config={self.config})"
    
    @classmethod
    def from_config(cls, path: str):
        """Create from config file."""
        pass
    
    @staticmethod
    def validate_config(config: MemoryConfig):
        """Validate configuration."""
        pass
    
    @property
    def tier_count(self) -> int:
        """Number of configured tiers."""
        return len(self.config.tiers)
    
    async def store(self, content: str):
        """Public API method."""
        pass
    
    async def _store_to_tier(self, entry, tier):
        """Private helper method."""
        pass
```

---

## Error Handling

### Exception Style

```python
# ✅ Good - specific exceptions
if not content:
    raise ValueError("Content cannot be empty")

if not isinstance(tier, MemoryTier):
    raise TypeError(f"Expected MemoryTier, got {type(tier)}")

# ❌ Bad - generic exceptions
if not content:
    raise Exception("Invalid content")
```

### Try-Except

```python
# ✅ Good - specific exception handling
try:
    result = await adapter.store(entry)
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except TimeoutError as e:
    logger.warning(f"Operation timed out: {e}")
    return None

# ❌ Bad - bare except
try:
    result = await adapter.store(entry)
except:
    pass
```

---

## Comments

### When to Comment

```python
# ✅ Good - explains WHY
# Use exponential backoff to avoid overwhelming the API
await asyncio.sleep(2 ** retry_count)

# ✅ Good - explains complex logic
# Convert tier hierarchy to priority queue (ephemeral=1, session=2, persistent=3)
priority = {"ephemeral": 1, "session": 2, "persistent": 3}[tier]

# ❌ Bad - obvious comment
# Increment counter by 1
counter += 1

# ❌ Bad - outdated comment
# TODO: Implement caching (already implemented)
```

### Docstrings vs Comments

- **Docstrings**: Public API documentation
- **Comments**: Implementation details

```python
def complex_algorithm(data: list[int]) -> int:
    """Calculate optimized score.
    
    Args:
        data: List of integers
        
    Returns:
        Optimized score value
    """
    # Use binary search for efficiency (O(log n) instead of O(n))
    result = binary_search(data)
    return result
```

---

## Best Practices

### 1. Single Responsibility

```python
# ✅ Good - single responsibility
def validate_content(content: str) -> bool:
    """Validate content is non-empty."""
    return bool(content and content.strip())

def store_to_adapter(entry: MemoryEntry, adapter: StorageAdapter) -> str:
    """Store entry to adapter."""
    return adapter.store(entry)

# ❌ Bad - multiple responsibilities
def validate_and_store(content: str, adapter: StorageAdapter):
    """Validate and store content."""
    if not content:
        raise ValueError("Invalid")
    return adapter.store(content)
```

### 2. Explicit is Better Than Implicit

```python
# ✅ Good - explicit
from axon.models import MemoryTier

tier = MemoryTier.PERSISTENT

# ❌ Bad - implicit
import axon

tier = axon.models.MemoryTier.PERSISTENT
```

### 3. Avoid Magic Numbers

```python
# ✅ Good - named constants
MAX_BATCH_SIZE = 1000
DEFAULT_K = 10

if len(batch) > MAX_BATCH_SIZE:
    raise ValueError(f"Batch too large: {len(batch)} > {MAX_BATCH_SIZE}")

# ❌ Bad - magic numbers
if len(batch) > 1000:
    raise ValueError("Batch too large")
```

### 4. Use Type Aliases

```python
# ✅ Good - readable type aliases
from typing import TypeAlias

EntryID: TypeAlias = str
Metadata: TypeAlias = dict[str, Any]
Embeddings: TypeAlias = list[float]

def store(content: str, metadata: Metadata) -> EntryID:
    pass

# ❌ Bad - complex inline types
def store(content: str, metadata: dict[str, Any]) -> str:
    pass
```

---

## Pre-commit Checklist

Before committing code:

- [ ] Run `black src/ tests/`
- [ ] Run `ruff check --fix src/ tests/`
- [ ] Run `mypy src/`
- [ ] Run tests: `pytest`
- [ ] Update docstrings if needed
- [ ] Check line length (<100 chars)
- [ ] Add type hints to new code
- [ ] Remove debug statements

---

## Tools Setup

### Editor Integration

**VS Code** (`settings.json`):
```json
{
    "python.formatting.provider": "black",
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [100]
}
```

**PyCharm**:
- Install Black plugin
- Configure Ruff as external tool
- Enable mypy inspection

---

## See Also

- [Development Guide](development.md) - Setup and workflow
- [Testing Guide](testing.md) - Writing tests
- [PEP 8](https://peps.python.org/pep-0008/) - Python style guide
- [Black Documentation](https://black.readthedocs.io/) - Code formatter
- [Ruff Documentation](https://docs.astral.sh/ruff/) - Linter
- [mypy Documentation](https://mypy.readthedocs.io/) - Type checker
