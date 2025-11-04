"""Basic usage example for Axon Memory SDK.

This example demonstrates the fundamental data models and their usage.
Full MemorySystem API will be available in Sprint 3.1.
"""

from axon import Filter, MemoryEntry, MemoryMetadata, MemoryTier, PrivacyLevel


def main():
    """Demonstrate basic Axon model usage."""

    # Create a memory entry
    print("Creating a memory entry...")
    entry = MemoryEntry(
        text="User mentioned they love science fiction movies, especially Blade Runner.",
        type="conversation_turn",
        metadata=MemoryMetadata(
            user_id="user_12345",
            session_id="session_abc",
            tags=["preferences", "movies", "sci-fi"],
            importance=0.8,
            privacy_level="public",
        ),
    )

    print(f"Created entry: {entry.id}")
    print(f"Text: {entry.text}")
    print(f"Type: {entry.type}")
    print(f"Has embedding: {entry.has_embedding}")
    print(f"User: {entry.metadata.user_id}")
    print(f"Tags: {entry.metadata.tags}")
    print(f"Importance: {entry.metadata.importance}")
    print()

    # Add provenance
    print("Adding provenance...")
    entry.add_provenance("store", "example_app", tier="persistent")
    print(f"Provenance events: {len(entry.metadata.provenance)}")
    print(f"Latest event: {entry.metadata.provenance[-1].action}")
    print()

    # Update access time
    print("Updating access time...")
    entry.update_accessed()
    print(f"Last accessed: {entry.metadata.last_accessed_at}")
    print()

    # Create a filter
    print("Creating a filter...")
    filter_obj = Filter(
        user_id="user_12345", tags=["preferences"], min_importance=0.5, privacy_level="public"
    )

    # Test filter matching
    print("Testing filter match...")
    matches = filter_obj.matches(entry)
    print(f"Entry matches filter: {matches}")
    print()

    # Serialize to JSON
    print("Serializing to JSON...")
    json_data = entry.model_dump_json(indent=2)
    print("JSON representation:")
    print(json_data[:200] + "...")
    print()

    # Demonstrate enums
    print("Memory tiers available:")
    for tier in MemoryTier:
        print(f"  - {tier.value}")

    print("\nPrivacy levels available:")
    for level in PrivacyLevel:
        print(f"  - {level.value}")

    print("\n✅ Basic usage example complete!")
    print("📚 Full MemorySystem API coming in Sprint 3.1")


if __name__ == "__main__":
    main()
