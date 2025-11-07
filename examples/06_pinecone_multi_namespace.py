"""Pinecone Multi-Namespace Architecture Example

This example demonstrates:
- Advanced namespace design patterns
- Cross-namespace search strategies
- Namespace lifecycle management
- Tenant isolation in multi-tenant applications
- Performance optimization with namespaces
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.axon.adapters import PineconeAdapter
from src.axon.models import MemoryEntry, MemoryMetadata, ProvenanceEvent

# Load environment variables
load_dotenv()


class MultiTenantMemorySystem:
    """Advanced multi-namespace memory management for SaaS applications."""

    def __init__(self, api_key: str, index_name: str = "axon-multitenant"):
        self.api_key = api_key
        self.index_name = index_name
        self.cloud = "aws"
        self.region = "us-east-1"

    def _get_adapter(self, namespace: str) -> PineconeAdapter:
        """Get adapter for specific namespace."""
        return PineconeAdapter(
            api_key=self.api_key,
            index_name=self.index_name,
            namespace=namespace,
            cloud=self.cloud,
            region=self.region,
        )

    # Namespace Design Patterns

    def get_org_namespace(self, org_id: str) -> str:
        """Get namespace for organization-level data."""
        return f"org_{org_id}"

    def get_team_namespace(self, org_id: str, team_id: str) -> str:
        """Get namespace for team-level data within organization."""
        return f"org_{org_id}_team_{team_id}"

    def get_user_namespace(self, org_id: str, user_id: str) -> str:
        """Get namespace for user-level data within organization."""
        return f"org_{org_id}_user_{user_id}"

    def get_session_namespace(self, user_id: str, session_id: str) -> str:
        """Get namespace for temporary session data."""
        return f"session_{user_id}_{session_id}"

    # Lifecycle Management

    async def provision_organization(
        self, org_id: str, initial_data: list[tuple[str, list[float]]]
    ):
        """Provision a new organization with initial knowledge base."""
        namespace = self.get_org_namespace(org_id)
        adapter = self._get_adapter(namespace)

        entries = []
        for text, embedding in initial_data:
            entry = MemoryEntry(
                id=str(uuid4()),
                text=text,
                embedding=embedding,
                metadata=MemoryMetadata(
                    source="system",
                    user_id=f"system_{org_id}",
                    session_id="provision",
                    privacy_level="public",
                    tags=["knowledge_base", "org_shared"],
                    importance=0.9,
                    provenance=[
                        ProvenanceEvent(
                            action="provision", by="system", timestamp=datetime.now(timezone.utc)
                        )
                    ],
                ),
            )
            entries.append(entry)

        await adapter.bulk_save(entries)
        return namespace

    async def create_team_workspace(
        self, org_id: str, team_id: str, team_docs: list[tuple[str, list[float]]]
    ):
        """Create a team workspace with shared documents."""
        namespace = self.get_team_namespace(org_id, team_id)
        adapter = self._get_adapter(namespace)

        entries = []
        for text, embedding in team_docs:
            entry = MemoryEntry(
                id=str(uuid4()),
                text=text,
                embedding=embedding,
                metadata=MemoryMetadata(
                    source="app",
                    user_id=f"team_{team_id}",
                    session_id="workspace_setup",
                    privacy_level="sensitive",
                    tags=["team_shared", team_id],
                    importance=0.8,
                    provenance=[
                        ProvenanceEvent(
                            action="team_provision",
                            by="admin",
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                ),
            )
            entries.append(entry)

        await adapter.bulk_save(entries)
        return namespace

    async def create_session(self, user_id: str, session_id: str):
        """Create ephemeral session namespace."""
        namespace = self.get_session_namespace(user_id, session_id)
        # Namespace is created automatically on first save
        return namespace

    async def cleanup_session(self, user_id: str, session_id: str):
        """Clean up session namespace after session ends."""
        namespace = self.get_session_namespace(user_id, session_id)
        adapter = self._get_adapter(namespace)
        await adapter.clear_async()
        return True

    # Multi-Namespace Search

    async def hierarchical_search(
        self, org_id: str, user_id: str, query_embedding: list[float], limit: int = 5
    ) -> dict[str, list[MemoryEntry]]:
        """Search across organizational hierarchy: org → user.

        This demonstrates how to search multiple namespaces in priority order.
        """
        results = {}

        # 1. Search user's personal namespace first (highest priority)
        user_namespace = self.get_user_namespace(org_id, user_id)
        user_adapter = self._get_adapter(user_namespace)
        user_results = await user_adapter.query(query_embedding, limit=limit)
        results["user"] = user_results

        # 2. Search organization-wide namespace (shared knowledge)
        org_namespace = self.get_org_namespace(org_id)
        org_adapter = self._get_adapter(org_namespace)
        org_results = await org_adapter.query(query_embedding, limit=limit)
        results["org"] = org_results

        return results

    async def team_search(
        self, org_id: str, team_ids: list[str], query_embedding: list[float], limit: int = 5
    ) -> dict[str, list[MemoryEntry]]:
        """Search across multiple team namespaces."""
        results = {}

        for team_id in team_ids:
            namespace = self.get_team_namespace(org_id, team_id)
            adapter = self._get_adapter(namespace)
            team_results = await adapter.query(query_embedding, limit=limit)
            results[team_id] = team_results

        return results

    # Namespace Analytics

    async def get_namespace_stats(self, namespace: str) -> dict:
        """Get detailed statistics for a namespace."""
        adapter = self._get_adapter(namespace)

        count = await adapter.count_async()
        ids = await adapter.list_ids_async()

        return {
            "namespace": namespace,
            "vector_count": count,
            "sample_ids": ids[:10],
            "has_more": count > 10,
        }

    async def get_org_overview(self, org_id: str) -> dict:
        """Get overview of all namespaces for an organization."""
        org_namespace = self.get_org_namespace(org_id)
        org_stats = await self.get_namespace_stats(org_namespace)

        return {"org_id": org_id, "org_namespace": org_stats}


async def main():
    """Demonstrate advanced multi-namespace patterns."""

    print("🏢 Initializing Multi-Tenant Memory System\n")

    system = MultiTenantMemorySystem(api_key=os.getenv("PINECONE_API_KEY"))

    # Simple embedding function
    def create_embedding(text: str, seed: int = 0) -> list[float]:
        return [hash(text + str(i) + str(seed)) % 1000 / 1000.0 for i in range(384)]

    # Scenario: Two organizations, each with teams and users
    print("📋 Scenario: Multi-tenant SaaS platform\n")

    # Organization 1: TechCorp
    print("🏢 Provisioning Organization: TechCorp")

    techcorp_kb = [
        ("TechCorp company policy: All code must be reviewed.", create_embedding("policy1")),
        ("TechCorp uses Python and TypeScript as primary languages.", create_embedding("policy2")),
        (
            "TechCorp security guidelines require 2FA for all employees.",
            create_embedding("policy3"),
        ),
    ]

    techcorp_namespace = await system.provision_organization("techcorp", techcorp_kb)
    print(f"   ✓ Created org namespace: {techcorp_namespace}")
    print(f"   ✓ Loaded {len(techcorp_kb)} knowledge base entries\n")

    # Create teams within TechCorp
    print("👥 Creating Team Workspaces within TechCorp")

    # Engineering team
    eng_docs = [
        ("Engineering team uses GitHub for version control.", create_embedding("eng1")),
        ("Engineering deploys to AWS using Terraform.", create_embedding("eng2")),
    ]
    eng_namespace = await system.create_team_workspace("techcorp", "engineering", eng_docs)
    print(f"   ✓ Engineering team: {eng_namespace} ({len(eng_docs)} docs)")

    # Product team
    product_docs = [
        ("Product team uses Figma for design collaboration.", create_embedding("prod1")),
        ("Product roadmap is managed in Linear.", create_embedding("prod2")),
    ]
    product_namespace = await system.create_team_workspace("techcorp", "product", product_docs)
    print(f"   ✓ Product team: {product_namespace} ({len(product_docs)} docs)\n")

    # Wait for indexing
    await asyncio.sleep(2)

    # Demonstrate hierarchical search
    print("🔍 Hierarchical Search Demo")
    print("   User 'alice' searches across personal + org namespaces\n")

    query = "company security policy"
    query_embedding = create_embedding(query)

    search_results = await system.hierarchical_search(
        org_id="techcorp", user_id="alice", query_embedding=query_embedding, limit=3
    )

    print(f"   Query: '{query}'")
    print(f"\n   Personal Results ({len(search_results['user'])} found):")
    if search_results["user"]:
        for i, result in enumerate(search_results["user"], 1):
            print(f"      {i}. {result.text[:60]}...")
    else:
        print("      (none)")

    print(f"\n   Org-wide Results ({len(search_results['org'])} found):")
    for i, result in enumerate(search_results["org"], 1):
        print(f"      {i}. {result.text[:60]}...")

    print()

    # Team search across multiple teams
    print("🔍 Multi-Team Search Demo")
    print("   Searching across Engineering and Product teams\n")

    team_query = "collaboration tools"
    team_query_embedding = create_embedding(team_query)

    team_results = await system.team_search(
        org_id="techcorp",
        team_ids=["engineering", "product"],
        query_embedding=team_query_embedding,
        limit=2,
    )

    print(f"   Query: '{team_query}'\n")
    for team_id, results in team_results.items():
        print(f"   {team_id.capitalize()} Team ({len(results)} results):")
        for i, result in enumerate(results, 1):
            print(f"      {i}. {result.text[:60]}...")
        print()

    # Session namespace demo
    print("⏱️  Ephemeral Session Demo")

    session_id = str(uuid4())
    session_namespace = await system.create_session("alice", session_id)
    print(f"   ✓ Created session: {session_namespace}")

    # Store some temporary data
    session_adapter = system._get_adapter(session_namespace)
    temp_entry = MemoryEntry(
        id=str(uuid4()),
        text="Temporary calculation: 42 * 37 = 1554",
        embedding=create_embedding("temp"),
        metadata=MemoryMetadata(
            source="app",
            user_id="alice",
            session_id=session_id,
            privacy_level="private",
            tags=["temporary"],
            importance=0.3,
        ),
    )
    await session_adapter.save(temp_entry)
    print("   ✓ Stored temporary data")

    # Wait for indexing
    await asyncio.sleep(1)

    session_count = await session_adapter.count_async()
    print(f"   ✓ Session has {session_count} entries")

    # Cleanup session
    await system.cleanup_session("alice", session_id)
    print("   ✓ Cleaned up session\n")

    # Namespace analytics
    print("📊 Namespace Analytics\n")

    org_stats = await system.get_namespace_stats(techcorp_namespace)
    print(f"   Organization: {org_stats['namespace']}")
    print(f"      Vectors: {org_stats['vector_count']}")
    print(f"      Sample IDs: {org_stats['sample_ids'][:3]}\n")

    eng_stats = await system.get_namespace_stats(eng_namespace)
    print(f"   Engineering Team: {eng_stats['namespace']}")
    print(f"      Vectors: {eng_stats['vector_count']}")
    print(f"      Sample IDs: {eng_stats['sample_ids'][:3]}\n")

    # Cleanup demo
    print("🧹 Cleanup")

    # Clean all namespaces
    for namespace in [techcorp_namespace, eng_namespace, product_namespace]:
        adapter = system._get_adapter(namespace)
        await adapter.clear_async()
        print(f"   ✓ Cleared {namespace}")

    print("\n✨ Multi-namespace demo complete!")
    print("\n💡 Key Architecture Patterns:")
    print("   • Hierarchical namespaces: org → team → user → session")
    print("   • Namespace naming convention for clarity: org_X_team_Y")
    print("   • Search strategies: hierarchical (priority), multi-team (parallel)")
    print("   • Lifecycle: provision → use → cleanup")
    print("   • Isolation: Each tenant/team/user completely isolated")
    print("   • Ephemeral namespaces: Sessions auto-cleanup")
    print("\n🚀 Performance Benefits:")
    print("   • Reduced search scope (namespace filtering)")
    print("   • Better cache locality")
    print("   • Easier data management and deletion")
    print("   • Compliance-friendly (data residency per tenant)")


if __name__ == "__main__":
    asyncio.run(main())
