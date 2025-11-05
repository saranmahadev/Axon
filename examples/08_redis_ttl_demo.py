"""
Example 8: Redis TTL Patterns - Advanced Expiration Strategies

This example demonstrates different TTL patterns for various use cases:
- No TTL (manual cleanup required)
- Short TTL (ephemeral data)
- Medium TTL (session data)
- Long TTL (warm cache)
- Per-entry TTL override
- TTL refresh on access

Use Case: Optimize memory usage by applying appropriate TTL 
strategies based on data lifetime requirements.
"""

import asyncio
from datetime import datetime, timezone
from axon.adapters.redis import RedisAdapter
from axon.models.entry import MemoryEntry, MemoryMetadata

async def main():
    print("=" * 70)
    print("EXAMPLE 8: Redis TTL Patterns - Expiration Strategies")
    print("=" * 70)
    
    # Initialize adapter with 60-second default TTL
    adapter = RedisAdapter(
        host="localhost",
        port=6379,
        namespace="ttl_demo",
        default_ttl=60  # 1 minute default
    )
    
    print(f"\n📋 TTL Pattern Demonstrations:")
    print(f"   Default TTL: 60 seconds")
    
    # Pattern 1: No TTL (permanent until manually deleted)
    print(f"\n\n1️⃣  NO TTL - Permanent Storage")
    print(f"   Use case: Critical data that requires manual cleanup")
    
    permanent = MemoryEntry(
        id="perm_001",
        text="Critical configuration data",
        embedding=[0.1] * 384,
        metadata=MemoryMetadata(
            user_id="system",
            tags=["config", "permanent"],
            importance=1.0
        )
    )
    await adapter.save(permanent, ttl=None)
    ttl = await adapter.get_ttl("perm_001")
    print(f"   ✅ Saved with TTL=None")
    print(f"   ⏱️  TTL status: {ttl} (-1 means no expiration)")
    
    # Pattern 2: Short TTL (ephemeral/temporary data)
    print(f"\n\n2️⃣  SHORT TTL - Ephemeral Data (10 seconds)")
    print(f"   Use case: Rate limiting, one-time tokens, temporary flags")
    
    ephemeral = MemoryEntry(
        id="temp_001",
        text="One-time verification code: 123456",
        embedding=[0.2] * 384,
        metadata=MemoryMetadata(
            user_id="user_temp",
            tags=["ephemeral", "verification"],
            importance=0.3
        )
    )
    await adapter.save(ephemeral, ttl=10)
    ttl = await adapter.get_ttl("temp_001")
    print(f"   ✅ Saved with TTL=10 seconds")
    print(f"   ⏱️  TTL status: {ttl} seconds remaining")
    
    # Pattern 3: Medium TTL (session data) - uses default
    print(f"\n\n3️⃣  MEDIUM TTL - Session Data (60 seconds default)")
    print(f"   Use case: User sessions, conversation context")
    
    session = MemoryEntry(
        id="sess_001",
        text="User is browsing product catalog",
        embedding=[0.3] * 384,
        metadata=MemoryMetadata(
            user_id="user_123",
            session_id="session_abc",
            tags=["session", "activity"],
            importance=0.5
        )
    )
    await adapter.save(session)  # Uses default_ttl=60
    ttl = await adapter.get_ttl("sess_001")
    print(f"   ✅ Saved with default TTL")
    print(f"   ⏱️  TTL status: {ttl} seconds remaining")
    
    # Pattern 4: Long TTL (warm cache)
    print(f"\n\n4️⃣  LONG TTL - Warm Cache (300 seconds)")
    print(f"   Use case: Frequently accessed data, user preferences")
    
    cached = MemoryEntry(
        id="cache_001",
        text="User preferences: dark mode, compact view",
        embedding=[0.4] * 384,
        metadata=MemoryMetadata(
            user_id="user_123",
            tags=["preferences", "cache"],
            importance=0.7
        )
    )
    await adapter.save(cached, ttl=300)
    ttl = await adapter.get_ttl("cache_001")
    print(f"   ✅ Saved with TTL=300 seconds (5 minutes)")
    print(f"   ⏱️  TTL status: {ttl} seconds remaining")
    
    # Pattern 5: TTL Refresh on Access
    print(f"\n\n5️⃣  TTL REFRESH - Keep-Alive Pattern")
    print(f"   Use case: Active sessions, frequently accessed cache")
    
    active = MemoryEntry(
        id="active_001",
        text="Active user session - last activity",
        embedding=[0.5] * 384,
        metadata=MemoryMetadata(
            user_id="user_active",
            session_id="active_session",
            tags=["active", "session"],
            importance=0.6
        )
    )
    await adapter.save(active, ttl=30)
    print(f"   ✅ Saved with TTL=30 seconds")
    
    ttl_before = await adapter.get_ttl("active_001")
    print(f"   ⏱️  Initial TTL: {ttl_before} seconds")
    
    # Simulate access after some time
    await asyncio.sleep(2)
    
    # Refresh TTL by accessing with refresh_ttl=True
    retrieved = await adapter.get("active_001", refresh_ttl=True)
    ttl_after = await adapter.get_ttl("active_001")
    print(f"   🔄 Accessed entry with refresh_ttl=True")
    print(f"   ⏱️  Refreshed TTL: {ttl_after} seconds (reset to 30)")
    
    # Demonstrate TTL countdown
    print(f"\n\n6️⃣  TTL COUNTDOWN - Watching Expiration")
    print(f"   Use case: Monitoring ephemeral data lifecycle")
    
    countdown = MemoryEntry(
        id="countdown_001",
        text="Temporary data for countdown demo",
        embedding=[0.6] * 384,
        metadata=MemoryMetadata(
            user_id="demo",
            tags=["countdown"],
            importance=0.4
        )
    )
    await adapter.save(countdown, ttl=8)
    
    print(f"   ✅ Saved with TTL=8 seconds")
    print(f"   ⏱️  Watching countdown...")
    
    for i in range(4):
        await asyncio.sleep(2)
        ttl = await adapter.get_ttl("countdown_001")
        if ttl == -2:
            print(f"      {i*2 + 2}s: ❌ Entry expired and removed")
            break
        else:
            print(f"      {i*2 + 2}s: ⏳ TTL = {ttl} seconds")
    
    # Summary of all entries and their TTL status
    print(f"\n\n📊 TTL Status Summary:")
    print(f"   {'Entry ID':<15} {'TTL (sec)':<12} {'Status'}")
    print(f"   {'-'*15} {'-'*12} {'-'*20}")
    
    entries = [
        ("perm_001", "Permanent"),
        ("temp_001", "Ephemeral"),
        ("sess_001", "Session"),
        ("cache_001", "Warm Cache"),
        ("active_001", "Refreshed"),
        ("countdown_001", "Expired")
    ]
    
    for entry_id, label in entries:
        ttl = await adapter.get_ttl(entry_id)
        if ttl == -1:
            status = "✅ No expiration"
        elif ttl == -2:
            status = "❌ Expired/removed"
        else:
            status = f"⏳ {ttl}s remaining"
        print(f"   {entry_id:<15} {str(ttl):<12} {status}")
    
    # Pattern 6: Batch save with mixed TTLs
    print(f"\n\n7️⃣  BATCH OPERATIONS - Multiple TTL Strategies")
    
    batch_entries = [
        MemoryEntry(
            id=f"batch_{i:03d}",
            text=f"Batch entry {i}",
            embedding=[0.7 + i*0.01] * 384,
            metadata=MemoryMetadata(
                user_id="batch_user",
                tags=["batch"],
                importance=0.5
            )
        )
        for i in range(5)
    ]
    
    await adapter.bulk_save(batch_entries, ttl=120)
    print(f"   ✅ Saved 5 entries with TTL=120 seconds")
    
    # Count entries by TTL pattern
    total = await adapter.count_async()
    print(f"\n📈 Cache Statistics:")
    print(f"   Total entries: {total}")
    print(f"   Active entries will auto-expire based on their TTL")
    print(f"   Permanent entries require manual cleanup")
    
    # Cleanup
    print(f"\n🧹 Cleaning up demo data...")
    await adapter.clear_async()
    await adapter.close()
    
    print(f"\n✅ Example complete!")
    print(f"\n💡 Key Takeaways:")
    print(f"   • Use NO TTL for critical data requiring manual management")
    print(f"   • Use SHORT TTL (5-30s) for ephemeral/one-time data")
    print(f"   • Use MEDIUM TTL (1-5m) for session/context data")
    print(f"   • Use LONG TTL (5-30m) for warm cache/preferences")
    print(f"   • Use REFRESH pattern for active sessions")
    print(f"   • TTL strategies reduce memory pressure and improve performance")

if __name__ == "__main__":
    asyncio.run(main())
