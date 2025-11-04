"""
Comprehensive examples demonstrating all 4 embedder providers in Axon Memory SDK.

This example shows:
1. OpenAI Embeddings (API-based, paid)
2. Voyage AI Embeddings (API-based, paid)
3. Sentence Transformers (Local, free)
4. HuggingFace Transformers (Local, free)
5. Cache effectiveness across providers
6. Integration with InMemoryAdapter for semantic search
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from axon.embedders import (
    OpenAIEmbedder,
    VoyageAIEmbedder,
    SentenceTransformerEmbedder,
    HuggingFaceEmbedder,
    get_global_cache,
    clear_global_cache,
)
from axon.adapters import InMemoryAdapter
from axon.models import MemoryEntry, MemoryMetadata

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
print(f"📝 Loaded environment from: {env_path}")
print(f"   OpenAI API Key: {'✅ Found' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
print(f"   Voyage API Key: {'✅ Found' if os.getenv('VOYAGE_API_KEY') else '❌ Missing'}")


# ============================================================================
# Example 1: OpenAI Embeddings (API-based)
# ============================================================================
async def example_openai():
    """Demonstrate OpenAI embeddings with caching."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: OpenAI Embeddings")
    print("=" * 70)
    
    # Initialize embedder (requires OPENAI_API_KEY environment variable)
    api_key = os.getenv("OPENAI_API_KEY", "sk-test-key")
    embedder = OpenAIEmbedder(
        api_key=api_key,
        model="text-embedding-3-small",  # 1536 dimensions, cost-effective
        cache_enabled=True,
    )
    
    print(f"Model: {embedder.model_name}")
    print(f"Dimension: {embedder.get_dimension()}")
    
    # Embed single text
    text = "I love Python programming"
    embedding = await embedder.embed(text)
    print(f"\nEmbedding for '{text}':")
    print(f"  Vector length: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")
    
    # Embed again (should hit cache)
    cache = get_global_cache()
    stats_before = cache.get_stats()
    
    embedding2 = await embedder.embed(text)
    stats_after = cache.get_stats()
    
    print(f"\nCache effectiveness:")
    print(f"  Hits before: {stats_before['hits']}")
    print(f"  Hits after: {stats_after['hits']}")
    print(f"  Hit rate: {stats_after['hit_rate_percent']:.1f}%")
    
    # Batch embedding
    texts = [
        "Machine learning is fascinating",
        "Deep learning uses neural networks",
        "Python is great for data science",
    ]
    embeddings = await embedder.embed_batch(texts)
    print(f"\nBatch embedded {len(embeddings)} texts")
    
    print("✅ OpenAI embeddings working perfectly!")


# ============================================================================
# Example 2: Voyage AI Embeddings (API-based)
# ============================================================================
async def example_voyage():
    """Demonstrate Voyage AI embeddings."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Voyage AI Embeddings")
    print("=" * 70)
    
    # Initialize embedder (requires VOYAGE_API_KEY environment variable)
    api_key = os.getenv("VOYAGE_API_KEY", "pa-test-key")
    embedder = VoyageAIEmbedder(
        api_key=api_key,
        model="voyage-2",  # 1024 dimensions, general purpose
        cache_enabled=True,
    )
    
    print(f"Model: {embedder.model_name}")
    print(f"Dimension: {embedder.get_dimension()}")
    
    # Embed technical text
    text = "def quicksort(arr): return sorted(arr)"
    embedding = await embedder.embed(text)
    print(f"\nEmbedding for code snippet:")
    print(f"  Vector length: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")
    
    # Batch with different domains
    texts = [
        "SELECT * FROM users WHERE active = true",
        "async function fetchData() { await api.get('/data'); }",
        "import pandas as pd; df = pd.read_csv('data.csv')",
    ]
    embeddings = await embedder.embed_batch(texts)
    print(f"\nBatch embedded {len(embeddings)} code snippets")


# ============================================================================
# Example 3: Sentence Transformers (Local, Free)
# ============================================================================
async def example_sentence_transformer():
    """Demonstrate local Sentence Transformers embeddings."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Sentence Transformers (Local & Free)")
    print("=" * 70)
    
    # Initialize embedder (downloads model on first use, ~90MB)
    embedder = SentenceTransformerEmbedder(
        model_name="all-MiniLM-L6-v2",  # 384 dimensions, fast & lightweight
        cache_enabled=True,
    )
    
    print(f"Model: {embedder.model_name}")
    print(f"Dimension: {embedder.get_dimension()}")
    print("Note: Runs locally, no API costs!")
    
    # Embed conversational text
    text = "How do I reset my password?"
    embedding = await embedder.embed(text)
    print(f"\nEmbedding for '{text}':")
    print(f"  Vector length: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")
    
    # Batch FAQ embeddings
    faqs = [
        "What are your business hours?",
        "How can I track my order?",
        "What is your return policy?",
        "Do you offer international shipping?",
    ]
    embeddings = await embedder.embed_batch(faqs)
    print(f"\nBatch embedded {len(embeddings)} FAQ questions")


