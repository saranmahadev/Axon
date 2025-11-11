"""
Hello World - Your First Memory with Axon

This is the simplest possible example to get started with Axon.
It demonstrates storing and recalling a single piece of information.

Learn:
- How to create a MemorySystem
- How to store your first memory
- How to recall stored memories

Run:
    python 01_hello_world.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG


async def main():
    """Store and recall your first memory."""
    print("=== Axon Hello World ===\n")

    # Step 1: Create a memory system
    print("1. Creating memory system...")
    memory = MemorySystem(DEVELOPMENT_CONFIG)
    print("   OK Memory system created\n")

    # Step 2: Store a memory
    print("2. Storing a memory...")
    content = "Hello, Axon! This is my first memory."
    entry_id = await memory.store(content)
    print(f"   OK Memory stored with ID: {entry_id}\n")

    # Step 3: Recall the memory
    print("3. Recalling memories about 'hello'...")
    results = await memory.recall("hello", k=1)
    print(f"   OK Found {len(results)} result(s)\n")

    # Step 4: Display the result
    if results:
        print("4. Retrieved memory:")
        print(f"   Content: {results[0].text}")
        print(f"   ID: {results[0].id}")
        print(f"   Type: {results[0].type}")

    print("\n* Success! You've stored and recalled your first memory with Axon.")


if __name__ == "__main__":
    asyncio.run(main())
