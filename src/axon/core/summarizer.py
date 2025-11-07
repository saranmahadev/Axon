"""
Memory Summarization Module

This module provides interfaces and implementations for summarizing groups of
memory entries into concise representations using LLMs or other techniques.

Key Components:
- Summarizer: Abstract base class for all summarizers
- LLMSummarizer: OpenAI-based summarization implementation

Usage:
    >>> from axon.core.summarizer import LLMSummarizer
    >>> summarizer = LLMSummarizer(api_key="sk-...")
    >>> entries = [entry1, entry2, entry3]
    >>> summary = await summarizer.summarize(entries)
    >>> print(summary)
"""

import asyncio
import os
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from ..models.entry import MemoryEntry


class Summarizer(ABC):
    """
    Abstract base class for memory summarization.

    A summarizer takes a list of memory entries and produces a concise
    text summary that captures the key information while reducing the
    overall memory footprint.

    Implementations should handle:
    - Temporal ordering of memories
    - Importance weighting
    - Context preservation
    - Error handling

    Example:
        >>> class MySummarizer(Summarizer):
        ...     async def summarize(self, entries, context=None, max_length=None):
        ...         texts = [e.text for e in entries]
        ...         return " | ".join(texts[:5])  # Simple concatenation
    """

    @abstractmethod
    async def summarize(
        self,
        entries: list[MemoryEntry],
        context: str | None = None,
        max_length: int | None = None,
    ) -> str:
        """
        Summarize a list of memory entries into a single text.

        Args:
            entries: List of memory entries to summarize (must be non-empty)
            context: Optional context to guide summarization (e.g., "user preferences")
            max_length: Maximum length of summary in characters (None = no limit)

        Returns:
            Summarized text that captures key information from all entries

        Raises:
            ValueError: If entries list is empty

        Example:
            >>> entries = [
            ...     MemoryEntry(id="1", text="User likes dark mode"),
            ...     MemoryEntry(id="2", text="User prefers compact layout"),
            ...     MemoryEntry(id="3", text="User uses keyboard shortcuts")
            ... ]
            >>> summary = await summarizer.summarize(entries, context="UI preferences")
            >>> # Returns: "User prefers dark mode, compact layout, and keyboard shortcuts"
        """
        pass

    def summarize_sync(
        self,
        entries: list[MemoryEntry],
        context: str | None = None,
        max_length: int | None = None,
    ) -> str:
        """
        Synchronous wrapper for summarize().

        This is a convenience method for non-async contexts. It internally
        runs the async summarize() method.

        Args:
            entries: List of memory entries to summarize
            context: Optional context to guide summarization
            max_length: Maximum length of summary in characters

        Returns:
            Summarized text

        Example:
            >>> summary = summarizer.summarize_sync(entries)
        """
        return asyncio.run(self.summarize(entries, context, max_length))