# ============================================================================
# Example 4: HuggingFace Transformers (Local, Free)
# ============================================================================
async def example_huggingface():
    """Demonstrate HuggingFace BGE embeddings."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: HuggingFace BGE Embeddings (Local & Free)")
    print("=" * 70)
    
    # Initialize embedder (downloads model on first use, ~400MB)
    embedder = HuggingFaceEmbedder(
        model_name="BAAI/bge-base-en-v1.5",  # 768 dimensions, high quality
        cache_enabled=True,
    )
    
    print(f"Model: {embedder.model_name}")
    print(f"Dimension: {embedder.get_dimension()}")
    print("Note: State-of-the-art quality, runs locally!")
    
    # Embed semantic search query
    text = "Best practices for microservices architecture"
    embedding = await embedder.embed(text)
    print(f"\nEmbedding for '{text}':")
    print(f"  Vector length: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")
    
    # Batch document embeddings
    docs = [
        "Microservices communicate via REST APIs or message queues",
        "Each microservice should have its own database",
        "Use API gateways for external communication",
    ]
    embeddings = await embedder.embed_batch(docs)
    print(f"\nBatch embedded {len(embeddings)} documents")


# ============================================================================
# Example 5: Cache Effectiveness Comparison
# ============================================================================
async def example_cache_comparison():
    """Compare cache effectiveness across embedders."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Cache Effectiveness Across Embedders")
    print("=" * 70)
    
    # Clear cache for fresh start
    clear_global_cache()
    
    # Create embedders - include ALL 4 if API keys available
    embedders = []
    
    # Try adding OpenAI if API key exists
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        embedders.append(("OpenAI", OpenAIEmbedder(api_key=openai_key, cache_enabled=True)))
        print("✅ OpenAI embedder added")
    
    # Try adding Voyage if API key exists
    voyage_key = os.getenv("VOYAGE_API_KEY")
    if voyage_key:
        embedders.append(("VoyageAI", VoyageAIEmbedder(api_key=voyage_key, cache_enabled=True)))
        print("✅ Voyage AI embedder added")
    
    # Always add local models
    embedders.append(("SentenceTransformer", SentenceTransformerEmbedder(cache_enabled=True)))
    embedders.append(("HuggingFace", HuggingFaceEmbedder(cache_enabled=True)))
    print("✅ Local embedders added")
    
    text = "The quick brown fox jumps over the lazy dog"
    
    print(f"\nTesting cache effectiveness with {len(embedders)} embedders:\n")
    for name, embedder in embedders:
        # First embed (cache miss)
        await embedder.embed(text)
        
        # Second embed (cache hit)
        await embedder.embed(text)
        
        stats = get_global_cache().get_stats()
        print(f"{name:20} - Hits: {stats['hits']:2}, Misses: {stats['misses']:2}, Hit Rate: {stats['hit_rate_percent']:.1f}%")
    
    print("\n✅ Cache working perfectly - second embeds hit cache!")


