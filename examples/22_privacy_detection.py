"""
Privacy & PII Detection Example

This example demonstrates Axon's automatic PII (Personally Identifiable Information)
detection and privacy level classification system.

Features demonstrated:
- Automatic PII detection (email, SSN, credit cards, phone, IP addresses)
- Privacy level auto-tagging (PUBLIC, INTERNAL, RESTRICTED)
- User override of privacy levels
- Filtering by privacy level
- PII detection metadata storage
- Enabling/disabling PII detection

Run: python examples/22_privacy_detection.py
"""

import asyncio

from axon.core import MemorySystem, PIIDetector
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.base import PrivacyLevel


async def basic_pii_detection():
    """Demonstrate basic PII detection."""
    print("=" * 80)
    print("BASIC PII DETECTION")
    print("=" * 80)

    detector = PIIDetector()

    # Test various PII types
    test_cases = [
        "Contact me at john.doe@example.com",
        "My SSN is 123-45-6789",
        "Payment card: 4532 1234 5678 9010",
        "Call us at (555) 123-4567",
        "Server IP: 192.168.1.100",
        "Email support@company.com or call 555-987-6543. IP: 10.0.0.1",
        "This is just regular text without any sensitive information",
    ]

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"  Has PII: {result.has_pii}")
        if result.has_pii:
            print(f"  Detected types: {', '.join(result.detected_types)}")
            print(f"  Privacy level: {result.recommended_privacy_level.value}")
            print(f"  Details: {result.details}")


async def automatic_privacy_classification():
    """Demonstrate automatic privacy level classification during storage."""
    print("\n\n" + "=" * 80)
    print("AUTOMATIC PRIVACY CLASSIFICATION")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    # Store different types of content
    entries = [
        ("Public info", "The weather is nice today", None),
        ("Email", "Contact sales@company.com for pricing", PrivacyLevel.INTERNAL),
        ("SSN", "Employee SSN: 123-45-6789", PrivacyLevel.RESTRICTED),
        ("Credit Card", "Card number: 4532-1234-5678-9010", PrivacyLevel.RESTRICTED),
        ("Mixed PII", "Email: user@ex.com, Phone: 555-123-4567", PrivacyLevel.INTERNAL),
    ]

    stored_ids = []
    for label, text, expected_level in entries:
        entry_id = await system.store(text)
        stored_ids.append((label, entry_id, expected_level))

        # Retrieve and check privacy level
        tier, entry = await system._get_entry_by_id(entry_id)
        print(f"\n{label}:")
        print(f"  Text: {text}")
        print(f"  Auto-detected level: {entry.metadata.privacy_level.value}")
        print(f"  Expected level: {expected_level.value if expected_level else 'PUBLIC'}")

        if hasattr(entry.metadata, "pii_detection"):
            pii_info = entry.metadata.pii_detection
            print(f"  Detected PII types: {', '.join(pii_info['detected_types'])}")
            print(f"  PII counts: {pii_info['details']}")


async def user_privacy_override():
    """Demonstrate user override of auto-detected privacy levels."""
    print("\n\n" + "=" * 80)
    print("USER PRIVACY LEVEL OVERRIDE")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    # Text with email (normally INTERNAL) but user wants RESTRICTED
    text = "Company email: confidential@example.com"

    # Store without override (auto-detect)
    id1 = await system.store(text)
    tier1, entry1 = await system._get_entry_by_id(id1)
    print(f"\nAuto-detected:")
    print(f"  Privacy level: {entry1.metadata.privacy_level.value}")

    # Store with user override
    id2 = await system.store(text, metadata={"privacy_level": PrivacyLevel.RESTRICTED})
    tier2, entry2 = await system._get_entry_by_id(id2)
    print(f"\nUser override:")
    print(f"  Privacy level: {entry2.metadata.privacy_level.value}")
    print(f"  PII still detected: {'pii_detection' in entry2.metadata.custom}")


async def filter_by_privacy_level():
    """Demonstrate filtering recalls by privacy level."""
    print("\n\n" + "=" * 80)
    print("FILTERING BY PRIVACY LEVEL")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    # Store entries with different privacy levels
    await system.store("General company info")  # PUBLIC
    await system.store("Internal email: team@company.com")  # INTERNAL
    await system.store("Employee SSN: 123-45-6789")  # RESTRICTED
    await system.store("Customer phone: 555-123-4567")  # INTERNAL
    await system.store("Credit card: 4532 1234 5678 9010")  # RESTRICTED

    # Recall all
    all_results = await system.recall("information", k=10)
    print(f"\nTotal entries stored: {len(all_results)}")

    # Group by privacy level
    by_level = {}
    for result in all_results:
        level = result.metadata.privacy_level
        by_level.setdefault(level, []).append(result)

    for level in [PrivacyLevel.PUBLIC, PrivacyLevel.INTERNAL, PrivacyLevel.RESTRICTED]:
        count = len(by_level.get(level, []))
        print(f"{level.value.upper()}: {count} entries")

    # Filter for only RESTRICTED data
    print("\n\nRetrieving only RESTRICTED data:")
    restricted = await system.recall(
        "data", k=10, filter_dict={"privacy_level": PrivacyLevel.RESTRICTED}
    )
    for entry in restricted:
        print(f"  - {entry.text[:50]}... (Privacy: {entry.metadata.privacy_level.value})")


