"""
PII Detection

Automatic detection of Personally Identifiable Information.

Run: python 02_pii_detection.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.base import PrivacyLevel
from axon.models.filter import Filter


async def main():
    print("=== PII Detection ===\n")

    # PII detection enabled by default
    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("1. Storing content with PII...")

    # Email - Internal
    id1 = await memory.store("Contact support at help@company.com")

    # SSN - Restricted
    id2 = await memory.store("SSN: 123-45-6789")

    # No PII - Public
    id3 = await memory.store("Python is a programming language")

    print("  OK Stored 3 entries with varying PII\n")

    # Check privacy levels
    print("2. Checking auto-assigned privacy levels...")

    all_entries = await memory.recall("", k=10)
    for entry in all_entries:
        print(f"\n  Text: {entry.text[:40]}...")
        print(f"  Privacy: {entry.metadata.privacy_level}")
        if hasattr(entry.metadata, 'pii_detection'):
            print(f"  PII Types: {entry.metadata.pii_detection.get('detected_types', [])}")

    # Filter by privacy level
    print("\n3. Query by privacy level...")
    restricted = await memory.recall("", k=100, filter=Filter(privacy_level="restricted"))
    print(f"  Restricted entries: {len(restricted)}\n")

    print("=" * 50)
    print("* PII detection complete!")


if __name__ == "__main__":
    asyncio.run(main())
