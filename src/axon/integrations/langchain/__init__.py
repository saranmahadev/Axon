"""
LangChain Integration

Provides Axon adapters compatible with LangChain's memory and vector store interfaces:
- AxonChatMemory: Chat memory adapter implementing BaseMemory
- AxonVectorStore: Vector store adapter for LangChain retrieval chains
"""

from typing import TYPE_CHECKING

__all__ = ["AxonChatMemory", "AxonVectorStore"]


def __getattr__(name: str):
    """Lazy import of LangChain integration modules."""
    if name == "AxonChatMemory":
        from .memory import AxonChatMemory

        return AxonChatMemory

    if name == "AxonVectorStore":
        from .vectorstore import AxonVectorStore

        return AxonVectorStore

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
