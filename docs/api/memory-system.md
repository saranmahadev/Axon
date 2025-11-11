# MemorySystem API

!!! note "Documentation Location"
    The MemorySystem API documentation has been reorganized. Please refer to the following sections:

- **[Configuration API](config.md)** - MemorySystem configuration and setup
- **[Models API](models.md)** - Data models and schemas
- **[Router API](router.md)** - Routing and tier management
- **[Adapters API](adapters.md)** - Storage adapter interfaces
- **[Policies API](policies.md)** - Policy configuration

---

## Quick Reference

### Import

```python
from axon import MemorySystem
from axon.models import MemoryTier, MemoryEntry
```

### Basic Usage

```python
# Initialize
memory = MemorySystem()

# Store memory
entry_id = await memory.store("Important information")

# Search memories
results = await memory.search("information", k=5)

# Get specific memory
entry = await memory.get(entry_id)

# Delete memory
await memory.forget(entry_id)
```

### Configuration

```python
from axon import MemorySystem, MemoryConfig

# Use pre-configured template
config = MemoryConfig.balanced()
memory = MemorySystem(config=config)

# Custom configuration
config = MemoryConfig(
    tiers=["ephemeral", "session", "persistent"],
    # ... other options
)
```

---

For detailed API documentation, see:

- **[Configuration API](config.md)** - Complete MemorySystem setup
- **[Getting Started Guide](../getting-started/quickstart.md)** - Tutorials
- **[Examples](../examples/basic.md)** - Working code examples
