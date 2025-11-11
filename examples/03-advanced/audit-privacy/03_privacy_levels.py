"""
Privacy Levels

Manage data classification with privacy levels.

Run: python 03_privacy_levels.py
"""

import asyncio
from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.base import PrivacyLevel
from axon.models.filter import Filter


async def main():
    print("=== Privacy Levels ===\n")

    memory = MemorySystem(DEVELOPMENT_CONFIG)

    print("Privacy Levels:\n")
    print("  PUBLIC - No PII, safe for public")
    print("  INTERNAL - Contains emails, phones")
    print("  SENSITIVE - Business-sensitive")
    print("  RESTRICTED - SSN, credit cards\n")

    print("1. Storing with explicit privacy levels...")

    await memory.store(
        "Company blog post content",
        metadata={"privacy_level": PrivacyLevel.PUBLIC}
    )

    await memory.store(
        "Internal team email: team@company.com",
        metadata={"privacy_level": PrivacyLevel.INTERNAL}
    )

    await memory.store(
        "Payment card: 4532-xxxx-xxxx-9010",
        metadata={"privacy_level": PrivacyLevel.RESTRICTED}
    )

    print("  OK Stored with explicit privacy levels\n")

    # Query by privacy
    print("2. Filtering by privacy level...")

    public = await memory.recall("", k=100, filter=Filter(privacy_level="public"))
    internal = await memory.recall("", k=100, filter=Filter(privacy_level="internal"))
    restricted = await memory.recall("", k=100, filter=Filter(privacy_level="restricted"))

    print(f"  PUBLIC: {len(public)} entries")
    print(f"  INTERNAL: {len(internal)} entries")
    print(f"  RESTRICTED: {len(restricted)} entries\n")

    print("=" * 50)
    print("* Privacy levels complete!")


if __name__ == "__main__":
    asyncio.run(main())
