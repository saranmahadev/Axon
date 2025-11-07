"""
Unit tests for memory summarization functionality.

Tests cover:
- Summarizer ABC interface
- LLMSummarizer implementation
- Prompt building
- Error handling
- API integration
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from axon.core.summarizer import LLMSummarizer, Summarizer
from axon.models.entry import MemoryEntry, MemoryMetadata


class TestSummarizerInterface:
    """Test Summarizer abstract base class."""

    def test_cannot_instantiate_abc(self):
        """Test that Summarizer ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Summarizer()

    def test_summarizer_has_required_methods(self):
        """Test that Summarizer defines required abstract methods."""
        # Check that summarize is abstract
        assert hasattr(Summarizer, "summarize")
        assert hasattr(Summarizer, "__abstractmethods__")
        assert "summarize" in Summarizer.__abstractmethods__

    def test_sync_wrapper_exists(self):
        """Test that Summarizer provides sync wrapper."""
        assert hasattr(Summarizer, "summarize_sync")
        # Should be a concrete method, not abstract
        assert "summarize_sync" not in Summarizer.__abstractmethods__

    def test_llm_summarizer_implements_interface(self):
        """Test that LLMSummarizer implements Summarizer interface."""
        # This should not raise TypeError
        summarizer = LLMSummarizer(api_key="test-key")
        assert isinstance(summarizer, Summarizer)

        # Should have all required methods
        assert hasattr(summarizer, "summarize")
        assert hasattr(summarizer, "summarize_sync")

    def test_custom_implementation(self):
        """Test that custom implementations work correctly."""

        class SimpleSummarizer(Summarizer):
            async def summarize(self, entries, context=None, max_length=None):
                texts = [e.text for e in entries]
                return " | ".join(texts[:3])

        # Should instantiate without error
        summarizer = SimpleSummarizer()
        assert isinstance(summarizer, Summarizer)


