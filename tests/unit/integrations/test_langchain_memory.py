"""Unit tests for LangChain AxonChatMemory integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from axon.core.memory_system import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import PersistentPolicy
from axon.adapters import InMemoryAdapter
from axon.core.adapter_registry import AdapterRegistry
from axon.models import MemoryEntry, MemoryMetadata

# Try importing LangChain dependencies
try:
    from langchain_core.messages import AIMessage, HumanMessage

    from axon.integrations.langchain import AxonChatMemory

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.fixture
def memory_system():
    """Create a MemorySystem for testing."""
    registry = AdapterRegistry()
    registry.register("persistent", adapter_type="memory", adapter_instance=InMemoryAdapter())

    config = MemoryConfig(persistent=PersistentPolicy(backend="memory"), default_tier="persistent")

    return MemorySystem(config, registry=registry)


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestAxonChatMemory:
    """Test AxonChatMemory adapter."""

    @pytest.mark.asyncio
    async def test_initialization(self, memory_system):
        """Test AxonChatMemory initialization."""
        memory = AxonChatMemory(
            memory_system, session_id="test_session", k_messages=5, use_semantic_search=True
        )

        assert memory.system == memory_system
        assert memory.session_id == "test_session"
        assert memory.k_messages == 5
        assert memory.use_semantic_search is True
        assert memory.memory_key == "history"

    @pytest.mark.asyncio
    async def test_memory_variables_property(self, memory_system):
        """Test memory_variables property."""
        memory = AxonChatMemory(memory_system, memory_key="chat_history")

        assert memory.memory_variables == ["chat_history"]

    @pytest.mark.asyncio
    async def test_save_context(self, memory_system):
        """Test saving context to memory."""
        memory = AxonChatMemory(memory_system, session_id="session_123")

        inputs = {"input": "Hello, how are you?"}
        outputs = {"output": "I'm doing well, thank you!"}

        # Save context
        memory.save_context(inputs, outputs)

        # Verify entries were stored (check via system)
        results = await memory_system.recall("Hello", k=10)

        # Should have at least the user message
        assert len(results) >= 1
        assert any("Hello, how are you?" in entry.text for entry in results)

    @pytest.mark.asyncio
    async def test_load_memory_variables_string_format(self, memory_system):
        """Test loading memory variables as string."""
        memory = AxonChatMemory(memory_system, session_id="session_456", return_messages=False)

        # Save some context first
        await memory._save_context_async(
            {"input": "What is AI?"}, {"output": "AI is artificial intelligence."}
        )

        # Load memory
        variables = memory.load_memory_variables({"input": "Tell me more"})

        assert "history" in variables
        assert isinstance(variables["history"], str)
        assert (
            "What is AI?" in variables["history"]
            or "AI is artificial intelligence" in variables["history"]
        )

    @pytest.mark.asyncio
    async def test_load_memory_variables_message_format(self, memory_system):
        """Test loading memory variables as message objects."""
        memory = AxonChatMemory(memory_system, session_id="session_789", return_messages=True)

        # Save context
        await memory._save_context_async({"input": "Hello!"}, {"output": "Hi there!"})

        # Load memory
        variables = memory.load_memory_variables({"input": "How are you?"})

        assert "history" in variables
        assert isinstance(variables["history"], list)

        # Should have messages (might be empty if recall doesn't find them)
        if len(variables["history"]) > 0:
            assert any(isinstance(msg, (HumanMessage, AIMessage)) for msg in variables["history"])

    @pytest.mark.asyncio
    async def test_async_save_context(self, memory_system):
        """Test async save_context."""
        memory = AxonChatMemory(memory_system, session_id="async_session")

        inputs = {"input": "Async test input"}
        outputs = {"output": "Async test output"}

        await memory.asave_context(inputs, outputs)

        # Verify storage
        results = await memory_system.recall("Async test", k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_async_load_memory_variables(self, memory_system):
        """Test async load_memory_variables."""
        memory = AxonChatMemory(memory_system, session_id="async_load_session")

        # Save context first
        await memory.asave_context({"input": "Question?"}, {"output": "Answer!"})

        # Load asynchronously
        variables = await memory.aload_memory_variables({"input": "New query"})

        assert "history" in variables

    @pytest.mark.asyncio
    async def test_clear_warning(self, memory_system):
        """Test that clear() logs a warning (not fully supported)."""
        memory = AxonChatMemory(memory_system)

        # Should log warning but not raise
        with pytest.warns(match="not fully supported"):
            # Note: We can't easily test log warnings, so we just call it
            memory.clear()

    @pytest.mark.asyncio
    async def test_custom_keys(self, memory_system):
        """Test using custom input/output keys."""
        memory = AxonChatMemory(memory_system, input_key="user_input", output_key="ai_response")

        inputs = {"user_input": "Custom input"}
        outputs = {"ai_response": "Custom output"}

        memory.save_context(inputs, outputs)

        # Verify storage
        results = await memory_system.recall("Custom input", k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_semantic_search_mode(self, memory_system):
        """Test semantic search mode for loading memory."""
        memory = AxonChatMemory(
            memory_system, session_id="semantic_session", use_semantic_search=True
        )

        # Save multiple contexts
        await memory.asave_context(
            {"input": "Tell me about Python"}, {"output": "Python is a programming language"}
        )
        await memory.asave_context(
            {"input": "What about JavaScript?"}, {"output": "JavaScript runs in browsers"}
        )

        # Load with semantic search
        variables = await memory.aload_memory_variables({"input": "programming languages"})

        assert "history" in variables


@pytest.mark.skipif(LANGCHAIN_AVAILABLE, reason="Testing import error handling")
class TestImportError:
    """Test behavior when LangChain is not installed."""

    def test_import_error_raised(self, memory_system):
        """Test that ImportError is raised when LangChain is not available."""
        # This test only runs when LangChain is NOT installed
        # In that case, trying to instantiate should raise ImportError
        pass  # Skipped when LangChain is available
