"""
Basic MemorySystem Usage Example.

Demonstrates fundamental MemorySystem operations:
- Configuration with multiple tiers
- Storing memories with different importance levels
- Recalling memories with filters
- Tracing and monitoring operations
- Viewing statistics

This example shows how memories are automatically routed to appropriate
tiers (ephemeral, session, persistent) based on importance scores.
"""

import asyncio
from datetime import datetime

from axon.core.memory_system import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy
from axon.models.filter import Filter


async def main():
    """Demonstrate basic MemorySystem operations."""
    
    print("=" * 70)
    print("AxonML Memory System - Basic Usage Example")
    print("=" * 70)
    print()
    
    # ========================================================================
    # Step 1: Configure the Memory System
    # ========================================================================
    print("Step 1: Configuring Memory System with 3 tiers")
    print("-" * 70)
    
    config = MemoryConfig(
        # Ephemeral tier: Short-lived, low-importance memories
        ephemeral=EphemeralPolicy(
            adapter_type="memory",      # In-memory storage
            max_entries=10,              # Limit to 10 entries
            ttl_seconds=60               # Auto-expire after 60 seconds
        ),
        
        # Session tier: Medium-lived, moderate-importance memories
        session=SessionPolicy(
            adapter_type="memory",       # In-memory storage
            max_entries=50,              # Limit to 50 entries
            ttl_seconds=3600             # Auto-expire after 1 hour
        ),
        
        # Persistent tier: Long-lived, high-importance memories
        persistent=PersistentPolicy(
            adapter_type="memory",       # In-memory storage
            max_entries=1000             # Limit to 1000 entries
        ),
        
        default_tier="session",          # Default tier for new memories
        enable_promotion=True,           # Auto-promote important memories
        enable_demotion=True             # Auto-demote old/unimportant memories
    )
    
    print(f"✓ Ephemeral tier: {config.ephemeral.max_entries} entries, "
          f"{config.ephemeral.ttl_seconds}s TTL")
    print(f"✓ Session tier: {config.session.max_entries} entries, "
          f"{config.session.ttl_seconds}s TTL")
    print(f"✓ Persistent tier: {config.persistent.max_entries} entries")
    print(f"✓ Default tier: {config.default_tier}")
    print()
    
    # ========================================================================
    # Step 2: Initialize the Memory System
    # ========================================================================
    print("Step 2: Initializing Memory System")
    print("-" * 70)
    
    async with MemorySystem(config=config) as memory:
        print("✓ Memory System initialized successfully")
        print()
        
        # ====================================================================
        # Step 3: Store Memories with Different Importance Levels
        # ====================================================================
        print("Step 3: Storing memories with different importance levels")
        print("-" * 70)
        
        # Low importance → Ephemeral tier
        id1 = await memory.store(
            "User viewed the homepage",
            importance=0.1,
            tags=["analytics", "page-view"],
            metadata={"page": "home", "duration": 5}
        )
        print(f"✓ Stored low-importance memory (ID: {id1[:8]}...) → Ephemeral tier")
        
        # Medium importance → Session tier
        id2 = await memory.store(
            "User added item to shopping cart",
            importance=0.5,
            tags=["commerce", "cart"],
            metadata={"item_id": "ABC123", "price": 29.99}
        )
        print(f"✓ Stored medium-importance memory (ID: {id2[:8]}...) → Session tier")
        
        # High importance → Persistent tier
        id3 = await memory.store(
            "User completed purchase and payment",
            importance=0.95,
            tags=["commerce", "purchase", "critical"],
            metadata={"order_id": "ORD-2025-001", "amount": 129.99}
        )
        print(f"✓ Stored high-importance memory (ID: {id3[:8]}...) → Persistent tier")
        
        # Store more memories for demonstration
        await memory.store(
            "User searched for 'python tutorials'",
            importance=0.3,
            tags=["search", "learning"],
            metadata={"query": "python tutorials", "results": 42}
        )
        
        await memory.store(
            "User updated profile information",
            importance=0.8,
            tags=["profile", "settings"],
            metadata={"fields_changed": ["email", "phone"]}
        )
        
        print(f"✓ Stored 5 total memories")
        print()
        
        # ====================================================================
        # Step 4: Recall Memories
        # ====================================================================
        print("Step 4: Recalling memories")
        print("-" * 70)
        
        # Basic recall - searches all tiers
        print("\n4a. Basic recall (searching all tiers):")
        results = await memory.recall("user", k=10)
        print(f"   Found {len(results)} memories containing 'user'")
        for i, entry in enumerate(results[:3], 1):
            print(f"   {i}. {entry.text[:50]}... "
                  f"(importance: {entry.metadata.importance:.2f})")
        
        # Recall with tag filter
        print("\n4b. Recall with tag filter (commerce):")
        results = await memory.recall(
            "purchase",
            k=5,
            filter=Filter(tags=["commerce"])
        )
        print(f"   Found {len(results)} commerce-related memories")
        for entry in results:
            print(f"   - {entry.text[:50]}...")
        
        # Recall with importance threshold
        print("\n4c. Recall high-importance memories only:")
        results = await memory.recall(
            "user",
            k=10,
            min_importance=0.7
        )
        print(f"   Found {len(results)} memories with importance ≥ 0.7")
        for entry in results:
            print(f"   - {entry.text[:50]}... "
                  f"(importance: {entry.metadata.importance:.2f})")
        
        # Recall from specific tiers
        print("\n4d. Recall from persistent tier only:")
        results = await memory.recall(
            "user",
            k=10,
            tiers=["persistent"]
        )
        print(f"   Found {len(results)} memories in persistent tier")
        print()
        
        # ====================================================================
        # Step 5: View Tracing Information
        # ====================================================================
        print("Step 5: Viewing trace events")
        print("-" * 70)
        
        trace = memory.get_trace_events(limit=5)
        print(f"Showing last {len(trace)} trace events:")
        print()
        
        for i, event in enumerate(trace, 1):
            print(f"{i}. Operation: {event.operation.upper()}")
            print(f"   Timestamp: {event.timestamp.strftime('%H:%M:%S')}")
            print(f"   Duration: {event.duration_ms:.2f}ms")
            if event.tier:
                print(f"   Tier: {event.tier}")
            if event.entry_id:
                print(f"   Entry ID: {event.entry_id[:8]}...")
            print()
        
        # Filter trace by operation
        print("Filtering trace for 'store' operations only:")
        store_events = memory.get_trace_events(operation="store")
        print(f"Found {len(store_events)} store operations")
        print()
        
        # ====================================================================
        # Step 6: View Statistics
        # ====================================================================
        print("Step 6: Viewing system statistics")
        print("-" * 70)
        
        stats = memory.get_statistics()
        
        print("Total Operations:")
        print(f"  Stores:  {stats['total_operations']['stores']}")
        print(f"  Recalls: {stats['total_operations']['recalls']}")
        print(f"  Forgets: {stats['total_operations']['forgets']}")
        print()
        
        print("Per-Tier Statistics:")
        for tier_name, tier_stats in stats['tier_stats'].items():
            print(f"  {tier_name.capitalize()}:")
            print(f"    Stores:  {tier_stats.get('stores', 0)}")
            print(f"    Recalls: {tier_stats.get('recalls', 0)}")
            if 'promotions' in tier_stats:
                print(f"    Promotions: {tier_stats['promotions']}")
        print()
        
        print(f"Total Trace Events: {stats['trace_events']}")
        print()
        
        # ====================================================================
        # Step 7: Demonstrate Trace Control
        # ====================================================================
        print("Step 7: Controlling tracing")
        print("-" * 70)
        
        # Disable tracing
        memory.enable_tracing(False)
        print("✓ Tracing disabled")
        
        # Perform operations (won't be traced)
        await memory.store("This won't be traced", importance=0.5)
        
        # Re-enable tracing
        memory.enable_tracing(True)
        print("✓ Tracing re-enabled")
        
        # Clear trace history
        memory.clear_trace_events()
        print("✓ Trace history cleared")
        print()
        
        # ====================================================================
        # Step 8: Error Handling Examples
        # ====================================================================
        print("Step 8: Error handling examples")
        print("-" * 70)
        
        # Empty content
        try:
            await memory.store("", importance=0.5)
        except ValueError as e:
            print(f"✓ Empty content rejected: {e}")
        
        # Invalid importance
        try:
            await memory.store("Test", importance=1.5)
        except ValueError as e:
            print(f"✓ Invalid importance rejected: {e}")
        
        # Invalid tier
        try:
            await memory.store("Test", importance=0.5, tier="nonexistent")
        except ValueError as e:
            print(f"✓ Invalid tier rejected: {e}")
        
        # Empty query
        try:
            await memory.recall("", k=5)
        except ValueError as e:
            print(f"✓ Empty query rejected: {e}")
        
        print()
        
        # ====================================================================
        # Step 9: Final Summary
        # ====================================================================
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        
        final_stats = memory.get_statistics()
        total_stores = final_stats['total_operations']['stores']
        total_recalls = final_stats['total_operations']['recalls']
        
        print(f"✓ Successfully stored {total_stores} memories")
        print(f"✓ Performed {total_recalls} recall operations")
        print(f"✓ Memory system automatically routed memories to appropriate tiers")
        print(f"✓ All operations traced and monitored")
        print()
        print("Example completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
