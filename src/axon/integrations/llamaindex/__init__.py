"""
LlamaIndex Integration

Provides Axon vector store adapter compatible with LlamaIndex:
- AxonLlamaIndexVectorStore: Vector store adapter implementing BasePydanticVectorStore
"""

from typing import TYPE_CHECKING

__all__ = ["AxonLlamaIndexVectorStore"]


def __getattr__(name: str):
    """Lazy import of LlamaIndex integration modules."""
    if name == "AxonLlamaIndexVectorStore":
        from .vectorstore import AxonLlamaIndexVectorStore

        return AxonLlamaIndexVectorStore

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
