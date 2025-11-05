"""Customer Support Knowledge Base - Real-World Application.

This example demonstrates a practical use case: a customer support knowledge base
that uses Qdrant for semantic search of support articles and FAQs.

Features:
    - Store support articles with metadata
    - Semantic search for customer queries
    - Filter by category, importance, and date
    - Track provenance for audit trail

Prerequisites:
    - Qdrant running at localhost:6333
    - OpenAI API key in .env file

Run:
    python examples/02_customer_support_kb.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.axon.adapters import QdrantAdapter
from src.axon.embedders import OpenAIEmbedder
from src.axon.models import DateRange, Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent


# Sample knowledge base articles
SUPPORT_ARTICLES = [
    {
        "title": "How to Reset Your Password",
        "content": "To reset your password: 1) Click 'Forgot Password' on the login page. 2) Enter your email address. 3) Check your email for a reset link. 4) Click the link and create a new password. The link expires in 24 hours.",
        "category": "account",
        "importance": 0.9,
        "tags": ["password", "security", "account"]
    },
    {
        "title": "Billing and Payment Methods",
        "content": "We accept all major credit cards (Visa, Mastercard, American Express) and PayPal. You can update your payment method in Settings > Billing. Charges appear on your statement as 'AXONML SERVICE'.",
        "category": "billing",
        "importance": 0.95,
        "tags": ["billing", "payment", "pricing"]
    },
    {
        "title": "API Rate Limits",
        "content": "Free tier: 100 requests/hour. Pro tier: 1,000 requests/hour. Enterprise: Custom limits. If you exceed your limit, you'll receive a 429 error. Rate limits reset every hour on the hour.",
        "category": "technical",
        "importance": 0.85,
        "tags": ["api", "limits", "technical"]
    },
    {
        "title": "Data Export and GDPR Compliance",
        "content": "Users can export their data at any time from Settings > Privacy. We comply with GDPR and will delete all user data within 30 days of account deletion. Data exports include all memories, metadata, and usage logs in JSON format.",
        "category": "privacy",
        "importance": 1.0,
        "tags": ["gdpr", "privacy", "export", "compliance"]
    },
    {
        "title": "Troubleshooting Connection Issues",
        "content": "If you're experiencing connection issues: 1) Check your internet connection. 2) Verify the API endpoint URL. 3) Check for firewall or proxy blocking. 4) Try using a different network. 5) Contact support if issues persist.",
        "category": "technical",
        "importance": 0.8,
        "tags": ["troubleshooting", "connection", "technical"]
    },
    {
        "title": "Understanding Vector Embeddings",
        "content": "Vector embeddings are numerical representations of text that capture semantic meaning. Our system uses 1536-dimensional embeddings from OpenAI's text-embedding-3-small model. Similar concepts have similar embeddings, enabling semantic search.",
        "category": "education",
        "importance": 0.7,
        "tags": ["embeddings", "vector", "education", "ai"]
    },
    {
        "title": "Mobile App Installation",
        "content": "Download our app from the App Store (iOS) or Google Play Store (Android). Search for 'AxonML' and install. The app requires iOS 14+ or Android 8+. First-time setup takes about 2 minutes.",
        "category": "setup",
        "importance": 0.75,
        "tags": ["mobile", "installation", "setup"]
    },
    {
        "title": "Upgrading Your Subscription",
        "content": "Upgrade anytime from Settings > Subscription. Changes take effect immediately. You'll be charged a prorated amount for the current billing period. No data is lost during upgrades. Downgrading requires contacting support.",
        "category": "billing",
        "importance": 0.85,
        "tags": ["subscription", "upgrade", "billing"]
    },
    {
        "title": "Data Retention Policies",
        "content": "Free tier: 30 days retention. Pro tier: 1 year retention. Enterprise: Custom retention. Archived data can be restored within the retention period. After expiration, data is permanently deleted and cannot be recovered.",
        "category": "privacy",
        "importance": 0.9,
        "tags": ["retention", "privacy", "data"]
    },
    {
        "title": "Integrating with LangChain",
        "content": "AxonML integrates seamlessly with LangChain. Use our StorageAdapter as a custom memory backend. Install with: pip install axonml langchain. See our documentation for code examples and best practices.",
        "category": "integration",
        "importance": 0.8,
        "tags": ["langchain", "integration", "developer"]
    }
]


class SupportKnowledgeBase:
    """Customer support knowledge base with semantic search."""
    
    def __init__(self, storage: QdrantAdapter, embedder: OpenAIEmbedder):
        """Initialize the knowledge base.
        
        Args:
            storage: Qdrant storage adapter
            embedder: OpenAI embedder
        """
        self.storage = storage
        self.embedder = embedder
    
    async def populate(self):
        """Populate the knowledge base with support articles."""
        print("\n📚 Populating knowledge base...")
        
        entries = []
        for article in SUPPORT_ARTICLES:
            # Create full text from title and content
            full_text = f"{article['title']}: {article['content']}"
            
            # Generate embedding
            embedding = await self.embedder.embed(full_text)
            
            # Create memory entry
            entry = MemoryEntry(
                text=full_text,
                embedding=embedding,
                metadata=MemoryMetadata(
                    source="system",
                    privacy_level="public",
                    importance=article["importance"],
                    tags=article["tags"],
                    provenance=[
                        ProvenanceEvent(
                            action="store",
                            by="knowledge_base_init",
                            metadata={
                                "category": article["category"],
                                "title": article["title"]
                            }
                        )
                    ]
                )
            )
            entries.append(entry)
        
        # Batch save
        await self.storage.bulk_save(entries)
        print(f"   ✓ Added {len(entries)} support articles")
        
        return entries
    
    async def search(self, query: str, category: str = None, limit: int = 3):
        """Search the knowledge base for relevant articles.
        
        Args:
            query: Customer question
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of relevant articles
        """
        # Generate query embedding
        query_embedding = await self.embedder.embed(query)
        
        # Build filter
        filter_obj = None
        if category:
            filter_obj = Filter(tags=[category])
        
        # Search
        results = await self.storage.query(
            query_embedding,
            filter=filter_obj,
            limit=limit
        )
        
        return results
    
    async def get_by_category(self, category: str):
        """Get all articles in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of articles in category
        """
        # Use a dummy embedding for broad search
        dummy_embedding = [0.0] * 1536
        
        results = await self.storage.query(
            dummy_embedding,
            filter=Filter(tags=[category]),
            limit=100
        )
        
        return results
    
    async def get_critical_articles(self):
        """Get all high-importance articles.
        
        Returns:
            List of critical articles
        """
        dummy_embedding = [0.0] * 1536
        
        results = await self.storage.query(
            dummy_embedding,
            filter=Filter(min_importance=0.9),
            limit=100
        )
        
        return results


async def demo_customer_queries(kb: SupportKnowledgeBase):
    """Demonstrate customer support queries."""
    
    print("\n" + "=" * 60)
    print("🎯 CUSTOMER SUPPORT QUERY DEMO")
    print("=" * 60)
    
    # Sample customer queries
    queries = [
        "I forgot my password, how do I reset it?",
        "What payment methods do you accept?",
        "I'm getting rate limit errors from the API",
        "How do I export my data?",
        "How do I install the mobile app?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'─' * 60}")
        print(f"Query {i}: '{query}'")
        print(f"{'─' * 60}")
        
        results = await kb.search(query, limit=2)
        
        if results:
            print(f"\n📄 Top {len(results)} matching articles:\n")
            for j, result in enumerate(results, 1):
                # Extract title from provenance metadata
                title = "Unknown"
                if result.metadata.provenance:
                    prov_metadata = result.metadata.provenance[0].metadata
                    if prov_metadata and "title" in prov_metadata:
                        title = prov_metadata["title"]
                
                print(f"{j}. {title}")
                print(f"   Importance: {'⭐' * int(result.metadata.importance * 5)}")
                print(f"   Tags: {', '.join(result.metadata.tags)}")
                
                # Show snippet of content
                content = result.text.split(": ", 1)[1] if ": " in result.text else result.text
                snippet = content[:150] + "..." if len(content) > 150 else content
                print(f"   Content: {snippet}\n")
        else:
            print("   ❌ No results found")


async def demo_category_filtering(kb: SupportKnowledgeBase):
    """Demonstrate category-based filtering."""
    
    print("\n" + "=" * 60)
    print("📁 CATEGORY FILTERING DEMO")
    print("=" * 60)
    
    categories = ["billing", "technical", "privacy"]
    
    for category in categories:
        print(f"\n📂 Category: {category.upper()}")
        results = await kb.get_by_category(category)
        print(f"   Found {len(results)} articles")
        
        for result in results:
            if result.metadata.provenance:
                prov_metadata = result.metadata.provenance[0].metadata
                if prov_metadata and "title" in prov_metadata:
                    print(f"   • {prov_metadata['title']}")


async def demo_critical_articles(kb: SupportKnowledgeBase):
    """Demonstrate filtering by importance."""
    
    print("\n" + "=" * 60)
    print("⚠️  CRITICAL ARTICLES (Importance >= 0.9)")
    print("=" * 60)
    
    results = await kb.get_critical_articles()
    print(f"\n   Found {len(results)} critical articles:\n")
    
    for result in results:
        if result.metadata.provenance:
            prov_metadata = result.metadata.provenance[0].metadata
            if prov_metadata and "title" in prov_metadata:
                importance_stars = "⭐" * int(result.metadata.importance * 5)
                print(f"   • {prov_metadata['title']}")
                print(f"     {importance_stars} ({result.metadata.importance:.2f})\n")


async def main():
    """Run the customer support knowledge base demo."""
    
    print("\n" + "=" * 60)
    print("🎓 CUSTOMER SUPPORT KNOWLEDGE BASE")
    print("   Real-World Qdrant Application")
    print("=" * 60)
    
    # Load environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Please create a .env file with your OpenAI API key")
        return
    
    # Initialize
    print("\n🔧 Initializing system...")
    embedder = OpenAIEmbedder(api_key=api_key, model="text-embedding-3-small")
    storage = QdrantAdapter(
        url="http://localhost:6333",
        collection_name="customer_support_kb"
    )
    
    # Create knowledge base
    kb = SupportKnowledgeBase(storage, embedder)
    
    # Populate with articles
    await kb.populate()
    
    # Run demos
    await demo_customer_queries(kb)
    await demo_category_filtering(kb)
    await demo_critical_articles(kb)
    
    # Statistics
    print("\n" + "=" * 60)
    print("📊 KNOWLEDGE BASE STATISTICS")
    print("=" * 60)
    
    total = await storage.count_async()
    print(f"\n   Total Articles: {total}")
    print(f"   Collection: customer_support_kb")
    print(f"   Embedding Model: text-embedding-3-small")
    print(f"   Vector Dimensions: 1536")
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("\n💡 Next steps:")
    print("   - Add more support articles")
    print("   - Implement user feedback tracking")
    print("   - Add article versioning")
    print("   - Build a web interface")
    print("   - View in Qdrant dashboard: http://localhost:6333/dashboard")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
