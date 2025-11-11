# Testing Guide

Comprehensive testing guide for Axon contributors. Learn how to write, run, and maintain tests.

---

## Overview

Axon uses **pytest** for testing with the following goals:

- **Coverage**: >90% on core modules
- **Speed**: Fast unit tests, slower integration tests
- **Reliability**: Deterministic and reproducible
- **Clarity**: Tests as documentation

---

## Test Organization

```
tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── test_memory_system.py
│   ├── test_router.py
│   ├── test_policies.py
│   └── ...
├── integration/           # Integration tests (slower, multi-component)
│   ├── test_multi_tier.py
│   ├── test_adapters.py
│   └── ...
└── conftest.py           # Shared fixtures
```

---

## Running Tests

### All Tests

```bash
pytest
```

### Unit Tests Only

```bash
pytest -m unit
```

### Integration Tests Only

```bash
pytest -m integration
```

### Specific Test File

```bash
pytest tests/unit/test_memory_system.py
```

### Specific Test Function

```bash
pytest tests/unit/test_memory_system.py::test_store
```

### With Coverage

```bash
pytest --cov=axon --cov-report=html
```

Open `htmlcov/index.html` to view coverage report.

### Verbose Output

```bash
pytest -vv
```

### Show Print Statements

```bash
pytest -s
```

### Stop on First Failure

```bash
pytest -x
```

---

## Writing Tests

### Unit Test Structure

```python
import pytest
from axon import MemorySystem
from axon.models import MemoryEntry, MemoryTier

@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_memory():
    """Test storing a memory entry."""
    # Arrange
    memory = MemorySystem()
    content = "Test memory content"
    
    # Act
    entry_id = await memory.store(content, tier=MemoryTier.PERSISTENT)
    
    # Assert
    assert entry_id is not None
    assert isinstance(entry_id, str)
    assert len(entry_id) > 0
```

### Test Naming

Follow the pattern: `test_<function>_<scenario>_<expected>`

**Good Examples:**
```python
test_store_valid_content_returns_id()
test_store_empty_content_raises_error()
test_recall_with_filter_returns_filtered_results()
test_forget_nonexistent_id_returns_false()
```

---

## Test Markers

### @pytest.mark.unit

For fast, isolated unit tests:

```python
@pytest.mark.unit
async def test_policy_evaluation():
    """Test policy evaluation logic."""
    policy = RetentionPolicy(days=30)
    entry = MemoryEntry(content="test")
    
    result = policy.evaluate(entry)
    assert result is True
```

### @pytest.mark.integration

For multi-component integration tests:

```python
@pytest.mark.integration
async def test_multi_tier_storage():
    """Test storing across multiple tiers."""
    config = MemoryConfig.balanced()
    memory = MemorySystem(config=config)
    
    # Store in different tiers
    id1 = await memory.store("ephemeral", tier=MemoryTier.EPHEMERAL)
    id2 = await memory.store("persistent", tier=MemoryTier.PERSISTENT)
    
    # Verify
    entry1 = await memory.get(id1)
    entry2 = await memory.get(id2)
    
    assert entry1.tier == MemoryTier.EPHEMERAL
    assert entry2.tier == MemoryTier.PERSISTENT
```

### @pytest.mark.slow

For tests taking >1 second:

```python
@pytest.mark.slow
@pytest.mark.integration
async def test_large_batch_processing():
    """Test processing 1000+ entries."""
    memory = MemorySystem()
    
    # Generate large dataset
    entries = [f"Entry {i}" for i in range(1000)]
    
    # Process
    ids = await memory.store_batch(entries)
    
    assert len(ids) == 1000
```

### @pytest.mark.asyncio

