"""
Structured Logging Example

This example demonstrates Axon's high-standard structured logging capabilities:
- JSON-formatted logs for machine readability
- Correlation ID tracking for distributed tracing
- Performance metrics logging
- Configurable log levels via environment variables
- Context-aware logging with user_id, session_id, etc.

Features demonstrated:
- Basic structured logging
- Correlation ID propagation
- Performance metric decorators
- Custom log context
- Error logging with full context
- Environment variable configuration

Run: python examples/23_structured_logging.py
"""

import asyncio
import os

from axon.core import MemorySystem
from axon.core.logging_config import (
    get_logger,
    log_performance,
    set_correlation_id,
    setup_structured_logging,
)
from axon.core.templates import DEVELOPMENT_CONFIG

# Enable structured JSON logging
os.environ["AXON_STRUCTURED_LOGGING"] = "true"
os.environ["AXON_LOG_LEVEL"] = "INFO"


async def basic_logging_demo():
    """Demonstrate basic structured logging."""
    print("=" * 80)
    print("BASIC STRUCTURED LOGGING")
    print("=" * 80)
    print()

    # Get logger for this module
    logger = get_logger(__name__)

    # Simple log message
    logger.info("This is a simple log message")
    print()

    # Log with extra context
    logger.info(
        "Processing user request",
        extra={
            "user_id": "user_123",
            "session_id": "session_abc",
            "operation": "store",
        },
    )
    print()

    # Log at different levels
    logger.debug("Debug information")
    logger.info("Informational message")
    logger.warning("Warning message")
    print()


async def correlation_id_demo():
    """Demonstrate correlation ID tracking."""
    print("=" * 80)
    print("CORRELATION ID TRACKING")
    print("=" * 80)
    print()

    logger = get_logger(__name__)

    # Set correlation ID for this request
    request_id = "req-20251108-001"
    set_correlation_id(request_id)

    logger.info("Request started", extra={"endpoint": "/api/memory/store"})
    logger.info("Validating input", extra={"validation_step": 1})
    logger.info("Storing memory", extra={"validation_step": 2})
    logger.info("Request completed", extra={"status_code": 200})

    # Correlation ID is automatically included in all logs
    print("\nAll logs above include correlation_id:", request_id)
    print()


