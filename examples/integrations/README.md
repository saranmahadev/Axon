# Framework Integration Examples

Axon integration with popular LLM frameworks.

## Examples

- `26_langchain_chatbot.py` - LangChain memory integration
- `27_llamaindex_rag.py` - LlamaIndex RAG with Axon

## Frameworks

- **LangChain** - `AxonChatMemory` + `AxonVectorStore`
- **LlamaIndex** - `AxonVectorStore` implementation

## Prerequisites

```bash
# Install integrations
pip install "axon[langchain,llamaindex]"

# Set API key
export OPENAI_API_KEY="sk-..."
```

## Quick Start

```bash
python examples/integrations/26_langchain_chatbot.py
```

## Features

- Persistent conversation memory
- Multi-user session management
- Semantic memory recall
- RAG with multi-tier storage
