"""
Performance Optimization Tips

Best practices for optimizing Axon performance.

Run: python 03_optimization_tips.py
"""

import asyncio


async def main():
    print("=== Performance Optimization Tips ===\n")

    print("1. ADAPTER SELECTION")
    print("-" * 50)
    print("  * Use InMemory for development (fastest)")
    print("  * Use Redis for production caching")
    print("  * Use Qdrant/Pinecone for persistent tier")
    print("  * Avoid vector DBs for ephemeral/session\n")

    print("2. BATCH OPERATIONS")
    print("-" * 50)
    print("  * Group multiple stores together")
    print("  * Use bulk_save() when available")
    print("  * Minimize roundtrips to storage\n")

    print("3. QUERY OPTIMIZATION")
    print("-" * 50)
    print("  * Query specific tiers (not all)")
    print("  * Use filters to reduce result sets")
    print("  * Set appropriate k values")
    print("  * Cache frequent queries\n")

    print("4. COMPACTION STRATEGY")
    print("-" * 50)
    print("  * Set realistic thresholds")
    print("  * Use 'count' for speed")
    print("  * Use 'semantic' for quality")
    print("  * Schedule during low-traffic periods\n")

    print("5. MEMORY MANAGEMENT")
    print("-" * 50)
    print("  * Set max_entries limits")
    print("  * Enable TTL expiration")
    print("  * Monitor tier sizes")
    print("  * Use compaction proactively\n")

    print("6. EMBEDDER SELECTION")
    print("-" * 50)
    print("  * OpenAI: Good balance")
    print("  * Voyage: Better quality")
    print("  * Sentence Transformers: Local, fast")
    print("  * Cache embeddings when possible\n")

    print("=" * 50)
    print("* Optimization tips complete!")


if __name__ == "__main__":
    asyncio.run(main())
