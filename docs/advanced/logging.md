# Structured Logging

Production-grade structured logging for observability and debugging.

---

## Overview

Axon provides **high-standard structured logging** with JSON formatting, correlation ID tracking, performance metrics, and context-aware logging for production observability and debugging.

**Key Features:**
- ✓ Structured JSON logs (machine-readable)
- ✓ Correlation ID tracking (distributed tracing)
- ✓ Performance metrics integration
- ✓ Context-aware logging (user_id, session_id)
- ✓ Configurable log levels
- ✓ Async-safe operation

---

## Why Structured Logging?

### Traditional Logging

```python
# ❌ Hard to parse, no structure
logger.info("User user_123 stored entry entry_456 in 42.5ms")

# Parsing requires regex, brittle
```

### Structured Logging

```python
# ✓ Machine-readable JSON
logger.info("Entry stored", extra={
    "user_id": "user_123",
    "entry_id": "entry_456",
    "latency_ms": 42.5,
    "operation": "store"
})

# Output:
{
    "timestamp": "2025-11-08T10:30:45.123Z",
    "level": "INFO",
    "message": "Entry stored",
    "user_id": "user_123",
    "entry_id": "entry_456",
    "latency_ms": 42.5,
    "operation": "store"
}
```

---

## Basic Usage

### Enable Structured Logging

```python
from axon.core.logging_config import configure_logging, get_logger

# Configure structured logging
configure_logging(
    level="INFO",
    structured=True,  # Enable JSON formatting
    output_file="axon.log"
)

# Get logger
logger = get_logger(__name__)

# Log with context
logger.info("Operation completed", extra={
    "user_id": "user_123",
    "duration_ms": 42.5
})
```

### Environment Variables

```bash
# Configure via environment
export AXON_LOG_LEVEL=INFO
export AXON_STRUCTURED_LOGGING=true
export AXON_LOG_FILE=axon.log
```

---

## Correlation IDs

Track requests across distributed systems:

```python
from axon.core.logging_config import set_correlation_id, get_correlation_id

# Set correlation ID (per request)
set_correlation_id("req-abc123")

# All logs automatically include correlation_id
logger.info("Processing request")
# Output: {"correlation_id": "req-abc123", "message": "Processing request", ...}

# Get current correlation ID
correlation_id = get_correlation_id()
```

### In Web Applications

```python
from fastapi import FastAPI, Request
from axon.core.logging_config import set_correlation_id
import uuid

app = FastAPI()

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    # Generate or extract correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Set for logging
    set_correlation_id(correlation_id)
    
    # Process request
    response = await call_next(request)
    
    # Include in response
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.get("/store")
async def store_memory(text: str):
    # All logs in this request have same correlation_id
    logger.info("Storing memory", extra={"text_length": len(text)})
    await memory.store(text)
    return {"status": "success"}
```

---

## Log Levels

### Available Levels

```python
import logging

# Standard levels
logging.DEBUG     # Detailed information for debugging
logging.INFO      # General informational messages
logging.WARNING   # Warning messages
logging.ERROR     # Error messages
logging.CRITICAL  # Critical errors
```

### Configure Level

```python
from axon.core.logging_config import configure_logging

# Configure log level
configure_logging(level="INFO")  # Only INFO and above

# Or via environment
# AXON_LOG_LEVEL=DEBUG
```

### Per-Module Levels

```python
import logging

# Set specific module to DEBUG
logging.getLogger("axon.core.memory_system").setLevel(logging.DEBUG)

# Set adapter to WARNING only
logging.getLogger("axon.adapters.redis").setLevel(logging.WARNING)
```

---

## Context Logging

### User Context

```python
from axon import MemorySystem

memory = MemorySystem(config)

# Operations automatically log user context
await memory.store(
    "Important data",
    user_id="user_123",      # Logged
    session_id="session_abc"  # Logged
)

# Log output includes user context:
{
    "message": "Entry stored",
    "user_id": "user_123",
    "session_id": "session_abc",
    "entry_id": "entry_456"
}
```

### Custom Context

```python
# Add custom context to any log
logger.info("Custom operation", extra={
    "tenant_id": "tenant_123",
    "environment": "production",
    "version": "1.0.0"
})
```

---

## Performance Logging

### Automatic Timing

```python
from axon.core.logging_config import log_performance

@log_performance
async def expensive_operation():
    """Automatically logs duration."""
    # ... operation code ...
    pass

# Output:
{
    "message": "expensive_operation completed",
    "duration_ms": 125.5,
    "function": "expensive_operation"
}
```

### Manual Timing

```python
import time

start = time.time()

# Your operation
await memory.store("data")

duration_ms = (time.time() - start) * 1000

logger.info("Store completed", extra={
    "operation": "store",
    "duration_ms": duration_ms
})
```

---

## JSON Log Format

### Output Structure

```json
{
  "timestamp": "2025-11-08T10:30:45.123456Z",
  "level": "INFO",
  "logger": "axon.core.memory_system",
  "message": "Entry stored successfully",
  "correlation_id": "req-abc123",
  "user_id": "user_123",
  "session_id": "session_abc",
  "entry_id": "entry_456",
  "tier": "persistent",
  "duration_ms": 42.5,
  "metadata": {
    "importance": 0.8,
    "tags": ["verified"]
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When log was created |
| `level` | string | Log level (INFO, ERROR, etc.) |
| `logger` | string | Logger name (module path) |
| `message` | string | Human-readable message |
| `correlation_id` | string | Request correlation ID |
| `user_id` | string | User identifier (optional) |
| `session_id` | string | Session identifier (optional) |
| `duration_ms` | float | Operation duration (optional) |
| `*` | any | Custom fields from `extra` |

---

## Log Aggregation

### Sending to Logging Services

#### Datadog

```python
from axon.core.logging_config import configure_logging
import logging
from datadog import initialize, statsd

