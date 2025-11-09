import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def test():
    system = MemorySystem(config=DEVELOPMENT_CONFIG)
    
    # Store entries
    id1 = await system.store("Entry 1")
    id2 = await system.store("Entry 2")
    print(f"Stored: {id1}, {id2}")
    
    # Check which tier they're in
    for tier in ["ephemeral", "session", "persistent"]:
        adapter = await system.registry.get_adapter(tier)
        ids = adapter.list_ids()  # list_ids is sync
        print(f"{tier}: {len(ids)} entries - {ids}")
    
    # Export
    data = await system.export()
    print(f"\nExport entries: {len(data['entries'])}")
    print(f"Total: {data['statistics']['total_entries']}")
    print(f"Stats by tier: {data['statistics']['by_tier']}")
    
    # Also try to recall
    results = await system.recall("Entry")
    print(f"\nRecall results: {len(results)}")


if __name__ == "__main__":
    asyncio.run(test())
