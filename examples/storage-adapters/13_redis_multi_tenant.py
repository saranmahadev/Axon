"""
Example 9: Redis Multi-Tenant Cache - Namespace Isolation

This example demonstrates multi-tenant isolation using namespaces:
- Complete data isolation between tenants
- Per-tenant cache management
- Shared Redis instance with logical separation
- Independent TTL policies per tenant
- Efficient resource utilization

Use Case: SaaS application serving multiple customers where each
customer's data must be completely isolated from others while
sharing the same Redis infrastructure.
"""

import asyncio

from axon.adapters.redis import RedisAdapter
from axon.models.entry import MemoryEntry, MemoryMetadata
from axon.models.filter import Filter


async def create_tenant_adapter(tenant_id: str, ttl: int = 300) -> RedisAdapter:
    """Create a Redis adapter for a specific tenant."""
    return RedisAdapter(
        host="localhost", port=6379, namespace=f"tenant_{tenant_id}", default_ttl=ttl
    )


async def simulate_tenant_activity(adapter: RedisAdapter, tenant_id: str, num_entries: int) -> None:
    """Simulate activity for a tenant."""
    entries = []
    for i in range(num_entries):
        entry = MemoryEntry(
            id=f"{tenant_id}_entry_{i:03d}",
            text=f"Data from {tenant_id}: {i}",
            embedding=[float(i) * 0.1] * 384,
            metadata=MemoryMetadata(
                user_id=f"{tenant_id}_user_{i % 3}",
                session_id=f"{tenant_id}_session_{i % 2}",
                tags=[tenant_id, f"entry_{i}"],
                importance=0.3 + (i * 0.05) % 0.7,
                privacy_level="private",
            ),
        )
        entries.append(entry)

    # Bulk save all entries
    await adapter.bulk_save(entries)
    return entries