For async tests (automatically applied):

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async memory operation."""
    memory = MemorySystem()
    result = await memory.store("async test")
    assert result is not None
```

---

## Fixtures

### Basic Fixture

```python
import pytest
from axon import MemorySystem

@pytest.fixture
def memory_system():
    """Create a test memory system."""
    return MemorySystem()

def test_with_fixture(memory_system):
    """Use fixture in test."""
    assert memory_system is not None
```

### Async Fixture

```python
@pytest.fixture
async def populated_memory():
    """Create memory system with test data."""
    memory = MemorySystem()
    await memory.store("Test entry 1")
    await memory.store("Test entry 2")
    return memory

@pytest.mark.asyncio
async def test_with_populated_memory(populated_memory):
    """Test with pre-populated data."""
    results = await populated_memory.list()
    assert len(results) >= 2
```

### Scope

```python
@pytest.fixture(scope="session")
def config():
    """Session-scoped config (created once)."""
    return MemoryConfig.balanced()

@pytest.fixture(scope="function")
def memory():
    """Function-scoped memory (created per test)."""
    return MemorySystem()
```

### Cleanup

```python
@pytest.fixture
async def memory_with_cleanup():
    """Memory system with automatic cleanup."""
    memory = MemorySystem()
    
    yield memory
    
    # Cleanup after test
    await memory.clear_all()
```

---

## Mocking

### Mock External Services

```python
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock_embedder():
    """Test with mocked embedder."""
    mock_embedder = AsyncMock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
    
    memory = MemorySystem(embedder=mock_embedder)
    await memory.store("test")
    
    mock_embedder.embed.assert_called_once_with("test")
```

### Patch Module

```python
@patch('axon.adapters.redis_adapter.Redis')
def test_redis_adapter(mock_redis):
    """Test Redis adapter with mocked Redis."""
    mock_redis.return_value.get.return_value = '{"id": "123"}'
    
    adapter = RedisAdapter()
    result = adapter.get("123")
    
    assert result["id"] == "123"
```

---

## Parameterized Tests

### Multiple Inputs

```python
@pytest.mark.parametrize("content,expected", [
    ("short", True),
    ("a" * 1000, True),
    ("", False),
    (None, False),
])
def test_validate_content(content, expected):
    """Test content validation with various inputs."""
    result = validate_content(content)
    assert result == expected
```

### Multiple Tiers

```python
@pytest.mark.parametrize("tier", [
    MemoryTier.EPHEMERAL,
    MemoryTier.SESSION,
    MemoryTier.PERSISTENT,
])
@pytest.mark.asyncio
async def test_store_in_all_tiers(tier):
    """Test storing in each tier."""
    memory = MemorySystem()
    entry_id = await memory.store("test", tier=tier)
    
    entry = await memory.get(entry_id)
    assert entry.tier == tier
```

---

## Testing Exceptions

### Assert Raises

```python
@pytest.mark.asyncio
async def test_store_invalid_content():
    """Test that invalid content raises ValueError."""
    memory = MemorySystem()
    
    with pytest.raises(ValueError, match="Content cannot be empty"):
        await memory.store("")
```

### Multiple Exceptions

```python
@pytest.mark.parametrize("content,exception", [
    ("", ValueError),
    (None, TypeError),
    (123, TypeError),
])
def test_invalid_inputs(content, exception):
    """Test various invalid inputs."""
    with pytest.raises(exception):
        validate_content(content)
```

---

## Testing Async Code

### Basic Async Test

```python
@pytest.mark.asyncio
async def test_async_store():
    """Test async store operation."""
    memory = MemorySystem()
    entry_id = await memory.store("async content")
    assert entry_id is not None
```

### Multiple Async Calls

```python
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent memory operations."""
    memory = MemorySystem()
    
    # Run operations concurrently
    results = await asyncio.gather(
        memory.store("entry 1"),
        memory.store("entry 2"),
        memory.store("entry 3")
    )
    
    assert len(results) == 3
    assert all(r is not None for r in results)
```

---

## Coverage Requirements

### Target Coverage

- **Core Modules**: >90%
- **Adapters**: >80%
- **Utilities**: >70%

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=axon --cov-report=html

# View in browser
open htmlcov/index.html
```

### Coverage Configuration

In `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/axon"]
omit = ["*/tests/*", "*/conftest.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

---

## Best Practices

### 1. Test One Thing

```python
# ❌ Bad - tests multiple things
def test_memory_operations():
    memory = MemorySystem()
    id1 = memory.store("test")
    result = memory.get(id1)
    memory.forget(id1)
    # Too much in one test

# ✅ Good - focused tests
def test_store():
    memory = MemorySystem()
    entry_id = memory.store("test")
    assert entry_id is not None

def test_get():
    memory = MemorySystem()
    entry_id = memory.store("test")
    result = memory.get(entry_id)
    assert result.content == "test"
```

### 2. Use Descriptive Names

```python
# ❌ Bad
def test_1():
    pass

# ✅ Good
def test_store_valid_content_returns_uuid():
    pass
```

### 3. Arrange-Act-Assert

```python
def test_memory_recall():
    # Arrange - set up test data
    memory = MemorySystem()
    await memory.store("test content")
    
    # Act - perform operation
    results = await memory.search("test")
    
    # Assert - verify results
    assert len(results) > 0
    assert results[0].content == "test content"
```

### 4. Don't Repeat Yourself

```python
# ❌ Bad - repetitive setup
def test_store():
    config = MemoryConfig()
    registry = AdapterRegistry()
    memory = MemorySystem(config, registry)
    # ...

def test_recall():
    config = MemoryConfig()
    registry = AdapterRegistry()
    memory = MemorySystem(config, registry)
    # ...

# ✅ Good - use fixtures
@pytest.fixture
def memory():
    config = MemoryConfig()
    registry = AdapterRegistry()
    return MemorySystem(config, registry)

def test_store(memory):
    # ...

def test_recall(memory):
    # ...
```

---

## Continuous Testing

### Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/sh
pytest -x
```

---

## Troubleshooting

### Tests Pass Locally But Fail in CI

- Check Python version compatibility
- Verify all dependencies installed
- Look for timing issues in async tests
- Check for environment-specific behavior

### Flaky Tests

- Add retry logic for network calls
- Use fixtures for consistent state
- Avoid time-based assertions
- Mock external dependencies

### Slow Tests

- Use `@pytest.mark.slow` to skip in normal runs
- Mock expensive operations
- Use smaller datasets
- Parallelize with `pytest-xdist`

---

## See Also

- [Development Guide](development.md) - Setup and workflow
- [Code Style Guide](style.md) - Coding standards
- [pytest Documentation](https://docs.pytest.org/) - Official pytest docs