async def performance_metrics_demo():
    """Demonstrate performance metrics logging."""
    print("=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)
    print()

    logger = get_logger(__name__)

    # Log metrics manually
    logger.log_metric("query_latency", 45.2, unit="ms", operation="recall", tier="persistent")
    logger.log_metric("throughput", 1250, unit="ops/sec", operation="batch_store")
    logger.log_metric("cache_hit_rate", 0.85, unit="", cache_type="embeddings")

    print("\nMetrics logged with structured format")
    print()


async def performance_decorator_demo():
    """Demonstrate automatic performance tracking with decorator."""
    print("=" * 80)
    print("PERFORMANCE DECORATOR")
    print("=" * 80)
    print()

    @log_performance("store_operation")
    async def store_memory(content: str) -> str:
        """Simulated store operation."""
        await asyncio.sleep(0.05)  # Simulate work
        return f"entry_{hash(content)}"

    # Call function - performance is automatically logged
    entry_id = await store_memory("Important information")
    print(f"Stored entry: {entry_id}")
    print("\nPerformance metrics logged automatically (latency_ms, status)")
    print()


async def error_logging_demo():
    """Demonstrate error logging with full context."""
    print("=" * 80)
    print("ERROR LOGGING")
    print("=" * 80)
    print()

    logger = get_logger(__name__)

    try:
        # Simulate an error
        raise ValueError("Invalid memory content: empty string not allowed")
    except Exception as e:
        logger.log_error(
            e,
            operation="store",
            user_id="user_456",
            session_id="session_xyz",
            tier="persistent",
        )

    print("\nError logged with full context and stack trace")
    print()


async def memory_system_integration_demo():
    """Demonstrate logging integration with MemorySystem."""
    print("=" * 80)
    print("MEMORY SYSTEM INTEGRATION")
    print("=" * 80)
    print()

    # Set correlation ID for this request
    set_correlation_id("req-memory-demo-001")

    logger = get_logger(__name__)
    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    # Operations are logged with context
    logger.info("Starting memory storage", extra={"operation": "store"})

    entry_id = await system.store(
        "User preferences: dark mode enabled",
        metadata={"user_id": "user_789", "session_id": "session_123"},
    )

    logger.info(
        "Memory stored successfully",
        extra={
            "operation": "store",
            "entry_id": entry_id,
            "user_id": "user_789",
        },
    )

    # Recall with logging
    logger.info("Starting memory recall", extra={"operation": "recall"})

    results = await system.recall("user preferences", k=5)

    logger.info(
        "Memory recalled successfully",
        extra={
            "operation": "recall",
            "result_count": len(results),
            "query": "user preferences",
        },
    )

    print(f"\nStored 1 entry, recalled {len(results)} entries")
    print("All operations logged with correlation_id")
    print()


async def custom_context_demo():
    """Demonstrate custom logging context."""
    print("=" * 80)
    print("CUSTOM LOGGING CONTEXT")
    print("=" * 80)
    print()

    logger = get_logger(__name__)

    # Rich context with custom fields
    logger.info(
        "Processing batch operation",
        extra={
            "user_id": "user_abc",
            "session_id": "session_xyz",
            "operation": "batch_store",
            "batch_size": 100,
            "tier": "persistent",
            "adapter": "chroma",
            "model": "text-embedding-3-small",
            "estimated_cost_usd": 0.002,
        },
    )

    print("\nLog includes all custom context fields in JSON")
    print()


async def log_level_configuration_demo():
    """Demonstrate log level configuration."""
    print("=" * 80)
    print("LOG LEVEL CONFIGURATION")
    print("=" * 80)
    print()

    # Reconfigure to DEBUG level
    setup_structured_logging(level="DEBUG")

    logger = get_logger(__name__)

    logger.debug("This debug message is now visible")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Reset to INFO
    setup_structured_logging(level="INFO")

    logger.debug("This debug message is hidden")
    logger.info("Info message is visible")

    print("\nLog levels can be configured via setup_structured_logging()")
    print("Or via AXON_LOG_LEVEL environment variable")
    print()


async def text_format_demo():
    """Demonstrate non-JSON text format for development."""
    print("=" * 80)
    print("TEXT FORMAT (DEVELOPMENT MODE)")
    print("=" * 80)
    print()

    # Switch to text format
    setup_structured_logging(enable_json=False)

    logger = get_logger(__name__)

    logger.info("This is in text format for easy reading during development")
    logger.info(
        "Context is still captured",
        extra={
            "user_id": "user_123",
            "operation": "store",
        },
    )

    # Switch back to JSON
    setup_structured_logging(enable_json=True)

    print("\nText format available via setup_structured_logging(enable_json=False)")
    print("Or AXON_STRUCTURED_LOGGING=false environment variable")
    print()


async def main():
    """Run all logging examples."""
    print("\n" + "=" * 80)
    print("AXON STRUCTURED LOGGING EXAMPLES")
    print("=" * 80)
    print()

    await basic_logging_demo()
    await correlation_id_demo()
    await performance_metrics_demo()
    await performance_decorator_demo()
    await error_logging_demo()
    await memory_system_integration_demo()
    await custom_context_demo()
    await log_level_configuration_demo()
    await text_format_demo()

    print("=" * 80)
    print("STRUCTURED LOGGING EXAMPLES COMPLETE")
    print("=" * 80)
    print()
    print("Key Features:")
    print("  [+] JSON-formatted logs for machine readability")
    print("  [+] Correlation ID tracking for distributed tracing")
    print("  [+] Performance metrics logging")
    print("  [+] Configurable log levels (DEBUG, INFO, WARNING, ERROR)")
    print("  [+] Context-aware logging with custom fields")
    print("  [+] Error logging with stack traces")
    print("  [+] Performance decorators for automatic tracking")
    print()
    print("Configuration:")
    print("  - AXON_STRUCTURED_LOGGING=true|false (default: true)")
    print("  - AXON_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR (default: INFO)")
    print()
    print("Usage:")
    print("  from axon.core.logging_config import get_logger, set_correlation_id")
    print("  logger = get_logger(__name__)")
    print("  set_correlation_id('req-123')")
    print("  logger.info('Message', extra={'user_id': 'user_456'})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
