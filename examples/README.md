# Axon Examples

Comprehensive examples demonstrating all Axon features organized by category.

**Total: 31 examples across 7 categories**

## Example Categories

### [basics/](basics/) - 7 examples ⭐
Getting started with Axon:
- Basic store/recall operations
- MemorySystem fundamentals
- Chatbot implementation
- Knowledge base example
- Adapter usage patterns
- Embedder examples

### [routing/](routing/) - 4 examples
Intelligent tier routing:
- Basic router operations
- Multi-tier routing demonstration
- Automatic promotion/demotion
- Scoring engine configuration

### [storage-adapters/](storage-adapters/) - 7 examples
Different storage backends:
- Qdrant vector store
- Pinecone (basic, serverless, multi-namespace)
- Redis (session cache, TTL, multi-tenant)

### [policies-and-routing/](policies-and-routing/) - 3 examples
Policy engine configuration:
- Basic policy setup
- Custom policy implementation
- Policy serialization

### [advanced-features/](advanced-features/) - 6 examples
Advanced capabilities:
- Memory compaction strategies
- Audit logging for compliance
- PII detection and privacy
- Structured JSON logging
- Two-phase commit transactions

### [integrations/](integrations/) - 2 examples ⭐
Framework integrations:
- LangChain chatbot with persistent memory
- LlamaIndex RAG with multi-tier storage

### [demos/](demos/) - 2 examples
Complete applications:
- Customer support knowledge base
- Interactive CLI demo

## Quick Start

```bash
# Install Axon with all dependencies
pip install "axon[all]"

# Set API keys (if needed)
export OPENAI_API_KEY="sk-..."

# Run a basic example
python examples/basics/basic_usage.py

# Run integration example
python examples/integrations/26_langchain_chatbot.py
```

## Documentation

- **Live Docs:** https://saranmahadev.github.io/Axon/
- **API Reference:** https://saranmahadev.github.io/Axon/api/memory-system/
- **Quickstart:** https://saranmahadev.github.io/Axon/getting-started/quickstart/

## Prerequisites

Different examples have different requirements:

| Category | Requirements |
|----------|--------------|
| **basics/** | None (works out of the box) |
| **routing/** | None |
| **storage-adapters/** | Qdrant/Pinecone/Redis running |
| **policies/** | None |
| **advanced-features/** | OpenAI API key (for some) |
| **integrations/** | OpenAI API key + framework |
| **demos/** | Varies by example |

Check individual folder READMEs and file headers for specific setup instructions.

## Example Navigation

- ⭐ = Recommended starting point
- Each folder has its own README with details
- Examples are numbered for easy reference
- All examples include inline documentation
