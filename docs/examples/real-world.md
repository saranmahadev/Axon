# Real-World Examples

Production-ready applications and complete use cases from `examples/05-real-world/`.

---

## Overview

These real-world examples demonstrate complete, production-ready applications built with Axon.

**Examples Covered:**
- User Preferences System
- Session Management
- Production Deployment
- Chatbot with Memory
- Knowledge Base
- RAG System

**What You'll Learn:**
- Production architecture patterns
- Complete application structure
- Best practices
- Real-world use cases
- Deployment strategies

**Prerequisites:**
- Completed all previous examples
- Production deployment experience
- Understanding of application architecture

**Location:** `examples/05-real-world/`

---

## Standalone Examples

### 02_user_preferences.py

**User preferences system** - Store and manage user settings.

**File:** `examples/05-real-world/02_user_preferences.py`

**What it demonstrates:**
- User-specific memory storage
- Preference management
- Multi-user support
- Preference recall and updates
- Default preferences

**Use case:**
```python
from axon import MemorySystem, MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy

# Configure for user preferences
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=3600  # 1 hour cache
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma"  # Long-term storage
    )
)

memory = MemorySystem(config)

# Store user preferences
await memory.store(
    "User prefers dark mode and large font",
    metadata={
        "user_id": "user_123",
        "category": "preferences",
        "settings": {
            "theme": "dark",
            "font_size": "large"
        }
    },
    importance=0.9,
    tier="persistent"
)

# Recall preferences
from axon.models.filter import Filter

prefs = await memory.recall(
    "user settings",
    filter=Filter(metadata={"user_id": "user_123", "category": "preferences"})
)
```

**Features:**
- Per-user isolation
- Fast preference lookup
- Persistent storage
- Update tracking

---

### 03_session_management.py

**Session management** - Track and manage user sessions.

**File:** `examples/05-real-world/03_session_management.py`

**What it demonstrates:**
- Session creation and tracking
- Session expiration (TTL)
- Session data storage
- Multi-session support
- Session cleanup

**Use case:**
```python
# Create session
session_id = "session_abc123"
user_id = "user_456"

# Store session data
await memory.store(
    f"Session started at {datetime.now()}",
    metadata={
        "user_id": user_id,
        "session_id": session_id,
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0..."
    },
    tier="session",
    tags=["session", "auth"]
)

# Store activity in session
await memory.store(
    "User viewed product page: laptop-123",
    metadata={
        "session_id": session_id,
        "action": "view_product",
        "product_id": "laptop-123"
    },
    tier="session"
)

# Recall session history
history = await memory.recall(
    "session activity",
    filter=Filter(metadata={"session_id": session_id}),
    tier="session"
)
```

**Features:**
- Automatic session expiration
- Activity tracking
- Session analytics
- Cross-device sessions

---

### 04_production_deployment.py

**Production deployment** - Complete production configuration.

**File:** `examples/05-real-world/04_production_deployment.py`

**What it demonstrates:**
- Production-ready configuration
- High availability setup
- Monitoring and logging
- Error handling
- Security best practices

**Production config:**
```python
from axon import MemorySystem, MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy
from axon.core import AuditLogger
from axon.core.privacy import PIIDetector

# Production configuration
config = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://redis-master:6379",
            "password": os.getenv("REDIS_PASSWORD"),
            "max_connections": 50,
            "socket_timeout": 5
        },
        ttl_seconds=60,
        max_entries=1000
    ),
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://redis-master:6379",
            "password": os.getenv("REDIS_PASSWORD"),
            "max_connections": 100
        },
        ttl_seconds=3600,
        max_entries=10000
    ),
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        adapter_config={
            "url": "http://qdrant:6333",
            "api_key": os.getenv("QDRANT_API_KEY"),
            "collection_name": "memories",
            "prefer_grpc": True,
            "timeout": 60
        },
        compaction_threshold=100000
    ),
    enable_promotion=True,
    enable_demotion=True
)

# Enable audit and PII detection
audit_logger = AuditLogger(storage_path="/var/log/axon/audit.log")
pii_detector = PIIDetector()

memory = MemorySystem(
    config=config,
    audit_logger=audit_logger,
    pii_detector=pii_detector,
    enable_pii_detection=True
)
```

**Production features:**
- Connection pooling
- Secrets from environment
- Audit logging
- PII detection
- High availability

---

## Application Examples

### Chatbot

**01_conversation_memory.py** - Chatbot with multi-tier conversation memory.

**File:** `examples/05-real-world/chatbot/01_conversation_memory.py`

**What it demonstrates:**
- Conversation history management
- Context-aware responses
- Multi-turn dialogue
- Session-based memory
- Conversation summarization

**Architecture:**
```
User Input
    ↓
Retrieve Context (from Axon)
    ↓
Generate Response (LLM)
    ↓
Store Conversation (to Axon)
    ↓
Response to User
```

**Implementation:**
```python
class Chatbot:
    def __init__(self, memory: MemorySystem, llm):
        self.memory = memory
        self.llm = llm
    
    async def chat(self, user_id: str, message: str) -> str:
        # 1. Store user message
        await self.memory.store(
            f"user: {message}",
            metadata={"user_id": user_id, "role": "user"},
            tier="session"
        )
        
        # 2. Retrieve conversation context
        context = await self.memory.recall(
            message,
            filter=Filter(metadata={"user_id": user_id}),
            k=5
        )
        
        # 3. Generate response
        context_str = "\n".join([e.text for e in context])
        prompt = f"Context:\n{context_str}\n\nUser: {message}\nAssistant:"
        response = await self.llm.generate(prompt)
        
        # 4. Store assistant response
        await self.memory.store(
            f"assistant: {response}",
            metadata={"user_id": user_id, "role": "assistant"},
            tier="session"
        )
        
        return response
```

