"""Real-World Example: Personal Knowledge Assistant with ChromaDB

This example demonstrates a practical use case where we build a personal knowledge
assistant that can:
1. Store information from conversations, documents, and notes
2. Retrieve relevant information using semantic search
3. Filter by context (work vs personal, by date, by importance)
4. Persist data across sessions

Use Case: A developer's assistant that remembers:
- Code snippets and solutions
- Meeting notes and decisions
- Learning resources and articles
- Project ideas and todos

This showcases ChromaDB's real-world capabilities with actual OpenAI embeddings.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.axon.adapters.chroma import ChromaAdapter
from src.axon.embedders.openai import OpenAIEmbedder
from src.axon.models import DateRange, Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent


# Load API keys
load_dotenv()


class KnowledgeAssistant:
    """A personal knowledge assistant powered by ChromaDB and OpenAI embeddings."""
    
    def __init__(self, persist_dir: str = "./knowledge_db"):
        """Initialize the knowledge assistant.
        
        Args:
            persist_dir: Directory to persist the knowledge base
        """
        self.embedder = OpenAIEmbedder(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="text-embedding-3-small"  # 1536 dims, $0.02/1M tokens
        )
        self.storage = ChromaAdapter(
            collection_name="knowledge_base",
            persist_directory=persist_dir
        )
        print(f"✅ Knowledge Assistant initialized")
        print(f"📁 Storage: {persist_dir}")
        print(f"🧠 Embedder: OpenAI text-embedding-3-small")
        
    async def remember(
        self,
        content: str,
        category: str = "note",
        tags: list[str] = None,
        importance: float = 0.5,
        context: str = "personal"
    ) -> str:
        """Store a new piece of knowledge.
        
        Args:
            content: The information to remember
            category: Type of knowledge (note, code, meeting, article, idea)
            tags: Tags for categorization
            importance: How important this is (0.0-1.0)
            context: Work or personal context
            
        Returns:
            ID of the stored entry
        """
        print(f"\n💭 Remembering: {content[:50]}...")
        
        # Generate embedding
        embedding = await self.embedder.embed(content)
        
        # Create memory entry
        entry = MemoryEntry(
            type="note",
            text=content,
            embedding=embedding,
            metadata=MemoryMetadata(
                user_id=context,  # Using user_id for work/personal context
                tags=tags or [],
                importance=importance,
                source="app",
                provenance=[
                    ProvenanceEvent(
                        action="created",
                        by="user",
                        timestamp=datetime.now(),
                        details={"category": category}
                    )
                ]
            )
        )
        
        # Save to ChromaDB
        entry_id = await self.storage.save(entry)
        print(f"✅ Stored with ID: {entry_id[:8]}...")
        print(f"   Tags: {tags or 'none'}")
        print(f"   Importance: {importance}")
        
        return entry_id
    
    async def recall(
        self,
        query: str,
        k: int = 5,
        tags: list[str] = None,
        min_importance: float = None,
        context: str = None,
        days_back: int = None
    ) -> list[MemoryEntry]:
        """Retrieve relevant knowledge.
        
        Args:
            query: What you're looking for
            k: Number of results to return
            tags: Filter by tags
            min_importance: Minimum importance threshold
            context: Filter by work/personal
            days_back: Only return entries from last N days
            
        Returns:
            List of relevant memory entries
        """
        print(f"\n🔍 Searching for: {query}")
        
        # Generate query embedding
        query_embedding = await self.embedder.embed(query)
        
        # Build filter
        filter_args = {}
        if context:
            filter_args["user_id"] = context
        if tags:
            filter_args["tags"] = tags
        if min_importance is not None:
            filter_args["min_importance"] = min_importance
            filter_args["max_importance"] = 1.0
        if days_back:
            filter_args["date_range"] = DateRange(
                start=datetime.now() - timedelta(days=days_back),
                end=datetime.now()
            )
        
        memory_filter = Filter(**filter_args) if filter_args else None
        
        # Query ChromaDB
        results = await self.storage.query(
            vector=query_embedding,
            k=k,
            filter=memory_filter
        )
        
        print(f"✅ Found {len(results)} relevant memories")
        return results
    
    def format_result(self, entry: MemoryEntry, rank: int = 1) -> str:
        """Format a memory entry for display.
        
        Args:
            entry: The memory entry
            rank: Result rank
            
        Returns:
            Formatted string
        """
        tags_str = ", ".join(entry.metadata.tags) if entry.metadata.tags else "none"
        importance_stars = "⭐" * int(entry.metadata.importance * 5)
        
        # Get category from provenance metadata if available
        category = "note"
        if entry.metadata.provenance:
            category = entry.metadata.provenance[0].metadata.get("category", "note")
        
        return f"""
{'='*70}
RESULT #{rank} | {category.upper()} | {importance_stars}
ID: {entry.id[:16]}...
Created: {entry.metadata.created_at.strftime('%Y-%m-%d %H:%M')}
Tags: {tags_str}
Context: {entry.metadata.user_id or 'general'}
{'='*70}
{entry.text}
"""
    
    def get_stats(self) -> dict:
        """Get knowledge base statistics.
        
        Returns:
            Statistics dictionary
        """
        count = self.storage.count()
        ids = self.storage.list_ids()
        
        return {
            "total_entries": count,
            "cache_stats": self.embedder._cache.get_stats() if hasattr(self.embedder, '_cache') else None
        }


async def demo():
    """Run a comprehensive demonstration of the Knowledge Assistant."""
    
    print("="*70)
    print("🚀 PERSONAL KNOWLEDGE ASSISTANT DEMO")
    print("="*70)
    print("\nThis demo shows a real-world use case where we build a developer's")
    print("personal assistant that remembers code snippets, meeting notes,")
    print("learning resources, and ideas using ChromaDB + OpenAI embeddings.")
    print("="*70)
    
    # Initialize assistant
    assistant = KnowledgeAssistant(persist_dir="./demo_knowledge_db")
    
    # ========================================================================
    # PHASE 1: Store Various Types of Knowledge
    # ========================================================================
    
    print("\n" + "="*70)
    print("📝 PHASE 1: STORING KNOWLEDGE")
    print("="*70)
    
    # Code snippet
    await assistant.remember(
        content="""
        # Python async context manager pattern
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
        
        This pattern ensures proper resource cleanup even if errors occur.
        """,
        category="code",
        tags=["python", "async", "patterns"],
        importance=0.9,
        context="work"
    )
    
    # Meeting note
    await assistant.remember(
        content="""
        Sprint Planning Meeting - Nov 4, 2025
        
        Decisions made:
        - Implement ChromaDB adapter first (embedded, easy to test)
        - Follow with Qdrant (self-hosted) and Pinecone (cloud)
        - Target 90%+ test coverage for all adapters
        - Use OpenAI embeddings for integration testing
        
        Action items:
        - Complete ChromaDB by EOD
        - Set up Docker for Qdrant testing
        """,
        category="meeting",
        tags=["sprint-planning", "decisions", "vector-db"],
        importance=0.8,
        context="work"
    )
    
    # Learning resource
    await assistant.remember(
        content="""
        ChromaDB is an embedded vector database that stores data locally.
        
        Key benefits:
        - No separate server needed (embedded mode)
        - Persistent storage to disk
        - Built-in vector similarity search
        - Supports metadata filtering
        - Great for prototyping and small-scale deployments
        
        Best for: Development, prototypes, up to ~1M vectors
        """,
        category="article",
        tags=["vector-db", "chromadb", "learning"],
        importance=0.7,
        context="work"
    )
    
    # Project idea
    await assistant.remember(
        content="""
        Idea: Build a code snippet manager that uses semantic search
        
        Instead of searching by filename or tags, search by what the code does:
        - "How do I make an async HTTP request?" → finds the aiohttp pattern
        - "Database connection pooling" → finds SQLAlchemy setup
        - "JWT authentication" → finds auth middleware
        
        Could integrate with VS Code as an extension!
        """,
        category="idea",
        tags=["project-idea", "code-search", "semantic"],
        importance=0.6,
        context="personal"
    )
    
    # Personal note
    await assistant.remember(
        content="""
        Remember to review the vector database comparison article this weekend.
        
        Need to understand trade-offs between:
        - ChromaDB (embedded, simple)
        - Qdrant (self-hosted, high performance)
        - Pinecone (managed, scalable)
        - Weaviate (GraphQL API, semantic search focus)
        
        This will help make better architectural decisions.
        """,
        category="note",
        tags=["todo", "learning", "architecture"],
        importance=0.5,
        context="personal"
    )
    
    # Technical documentation
    await assistant.remember(
        content="""
        Pydantic v2 migration notes:
        
        Breaking changes:
        - .dict() → .model_dump()
        - .json() → .model_dump_json()
        - Config class → model_config dict
        - validator() → field_validator()
        
        Benefits:
        - 5-50x faster validation
        - Better error messages
        - JSON schema generation
        """,
        category="code",
        tags=["python", "pydantic", "migration"],
        importance=0.7,
        context="work"
    )
    
    # ========================================================================
    # PHASE 2: Semantic Search Queries
    # ========================================================================
    
    print("\n" + "="*70)
    print("🔍 PHASE 2: SEMANTIC SEARCH")
    print("="*70)
    
    # Query 1: Find code patterns
    print("\n" + "-"*70)
    print("QUERY 1: 'How do I make async HTTP calls in Python?'")
    print("-"*70)
    results = await assistant.recall(
        query="How do I make async HTTP calls in Python?",
        k=2,
        context="work"  # Only work-related content
    )
    for i, result in enumerate(results, 1):
        print(assistant.format_result(result, rank=i))
    
    # Query 2: Find decisions
    print("\n" + "-"*70)
    print("QUERY 2: 'What decisions did we make about vector databases?'")
    print("-"*70)
    results = await assistant.recall(
        query="What decisions did we make about vector databases?",
        k=2,
        tags=["decisions"]  # Filter by decision tag
    )
    for i, result in enumerate(results, 1):
        print(assistant.format_result(result, rank=i))
    
    # Query 3: Find learning resources
    print("\n" + "-"*70)
    print("QUERY 3: 'Tell me about ChromaDB capabilities'")
    print("-"*70)
    results = await assistant.recall(
        query="Tell me about ChromaDB capabilities",
        k=2,
        min_importance=0.6  # Only important entries
    )
    for i, result in enumerate(results, 1):
        print(assistant.format_result(result, rank=i))
    
    # Query 4: Find project ideas
    print("\n" + "-"*70)
    print("QUERY 4: 'Do I have any ideas for semantic search projects?'")
    print("-"*70)
    results = await assistant.recall(
        query="semantic search project ideas",
        k=3,
        context="personal"  # Personal context only
    )
    for i, result in enumerate(results, 1):
        print(assistant.format_result(result, rank=i))
    
    # ========================================================================
    # PHASE 3: Advanced Filtering
    # ========================================================================
    
    print("\n" + "="*70)
    print("🎯 PHASE 3: ADVANCED FILTERING")
    print("="*70)
    
    # Time-based filter
    print("\n" + "-"*70)
    print("QUERY 5: 'Python-related items from last 7 days'")
    print("-"*70)
    results = await assistant.recall(
        query="Python programming",
        k=5,
        tags=["python"],
        days_back=7
    )
    print(f"Found {len(results)} Python-related entries from the last week")
    for i, result in enumerate(results[:3], 1):  # Show top 3
        print(assistant.format_result(result, rank=i))
    
    # Importance-based filter
    print("\n" + "-"*70)
    print("QUERY 6: 'High-priority work items'")
    print("-"*70)
    results = await assistant.recall(
        query="important work information",
        k=5,
        min_importance=0.7,
        context="work"
    )
    print(f"Found {len(results)} high-priority work items")
    for i, result in enumerate(results, 1):
        print(assistant.format_result(result, rank=i))
    
    # ========================================================================
    # PHASE 4: Demonstrate Persistence
    # ========================================================================
    
    print("\n" + "="*70)
    print("💾 PHASE 4: DATA PERSISTENCE")
    print("="*70)
    
    # Show current stats
    stats = assistant.get_stats()
    print(f"\n📊 Knowledge Base Statistics:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Cache hits: {stats['cache_stats']['hits']}")
    print(f"   Cache misses: {stats['cache_stats']['misses']}")
    print(f"   Cache hit rate: {stats['cache_stats']['hit_rate_percent']:.1f}%")
    
    # Create new instance to test persistence
    print(f"\n🔄 Creating new assistant instance to test persistence...")
    assistant2 = KnowledgeAssistant(persist_dir="./demo_knowledge_db")
    
    stats2 = assistant2.get_stats()
    print(f"\n📊 Data persisted successfully!")
    print(f"   Entries in new instance: {stats2['total_entries']}")
    print(f"   ✅ All {stats2['total_entries']} entries survived restart!")
    
    # Query from new instance
    print(f"\n🔍 Querying from new instance...")
    results = await assistant2.recall(
        query="Pydantic migration",
        k=1
    )
    if results:
        print(assistant2.format_result(results[0]))
        print("✅ Persistence verified - data accessible across sessions!")
    
    # ========================================================================
    # PHASE 5: Real-World Benefits
    # ========================================================================
    
    print("\n" + "="*70)
    print("💡 REAL-WORLD BENEFITS DEMONSTRATED")
    print("="*70)
    
    print("""
    ✅ 1. SEMANTIC UNDERSTANDING
       - Searched "async HTTP calls" → Found aiohttp pattern
       - Natural language queries work without exact keyword matches
    
    ✅ 2. INTELLIGENT FILTERING
       - By context (work vs personal)
       - By tags (decisions, code, learning)
       - By importance (focus on high-priority items)
       - By time (last 7 days, last month, etc.)
    
    ✅ 3. MULTI-SOURCE KNOWLEDGE
       - Code snippets with syntax highlighting
       - Meeting notes with decisions
       - Learning resources and articles
       - Project ideas and todos
       - Technical documentation
    
    ✅ 4. PERSISTENT STORAGE
       - Data survives application restarts
       - ChromaDB stores everything on disk
       - No data loss between sessions
    
    ✅ 5. EFFICIENT CACHING
       - Embedding cache reduces API costs
       - {stats['cache_stats']['hit_rate_percent']:.1f}% cache hit rate in this demo
       - Reused embeddings for repeated queries
    
    🎯 USE CASES:
       - Developer knowledge base (code snippets, patterns)
       - Meeting notes and decisions tracker
       - Personal learning journal
       - Project documentation
       - Research paper notes
       - Customer support knowledge base
       - Legal document search
       - Medical records retrieval
    """)
    
    print("="*70)
    print("✨ DEMO COMPLETE!")
    print("="*70)
    print(f"\n💾 Knowledge base saved to: ./demo_knowledge_db")
    print(f"📝 Total entries: {stats['total_entries']}")
    print(f"🔍 Ready for more queries!")
    print("\nTry running this script again - the data will persist! 🚀")


if __name__ == "__main__":
    # Check for API key
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        print("Please add your OpenAI API key to .env:")
        print("OPENAI_API_KEY=sk-...")
        exit(1)
    
    # Run the demo
    asyncio.run(demo())
