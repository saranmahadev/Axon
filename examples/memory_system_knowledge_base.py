"""
Knowledge Base Memory Example.

Demonstrates using MemorySystem for a knowledge management system:
- Storing documents and articles
- Semantic search and retrieval
- Topic-based organization
- Importance-based prioritization
- Knowledge discovery and connections

This example simulates a technical documentation system that stores,
organizes, and retrieves knowledge efficiently.
"""

import asyncio
from datetime import datetime

from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.models.filter import Filter


async def main():
    """Demonstrate knowledge base with memory."""

    print("=" * 70)
    print("AxonML Memory System - Knowledge Base Example")
    print("=" * 70)
    print()

    # ========================================================================
    # Step 1: Configure Knowledge Base Memory
    # ========================================================================
    print("Step 1: Configuring Knowledge Base Memory System")
    print("-" * 70)

    config = MemoryConfig(
        # Ephemeral: Frequently accessed queries and temporary notes
        ephemeral=EphemeralPolicy(
            adapter_type="memory", max_entries=50, ttl_seconds=600  # 10 minutes
        ),
        # Session: Recently added or updated documents
        session=SessionPolicy(
            adapter_type="memory", max_entries=200, ttl_seconds=86400  # 24 hours
        ),
        # Persistent: Core knowledge base articles
        persistent=PersistentPolicy(adapter_type="memory", max_entries=10000),
        default_tier="persistent",  # Default to persistent for knowledge
        enable_promotion=True,
        enable_demotion=True,
    )

    print("✓ Memory configured for knowledge base:")
    print("  - Ephemeral: 50 entries, 10min TTL (query cache)")
    print("  - Session: 200 entries, 24hr TTL (recent updates)")
    print("  - Persistent: 10000 entries (core knowledge)")
    print()

    # ========================================================================
    # Step 2: Initialize Knowledge Base
    # ========================================================================
    async with MemorySystem(config=config) as kb:
        print("Step 2: Initializing Knowledge Base")
        print("-" * 70)
        print("✓ Knowledge base initialized")
        print()

        # ====================================================================
        # Step 3: Add Technical Documentation
        # ====================================================================
        print("Step 3: Adding Technical Documentation")
        print("-" * 70)

        # Python documentation
        await kb.store(
            "Python list comprehensions provide a concise way to create lists. "
            "Syntax: [expression for item in iterable if condition]. "
            "Example: squares = [x**2 for x in range(10)]",
            importance=0.95,
            tags=["python", "syntax", "lists", "tutorial"],
            metadata={
                "category": "programming",
                "language": "python",
                "difficulty": "beginner",
                "last_updated": datetime.now().isoformat(),
            },
        )

        await kb.store(
            "Python async/await enables asynchronous programming. "
            "Use async def to define coroutines, await to call them. "
            "Requires asyncio event loop. Great for I/O-bound operations.",
            importance=0.9,
            tags=["python", "async", "concurrency", "advanced"],
            metadata={
                "category": "programming",
                "language": "python",
                "difficulty": "advanced",
                "last_updated": datetime.now().isoformat(),
            },
        )

        # Machine Learning documentation
        await kb.store(
            "Neural networks consist of interconnected layers of nodes. "
            "Each connection has a weight that's adjusted during training. "
            "Common architectures: feedforward, CNN, RNN, transformer.",
            importance=0.95,
            tags=["machine-learning", "neural-networks", "deep-learning"],
            metadata={
                "category": "ai-ml",
                "topic": "neural-networks",
                "difficulty": "intermediate",
                "last_updated": datetime.now().isoformat(),
            },
        )

        await kb.store(
            "Gradient descent is an optimization algorithm for finding "
            "minimum of a function. Updates parameters in direction of "
            "steepest descent. Variants: SGD, Adam, RMSprop.",
            importance=0.9,
            tags=["machine-learning", "optimization", "algorithms"],
            metadata={
                "category": "ai-ml",
                "topic": "optimization",
                "difficulty": "intermediate",
                "last_updated": datetime.now().isoformat(),
            },
        )

        # Database documentation
        await kb.store(
            "Database indexing improves query performance by creating "
            "data structures for fast lookups. B-tree is most common. "
            "Trade-off: faster reads, slower writes, more storage.",
            importance=0.85,
            tags=["databases", "indexing", "performance"],
            metadata={
                "category": "databases",
                "topic": "optimization",
                "difficulty": "intermediate",
                "last_updated": datetime.now().isoformat(),
            },
        )

        # API documentation
        await kb.store(
            "REST API best practices: use proper HTTP methods (GET, POST, PUT, DELETE), "
            "return appropriate status codes, version your API, "
            "implement rate limiting and authentication.",
            importance=0.8,
            tags=["api", "rest", "web-development", "best-practices"],
            metadata={
                "category": "web-development",
                "topic": "api-design",
                "difficulty": "intermediate",
                "last_updated": datetime.now().isoformat(),
            },
        )

        print("✓ Added 6 technical articles to knowledge base")
        print()

        # ====================================================================
        # Step 4: Search Knowledge Base - Topic-Based
        # ====================================================================
        print("Step 4: Topic-Based Knowledge Retrieval")
        print("-" * 70)

        # Search for Python content
        python_docs = await kb.recall(
            "python programming syntax", k=10, filter=Filter(tags=["python"])
        )

        print(f"Found {len(python_docs)} Python-related articles:")
        for doc in python_docs:
            print(f"  - {doc.text[:60]}...")
            print(f"    Tags: {', '.join(doc.metadata.tags)}")
        print()

        # Search for machine learning content
        ml_docs = await kb.recall(
            "machine learning neural networks", k=10, filter=Filter(tags=["machine-learning"])
        )

        print(f"Found {len(ml_docs)} Machine Learning articles:")
        for doc in ml_docs:
            print(f"  - {doc.text[:60]}...")
            print(f"    Tags: {', '.join(doc.metadata.tags)}")
        print()

        # ====================================================================
        # Step 5: Search by Importance (Critical Knowledge)
        # ====================================================================
        print("Step 5: Retrieving Critical Knowledge (High Importance)")
        print("-" * 70)

        critical_docs = await kb.recall("programming concepts", k=20, min_importance=0.9)

        print(f"Found {len(critical_docs)} critical articles (importance ≥ 0.9):")
        for doc in critical_docs:
            print(f"  - Importance: {doc.importance:.2f}")
            print(f"    Content: {doc.text[:70]}...")
        print()

        # ====================================================================
        # Step 6: Search by Difficulty Level
        # ====================================================================
        print("Step 6: Filtering by Difficulty Level")
        print("-" * 70)

        # Get all documents
        all_docs = await kb.recall("technical documentation", k=50)

        # Filter by metadata
        beginner_docs = [
            d for d in all_docs if getattr(d.metadata, "difficulty", None) == "beginner"
        ]
        advanced_docs = [
            d for d in all_docs if getattr(d.metadata, "difficulty", None) == "advanced"
        ]

        print(f"Beginner-level articles: {len(beginner_docs)}")
        for doc in beginner_docs:
            print(f"  - {doc.text[:60]}...")
        print()

        print(f"Advanced-level articles: {len(advanced_docs)}")
        for doc in advanced_docs:
            print(f"  - {doc.text[:60]}...")
        print()

        # ====================================================================
        # Step 7: Add Temporary Research Notes
        # ====================================================================
        print("Step 7: Adding Temporary Research Notes")
        print("-" * 70)

        # Add low-importance research notes (will go to ephemeral tier)
        await kb.store(
            "Quick note: Check latest Python 3.12 features for documentation update",
            importance=0.2,
            tags=["todo", "research", "python"],
            metadata={"type": "note", "priority": "low"},
        )

        await kb.store(
            "Reminder: Update neural network diagrams with new architecture",
            importance=0.3,
            tags=["todo", "graphics", "machine-learning"],
            metadata={"type": "reminder", "priority": "medium"},
        )

        print("✓ Added 2 temporary research notes (low importance → ephemeral tier)")
        print()

        # ====================================================================
        # Step 8: Knowledge Discovery - Related Content
        # ====================================================================
        print("Step 8: Knowledge Discovery - Finding Related Content")
        print("-" * 70)

        # Find content related to optimization
        optimization_content = await kb.recall("optimization performance", k=10)

        print(f"Found {len(optimization_content)} optimization-related articles:")
        for doc in optimization_content:
            categories = set()
            for tag in doc.metadata.tags:
                if tag in ["machine-learning", "databases", "algorithms"]:
                    categories.add(tag)
            print(f"  - Categories: {', '.join(categories) if categories else 'general'}")
            print(f"    Content: {doc.text[:70]}...")
        print()

        # ====================================================================
        # Step 9: View Knowledge Base Statistics
        # ====================================================================
        print("Step 9: Knowledge Base Statistics")
        print("-" * 70)

        stats = kb.get_statistics()

        print(f"Total articles stored: {stats['total_operations']['stores']}")
        print(f"Total searches performed: {stats['total_operations']['recalls']}")
        print()

        print("Articles per tier:")
        for tier, tier_stats in stats["tier_stats"].items():
            stores = tier_stats.get("stores", 0)
            if stores > 0:
                print(f"  {tier.capitalize()}: {stores} articles")
        print()

        # ====================================================================
        # Step 10: Analyze Content Distribution
        # ====================================================================
        print("Step 10: Content Distribution Analysis")
        print("-" * 70)

        # Get all content (using a generic query to retrieve everything)
        all_content = await kb.recall("documentation technical", k=100)

        # Analyze by category
        categories = {}
        for doc in all_content:
            category = getattr(doc.metadata, "category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1

        print("Content by category:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} articles")
        print()

        # Analyze by importance
        high_importance = sum(1 for d in all_content if d.metadata.importance >= 0.9)
        medium_importance = sum(1 for d in all_content if 0.5 <= d.metadata.importance < 0.9)
        low_importance = sum(1 for d in all_content if d.metadata.importance < 0.5)

        print("Content by importance:")
        print(f"  High (≥0.9): {high_importance} articles")
        print(f"  Medium (0.5-0.9): {medium_importance} articles")
        print(f"  Low (<0.5): {low_importance} articles")
        print()

        # ====================================================================
        # Step 11: Trace Recent Operations
        # ====================================================================
        print("Step 11: Recent Knowledge Base Operations")
        print("-" * 70)

        trace = kb.get_trace_events(limit=10)

        store_ops = [e for e in trace if e.operation == "store"]
        recall_ops = [e for e in trace if e.operation == "recall"]

        print("Last 10 operations:")
        print(f"  Stores:  {len(store_ops)}")
        print(f"  Recalls: {len(recall_ops)}")
        print()

        if trace:
            avg_duration = sum(e.duration_ms for e in trace) / len(trace)
            print(f"Average operation time: {avg_duration:.2f}ms")

            # Find slowest operation
            slowest = max(trace, key=lambda e: e.duration_ms)
            print(f"Slowest operation: {slowest.operation} ({slowest.duration_ms:.2f}ms)")
        print()

        # ====================================================================
        # Step 12: Summary
        # ====================================================================
        print("=" * 70)
        print("Knowledge Base Summary")
        print("=" * 70)

        final_stats = kb.get_statistics()

        print(f"✓ Knowledge base contains {final_stats['total_operations']['stores']} articles")
        print(f"✓ Performed {final_stats['total_operations']['recalls']} knowledge retrievals")
        print(f"✓ Covered {len(categories)} categories")
        print("✓ Automatically tiered by importance:")
        print("    - Critical knowledge: persistent tier")
        print("    - Standard docs: session tier")
        print("    - Temporary notes: ephemeral tier")
        print()
        print("Knowledge base capabilities:")
        print("  ✓ Semantic search across all content")
        print("  ✓ Tag-based filtering and organization")
        print("  ✓ Importance-based prioritization")
        print("  ✓ Metadata-rich article storage")
        print("  ✓ Topic discovery and related content")
        print("  ✓ Performance tracking and analytics")
        print()
        print("Example completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