# ============================================================================
# Example 6: Integration with InMemoryAdapter (Semantic Search)
# ============================================================================
async def example_semantic_search():
    """Demonstrate end-to-end semantic search with embedder + adapter."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Semantic Search with Embedder + InMemoryAdapter")
    print("=" * 70)
    
    # Use local embedder for fast, free search
    embedder = SentenceTransformerEmbedder(cache_enabled=True)
    adapter = InMemoryAdapter()
    
    # Store knowledge base
    knowledge_base = [
        "Python is a high-level programming language",
        "JavaScript is used for web development",
        "Machine learning enables computers to learn from data",
        "Docker containers package applications with dependencies",
        "Kubernetes orchestrates containerized applications",
    ]
    
    print("Storing knowledge base...")
    for idx, text in enumerate(knowledge_base):
        embedding = await embedder.embed(text)
        entry = MemoryEntry(
            id=f"kb-{idx}",
            text=text,
            embedding=embedding,
            metadata=MemoryMetadata(tags=["knowledge_base"], importance=0.8),
        )
        await adapter.save(entry)
    
    print(f"Stored {len(knowledge_base)} entries")
    
    # Semantic search queries
    queries = [
        "What language is good for AI?",
        "How to deploy applications?",
        "Frontend development tools?",
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        
        # Embed query
        query_embedding = await embedder.embed(query)
        
        # Search with cosine similarity (k=2 for top 2 results)
        results = await adapter.query(
            vector=query_embedding,
            k=2,
        )
        
        print(f"  Top results:")
        for i, result in enumerate(results, 1):
            print(f"    {i}. {result.text}")


# ============================================================================
# Example 7: Choosing the Right Embedder
# ============================================================================
def example_embedder_selection_guide():
    """Guide for choosing the right embedder for your use case."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Embedder Selection Guide")
    print("=" * 70)
    
    guide = """
    ┌─────────────────────┬──────────┬──────┬───────────┬─────────────────┐
    │ Embedder            │ Cost     │ Dims │ Quality   │ Best For        │
    ├─────────────────────┼──────────┼──────┼───────────┼─────────────────┤
    │ OpenAI              │ $0.02/1M │ 1536 │ Excellent │ Production apps │
    │ text-embedding-3    │ tokens   │      │           │ with budget     │
    ├─────────────────────┼──────────┼──────┼───────────┼─────────────────┤
    │ Voyage AI           │ $0.12/1M │ 1024 │ Excellent │ Code search,    │
    │ voyage-2            │ tokens   │      │           │ technical docs  │
    ├─────────────────────┼──────────┼──────┼───────────┼─────────────────┤
    │ Sentence            │ FREE     │  384 │ Good      │ Prototyping,    │
    │ Transformers        │ (local)  │      │           │ small datasets  │
    ├─────────────────────┼──────────┼──────┼───────────┼─────────────────┤
    │ HuggingFace BGE     │ FREE     │  768 │ Very Good │ High quality    │
    │ bge-base-en-v1.5    │ (local)  │      │           │ without API     │
    └─────────────────────┴──────────┴──────┴───────────┴─────────────────┘
    
    Recommendations:
    
    1. **Production with Budget**: OpenAI text-embedding-3-small
       - Best balance of cost, quality, and speed
       - Reliable API with 99.9% uptime
    
    2. **Code & Technical Content**: Voyage AI voyage-code-2
       - Specialized for code understanding
       - Superior for programming languages
    
    3. **Prototyping & Development**: Sentence Transformers
       - No API costs, fast iteration
       - Good enough for most use cases
       - Small model size (~90MB)
    
    4. **High Quality Local**: HuggingFace BGE
       - State-of-the-art open source
       - Comparable to commercial APIs
       - Larger model (~400MB)
    
    5. **Hybrid Approach**: 
       - Development: Sentence Transformers (free, fast)
       - Production: OpenAI (reliable, scalable)
       - Switch by changing one line of code!
    """
    
    print(guide)


# ============================================================================
# Main Execution
# ============================================================================
async def main():
    """Run all examples - automatically detects available API keys."""
    print("\n")
    print("=" * 70)
    print(" AXON MEMORY SDK - EMBEDDER EXAMPLES")
    print("=" * 70)
    
    # Run API-based examples if keys are available
    if os.getenv("OPENAI_API_KEY"):
        print("\n🔑 OpenAI API key detected - running OpenAI example...")
        await example_openai()
    else:
        print("\n⏭️  Skipping OpenAI example (no API key)")
    
    if os.getenv("VOYAGE_API_KEY"):
        print("\n🔑 Voyage API key detected - running Voyage AI example...")
        await example_voyage()
    else:
        print("\n⏭️  Skipping Voyage AI example (no API key)")
    
    # Free local embedders (always work)
    await example_sentence_transformer()
    await example_huggingface()
    
    # Cache comparison (automatically uses available embedders)
    await example_cache_comparison()
    
    # Semantic search demo
    await example_semantic_search()
    
    # Selection guide
    example_embedder_selection_guide()
    
    print("\n" + "=" * 70)
    print(" ALL EXAMPLES COMPLETED!")
    print("=" * 70)
    print(f"\nGlobal cache stats: {get_global_cache().get_stats()}")


if __name__ == "__main__":
    asyncio.run(main())
