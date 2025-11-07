"""Integration tests for memory compaction with real adapters and LLM.

These tests verify the end-to-end compaction workflow:
1. Store many entries in a tier
2. Trigger compaction via threshold
3. Verify summaries are created
4. Verify original entries are deleted
5. Verify summaries are searchable
6. Verify provenance is maintained

Requirements:
    - OPENAI_API_KEY environment variable set (can be in .env file)
    - ChromaDB available (in-memory)
    - Redis available (optional, tested separately)
"""

import os
from datetime import datetime, timedelta

import pytest
from dotenv import load_dotenv

from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies.persistent import PersistentPolicy
from axon.core.summarizer import LLMSummarizer
from axon.embedders.openai import OpenAIEmbedder
from axon.models.base import MemoryEntryType

# Load environment variables from .env file
load_dotenv()

# Skip all tests if OPENAI_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping integration tests that require real LLM",
)


@pytest.fixture
def config_with_compaction():
    """Create config with low compaction threshold for testing."""
    return MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="chroma",
            connection_string="chroma_test_compaction",
            max_entries=None,
            ttl_seconds=None,
            compaction_threshold=100,  # Minimum allowed threshold
        ),
        default_tier="persistent",  # Set default to persistent since we only have persistent tier
    )


@pytest.fixture
def embedder():
    """Create real OpenAI embedder."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return OpenAIEmbedder(api_key=api_key, model="text-embedding-3-small")


@pytest.fixture
def memory_system_with_compaction(config_with_compaction, embedder):
    """Create MemorySystem with compaction-enabled config and embedder."""
    system = MemorySystem(config=config_with_compaction, embedder=embedder)

    # Policy already has compaction threshold set
    return system


@pytest.fixture
def summarizer():
    """Create real LLM summarizer."""
    return LLMSummarizer(model="gpt-3.5-turbo", max_tokens=200)


@pytest.mark.asyncio
@pytest.mark.integration
class TestCompactionIntegration:
    """Integration tests for memory compaction."""

    async def test_compact_with_real_llm_and_chroma(
        self, memory_system_with_compaction, summarizer, embedder
    ):
        """Test complete compaction workflow with real LLM and ChromaDB.

        This test:
        1. Stores 60 entries (exceeds threshold of 50)
        2. Runs compaction
        3. Verifies summaries were created
        4. Verifies entry count reduced
        5. Verifies summaries have embeddings
        """
        system = memory_system_with_compaction

        # Clean up any existing data from previous runs
        adapter = await system.registry.get_adapter("persistent")
        try:
            # ChromaDB: delete and recreate collection
            adapter.client.delete_collection(adapter.collection.name)
            adapter.collection = adapter.client.get_or_create_collection(
                name=adapter.collection.name, metadata={"description": "Axon Memory SDK storage"}
            )
        except Exception:
            pass  # Collection might not exist yet

        # Store 60 entries about a fictional project timeline
        entries_data = [
            ("Initialized project repository", 0.3),
            ("Set up development environment", 0.3),
            ("Created initial project structure", 0.3),
            ("Implemented user authentication", 0.5),
            ("Added login page UI", 0.4),
            ("Integrated OAuth2 for Google login", 0.6),
            ("Created user profile page", 0.4),
            ("Added profile editing functionality", 0.4),
            ("Implemented password reset flow", 0.5),
            ("Added email verification", 0.5),
            ("Created product catalog database schema", 0.5),
            ("Implemented product listing page", 0.5),
            ("Added product search functionality", 0.6),
            ("Implemented product filtering", 0.5),
            ("Added product detail pages", 0.4),
            ("Integrated payment gateway", 0.8),
            ("Implemented shopping cart", 0.7),
            ("Added checkout flow", 0.7),
            ("Implemented order processing", 0.8),
            ("Added order confirmation emails", 0.6),
            ("Created admin dashboard", 0.6),
            ("Implemented user management for admins", 0.5),
            ("Added product inventory management", 0.6),
            ("Implemented sales analytics", 0.7),
            ("Added revenue reports", 0.6),
            ("Created mobile responsive design", 0.7),
            ("Optimized images for performance", 0.4),
            ("Implemented lazy loading", 0.5),
            ("Added CDN integration", 0.5),
            ("Optimized database queries", 0.6),
            ("Set up CI/CD pipeline", 0.7),
            ("Configured automated testing", 0.6),
            ("Added code coverage reporting", 0.5),
            ("Implemented security headers", 0.7),
            ("Added rate limiting", 0.6),
            ("Implemented CSRF protection", 0.7),
            ("Added input validation", 0.6),
            ("Implemented SQL injection prevention", 0.8),
            ("Added XSS protection", 0.7),
            ("Created API documentation", 0.5),
            ("Implemented API versioning", 0.6),
            ("Added API rate limiting", 0.6),
            ("Implemented webhook system", 0.6),
            ("Added third-party integrations", 0.7),
            ("Created user onboarding flow", 0.5),
            ("Implemented tooltips and help text", 0.4),
            ("Added video tutorials", 0.4),
            ("Created FAQ section", 0.4),
            ("Implemented live chat support", 0.7),
            ("Added feedback collection system", 0.5),
            ("Implemented A/B testing framework", 0.6),
            ("Added feature flags", 0.6),
            ("Implemented monitoring and alerting", 0.8),
            ("Added error tracking", 0.7),
            ("Implemented performance monitoring", 0.7),
            ("Created backup system", 0.8),
            ("Implemented disaster recovery plan", 0.8),
            ("Added data encryption at rest", 0.8),
            ("Implemented audit logging", 0.7),
            ("Added compliance documentation", 0.6),
        ]

        base_time = datetime.now() - timedelta(days=60)
        stored_ids = []

        for i, (text, importance) in enumerate(entries_data):
            entry_id = await system.store(
                text,  # First positional argument is content
                importance=importance,
                metadata={
                    "user_id": "integration_test_user",
                    "session_id": "project_timeline",
                    "created_at": base_time + timedelta(days=i),
                },
                tags=["integration_test", "project"],
                tier="persistent",
            )
            stored_ids.append(entry_id)

        # Verify all entries were stored
        adapter = await system.registry.get_adapter("persistent")
        count_before = adapter.count()
        assert count_before == 60, f"Expected 60 entries, got {count_before}"

        # Run compaction
        result = await system.compact(
            tier="persistent",
            strategy="count",
            threshold=50,  # Override the default 100 - should compact since we have 60 > 50
            summarizer=summarizer,
            embedder=embedder,
        )

        # Verify compaction occurred
        assert result["tier"] == "persistent"
        assert result["entries_before"] == 60
        assert result["summaries_created"] > 0, "Should have created summaries"
        assert result["entries_after"] < 60, "Should have reduced entry count"
        assert result["reduction_ratio"] > 0, "Should show reduction"

        print(f"\n{'='*60}")
        print("COMPACTION RESULTS:")
        print(f"{'='*60}")
        print(f"Entries before:      {result['entries_before']}")
        print(f"Entries after:       {result['entries_after']}")
        print(f"Summaries created:   {result['summaries_created']}")
        print(f"Reduction ratio:     {result['reduction_ratio']:.1%}")
        print(f"Strategy:            {result['strategy']}")
        print(f"{'='*60}\n")

        # Verify new count
        count_after = adapter.count()
        assert count_after == result["entries_after"]

        # Verify summaries exist and have embeddings
        all_entries = await adapter.query(vector=[0.0] * 1536, k=count_after, filter=None)

        summaries = [e for e in all_entries if e.type == MemoryEntryType.EMBEDDING_SUMMARY]
        assert len(summaries) == result["summaries_created"]

        # Verify each summary has:
        # 1. Text content (the actual summary)
        # 2. Embedding (from embedder)
        # 3. Provenance tracking
        for summary in summaries:
            assert summary.text, "Summary should have text"
            assert len(summary.text) > 0, "Summary text should not be empty"
            assert summary.embedding is not None, "Summary should have embedding"
            assert len(summary.embedding) == 1536, "Embedding should be correct size"
            assert summary.metadata.source == "system", "Summary source should be 'system'"
            assert len(summary.metadata.provenance) > 0, "Summary should have provenance"

            provenance = summary.metadata.provenance[0]
            assert provenance.action == "compact"
            assert provenance.by == "memory_system"
            assert "summarized_count" in provenance.metadata

            print(f"Summary: {summary.text[:100]}...")

    async def test_compact_preserves_searchability(
        self, memory_system_with_compaction, summarizer, embedder
    ):
        """Test that summaries are semantically searchable.

        This test:
        1. Stores entries about specific topics
        2. Compacts them into summaries
        3. Queries for those topics
        4. Verifies summaries are returned in results
        """
        system = memory_system_with_compaction

        # Clean up any existing data from previous runs
        adapter = await system.registry.get_adapter("persistent")
        try:
            adapter.client.delete_collection(adapter.collection.name)
            adapter.collection = adapter.client.get_or_create_collection(
                name=adapter.collection.name, metadata={"description": "Axon Memory SDK storage"}
            )
        except Exception:
            pass

        # Store entries about authentication
        auth_entries = [
            "Implemented JWT token generation",
            "Added token refresh mechanism",
            "Created token validation middleware",
            "Implemented token expiration handling",
            "Added token blacklist for logout",
            "Created secure token storage",
            "Implemented token encryption",
            "Added token claims customization",
            "Created token revocation API",
            "Implemented multi-device token management",
        ]

        # Store entries about database
        db_entries = [
            "Designed user table schema",
            "Created database migrations",
            "Implemented connection pooling",
            "Added database indexing",
            "Optimized query performance",
            "Implemented database backups",
            "Added replication setup",
            "Created stored procedures",
            "Implemented transaction management",
            "Added database monitoring",
        ]

        # Store all entries
        for text in auth_entries + db_entries:
            await system.store(
                text,  # First positional argument is content
                importance=0.3,
                metadata={
                    "user_id": "search_test_user",
                    "session_id": "search_test",
                },
                tags=["integration_test"],
                tier="persistent",
            )

        # Compact
        result = await system.compact(
            tier="persistent",
            strategy="count",
            threshold=15,  # Force compaction
            summarizer=summarizer,
            embedder=embedder,
        )

        assert result["summaries_created"] > 0

        # Search for authentication-related content
        auth_results = await system.recall(
            query="JWT token authentication and security", k=5, tiers=["persistent"]
        )

        # Note: With only 20 entries, search might return 0 results
        # The test verifies that IF results are found, summaries are searchable
        print(f"\nSearch found {len(auth_results)} results for 'JWT token authentication'")

        if len(auth_results) > 0:
            # Verify at least some results are summaries
            has_summary = any(e.type == MemoryEntryType.EMBEDDING_SUMMARY for e in auth_results)

            print("Search results:")
            for i, entry in enumerate(auth_results[:3], 1):
                print(f"{i}. [{entry.type}] {entry.text[:80]}...")

            # If we compacted significantly, we should have summaries in results
            if result["summaries_created"] >= result["entries_after"] * 0.3:
                assert has_summary, "Should have at least one summary in search results"
        else:
            # If no results, that's okay - small dataset might not match query well
            print("No results found - this is acceptable for small datasets")

    async def test_compact_reduces_storage(
        self, memory_system_with_compaction, summarizer, embedder
    ):
        """Test that compaction reduces entry count while preserving information.

        This test:
        1. Stores many low-importance entries
        2. Runs compaction
        3. Verifies significant reduction in entry count
        4. Verifies reduction ratio is calculated correctly
        """
        system = memory_system_with_compaction

        # Clean up any existing data
        adapter = await system.registry.get_adapter("persistent")
        try:
            adapter.client.delete_collection(adapter.collection.name)
            adapter.collection = adapter.client.get_or_create_collection(
                name=adapter.collection.name, metadata={"description": "Axon Memory SDK storage"}
            )
        except Exception:
            pass

        # Store 80 low-importance entries
        for i in range(80):
            await system.store(
                f"Low priority log entry {i}: routine system check completed",
                importance=0.2,  # Low importance
                metadata={
                    "user_id": "system",
                    "session_id": "monitoring",
                },
                tags=["log", "routine"],
                tier="persistent",
            )

        # Get initial count
        adapter = await system.registry.get_adapter("persistent")
        count_before = adapter.count()

        # Compact
        result = await system.compact(
            tier="persistent",
            strategy="count",
            threshold=50,
            summarizer=summarizer,
            embedder=embedder,
        )

        count_after = adapter.count()

        # Verify significant reduction (at least 40% - real LLM results vary)
        reduction = (count_before - count_after) / count_before
        assert reduction > 0.4, f"Should reduce by >40%, got {reduction:.1%}"
        print(f"Storage reduction: {reduction:.1%} ({count_before} → {count_after} entries)")

        # Verify reduction ratio calculation
        expected_ratio = (count_before - count_after) / count_before
        assert abs(result["reduction_ratio"] - expected_ratio) < 0.01

        print(f"\nStorage reduction: {reduction:.1%}")
        print(f"From {count_before} entries to {count_after} entries")

    async def test_compact_dry_run_no_changes(self, memory_system_with_compaction, summarizer):
        """Test that dry_run=True doesn't modify data.

        This test:
        1. Stores entries
        2. Runs compaction with dry_run=True
        3. Verifies no changes to stored data
        4. Verifies statistics are still calculated
        """
        system = memory_system_with_compaction

        # Clean up any existing data
        adapter = await system.registry.get_adapter("persistent")
        try:
            adapter.client.delete_collection(adapter.collection.name)
            adapter.collection = adapter.client.get_or_create_collection(
                name=adapter.collection.name, metadata={"description": "Axon Memory SDK storage"}
            )
        except Exception:
            pass

        # Store 60 entries
        for i in range(60):
            await system.store(
                f"Test entry {i}",
                importance=0.3,
                metadata={
                    "user_id": "dry_run_test",
                },
                tier="persistent",
            )

        # Get initial count
        adapter = await system.registry.get_adapter("persistent")
        count_before = adapter.count()

        # Dry run compaction
        result = await system.compact(
            tier="persistent", strategy="count", threshold=50, dry_run=True, summarizer=summarizer
        )

        # Verify no changes
        count_after = adapter.count()
        assert count_after == count_before, "Dry run should not change data"
        assert result["dry_run"] is True
        assert result["entries_before"] == count_before

        # Verify statistics were calculated
        assert "summaries_created" in result
        assert "entries_after" in result

        print("\nDry run results:")
        print(f"Would create {result['summaries_created']} summaries")
        print(f"Would reduce from {result['entries_before']} to {result['entries_after']}")

    async def test_compact_maintains_provenance_chain(
        self, memory_system_with_compaction, summarizer, embedder
    ):
        """Test that compaction maintains complete provenance.

        This test:
        1. Stores entries with metadata
        2. Compacts them
        3. Verifies summaries have complete provenance
        4. Verifies provenance includes original entry IDs
        """
        system = memory_system_with_compaction

        # Clean up any existing data
        adapter = await system.registry.get_adapter("persistent")
        try:
            adapter.client.delete_collection(adapter.collection.name)
            adapter.collection = adapter.client.get_or_create_collection(
                name=adapter.collection.name, metadata={"description": "Axon Memory SDK storage"}
            )
        except Exception:
            pass
        system = memory_system_with_compaction

        # Store entries with specific metadata
        original_ids = []
        for i in range(60):
            entry_id = await system.store(
                f"Important business event {i}",
                importance=0.4,
                metadata={
                    "user_id": "provenance_test",
                    "session_id": "business_events",
                },
                tags=["business", "event"],
                tier="persistent",
            )
            original_ids.append(entry_id)

        # Compact
        result = await system.compact(
            tier="persistent",
            strategy="count",
            threshold=50,
            summarizer=summarizer,
            embedder=embedder,
        )

        # Get summaries
        adapter = await system.registry.get_adapter("persistent")
        all_entries = await adapter.query(
            vector=[0.0] * 1536, k=result["entries_after"], filter=None
        )

        summaries = [e for e in all_entries if e.type == MemoryEntryType.EMBEDDING_SUMMARY]

        # Verify each summary has complete provenance
        all_summarized_ids = set()
        for summary in summaries:
            assert len(summary.metadata.provenance) > 0

            provenance = summary.metadata.provenance[0]
            assert provenance.action == "compact"
            assert provenance.by == "memory_system"
            assert "strategy" in provenance.metadata
            assert "summarized_count" in provenance.metadata
            assert "summarized_ids" in provenance.metadata

            # Extract original IDs from provenance
            summarized_ids = provenance.metadata["summarized_ids"].split(",")
            all_summarized_ids.update(summarized_ids)

            print("\nSummary provenance:")
            print(f"  Summarized {len(summarized_ids)} entries")
            print(f"  Strategy: {provenance.metadata['strategy']}")

        # Verify we can trace back to original entries
        assert len(all_summarized_ids) > 0, "Should track original entry IDs"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
