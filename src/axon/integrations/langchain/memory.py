"""
LangChain Memory Adapter for Axon

This module provides AxonChatMemory, a LangChain-compatible memory class that
uses Axon's MemorySystem as the backend. This allows LangChain applications to
leverage Axon's multi-tier storage, policy-driven lifecycle management, and
semantic recall capabilities.

Example:
    >>> from axon import MemorySystem
    >>> from axon.integrations.langchain import AxonChatMemory
    >>> from axon.core.templates import balanced
    >>>
    >>> # Create Axon memory system
    >>> system = MemorySystem(balanced())
    >>>
    >>> # Use with LangChain
    >>> memory = AxonChatMemory(system, session_id="user_123")
    >>> memory.save_context(
    ...     {"input": "Hello!"},
    ...     {"output": "Hi! How can I help you?"}
    ... )
    >>> variables = memory.load_memory_variables({"input": "What did I say?"})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from langchain_core.memory import BaseMemory
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseMemory = object  # type: ignore
    BaseMessage = object  # type: ignore
    HumanMessage = object  # type: ignore
    AIMessage = object  # type: ignore

from ...core.memory_system import MemorySystem
from ...models import Filter

logger = logging.getLogger(__name__)


class AxonChatMemory(BaseMemory):
    """
    LangChain-compatible chat memory backed by Axon MemorySystem.

    This adapter implements LangChain's BaseMemory interface, storing chat messages
    in Axon's multi-tier memory system. It provides:
    - Automatic storage of chat exchanges
    - Semantic search over conversation history
    - Session-based conversation tracking
    - Configurable memory retrieval (recent N messages or semantic search)

    Attributes:
        system: The Axon MemorySystem instance to use for storage
        session_id: Optional session identifier for conversation isolation
        memory_key: Key to use when injecting memory into prompts (default: "history")
        return_messages: If True, return message objects; if False, return string (default: False)
        input_key: Key for input in save_context (default: "input")
        output_key: Key for output in save_context (default: "output")
        k_messages: Number of recent messages to retrieve (default: 10)
        use_semantic_search: If True, use semantic search for retrieval (default: False)

    Example:
        >>> from axon import MemorySystem
        >>> from axon.integrations.langchain import AxonChatMemory
        >>>
        >>> system = MemorySystem.from_template("balanced")
        >>> memory = AxonChatMemory(
        ...     system,
        ...     session_id="user_123",
        ...     k_messages=10,
        ...     use_semantic_search=True
        ... )
        >>>
        >>> # Use with LangChain chains
        >>> from langchain.chains import ConversationChain
        >>> chain = ConversationChain(memory=memory, llm=llm)
    """

    def __init__(
        self,
        system: MemorySystem,
        session_id: Optional[str] = None,
        memory_key: str = "history",
        return_messages: bool = False,
        input_key: str = "input",
        output_key: str = "output",
        k_messages: int = 10,
        use_semantic_search: bool = False,
    ):
        """
        Initialize AxonChatMemory.

        Args:
            system: Axon MemorySystem instance
            session_id: Optional session ID for conversation isolation
            memory_key: Key for memory in chain inputs (default: "history")
            return_messages: Return message objects vs strings (default: False)
            input_key: Key for user input in save_context (default: "input")
            output_key: Key for AI output in save_context (default: "output")
            k_messages: Number of messages to retrieve (default: 10)
            use_semantic_search: Use semantic search vs chronological (default: False)

        Raises:
            ImportError: If langchain_core is not installed
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain_core is required for AxonChatMemory. "
                "Install it with: pip install langchain-core"
            )

        super().__init__()
        self.system = system
        self.session_id = session_id
        self.memory_key = memory_key
        self.return_messages = return_messages
        self.input_key = input_key
        self.output_key = output_key
        self.k_messages = k_messages
        self.use_semantic_search = use_semantic_search

        logger.info(
            f"AxonChatMemory initialized with session_id={session_id}, "
            f"k_messages={k_messages}, semantic_search={use_semantic_search}"
        )

    @property
    def memory_variables(self) -> List[str]:
        """Return the memory key."""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load conversation history from Axon memory.

        Args:
            inputs: Dictionary of input variables (used for semantic search if enabled)

        Returns:
            Dictionary with memory_key mapped to conversation history

        Raises:
            RuntimeError: If async recall operation fails
        """
        import asyncio

        try:
            # Run async recall in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new loop
                import nest_asyncio

                nest_asyncio.apply()

            messages = loop.run_until_complete(self._load_messages_async(inputs))

        except Exception as e:
            logger.error(f"Failed to load memory variables: {e}")
            messages = []

        if self.return_messages:
            return {self.memory_key: messages}
        else:
            # Convert messages to string format
            buffer = self._messages_to_string(messages)
            return {self.memory_key: buffer}

    async def _load_messages_async(self, inputs: Dict[str, Any]) -> List[BaseMessage]:
        """
        Async implementation of message loading.

        Args:
            inputs: Input dictionary (may contain query for semantic search)

        Returns:
            List of chat messages
        """
        # Build filter for session
        filter_dict: Dict[str, Any] = {}
        if self.session_id:
            filter_dict["session_id"] = self.session_id

        # Tag-based filtering for chat messages
        filter_dict["tags"] = ["chat_message"]

        msg_filter = Filter(**filter_dict) if filter_dict else None

        if self.use_semantic_search and self.input_key in inputs:
            # Semantic recall based on current input
            query_text = inputs[self.input_key]
            results = await self.system.recall(query_text, k=self.k_messages, filter=msg_filter)
        else:
            # Retrieve recent messages chronologically
            # Note: This requires Axon to support chronological retrieval
            # For now, we use recall with empty query and rely on recency scoring
            results = await self.system.recall("", k=self.k_messages, filter=msg_filter)

        # Convert MemoryEntry to LangChain messages
        messages = []
        for entry in results:
            msg_type = entry.metadata.custom_fields.get("message_type", "human")
            if msg_type == "ai":
                messages.append(AIMessage(content=entry.text))
            else:
                messages.append(HumanMessage(content=entry.text))

        return messages

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save chat exchange to Axon memory.

        Args:
            inputs: Dictionary containing user input (key: input_key)
            outputs: Dictionary containing AI output (key: output_key)

        Raises:
            RuntimeError: If async store operation fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()

            loop.run_until_complete(self._save_context_async(inputs, outputs))

        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    async def _save_context_async(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Async implementation of context saving.

        Args:
            inputs: User input dictionary
            outputs: AI output dictionary
        """
        # Extract input and output text
        input_text = inputs.get(self.input_key, "")
        output_text = outputs.get(self.output_key, "")

        # Store user message
        await self.system.store(
            input_text,
            session_id=self.session_id,
            tags=["chat_message"],
            importance=0.5,
            custom_fields={"message_type": "human"},
        )

        # Store AI message
        await self.system.store(
            output_text,
            session_id=self.session_id,
            tags=["chat_message"],
            importance=0.5,
            custom_fields={"message_type": "ai"},
        )

        logger.debug(
            f"Saved chat exchange to session {self.session_id}: "
            f"input_len={len(input_text)}, output_len={len(output_text)}"
        )

    def clear(self) -> None:
        """
        Clear all messages for this session.

        Note: This requires Axon to support filtering by session_id for deletion.
        Currently, this will log a warning as Axon doesn't have bulk delete by filter.
        """
        logger.warning(
            "AxonChatMemory.clear() is not fully supported. "
            "Axon does not currently support bulk delete by filter. "
            "Consider using a new session_id instead."
        )
        # TODO: Implement when Axon supports bulk delete by filter

    def _messages_to_string(self, messages: List[BaseMessage]) -> str:
        """
        Convert message objects to string format.

        Args:
            messages: List of chat messages

        Returns:
            Formatted string representation
        """
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"AI: {msg.content}")
            else:
                lines.append(f"{msg.content}")

        return "\n".join(lines)

    # Async versions (optional but recommended)
    async def aload_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async version of load_memory_variables.

        Args:
            inputs: Input dictionary

        Returns:
            Dictionary with memory variables
        """
        messages = await self._load_messages_async(inputs)

        if self.return_messages:
            return {self.memory_key: messages}
        else:
            buffer = self._messages_to_string(messages)
            return {self.memory_key: buffer}

    async def asave_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Async version of save_context.

        Args:
            inputs: User input dictionary
            outputs: AI output dictionary
        """
        await self._save_context_async(inputs, outputs)

    async def aclear(self) -> None:
        """Async version of clear."""
        self.clear()  # Same limitation as sync version