**Features:**
- Conversation context
- User-specific memory
- Session management
- Automatic summarization

---

### Knowledge Base

**01_knowledge_management.py** - Searchable knowledge base with semantic search.

**File:** `examples/05-real-world/knowledge-base/01_knowledge_management.py`

**What it demonstrates:**
- Document ingestion
- Semantic search
- Knowledge organization
- Metadata tagging
- Version control

**Use case:**
```python
class KnowledgeBase:
    def __init__(self, memory: MemorySystem):
        self.memory = memory
    
    async def add_document(
        self,
        title: str,
        content: str,
        category: str,
        tags: list[str]
    ):
        """Add document to knowledge base."""
        await self.memory.store(
            content,
            metadata={
                "title": title,
                "category": category,
                "type": "document",
                "added_at": datetime.now().isoformat()
            },
            tags=tags,
            importance=0.8,
            tier="persistent"
        )
    
    async def search(
        self,
        query: str,
        category: str = None,
        k: int = 10
    ) -> list[dict]:
        """Search knowledge base."""
        filter_dict = {"type": "document"}
        if category:
            filter_dict["category"] = category
        
        results = await self.memory.recall(
            query,
            filter=Filter(metadata=filter_dict),
            k=k
        )
        
        return [
            {
                "title": r.metadata.get("title"),
                "content": r.text,
                "category": r.metadata.get("category"),
                "relevance": r.score
            }
            for r in results
        ]
```

**Features:**
- Semantic search
- Category organization
- Metadata filtering
- Relevance scoring

---

### RAG System

**01_document_qa.py** - Complete RAG system for document Q&A.

**File:** `examples/05-real-world/rag-system/01_document_qa.py`

**What it demonstrates:**
- Document ingestion pipeline
- Chunking strategies
- Retrieval-augmented generation
- Answer generation
- Source attribution

**Architecture:**
```
Documents
    ↓
Chunking & Embedding
    ↓
Store in Axon
    ↓
User Question
    ↓
Semantic Retrieval
    ↓
LLM Generation
    ↓
Answer + Sources
```

**Implementation:**
```python
class DocumentQA:
    def __init__(self, memory: MemorySystem, llm):
        self.memory = memory
        self.llm = llm
    
    async def ingest_document(
        self,
        document: str,
        metadata: dict,
        chunk_size: int = 500
    ):
        """Ingest document with chunking."""
        chunks = self._chunk_document(document, chunk_size)
        
        for i, chunk in enumerate(chunks):
            await self.memory.store(
                chunk,
                metadata={
                    **metadata,
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                },
                importance=0.9,
                tier="persistent"
            )
    
    async def answer_question(
        self,
        question: str,
        k: int = 5
    ) -> dict:
        """Answer question using RAG."""
        # 1. Retrieve relevant chunks
        chunks = await self.memory.recall(question, k=k)
        
        # 2. Build context
        context = "\n\n".join([c.text for c in chunks])
        
        # 3. Generate answer
        prompt = f"""Context:
{context}

Question: {question}

Answer based on the context above:"""
        
        answer = await self.llm.generate(prompt)
        
        # 4. Return with sources
        return {
            "answer": answer,
            "sources": [
                {
                    "text": c.text,
                    "metadata": c.metadata,
                    "relevance": c.score
                }
                for c in chunks
            ]
        }
```

**Features:**
- Automatic chunking
- Semantic retrieval
- Source attribution
- Context-aware answers

---

## Architecture Patterns

### Pattern 1: Multi-Tier Caching

```
Ephemeral (60s)
    ↓ (on access)
Session (1h)
    ↓ (on importance)
Persistent (forever)
```

**Use case:** Fast access to frequently used data, with automatic promotion.

---

### Pattern 2: User Isolation

```
Each user has isolated memory space
Filter by user_id metadata
Separate sessions per user
Privacy-aware storage
```

**Use case:** Multi-tenant applications, user-specific data.

---

### Pattern 3: Event Sourcing

```
Store every event
Replay for state reconstruction
Audit trail included
Compaction for old events
```

**Use case:** Audit requirements, state management.

---

## Summary

Real-world examples demonstrate:

**Standalone:**
- User preferences
- Session management
- Production deployment

**Applications:**
- Chatbot with memory
- Knowledge base
- RAG system

**Patterns:**
- Multi-tier caching
- User isolation
- Event sourcing

**Run All Real-World Examples:**

```bash
cd examples/05-real-world

# Standalone
python 02_user_preferences.py
python 03_session_management.py
python 04_production_deployment.py

# Applications
python chatbot/01_conversation_memory.py
python knowledge-base/01_knowledge_management.py
python rag-system/01_document_qa.py
```

---

## Production Checklist

Before deploying to production:

- [ ] Configure Redis with persistence
- [ ] Set up vector database (Qdrant/Pinecone)
- [ ] Enable audit logging
- [ ] Enable PII detection
- [ ] Use environment variables for secrets
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (ELK)
- [ ] Set up alerts
- [ ] Implement backup strategy
- [ ] Load test your configuration
- [ ] Document your architecture
- [ ] Set up CI/CD pipelines

---

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Production Deployment**

    ---

    Deploy to production with confidence.

    [:octicons-arrow-right-24: Deployment Guide](../deployment/production.md)

-   :material-speedometer:{ .lg .middle } **Performance**

    ---

    Optimize for production workloads.

    [:octicons-arrow-right-24: Performance Guide](../deployment/performance.md)

-   :material-shield-lock:{ .lg .middle } **Security**

    ---

    Secure your deployment.

    [:octicons-arrow-right-24: Security Guide](../deployment/security.md)

</div>