async def pii_detection_metadata():
    """Demonstrate PII detection metadata storage."""
    print("\n\n" + "=" * 80)
    print("PII DETECTION METADATA")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    # Store text with multiple PII types
    text = "Contact john@company.com at (555) 123-4567. Server: 192.168.1.100"
    entry_id = await system.store(text)

    tier, entry = await system._get_entry_by_id(entry_id)

    print(f"\nText: {text}")
    print(f"Privacy level: {entry.metadata.privacy_level.value}")

    if hasattr(entry.metadata, "pii_detection"):
        pii_info = entry.metadata.pii_detection
        print(f"\nPII Detection Results:")
        print(f"  Has PII: {pii_info['has_pii']}")
        print(f"  Detected types: {', '.join(pii_info['detected_types'])}")
        print(f"  Details:")
        for pii_type, count in pii_info["details"].items():
            print(f"    {pii_type}: {count} occurrence(s)")


async def disable_pii_detection():
    """Demonstrate disabling PII detection."""
    print("\n\n" + "=" * 80)
    print("DISABLING PII DETECTION")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG

    # System with PII detection enabled (default)
    system_with_pii = MemorySystem(config, enable_pii_detection=True)
    id1 = await system_with_pii.store("Email: sensitive@company.com")
    tier1, entry1 = await system_with_pii._get_entry_by_id(id1)

    print(f"\nWith PII detection enabled:")
    print(f"  Privacy level: {entry1.metadata.privacy_level.value}")
    print(f"  Has PII metadata: {'pii_detection' in entry1.metadata.custom}")

    # System with PII detection disabled
    system_no_pii = MemorySystem(config, enable_pii_detection=False)
    id2 = await system_no_pii.store("Email: sensitive@company.com")
    tier2, entry2 = await system_no_pii._get_entry_by_id(id2)

    print(f"\nWith PII detection disabled:")
    print(f"  Privacy level: {entry2.metadata.privacy_level.value}")
    print(f"  Has PII metadata: {'pii_detection' in entry2.metadata.custom}")


async def supported_pii_types():
    """Show all supported PII types."""
    print("\n\n" + "=" * 80)
    print("SUPPORTED PII TYPES")
    print("=" * 80)

    detector = PIIDetector()
    types = detector.get_supported_types()

    print(f"\nCurrently supported PII types ({len(types)}):")
    for pii_type in types:
        privacy_level = detector.PRIVACY_LEVELS.get(pii_type, PrivacyLevel.PUBLIC)
        print(f"  - {pii_type}: {privacy_level.value.upper()}")


async def privacy_level_hierarchy():
    """Demonstrate privacy level priority (most restrictive wins)."""
    print("\n\n" + "=" * 80)
    print("PRIVACY LEVEL HIERARCHY")
    print("=" * 80)

    config = DEVELOPMENT_CONFIG
    system = MemorySystem(config)

    test_cases = [
        ("Email only", "Contact: user@example.com", PrivacyLevel.INTERNAL),
        ("Phone only", "Call: (555) 123-4567", PrivacyLevel.INTERNAL),
        (
            "Email + Phone",
            "Email user@ex.com or call 555-123-4567",
            PrivacyLevel.INTERNAL,
        ),
        ("Email + SSN", "Email user@ex.com, SSN: 123-45-6789", PrivacyLevel.RESTRICTED),
        (
            "All types",
            "Email: user@ex.com, SSN: 123-45-6789, Card: 4532-1234-5678-9010",
            PrivacyLevel.RESTRICTED,
        ),
    ]

    print("\nPrivacy level hierarchy (least to most restrictive):")
    print("  PUBLIC < INTERNAL < SENSITIVE < RESTRICTED")
    print("\nTest cases:")

    for label, text, expected in test_cases:
        entry_id = await system.store(text)
        tier, entry = await system._get_entry_by_id(entry_id)

        pii_types = []
        if hasattr(entry.metadata, "pii_detection"):
            pii_types = entry.metadata.pii_detection["detected_types"]

        print(f"\n{label}:")
        print(f"  PII types: {', '.join(pii_types)}")
        print(f"  Result: {entry.metadata.privacy_level.value.upper()}")
        print(f"  Expected: {expected.value.upper()}")
        print(f"  ✓ Correct" if entry.metadata.privacy_level == expected else "  ✗ Incorrect")


async def main():
    """Run all privacy detection examples."""
    print("\n" + "=" * 80)
    print("AXON PRIVACY & PII DETECTION EXAMPLES")
    print("=" * 80)

    await basic_pii_detection()
    await automatic_privacy_classification()
    await user_privacy_override()
    await filter_by_privacy_level()
    await pii_detection_metadata()
    await disable_pii_detection()
    await supported_pii_types()
    await privacy_level_hierarchy()

    print("\n\n" + "=" * 80)
    print("PRIVACY DETECTION EXAMPLES COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  1. PII is automatically detected using regex patterns")
    print("  2. Privacy levels are auto-assigned based on detected PII")
    print("  3. Most restrictive level wins when multiple PII types detected")
    print("  4. Users can override auto-detected privacy levels")
    print("  5. PII detection metadata is stored for audit trails")
    print("  6. PII detection can be disabled if not needed")
    print("\nSupported PII types:")
    print("  - Email addresses → INTERNAL")
    print("  - Phone numbers → INTERNAL")
    print("  - IP addresses → INTERNAL")
    print("  - Social Security Numbers → RESTRICTED")
    print("  - Credit card numbers → RESTRICTED")


if __name__ == "__main__":
    asyncio.run(main())