async def main():
    print("=" * 70)
    print("EXAMPLE 9: Redis Multi-Tenant Cache - Namespace Isolation")
    print("=" * 70)

    # Create adapters for three different tenants
    print("\n🏢 Setting up multi-tenant environment...")

    tenant_a = await create_tenant_adapter("acme_corp", ttl=300)
    tenant_b = await create_tenant_adapter("globex", ttl=600)
    tenant_c = await create_tenant_adapter("initech", ttl=900)

    tenants = {
        "acme_corp": {"adapter": tenant_a, "ttl": 300, "color": "🔵"},
        "globex": {"adapter": tenant_b, "ttl": 600, "color": "🟢"},
        "initech": {"adapter": tenant_c, "ttl": 900, "color": "🟡"},
    }

    print("   ✅ Created isolated namespaces for 3 tenants:")
    for tenant_id, info in tenants.items():
        print(f"      {info['color']} {tenant_id}: TTL={info['ttl']}s")

    # Simulate activity for each tenant
    print("\n📊 Simulating tenant activity...")

    for tenant_id, info in tenants.items():
        num_entries = 5 + (hash(tenant_id) % 5)  # 5-9 entries per tenant
        await simulate_tenant_activity(info["adapter"], tenant_id, num_entries)
        count = await info["adapter"].count_async()
        print(f"   {info['color']} {tenant_id}: Created {count} cache entries")

    # Verify namespace isolation
    print("\n\n🔒 Namespace Isolation Verification:")
    print(f"   {'Tenant':<15} {'Namespace':<25} {'Count':<8} {'Status'}")
    print(f"   {'-'*15} {'-'*25} {'-'*8} {'-'*20}")

    for tenant_id, info in tenants.items():
        adapter = info["adapter"]
        count = await adapter.count_async()
        namespace = adapter.namespace
        status = "✅ Isolated" if count > 0 else "❌ Empty"
        print(f"   {tenant_id:<15} {namespace:<25} {count:<8} {status}")

    # Demonstrate cross-tenant isolation
    print("\n\n🛡️  Cross-Tenant Access Test:")
    print("   Attempting to access Tenant A data from Tenant B namespace...")

    # Try to get Tenant A's entry using Tenant B's adapter
    tenant_a_entry_id = "acme_corp_entry_001"
    result = await tenant_b.get(tenant_a_entry_id)

    if result is None:
        print("   ✅ Access denied! Tenant B cannot see Tenant A's data")
        print(f"      Entry '{tenant_a_entry_id}' not found in globex namespace")
    else:
        print("   ❌ Isolation breach! Cross-tenant access detected")

    # Verify correct access within same tenant
    correct_result = await tenant_a.get(tenant_a_entry_id)
    if correct_result:
        print(f"   ✅ Tenant A can access its own data: '{correct_result.text}'")

    # Query within tenant scope
    print("\n\n🔍 Tenant-Scoped Queries:")

    for tenant_id, info in tenants.items():
        adapter = info["adapter"]

        # Query all entries for this tenant
        all_entries = await adapter.query(vector=None, k=100)

        # Query by user
        user_entries = await adapter.query(
            vector=None, k=100, filter=Filter(user_id=f"{tenant_id}_user_0")
        )

        # Query by session
        session_entries = await adapter.query(
            vector=None, k=100, filter=Filter(session_id=f"{tenant_id}_session_0")
        )

        print(f"   {info['color']} {tenant_id}:")
        print(f"      Total entries: {len(all_entries)}")
        print(f"      User '0' entries: {len(user_entries)}")
        print(f"      Session '0' entries: {len(session_entries)}")

    # Demonstrate selective cleanup (delete one tenant's data)
    print("\n\n🗑️  Selective Tenant Cleanup:")
    print("   Clearing cache for Tenant B (globex) only...")

    await tenant_b.clear_async()

    print("\n   Post-cleanup status:")
    for tenant_id, info in tenants.items():
        count = await info["adapter"].count_async()
        status = "🟢 Active" if count > 0 else "⚪ Cleared"
        print(f"      {info['color']} {tenant_id}: {count} entries - {status}")

    # Demonstrate different TTL policies per tenant
    print("\n\n⏱️  Per-Tenant TTL Policies:")

    # Add one test entry per tenant to check TTL
    for tenant_id, info in tenants.items():
        test_entry = MemoryEntry(
            id=f"{tenant_id}_ttl_test",
            text=f"TTL test for {tenant_id}",
            embedding=[0.9] * 384,
            metadata=MemoryMetadata(
                user_id=f"{tenant_id}_admin", tags=["ttl_test"], importance=0.8
            ),
        )
        await info["adapter"].save(test_entry)
        ttl = await info["adapter"].get_ttl(f"{tenant_id}_ttl_test")
        print(f"   {info['color']} {tenant_id}: TTL = {ttl}s (policy: {info['ttl']}s)")

    # Resource utilization summary
    print("\n\n📈 Resource Utilization Summary:")

    total_entries = 0
    for tenant_id, info in tenants.items():
        count = await info["adapter"].count_async()
        total_entries += count

    print(f"   Total entries across all tenants: {total_entries}")
    print(f"   Tenants sharing Redis instance: {len(tenants)}")
    print(f"   Average entries per tenant: {total_entries / len(tenants):.1f}")

    # List all IDs per tenant (demonstrates namespace separation)
    print("\n\n📋 Entry ID Listing (namespace-scoped):")

    for tenant_id, info in tenants.items():
        ids = await info["adapter"].list_ids_async()
        if ids:
            sample_ids = ids[:3]  # Show first 3 IDs
            print(f"   {info['color']} {tenant_id}: {len(ids)} entries")
            for entry_id in sample_ids:
                print(f"      - {entry_id}")
            if len(ids) > 3:
                print(f"      ... and {len(ids) - 3} more")
        else:
            print(f"   {info['color']} {tenant_id}: 0 entries (cleared)")

    # Final cleanup
    print("\n\n🧹 Cleaning up all tenant data...")

    for tenant_id, info in tenants.items():
        await info["adapter"].clear_async()
        await info["adapter"].close()
        print(f"   {info['color']} {tenant_id}: Cleaned and closed")

    print("\n✅ Example complete!")
    print("\n💡 Key Takeaways:")
    print("   • Namespaces provide complete data isolation between tenants")
    print("   • Single Redis instance efficiently serves multiple tenants")
    print("   • Each tenant can have independent TTL policies")
    print("   • Selective cleanup allows per-tenant cache management")
    print("   • Queries and operations are automatically scoped to namespace")
    print("   • No risk of cross-tenant data leakage")
    print("   • Cost-effective multi-tenancy without data mixing")


if __name__ == "__main__":
    asyncio.run(main())