class LLMSummarizer(Summarizer):
    """
    LLM-based summarization using OpenAI or compatible APIs.

    This summarizer uses large language models to create intelligent,
    coherent summaries that preserve the most important information
    while significantly reducing token count.

    Features:
    - Configurable model selection (GPT-4, GPT-3.5, etc.)
    - Temperature control for creativity vs consistency
    - Automatic prompt engineering
    - Retry logic for API failures
    - Token limit handling

    Example:
        >>> summarizer = LLMSummarizer(
        ...     api_key="sk-...",
        ...     model="gpt-4o-mini",
        ...     temperature=0.3
        ... )
        >>> entries = load_entries_from_tier("persistent")
        >>> summary = await summarizer.summarize(
        ...     entries[:100],
        ...     context="user conversation history"
        ... )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 500,
        base_url: str | None = None,
    ):
        """
        Initialize LLM summarizer.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use for summarization
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in summary
            base_url: Optional base URL for API (for compatible providers)

        Raises:
            ValueError: If api_key is not provided and not in environment
            ValueError: If model is not valid
            ValueError: If temperature is out of range

        Example:
            >>> # Use environment variable
            >>> summarizer = LLMSummarizer()

            >>> # Explicit configuration
            >>> summarizer = LLMSummarizer(
            ...     api_key="sk-...",
            ...     model="gpt-4o",
            ...     temperature=0.2,
            ...     max_tokens=300
            ... )
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided via api_key parameter "
                "or OPENAI_API_KEY environment variable"
            )

        # Validate model
        valid_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
        if model not in valid_models:
            raise ValueError(f"Invalid model: {model}. Must be one of {valid_models}")

        # Validate temperature
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"Temperature must be between 0.0 and 1.0, got {temperature}")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)

    async def summarize(
        self,
        entries: list[MemoryEntry],
        context: str | None = None,
        max_length: int | None = None,
    ) -> str:
        """
        Use LLM to create concise summary of entries.

        The summarizer builds a carefully crafted prompt that includes:
        - Temporal ordering of entries
        - Importance scores
        - User/session context
        - Instruction to preserve key details

        Args:
            entries: List of memory entries to summarize (1-1000 entries)
            context: Optional context (e.g., "user preferences", "conversation history")
            max_length: Maximum length hint for summary (actual may vary)

        Returns:
            Coherent summary text

        Raises:
            ValueError: If entries is empty
            RuntimeError: If OpenAI API call fails after retries

        Example:
            >>> entries = [
            ...     MemoryEntry(id="1", text="User asked about Python", importance=0.8),
            ...     MemoryEntry(id="2", text="Explained list comprehensions", importance=0.7),
            ...     MemoryEntry(id="3", text="User understood the concept", importance=0.6)
            ... ]
            >>> summary = await summarizer.summarize(entries, context="Python tutorial")
            >>> # Returns: "User learned about Python list comprehensions and understood the concept."
        """
        if not entries:
            raise ValueError("Cannot summarize empty list of entries")

        # Build the prompt
        prompt = self._build_prompt(entries, context, max_length)

        # Call OpenAI API with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a memory summarization assistant. Your job is to "
                                "create concise, coherent summaries of multiple memory entries "
                                "while preserving the most important information. Focus on "
                                "key facts, actions, and outcomes. Maintain temporal order "
                                "when relevant."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                # Extract summary text
                summary = response.choices[0].message.content.strip()
                return summary

            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed
                    raise RuntimeError(
                        f"Failed to summarize entries after {max_retries} attempts: {str(e)}"
                    ) from e

    def _build_prompt(
        self, entries: list[MemoryEntry], context: str | None, max_length: int | None = None
    ) -> str:
        """
        Build summarization prompt from entries.

        The prompt structure:
        1. Context (if provided)
        2. Number of entries being summarized
        3. Each entry with timestamp, importance, and text
        4. Instructions for summarization
        5. Length constraint (if specified)

        Args:
            entries: Memory entries to include in prompt
            context: Optional context string
            max_length: Optional maximum length for summary

        Returns:
            Formatted prompt string
        """
        # Sort entries by date (oldest first) for chronological narrative
        sorted_entries = sorted(entries, key=lambda e: e.metadata.created_at)

        # Build prompt parts
        parts = []

        # Add context if provided
        if context:
            parts.append(f"Context: {context}")
            parts.append("")

        # Add entry count
        parts.append(f"Summarize the following {len(entries)} memory entries:")
        parts.append("")

        # Add each entry with metadata
        for i, entry in enumerate(sorted_entries, 1):
            # Format timestamp
            timestamp = entry.metadata.created_at.strftime("%Y-%m-%d %H:%M")

            # Include importance if significant
            importance_str = ""
            if entry.metadata.importance >= 0.7:
                importance_str = f" [HIGH IMPORTANCE: {entry.metadata.importance:.2f}]"
            elif entry.metadata.importance >= 0.5:
                importance_str = f" [MEDIUM IMPORTANCE: {entry.metadata.importance:.2f}]"

            # Truncate very long texts
            text = entry.text
            if len(text) > 500:
                text = text[:497] + "..."

            parts.append(f"{i}. [{timestamp}]{importance_str}")
            parts.append(f"   {text}")
            parts.append("")

        # Add instructions
        parts.append("Create a concise summary that:")
        parts.append("- Captures the main themes and key information")
        parts.append("- Preserves important facts and outcomes")
        parts.append("- Maintains chronological flow when relevant")
        parts.append("- Uses clear, natural language")

        if max_length:
            parts.append(f"- Stays under approximately {max_length} characters")

        return "\n".join(parts)

    def __repr__(self) -> str:
        """String representation of summarizer."""
        return (
            f"LLMSummarizer(model='{self.model}', "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens})"
        )
