"""Unit tests for structured logging system."""

import asyncio
import json
import logging
import os
from io import StringIO

import pytest

from axon.core.logging_config import (
    JSONFormatter,
    StructuredLogger,
    clear_correlation_id,
    get_correlation_id,
    get_logger,
    log_performance,
    set_correlation_id,
    setup_structured_logging,
)


@pytest.fixture
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear all handlers
    logger = logging.getLogger("axon")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

    # Clear correlation ID
    clear_correlation_id()

    yield

    # Cleanup
    logger.handlers.clear()
    clear_correlation_id()


@pytest.fixture
def log_capture(reset_logging):
    """Capture log output for testing."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())

    # Get fresh logger and configure it
    setup_structured_logging(level="DEBUG", enable_json=True)

    logger = logging.getLogger("axon")
    # Clear default handlers and add our capture handler
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield stream

    logger.handlers.clear()


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_basic_formatting(self, log_capture):
        """Test basic JSON log formatting."""
        logger = get_logger("axon.test")
        logger.info("Test message")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "axon.test"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data

    def test_formatting_with_extra_fields(self, log_capture):
        """Test JSON formatting with extra context fields."""
        logger = get_logger("axon.test")
        logger.info(
            "Test message",
            extra={
                "user_id": "user_123",
                "session_id": "session_abc",
                "operation": "store",
            },
        )

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["user_id"] == "user_123"
        assert log_data["session_id"] == "session_abc"
        assert log_data["operation"] == "store"

    def test_formatting_with_correlation_id(self, log_capture):
        """Test JSON formatting includes correlation ID."""
        set_correlation_id("req-123")

        logger = get_logger("axon.test")
        logger.info("Test message")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["correlation_id"] == "req-123"

    def test_formatting_with_exception(self, log_capture):
        """Test JSON formatting includes exception info."""
        logger = get_logger("axon.test")

        try:
            raise ValueError("Test error")
        except Exception:
            logger.error("Error occurred", exc_info=True)

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test error" in log_data["exception"]

    def test_reserved_fields_excluded(self, log_capture):
        """Test that reserved logging fields are not included."""
        logger = get_logger("axon.test")
        logger.info("Test message")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        # Reserved fields should not appear
        assert "name" not in log_data
        assert "msg" not in log_data
        assert "args" not in log_data
        assert "created" not in log_data
        assert "filename" not in log_data


class TestStructuredLogger:
    """Test StructuredLogger methods."""

    def test_log_operation(self, log_capture):
        """Test log_operation method."""
        logger = get_logger("axon.test")
        logger.log_operation("store", user_id="user_123", entry_id="entry_456")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["message"] == "Operation: store"
        assert log_data["operation"] == "store"
        assert log_data["user_id"] == "user_123"
        assert log_data["entry_id"] == "entry_456"

    def test_log_metric(self, log_capture):
        """Test log_metric method."""
        logger = get_logger("axon.test")
        logger.log_metric("latency", 42.5, unit="ms", operation="store")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["metric_name"] == "latency"
        assert log_data["metric_value"] == 42.5
        assert log_data["metric_unit"] == "ms"
        assert log_data["operation"] == "store"

    def test_log_error(self, log_capture):
        """Test log_error method."""
        logger = get_logger("axon.test")

        error = ValueError("Invalid input")
        logger.log_error(error, operation="store", user_id="user_123")

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["error_type"] == "ValueError"
        assert log_data["error_message"] == "Invalid input"
        assert log_data["operation"] == "store"
        assert log_data["user_id"] == "user_123"


class TestCorrelationID:
    """Test correlation ID functionality."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("req-abc-123")
        assert get_correlation_id() == "req-abc-123"

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("req-abc-123")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_correlation_id_in_async_context(self):
        """Test correlation ID works in async context."""

        async def task_with_correlation():
            set_correlation_id("req-async-123")
            await asyncio.sleep(0.01)
            return get_correlation_id()

        result = asyncio.run(task_with_correlation())
        assert result == "req-async-123"


