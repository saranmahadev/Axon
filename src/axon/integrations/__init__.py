"""
Axon Integrations with LLM Frameworks

This module provides integration adapters for popular LLM frameworks:
- LangChain: Memory and VectorStore adapters
- LlamaIndex: VectorStore adapter

These adapters allow Axon to be used as a drop-in replacement or complement
to existing memory and storage systems in LangChain and LlamaIndex applications.
"""

from typing import TYPE_CHECKING

# Lazy imports for heavy dependencies
__all__ = [
    "AxonChatMemory",
    "AxonVectorStore",
    "AxonLlamaIndexVectorStore",
]


def __getattr__(name: str):
    """Lazy import of integration modules."""
    if name == "AxonChatMemory":
        from .langchain.memory import AxonChatMemory

        return AxonChatMemory

    if name == "AxonVectorStore":
        from .langchain.vectorstore import AxonVectorStore

        return AxonVectorStore

    if name == "AxonLlamaIndexVectorStore":
        from .llamaindex.vectorstore import AxonLlamaIndexVectorStore

        return AxonLlamaIndexVectorStore

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
