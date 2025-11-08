"""High-standard structured logging for Axon Memory SDK.

This module provides production-grade structured logging with:
- JSON formatting for machine-readable logs
- Correlation ID tracking for distributed tracing
- Performance metrics integration
- Configurable log levels via environment variables
- Context-aware logging (user_id, session_id, operation, etc.)

Example:
    >>> from axon.core.logging_config import get_logger, set_correlation_id
    >>>
    >>> logger = get_logger(__name__)
    >>> set_correlation_id("req-12345")
    >>>
    >>> logger.info("Processing request", extra={
    ...     "user_id": "user_123",
    ...     "operation": "store",
    ...     "latency_ms": 42.5
    ... })

    Output (JSON):
    {
        "timestamp": "2025-11-08T10:30:45.123Z",
        "level": "INFO",
        "logger": "axon.core.memory_system",
        "message": "Processing request",
        "correlation_id": "req-12345",
        "user_id": "user_123",
        "operation": "store",
        "latency_ms": 42.5
    }
"""

import json
import logging
import os
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

# Context variable for correlation ID (async-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Global flag for whether structured logging is enabled
_structured_logging_enabled = os.getenv("AXON_STRUCTURED_LOGGING", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Default log level from environment
_default_log_level = os.getenv("AXON_LOG_LEVEL", "INFO").upper()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Formats log records as JSON with:
    - ISO 8601 timestamp
    - Log level
    - Logger name
    - Message
    - Correlation ID (if set)
    - Extra context fields

    Example output:
        {
            "timestamp": "2025-11-08T10:30:45.123456Z",
            "level": "INFO",
            "logger": "axon.core.memory_system",
            "message": "Memory stored successfully",
            "correlation_id": "req-abc123",
            "user_id": "user_456",
            "entry_id": "entry_789",
            "latency_ms": 12.5
        }
    """

    # Reserved fields that should not be included in extra
    RESERVED_FIELDS = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
        "exc_info",
        "exc_text",
        "stack_info",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = _correlation_id.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data)


class StructuredLogger(logging.Logger):
    """Enhanced logger with structured logging support.

    Provides convenience methods for logging with context:
    - log_operation(): Log operations with automatic latency tracking
    - log_metric(): Log performance metrics
    - log_error(): Log errors with full context
    """

    def log_operation(
        self,
        operation: str,
        level: int = logging.INFO,
        **context: Any,
    ) -> None:
        """Log an operation with context.

        Args:
            operation: Operation name (e.g., "store", "recall")
            level: Log level (default: INFO)
            **context: Additional context fields

        Example:
            >>> logger.log_operation("store", user_id="user_123", entry_id="entry_456")
        """
        self.log(
            level,
            f"Operation: {operation}",
            extra={"operation": operation, **context},
        )

    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        **context: Any,
    ) -> None:
        """Log a performance metric.

        Args:
            metric_name: Metric name (e.g., "latency", "throughput")
            value: Metric value
            unit: Unit of measurement (e.g., "ms", "ops/sec")
            **context: Additional context fields

        Example:
            >>> logger.log_metric("latency", 42.5, unit="ms", operation="store")
        """
        self.info(
            f"Metric: {metric_name}={value}{unit}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                **context,
            },
        )

    def log_error(
        self,
        error: Exception,
        operation: Optional[str] = None,
        **context: Any,
    ) -> None:
        """Log an error with full context.

        Args:
            error: Exception that occurred
            operation: Operation that failed
            **context: Additional context fields

        Example:
            >>> try:
            ...     raise ValueError("Invalid input")
            ... except Exception as e:
            ...     logger.log_error(e, operation="store", user_id="user_123")
        """
        extra = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context,
        }
        if operation:
            extra["operation"] = operation

        self.error(
            f"Error in {operation or 'operation'}: {error}",
            exc_info=True,
            extra=extra,
        )


def setup_structured_logging(
    level: Optional[str] = None,
    enable_json: Optional[bool] = None,
) -> None:
    """Setup structured logging for Axon.

    Configures the root logger with JSON formatting and appropriate handlers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to AXON_LOG_LEVEL env var or INFO
        enable_json: Whether to use JSON formatting
                    Defaults to AXON_STRUCTURED_LOGGING env var or True

    Example:
        >>> setup_structured_logging(level="DEBUG", enable_json=True)
    """
    global _structured_logging_enabled

    # Determine log level
    log_level = level or _default_log_level
    level_value = getattr(logging, log_level, logging.INFO)

    # Determine whether to use JSON formatting
    if enable_json is not None:
        _structured_logging_enabled = enable_json

    # Set up custom logger class
    logging.setLoggerClass(StructuredLogger)

    # Configure root logger for axon namespace
    logger = logging.getLogger("axon")
    logger.setLevel(level_value)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level_value)

    # Set formatter based on configuration
    if _structured_logging_enabled:
        formatter = JSONFormatter()
    else:
        # Standard text formatter for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> StructuredLogger:
    """Get a logger instance with structured logging support.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"user_id": "user_123"})
    """
    # Ensure structured logging is set up
    if not logging.getLogger("axon").handlers:
        setup_structured_logging()

    return logging.getLogger(name)  # type: ignore


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current async context.

    The correlation ID will be automatically included in all log messages
    within the current async context (task).

    Args:
        correlation_id: Unique identifier for the request/operation

    Example:
        >>> set_correlation_id("req-abc-123")
        >>> logger.info("Processing")  # Will include correlation_id in JSON
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID for current async context.

    Returns:
        Correlation ID if set, None otherwise
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear correlation ID for current async context.

    Useful for cleanup or resetting context between operations.
    """
    _correlation_id.set(None)


# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


def log_performance(
    operation: str,
    logger: Optional[logging.Logger] = None,
) -> Callable[[F], F]:
    """Decorator to log operation performance metrics.

    Automatically tracks and logs:
    - Operation duration (latency_ms)
    - Success/failure status
    - Exception details (if any)

    Args:
        operation: Operation name
        logger: Logger to use (defaults to function's module logger)

    Returns:
        Decorated function

    Example:
        >>> @log_performance("store_memory")
        ... async def store(self, content: str) -> str:
        ...     # Store logic
        ...     return entry_id

        Logs (on success):
        {
            "operation": "store_memory",
            "latency_ms": 12.5,
            "status": "success"
        }

        Logs (on error):
        {
            "operation": "store_memory",
            "latency_ms": 8.2,
            "status": "error",
            "error_type": "ValueError",
            "error_message": "Invalid content"
        }
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get logger
            log = logger or get_logger(func.__module__)

            # Start timer
            start_time = time.perf_counter()

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                log.log_metric(
                    "latency",
                    round(duration_ms, 2),
                    unit="ms",
                    operation=operation,
                    status="success",
                )

                return result

            except Exception as e:
                # Log error
                duration_ms = (time.perf_counter() - start_time) * 1000
                log.log_error(
                    e,
                    operation=operation,
                    latency_ms=round(duration_ms, 2),
                    status="error",
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get logger
            log = logger or get_logger(func.__module__)

            # Start timer
            start_time = time.perf_counter()

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                log.log_metric(
                    "latency",
                    round(duration_ms, 2),
                    unit="ms",
                    operation=operation,
                    status="success",
                )

                return result

            except Exception as e:
                # Log error
                duration_ms = (time.perf_counter() - start_time) * 1000
                log.log_error(
                    e,
                    operation=operation,
                    latency_ms=round(duration_ms, 2),
                    status="error",
                )
                raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# Initialize structured logging on module import
setup_structured_logging()