class TestLLMSummarizerInit:
    """Test LLMSummarizer initialization."""

    def test_initialization_with_api_key(self):
        """Test basic initialization with API key."""
        summarizer = LLMSummarizer(api_key="sk-test-key")

        assert summarizer.api_key == "sk-test-key"
        assert summarizer.model == "gpt-4o-mini"  # default
        assert summarizer.temperature == 0.3  # default
        assert summarizer.max_tokens == 500  # default
        assert summarizer.client is not None

    def test_initialization_with_env_var(self, monkeypatch):
        """Test initialization using environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")

        summarizer = LLMSummarizer()
        assert summarizer.api_key == "sk-env-key"

    def test_initialization_without_api_key_raises(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="OpenAI API key must be provided"):
            LLMSummarizer()

    def test_initialization_invalid_model_raises(self):
        """Test that invalid model raises ValueError."""
        with pytest.raises(ValueError, match="Invalid model"):
            LLMSummarizer(api_key="test", model="invalid-model")

    def test_initialization_with_custom_settings(self):
        """Test initialization with custom settings."""
        summarizer = LLMSummarizer(
            api_key="test",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1000,
            base_url="https://custom.api",
        )

        assert summarizer.model == "gpt-4o"
        assert summarizer.temperature == 0.5
        assert summarizer.max_tokens == 1000
        assert summarizer.base_url == "https://custom.api"

    def test_temperature_validation(self):
        """Test temperature must be between 0 and 1."""
        # Too low
        with pytest.raises(ValueError, match="Temperature must be between"):
            LLMSummarizer(api_key="test", temperature=-0.1)

        # Too high
        with pytest.raises(ValueError, match="Temperature must be between"):
            LLMSummarizer(api_key="test", temperature=1.5)

        # Valid edges
        LLMSummarizer(api_key="test", temperature=0.0)
        LLMSummarizer(api_key="test", temperature=1.0)

    def test_repr(self):
        """Test string representation."""
        summarizer = LLMSummarizer(api_key="test", model="gpt-4o", temperature=0.2, max_tokens=300)

        repr_str = repr(summarizer)
        assert "LLMSummarizer" in repr_str
        assert "gpt-4o" in repr_str
        assert "0.2" in repr_str
        assert "300" in repr_str


class TestLLMSummarizerSummarize:
    """Test LLMSummarizer.summarize() method."""

    @pytest.fixture
    def summarizer(self):
        """Create summarizer instance for testing."""
        return LLMSummarizer(api_key="test-key")

    @pytest.fixture
    def sample_entries(self):
        """Create sample memory entries."""
        base_time = datetime.now()

        return [
            MemoryEntry(
                id="1",
                text="User asked about Python list comprehensions",
                metadata=MemoryMetadata(
                    created_at=base_time, importance=0.8, tags=["python", "programming"]
                ),
            ),
            MemoryEntry(
                id="2",
                text="Explained syntax: [x**2 for x in range(10)]",
                metadata=MemoryMetadata(
                    created_at=base_time + timedelta(minutes=1),
                    importance=0.7,
                    tags=["python", "example"],
                ),
            ),
            MemoryEntry(
                id="3",
                text="User successfully wrote their own comprehension",
                metadata=MemoryMetadata(
                    created_at=base_time + timedelta(minutes=2),
                    importance=0.6,
                    tags=["python", "success"],
                ),
            ),
        ]

    @pytest.mark.asyncio
    async def test_summarize_empty_list_raises(self, summarizer):
        """Test that empty entry list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot summarize empty list"):
            await summarizer.summarize([])

    @pytest.mark.asyncio
    async def test_summarize_basic(self, summarizer, sample_entries):
        """Test basic summarization with mocked API."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "User learned Python list comprehensions."

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await summarizer.summarize(sample_entries)

            assert result == "User learned Python list comprehensions."
            assert mock_create.called
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_summarize_with_context(self, summarizer, sample_entries):
        """Test summarization with context parameter."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary text"

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await summarizer.summarize(sample_entries, context="Python tutorial")

            # Check that context was included in the prompt
            call_args = mock_create.call_args
            messages = call_args.kwargs["messages"]
            user_message = messages[1]["content"]
            assert "Context: Python tutorial" in user_message

    @pytest.mark.asyncio
    async def test_summarize_with_max_length(self, summarizer, sample_entries):
        """Test summarization with max_length parameter."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Brief summary"

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await summarizer.summarize(sample_entries, max_length=100)

            # Check that max_length constraint was included
            call_args = mock_create.call_args
            messages = call_args.kwargs["messages"]
            user_message = messages[1]["content"]
            assert "100 characters" in user_message

    @pytest.mark.asyncio
    async def test_summarize_single_entry(self, summarizer):
        """Test summarization with single entry."""
        entry = MemoryEntry(
            id="1", text="Single memory entry", metadata=MemoryMetadata(created_at=datetime.now())
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary of single entry"

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await summarizer.summarize([entry])
            assert result == "Summary of single entry"

    @pytest.mark.asyncio
    async def test_summarize_many_entries(self, summarizer):
        """Test summarization with large batch of entries."""
        entries = [
            MemoryEntry(
                id=f"entry_{i}",
                text=f"Memory entry number {i}",
                metadata=MemoryMetadata(created_at=datetime.now() + timedelta(minutes=i)),
            )
            for i in range(100)
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary of 100 entries"

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await summarizer.summarize(entries)
            assert result == "Summary of 100 entries"

            # Verify API was called correctly
            call_args = mock_create.call_args
            assert call_args.kwargs["model"] == "gpt-4o-mini"
            assert call_args.kwargs["temperature"] == 0.3
            assert call_args.kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_summarize_api_error_retry(self, summarizer, sample_entries):
        """Test retry logic when API fails."""
        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Final summary"

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API Error")
            return mock_response

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = side_effect

            result = await summarizer.summarize(sample_entries)

            assert result == "Final summary"
            assert call_count == 3  # Retried twice

    @pytest.mark.asyncio
    async def test_summarize_api_error_max_retries(self, summarizer, sample_entries):
        """Test that max retries exhaustion raises error."""

        async def side_effect(*args, **kwargs):
            raise Exception("Persistent API Error")

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = side_effect

            with pytest.raises(RuntimeError, match="Failed to summarize entries after 3 attempts"):
                await summarizer.summarize(sample_entries)

    def test_summarize_sync_wrapper(self, summarizer, sample_entries):
        """Test synchronous wrapper calls async version."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Sync summary"

        with patch.object(
            summarizer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = summarizer.summarize_sync(sample_entries)
            assert result == "Sync summary"


class TestPromptBuilding:
    """Test prompt building functionality."""

    @pytest.fixture
    def summarizer(self):
        """Create summarizer instance."""
        return LLMSummarizer(api_key="test-key")

    def test_build_prompt_basic(self, summarizer):
        """Test basic prompt structure."""
        entries = [
            MemoryEntry(
                id="1",
                text="First entry",
                metadata=MemoryMetadata(created_at=datetime(2025, 1, 1, 10, 0)),
            ),
            MemoryEntry(
                id="2",
                text="Second entry",
                metadata=MemoryMetadata(created_at=datetime(2025, 1, 1, 11, 0)),
            ),
        ]

        prompt = summarizer._build_prompt(entries, context=None)

        assert "Summarize the following 2 memory entries:" in prompt
        assert "First entry" in prompt
        assert "Second entry" in prompt
        assert "2025-01-01" in prompt

    def test_build_prompt_with_context(self, summarizer):
        """Test prompt includes context."""
        entries = [
            MemoryEntry(
                id="1", text="Test entry", metadata=MemoryMetadata(created_at=datetime.now())
            )
        ]

        prompt = summarizer._build_prompt(entries, context="User preferences")

        assert "Context: User preferences" in prompt

    def test_build_prompt_with_importance(self, summarizer):
        """Test prompt includes importance markers."""
        entries = [
            MemoryEntry(
                id="1",
                text="High importance entry",
                metadata=MemoryMetadata(created_at=datetime.now(), importance=0.9),
            ),
            MemoryEntry(
                id="2",
                text="Medium importance entry",
                metadata=MemoryMetadata(created_at=datetime.now(), importance=0.6),
            ),
            MemoryEntry(
                id="3",
                text="Low importance entry",
                metadata=MemoryMetadata(created_at=datetime.now(), importance=0.3),
            ),
        ]

        prompt = summarizer._build_prompt(entries, context=None)

        assert "HIGH IMPORTANCE" in prompt
        assert "MEDIUM IMPORTANCE" in prompt
        # Low importance should not have marker
        assert prompt.count("IMPORTANCE") == 2

    def test_build_prompt_chronological_order(self, summarizer):
        """Test entries are sorted chronologically."""
        base_time = datetime(2025, 1, 1, 10, 0)

        # Create entries in random order
        entries = [
            MemoryEntry(
                id="2",
                text="Second",
                metadata=MemoryMetadata(created_at=base_time + timedelta(minutes=10)),
            ),
            MemoryEntry(id="1", text="First", metadata=MemoryMetadata(created_at=base_time)),
            MemoryEntry(
                id="3",
                text="Third",
                metadata=MemoryMetadata(created_at=base_time + timedelta(minutes=20)),
            ),
        ]

        prompt = summarizer._build_prompt(entries, context=None)

        # Check that "First" appears before "Second" before "Third"
        first_pos = prompt.index("First")
        second_pos = prompt.index("Second")
        third_pos = prompt.index("Third")

        assert first_pos < second_pos < third_pos

    def test_build_prompt_truncates_long_text(self, summarizer):
        """Test very long entry texts are truncated."""
        long_text = "X" * 1000  # 1000 characters

        entries = [
            MemoryEntry(id="1", text=long_text, metadata=MemoryMetadata(created_at=datetime.now()))
        ]

        prompt = summarizer._build_prompt(entries, context=None)

        # Should be truncated to 500 chars
        assert long_text not in prompt
        assert "..." in prompt

    def test_build_prompt_with_max_length(self, summarizer):
        """Test max_length parameter is included in prompt."""
        entries = [
            MemoryEntry(id="1", text="Test", metadata=MemoryMetadata(created_at=datetime.now()))
        ]

        prompt = summarizer._build_prompt(entries, context=None, max_length=200)

        assert "200 characters" in prompt

    def test_build_prompt_includes_instructions(self, summarizer):
        """Test prompt includes summarization instructions."""
        entries = [
            MemoryEntry(id="1", text="Test", metadata=MemoryMetadata(created_at=datetime.now()))
        ]

        prompt = summarizer._build_prompt(entries, context=None)

        assert "Create a concise summary" in prompt
        assert "main themes" in prompt
        assert "chronological flow" in prompt