# Configure Datadog
initialize(api_key="your-api-key")

# Configure Axon logging
configure_logging(
    level="INFO",
    structured=True,
    output_file="/var/log/axon.log"
)

# Logs are written to file, collected by Datadog agent
```

#### ELK Stack (Elasticsearch, Logstash, Kibana)

```python
# Configure logging to output JSON
configure_logging(
    level="INFO",
    structured=True,
    output_file="/var/log/axon.log"
)

# Logstash configuration (logstash.conf):
# input {
#   file {
#     path => "/var/log/axon.log"
#     codec => json
#   }
# }
# 
# output {
#   elasticsearch {
#     hosts => ["localhost:9200"]
#     index => "axon-logs-%{+YYYY.MM.dd}"
#   }
# }
```

#### CloudWatch

```python
import boto3
import watchtower

# Configure CloudWatch handler
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group="axon-logs",
    stream_name="production"
)

# Add to logger
logger = get_logger(__name__)
logger.addHandler(cloudwatch_handler)
```

---

## Examples

### Request Logging

```python
from axon.core.logging_config import set_correlation_id, get_logger

logger = get_logger(__name__)

async def handle_request(request_id: str, user_id: str, query: str):
    """Handle user request with full logging."""
    
    # Set correlation ID
    set_correlation_id(request_id)
    
    # Log request start
    logger.info("Request started", extra={
        "user_id": user_id,
        "query": query,
        "request_id": request_id
    })
    
    start_time = time.time()
    
    try:
        # Process request
        results = await memory.recall(query, user_id=user_id)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log success
        logger.info("Request completed", extra={
            "user_id": user_id,
            "results_count": len(results),
            "duration_ms": duration_ms,
            "status": "success"
        })
        
        return results
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log error
        logger.error("Request failed", extra={
            "user_id": user_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": duration_ms,
            "status": "error"
        }, exc_info=True)
        
        raise
```

### Error Tracking

```python
try:
    await memory.store("data", tier="persistent")
except Exception as e:
    logger.error("Store failed", extra={
        "error_type": type(e).__name__,
        "error_message": str(e),
        "tier": "persistent",
        "operation": "store"
    }, exc_info=True)  # Include stack trace
    
    # Optional: Send to error tracking service
    # sentry_sdk.capture_exception(e)
```

### Audit Trail

```python
# Log all operations for audit
@log_operation
async def store_with_audit(memory, text: str, user_id: str):
    logger.info("Store operation initiated", extra={
        "user_id": user_id,
        "operation": "store",
        "text_length": len(text)
    })
    
    entry_id = await memory.store(text, user_id=user_id)
    
    logger.info("Store operation completed", extra={
        "user_id": user_id,
        "operation": "store",
        "entry_id": entry_id,
        "status": "success"
    })
    
    return entry_id
```

---

## Best Practices

### 1. Use Structured Fields

```python
# ✓ Good: Structured fields
logger.info("User action", extra={
    "user_id": "user_123",
    "action": "store",
    "result": "success"
})

# ✗ Bad: String interpolation
logger.info(f"User user_123 performed store with result success")
```

### 2. Include Context

```python
# ✓ Good: Rich context
logger.info("Query executed", extra={
    "user_id": user_id,
    "query": query,
    "results_count": len(results),
    "duration_ms": duration,
    "tier": "persistent"
})

# ✗ Bad: Minimal context
logger.info("Query executed")
```

### 3. Log at Appropriate Levels

```python
# DEBUG: Detailed information for debugging
logger.debug("Entry details", extra={"entry": entry.dict()})

# INFO: General operational messages
logger.info("Store completed", extra={"entry_id": entry_id})

# WARNING: Unexpected but handled situations
logger.warning("Slow query detected", extra={"duration_ms": 5000})

# ERROR: Error conditions
logger.error("Store failed", extra={"error": str(e)})

# CRITICAL: System-threatening issues
logger.critical("Database connection lost")
```

### 4. Use Correlation IDs

```python
# Always set correlation ID for requests
set_correlation_id(request.id)

# All subsequent logs are correlated
# Makes debugging distributed systems much easier
```

---

## Performance

### Overhead

- **Structured logging:** ~0.1-0.5ms per log
- **JSON serialization:** ~0.1ms per log
- **File I/O:** Asynchronous, minimal blocking

### Optimization

```python
# 1. Use appropriate log levels in production
configure_logging(level="INFO")  # Not DEBUG

# 2. Sample high-frequency logs
if random.random() < 0.01:  # 1% sample
    logger.debug("High-frequency event")

# 3. Lazy evaluation for expensive operations
logger.debug("Expensive data: %s", lambda: expensive_function())
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-monitor:{ .lg .middle } **Monitoring**

    ---

    Set up production monitoring.

    [:octicons-arrow-right-24: Monitoring Guide](../deployment/monitoring.md)

-   :material-clipboard-text:{ .lg .middle } **Audit Logging**

    ---

    Combine with audit trail.

    [:octicons-arrow-right-24: Audit Guide](audit.md)

-   :material-rocket-launch:{ .lg .middle } **Production Deployment**

    ---

    Deploy with logging enabled.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