class TestPerformanceDecorator:
    """Test performance logging decorator."""

    @pytest.mark.asyncio
    async def test_async_performance_decorator_success(self, log_capture):
        """Test performance decorator on async function (success case)."""
        logger = get_logger("axon.test")

        @log_performance("test_operation", logger=logger)
        async def test_function() -> str:
            await asyncio.sleep(0.01)
            return "success"

        result = await test_function()

        assert result == "success"

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["metric_name"] == "latency"
        assert log_data["operation"] == "test_operation"
        assert log_data["status"] == "success"
        assert log_data["metric_value"] > 0  # Should have some latency

    @pytest.mark.asyncio
    async def test_async_performance_decorator_error(self, log_capture):
        """Test performance decorator on async function (error case)."""
        logger = get_logger("axon.test")

        @log_performance("test_operation", logger=logger)
        async def test_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await test_function()

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["error_type"] == "ValueError"
        assert log_data["error_message"] == "Test error"
        assert log_data["operation"] == "test_operation"
        assert log_data["status"] == "error"
        assert log_data["latency_ms"] > 0

    def test_sync_performance_decorator_success(self, log_capture):
        """Test performance decorator on sync function (success case)."""
        logger = get_logger("axon.test")

        @log_performance("test_operation", logger=logger)
        def test_function() -> str:
            return "success"

        result = test_function()

        assert result == "success"

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["metric_name"] == "latency"
        assert log_data["operation"] == "test_operation"
        assert log_data["status"] == "success"

    def test_sync_performance_decorator_error(self, log_capture):
        """Test performance decorator on sync function (error case)."""
        logger = get_logger("axon.test")

        @log_performance("test_operation", logger=logger)
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function()

        output = log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["error_type"] == "ValueError"
        assert log_data["operation"] == "test_operation"
        assert log_data["status"] == "error"


class TestLoggerConfiguration:
    """Test logger configuration."""

    def test_setup_with_custom_level(self, reset_logging):
        """Test setup with custom log level."""
        setup_structured_logging(level="DEBUG")

        logger = logging.getLogger("axon")
        assert logger.level == logging.DEBUG

    def test_setup_with_json_enabled(self, reset_logging):
        """Test setup with JSON formatting enabled."""
        setup_structured_logging(enable_json=True)

        logger = logging.getLogger("axon")
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_setup_with_json_disabled(self, reset_logging):
        """Test setup with JSON formatting disabled."""
        setup_structured_logging(enable_json=False)

        logger = logging.getLogger("axon")
        assert len(logger.handlers) > 0
        assert not isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_get_logger_creates_structured_logger(self, reset_logging):
        """Test that get_logger returns StructuredLogger."""
        logger = get_logger("test")
        assert isinstance(logger, StructuredLogger)

    def test_logger_namespace(self, reset_logging):
        """Test that logger is in axon namespace."""
        logger = get_logger("axon.test.module")
        assert logger.name == "axon.test.module"


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_log_level_from_env(self, monkeypatch):
        """Test log level configuration from environment."""
        # Clear existing handlers first
        logger = logging.getLogger("axon")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

        # Set env var before setup
        monkeypatch.setenv("AXON_LOG_LEVEL", "DEBUG")

        # Re-import to pick up the environment variable
        import importlib
        import axon.core.logging_config

        importlib.reload(axon.core.logging_config)

        from axon.core.logging_config import setup_structured_logging

        setup_structured_logging()

        logger = logging.getLogger("axon")
        assert logger.level == logging.DEBUG

        # Cleanup
        logger.handlers.clear()

    def test_structured_logging_from_env(self, reset_logging, monkeypatch):
        """Test structured logging enable from environment."""
        monkeypatch.setenv("AXON_STRUCTURED_LOGGING", "false")

        from axon.core.logging_config import setup_structured_logging

        setup_structured_logging()

        logger = logging.getLogger("axon")
        assert not isinstance(logger.handlers[0].formatter, JSONFormatter)


class TestLogLevels:
    """Test different log levels."""

    def test_debug_level(self, log_capture):
        """Test DEBUG level logging."""
        logger = get_logger("axon.test")

        logger.debug("Debug message")

        output = log_capture.getvalue()
        assert "DEBUG" in output

    def test_info_level(self, log_capture):
        """Test INFO level logging."""
        logger = get_logger("axon.test")
        logger.info("Info message")

        output = log_capture.getvalue()
        assert "INFO" in output

    def test_warning_level(self, log_capture):
        """Test WARNING level logging."""
        logger = get_logger("axon.test")
        logger.warning("Warning message")

        output = log_capture.getvalue()
        assert "WARNING" in output

    def test_error_level(self, log_capture):
        """Test ERROR level logging."""
        logger = get_logger("axon.test")
        logger.error("Error message")

        output = log_capture.getvalue()
        assert "ERROR" in output

    def test_log_level_filtering(self, reset_logging):
        """Test that log level filtering works."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())

        setup_structured_logging(level="WARNING", enable_json=True)

        logger = logging.getLogger("axon")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

        test_logger = get_logger("axon.test")
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")

        output = stream.getvalue()

        # DEBUG and INFO should be filtered out
        assert "Debug message" not in output
        assert "Info message" not in output
        # WARNING should be present
        assert "Warning message" in output
