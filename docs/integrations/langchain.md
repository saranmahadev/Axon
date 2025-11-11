# LangChain Integration

Use Axon as a memory backend for LangChain chatbots and conversational AI.

---

## Overview

Axon provides **native LangChain integration** through `AxonChatMemory`, allowing you to use Axon's multi-tier memory system as the backend for LangChain conversational chains.

**Key Features:**
- ✓ Drop-in replacement for LangChain memory
- ✓ Multi-tier storage (ephemeral, session, persistent)
- ✓ Semantic search over conversation history
- ✓ Session-based conversation tracking
- ✓ Policy-driven lifecycle management
- ✓ Automatic message storage and retrieval

---

## Installation

```bash
# Install LangChain and Axon
pip install langchain langchain-core langchain-openai axon-sdk

# Or with all dependencies
pip install "axon-sdk[all]" langchain langchain-openai
```

---

## Basic Usage

### Quick Start

```python
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from axon.integrations.langchain import AxonChatMemory
from axon.core.templates import DEVELOPMENT_CONFIG

# Create Axon memory
memory = AxonChatMemory(config=DEVELOPMENT_CONFIG)

# Create LangChain chain
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
chain = ConversationChain(llm=llm, memory=memory)

# Use the chain
response = chain.run("My name is Alice")
# Automatically stores in Axon

response = chain.run("What is my name?")
# Recalls from Axon: "Your name is Alice"
```

---

## Configuration

### Using Templates

```python
from axon.integrations.langchain import AxonChatMemory
from axon.core.templates import (
    DEVELOPMENT_CONFIG,
    STANDARD_CONFIG,
    PRODUCTION_CONFIG
)

# Development (in-memory)
memory = AxonChatMemory(config=DEVELOPMENT_CONFIG)

# Standard (Redis + ChromaDB)
memory = AxonChatMemory(config=STANDARD_CONFIG)

# Production (Redis + Qdrant)
memory = AxonChatMemory(config=PRODUCTION_CONFIG)
```

### Custom Configuration

```python
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy
from axon.integrations.langchain import AxonChatMemory

# Custom memory configuration
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl=timedelta(hours=24),
        compaction_threshold=1000
    )
)

system = MemorySystem(config)
memory = AxonChatMemory(
    system,
    session_id="user_123",
    k_messages=20,              # Retrieve last 20 messages
    use_semantic_search=True    # Use semantic search
)
```

---

## Features

### Session-Based Conversations

```python
# Different sessions for different users
alice_memory = AxonChatMemory(
    config=config,
    session_id="user_alice"
)

bob_memory = AxonChatMemory(
    config=config,
    session_id="user_bob"
)

# Alice's chain
alice_chain = ConversationChain(llm=llm, memory=alice_memory)
alice_chain.run("My favorite color is blue")

# Bob's chain
bob_chain = ConversationChain(llm=llm, memory=bob_memory)
bob_chain.run("My favorite color is red")

# Sessions are isolated
alice_chain.run("What's my favorite color?")
# → "Your favorite color is blue"

bob_chain.run("What's my favorite color?")
# → "Your favorite color is red"
```

### Semantic Search

```python
# Enable semantic search for context retrieval
memory = AxonChatMemory(
    config=config,
    use_semantic_search=True,  # Search by meaning, not just recency
    k_messages=10               # Return top 10 relevant messages
)

chain = ConversationChain(llm=llm, memory=memory)

# Conversation about multiple topics
chain.run("I love Python programming")
chain.run("My favorite food is pizza")
chain.run("I work at Google")
# ... many more messages ...

# Later, semantic search finds relevant context
chain.run("What programming language do I like?")
# Finds "I love Python programming" even if it's not recent
```

---

## Examples

### Chatbot with Context

```python
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from axon.integrations.langchain import AxonChatMemory
from axon.core.templates import STANDARD_CONFIG

async def run_chatbot():
    """Simple chatbot with Axon memory."""
    
    # Setup
    memory = AxonChatMemory(
        config=STANDARD_CONFIG,
        session_id="user_123",
        k_messages=10
    )
    
    llm = ChatOpenAI(temperature=0.7, model="gpt-3.5-turbo")
    chain = ConversationChain(llm=llm, memory=memory)
    
    # Conversation
    print("User: Hi, I'm working on a Python project")
    response = chain.run("Hi, I'm working on a Python project")
    print(f"Bot: {response}\n")
    
    print("User: Can you help me with async functions?")
    response = chain.run("Can you help me with async functions?")
    print(f"Bot: {response}\n")
    
    print("User: What programming language am I using?")
    response = chain.run("What programming language am I using?")
    print(f"Bot: {response}\n")
    # Bot remembers: "You're using Python"

# Run
import asyncio
asyncio.run(run_chatbot())
```

### Multi-User Support

```python
from typing import Dict
from langchain.chains import ConversationChain

class MultiUserChatbot:
    """Chatbot with per-user memory."""
    
    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(temperature=0.7)
        self.chains: Dict[str, ConversationChain] = {}
    
    def get_chain(self, user_id: str) -> ConversationChain:
        """Get or create chain for user."""
        if user_id not in self.chains:
            memory = AxonChatMemory(
                config=self.config,
                session_id=user_id,
                k_messages=15
            )
            self.chains[user_id] = ConversationChain(
                llm=self.llm,
                memory=memory
            )
        return self.chains[user_id]
    
    def chat(self, user_id: str, message: str) -> str:
        """Handle user message."""
        chain = self.get_chain(user_id)
        return chain.run(message)

# Usage
bot = MultiUserChatbot(STANDARD_CONFIG)

# Alice
response = bot.chat("alice", "My name is Alice")
print(f"Alice: {response}")

# Bob
response = bot.chat("bob", "My name is Bob")
print(f"Bob: {response}")

# Each user has isolated memory
response = bot.chat("alice", "What's my name?")
print(f"Alice: {response}")  # → "Your name is Alice"
```

---

## Best Practices

### 1. Use Session IDs

```python
# ✓ Good: Per-user sessions
memory = AxonChatMemory(
    config=config,
    session_id=f"user_{user_id}"
)

# ✗ Bad: Shared memory
memory = AxonChatMemory(config=config)
# All users share the same conversation!
```

### 2. Set Appropriate Message Limits

```python
# ✓ Good: Reasonable context window
memory = AxonChatMemory(
    config=config,
    k_messages=10  # Last 10 messages
)

# ✗ Bad: Too many messages
memory = AxonChatMemory(
    config=config,
    k_messages=1000  # Exceeds LLM context window
)
```

### 3. Clear Stale Sessions

```python
# Periodically clean up old sessions
async def cleanup_old_sessions():
    """Delete sessions older than 30 days."""
    
    cutoff = datetime.now() - timedelta(days=30)
    
    # Query old sessions
    old_entries = await memory.system.recall(
        "",
        filter=Filter(
            tags=["chat_message"],
            max_age_seconds=30 * 24 * 3600
        ),
        k=10000
    )
    
    # Delete
    for entry in old_entries:
        await memory.system.forget(entry.id)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-file-tree:{ .lg .middle } **LlamaIndex Integration**

    ---

    Use Axon with LlamaIndex.

    [:octicons-arrow-right-24: LlamaIndex Guide](llamaindex.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Advanced memory configuration.

    [:octicons-arrow-right-24: Configuration Guide](../getting-started/configuration.md)

-   :material-rocket-launch:{ .lg .middle } **Production**

    ---

    Deploy LangChain apps with Axon.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

</div>
