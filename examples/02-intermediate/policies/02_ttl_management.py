"""
TTL (Time-To-Live) Management

Learn how to configure and manage TTL settings for automatic memory
expiration across different tiers.

Learn:
- TTL configuration per tier
- TTL validation constraints
- Automatic expiration behavior
- TTL-based eviction
- Best practices for TTL values

Run:
    python 02_ttl_management.py
"""

import asyncio
from axon import MemorySystem
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


async def main():
    """Demonstrate TTL management across tiers."""
    print("=== TTL Management ===\n")

    # 1. TTL Configuration
    print("1. TTL Configuration by Tier")
    print("-" * 50)

    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",
            ttl_seconds=30  # 30 seconds
        ),
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=600,  # 10 minutes
            max_entries=100
        ),
        persistent=PersistentPolicy(
            adapter_type="memory",
            ttl_seconds=None  # No expiration
        ),
        default_tier="session"
    )

    print("  Ephemeral TTL: 30s")
    print("  Session TTL: 600s (10 minutes)")
    print("  Persistent TTL: None (permanent)")
    print()

    memory = MemorySystem(config)

    # 2. Store with different TTLs
    print("2. Store memories with different TTL behaviors")
    print("-" * 50)

    # Short-lived ephemeral
    ephemeral_id = await memory.store(
        "Temporary verification code: 123456",
        tier="ephemeral",
        tags=["temp", "verification"]
    )
    print(f"  OK Ephemeral: Expires in 30s")

    # Medium-lived session
    session_id = await memory.store(
        "User currently editing document_draft_v2",
        tier="session",
        tags=["session", "activity"]
    )
    print(f"  OK Session: Expires in 10 minutes")

    # Permanent persistent
    persistent_id = await memory.store(
        "User preference: Dark mode enabled",
        tier="persistent",
        tags=["preferences", "permanent"]
    )
    print(f"  OK Persistent: Never expires")
    print()

    # 3. TTL Constraints
    print("3. TTL Constraints and Validation")
    print("-" * 50)

    print("  Ephemeral tier:")
    print("    Min TTL: 5 seconds")
    print("    Max TTL: 3600 seconds (1 hour)")
    print("    Purpose: Prevent too short or too long ephemeral data")
    print()

    print("  Session tier:")
    print("    Min TTL: 60 seconds (if set)")
    print("    Max TTL: No limit")
    print("    Purpose: Avoid premature session expiration")
    print()

    print("  Persistent tier:")
    print("    TTL: Typically None (permanent)")
    print("    Can set TTL for: archival, compliance, GDPR")
    print()

    # 4. TTL Validation Examples
    print("4. TTL Validation")
    print("-" * 50)

    # Too short for ephemeral
    try:
        invalid = EphemeralPolicy(ttl_seconds=2)
    except ValueError as e:
        print(f"  X Ephemeral TTL=2s rejected: {e}")

    # Too long for ephemeral
    try:
        invalid = EphemeralPolicy(ttl_seconds=7200)
    except ValueError as e:
        print(f"  X Ephemeral TTL=7200s rejected: {e}")

    # Too short for session
    try:
        invalid = SessionPolicy(ttl_seconds=30)
    except ValueError as e:
        print(f"  X Session TTL=30s rejected: {e}")

    print()

    # 5. TTL Use Cases
    print("5. Common TTL Patterns")
    print("-" * 50)

    patterns = [
        ("Rate limiting tokens", "ephemeral", 60, "Prevent API abuse"),
        ("OTP codes", "ephemeral", 300, "5-minute verification window"),
        ("Chat history", "session", 3600, "1-hour conversation context"),
        ("Active workspace", "session", 7200, "2-hour work session"),
        ("User preferences", "persistent", None, "Permanent storage"),
        ("GDPR compliance data", "persistent", 2592000, "30-day retention"),
    ]

    for use_case, tier, ttl, description in patterns:
        ttl_str = f"{ttl}s" if ttl else "None"
        print(f"\n  {use_case}:")
        print(f"    Tier: {tier}")
        print(f"    TTL: {ttl_str}")
        print(f"    Purpose: {description}")

    print()

    # 6. TTL and Importance Interaction
    print("6. TTL vs. Importance")
    print("-" * 50)
    print("  TTL and importance are independent:")
    print()
    print("  High importance + Short TTL:")
    print("    Use case: Temporary high-value data (OTPs, tokens)")
    print()
    print("  Low importance + No TTL:")
    print("    Use case: Logs, audit trails (permanent but low priority)")
    print()
    print("  High importance + No TTL:")
    print("    Use case: Critical persistent data (credentials, preferences)")
    print()

    # 7. TTL Best Practices
    print("7. TTL Best Practices")
    print("-" * 50)
    print()
    print("  1. Match TTL to data lifecycle:")
    print("     - Ephemeral: Seconds to minutes")
    print("     - Session: Minutes to hours")
    print("     - Persistent: None or very long")
    print()
    print("  2. Consider access patterns:")
    print("     - Frequently accessed: Longer TTL")
    print("     - One-time use: Shorter TTL")
    print()
    print("  3. Balance memory and freshness:")
    print("     - Shorter TTL = Less memory usage")
    print("     - Longer TTL = Better cache hit rate")
    print()
    print("  4. Compliance and regulations:")
    print("     - GDPR: Consider data retention limits")
    print("     - Audit logs: May require minimum TTL")
    print()

    print("=" * 50)
    print("* Successfully demonstrated TTL management!")
    print("=" * 50)
    print("\nTTL Summary:")
    print("  * TTL controls automatic expiration")
    print("  * Each tier has different TTL constraints")
    print("  * Ephemeral: 5s to 1hr")
    print("  * Session: >=60s")
    print("  * Persistent: None or very long")
    print("  * Choose TTL based on data lifecycle and compliance")


if __name__ == "__main__":
    asyncio.run(main())
