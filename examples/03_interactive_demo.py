"""Interactive Qdrant Demo Application.

A full-featured interactive demo showcasing all Qdrant adapter capabilities.

Features:
    - Interactive CLI menu
    - Add/search/delete memories
    - Apply filters (tags, importance, dates)
    - View statistics
    - Export/import data

Prerequisites:
    - Qdrant running at localhost:6333
    - OpenAI API key in .env file

Run:
    python examples/03_interactive_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.axon.adapters import QdrantAdapter
from src.axon.embedders import OpenAIEmbedder
from src.axon.models import Filter, MemoryEntry, MemoryMetadata, ProvenanceEvent


class InteractiveDemo:
    """Interactive demo application for Qdrant adapter."""

    def __init__(self):
        """Initialize the demo app."""
        self.embedder = None
        self.storage = None
        self.running = True

    async def initialize(self):
        """Initialize embedder and storage."""
        import os

        from dotenv import load_dotenv

        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Error: OPENAI_API_KEY not found in environment")
            print("   Please create a .env file with your OpenAI API key")
            self.running = False
            return

        print("\n🔧 Initializing AxonML Memory System...")
        self.embedder = OpenAIEmbedder(api_key=api_key, model="text-embedding-3-small")
        self.storage = QdrantAdapter(
            url="http://localhost:6333", collection_name="interactive_demo"
        )
        print("   ✓ Ready!\n")

    def print_menu(self):
        """Print the main menu."""
        print("\n" + "=" * 60)
        print("🧠 AXONML INTERACTIVE DEMO - Qdrant Backend")
        print("=" * 60)
        print("\n📝 Memory Operations:")
        print("  1. Add a new memory")
        print("  2. Search memories (semantic)")
        print("  3. List all memories")
        print("  4. Delete a memory")
        print("\n🔍 Advanced Features:")
        print("  5. Search with filters")
        print("  6. View statistics")
        print("  7. Export memories")
        print("  8. Import memories")
        print("\n💡 Examples:")
        print("  9. Load sample data")
        print("  10. Clear all memories")
        print("\n  0. Exit")
        print("\n" + "─" * 60)

    async def add_memory(self):
        """Add a new memory."""
        print("\n➕ ADD NEW MEMORY")
        print("─" * 60)

        text = input("Memory text: ").strip()
        if not text:
            print("❌ Empty text, cancelling...")
            return

        # Get metadata
        print("\n📋 Metadata (press Enter to skip):")
        tags_input = input("  Tags (comma-separated): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

        importance_input = input("  Importance (0.0-1.0, default 0.5): ").strip()
        importance = float(importance_input) if importance_input else 0.5

        privacy_input = input(
            "  Privacy level (public/sensitive/private, default public): "
        ).strip()
        privacy_level = (
            privacy_input if privacy_input in ["public", "sensitive", "private"] else "public"
        )

        # Generate embedding
        print("\n🔄 Generating embedding...")
        embedding = await self.embedder.embed(text)

        # Create entry
        entry = MemoryEntry(
            text=text,
            embedding=embedding,
            metadata=MemoryMetadata(
                source="app",
                privacy_level=privacy_level,
                importance=importance,
                tags=tags,
                provenance=[
                    ProvenanceEvent(
                        action="store", by="interactive_demo", metadata={"method": "manual_entry"}
                    )
                ],
            ),
        )

        # Save
        await self.storage.save(entry)
        print("\n✅ Memory saved!")
        print(f"   ID: {entry.id}")
        print(f"   Importance: {importance}")
        print(f"   Tags: {', '.join(tags) if tags else 'none'}")

    async def search_memories(self):
        """Search memories semantically."""
        print("\n🔍 SEMANTIC SEARCH")
        print("─" * 60)

        query = input("Search query: ").strip()
        if not query:
            print("❌ Empty query, cancelling...")
            return

        limit_input = input("Max results (default 5): ").strip()
        limit = int(limit_input) if limit_input else 5

        # Generate query embedding
        print("\n🔄 Searching...")
        query_embedding = await self.embedder.embed(query)

        # Search
        results = await self.storage.query(query_embedding, limit=limit)

        if not results:
            print("\n❌ No results found")
            return

        print(f"\n📊 Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.text[:80]}{'...' if len(result.text) > 80 else ''}")
            print(f"   ID: {result.id}")
            print(
                f"   Importance: {'⭐' * int(result.metadata.importance * 5)} ({result.metadata.importance:.2f})"
            )
            print(f"   Tags: {', '.join(result.metadata.tags) if result.metadata.tags else 'none'}")
            print(f"   Created: {result.metadata.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()

    async def list_all_memories(self):
        """List all memories in the collection."""
        print("\n📋 ALL MEMORIES")
        print("─" * 60)

        ids = await self.storage.list_ids_async()

        if not ids:
            print("\n❌ No memories found")
            return

        print(f"\nTotal: {len(ids)} memories\n")

        # Retrieve and display first 10
        display_count = min(10, len(ids))
        print(f"Showing first {display_count}:\n")

        for i, memory_id in enumerate(ids[:display_count], 1):
            entry = await self.storage.get(memory_id)
            if entry:
                print(f"{i}. {entry.text[:70]}{'...' if len(entry.text) > 70 else ''}")
                print(f"   ID: {entry.id}")
                print(f"   Importance: {entry.metadata.importance:.2f}")
                print()

        if len(ids) > display_count:
            print(f"... and {len(ids) - display_count} more")

    async def delete_memory(self):
        """Delete a memory by ID."""
        print("\n🗑️  DELETE MEMORY")
        print("─" * 60)

        memory_id = input("Memory ID: ").strip()
        if not memory_id:
            print("❌ Empty ID, cancelling...")
            return

        # Confirm
        confirm = input(f"Delete memory {memory_id}? (y/N): ").strip().lower()
        if confirm != "y":
            print("❌ Cancelled")
            return

        # Delete
        deleted = await self.storage.delete(memory_id)
        if deleted:
            print("✅ Memory deleted")
        else:
            print("❌ Memory not found")

    async def search_with_filters(self):
        """Search with advanced filters."""
        print("\n🎯 ADVANCED SEARCH WITH FILTERS")
        print("─" * 60)

        query = input("Search query: ").strip()
        if not query:
            print("❌ Empty query, cancelling...")
            return

        # Build filter
        print("\n🔧 Filters (press Enter to skip):")

        tags_input = input("  Tags (comma-separated): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

        min_imp = input("  Min importance (0.0-1.0): ").strip()
        min_importance = float(min_imp) if min_imp else None

        privacy = input("  Privacy level (public/sensitive/private): ").strip()
        privacy_level = privacy if privacy in ["public", "sensitive", "private"] else None

        # Create filter
        filter_obj = Filter(tags=tags, min_importance=min_importance, privacy_level=privacy_level)

        # Search
        print("\n🔄 Searching...")
        query_embedding = await self.embedder.embed(query)
        results = await self.storage.query(query_embedding, filter=filter_obj, limit=10)

        if not results:
            print("\n❌ No results found")
            return

        print(f"\n📊 Found {len(results)} matching results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.text[:80]}{'...' if len(result.text) > 80 else ''}")
            print(f"   Importance: {result.metadata.importance:.2f}")
            print(f"   Privacy: {result.metadata.privacy_level}")
            print(f"   Tags: {', '.join(result.metadata.tags) if result.metadata.tags else 'none'}")
            print()

    async def view_statistics(self):
        """Display collection statistics."""
        print("\n📊 COLLECTION STATISTICS")
        print("─" * 60)

        total = await self.storage.count_async()
        ids = await self.storage.list_ids_async()

        print(f"\nTotal Memories: {total}")
        print("Collection: interactive_demo")
        print("Backend: Qdrant (http://localhost:6333)")
        print("Embedding Model: text-embedding-3-small")

        # Importance distribution
        if ids:
            print("\n📈 Sample Analysis (first 20):")
            sample_ids = ids[:20]
            importances = []
            privacy_counts = {"public": 0, "sensitive": 0, "private": 0}

            for memory_id in sample_ids:
                entry = await self.storage.get(memory_id)
                if entry:
                    importances.append(entry.metadata.importance)
                    privacy_counts[entry.metadata.privacy_level] = (
                        privacy_counts.get(entry.metadata.privacy_level, 0) + 1
                    )

            if importances:
                avg_importance = sum(importances) / len(importances)
                print(f"  Average Importance: {avg_importance:.2f}")
                print("  Privacy Distribution:")
                for level, count in privacy_counts.items():
                    print(f"    {level}: {count}")

    async def export_memories(self):
        """Export memories to JSON file."""
        print("\n💾 EXPORT MEMORIES")
        print("─" * 60)

        filename = input("Export filename (default: memories_export.json): ").strip()
        if not filename:
            filename = "memories_export.json"

        if not filename.endswith(".json"):
            filename += ".json"

        # Get all memories
        ids = await self.storage.list_ids_async()
        memories = []

        print(f"\n🔄 Exporting {len(ids)} memories...")
        for memory_id in ids:
            entry = await self.storage.get(memory_id)
            if entry:
                memories.append(entry.model_dump(mode="json"))

        # Write to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2, default=str)

        print(f"✅ Exported {len(memories)} memories to {filename}")

    async def load_sample_data(self):
        """Load sample data into the collection."""
        print("\n🎲 LOAD SAMPLE DATA")
        print("─" * 60)

        samples = [
            ("Python is a versatile programming language", ["programming", "python"], 0.7),
            ("Machine learning models require training data", ["ml", "ai"], 0.8),
            ("Vector databases enable semantic search", ["database", "vectors"], 0.9),
            ("Natural language processing analyzes text", ["nlp", "ai"], 0.75),
            ("APIs enable software integration", ["api", "integration"], 0.6),
        ]

        print(f"\n📦 Adding {len(samples)} sample memories...")

        entries = []
        for text, tags, importance in samples:
            embedding = await self.embedder.embed(text)
            entry = MemoryEntry(
                text=text,
                embedding=embedding,
                metadata=MemoryMetadata(
                    source="system",
                    importance=importance,
                    tags=tags,
                    provenance=[ProvenanceEvent(action="store", by="sample_data_loader")],
                ),
            )
            entries.append(entry)

        await self.storage.bulk_save(entries)
        print(f"✅ Added {len(entries)} sample memories")

    async def clear_all(self):
        """Clear all memories from the collection."""
        print("\n⚠️  CLEAR ALL MEMORIES")
        print("─" * 60)

        total = await self.storage.count_async()
        confirm = input(f"⚠️  Delete ALL {total} memories? Type 'DELETE' to confirm: ").strip()

        if confirm != "DELETE":
            print("❌ Cancelled")
            return

        await self.storage.clear_async()
        print("✅ All memories cleared")

    async def run(self):
        """Run the interactive demo."""
        await self.initialize()

        while self.running:
            self.print_menu()
            choice = input("Choose an option: ").strip()

            try:
                if choice == "0":
                    print("\n👋 Goodbye!")
                    self.running = False
                elif choice == "1":
                    await self.add_memory()
                elif choice == "2":
                    await self.search_memories()
                elif choice == "3":
                    await self.list_all_memories()
                elif choice == "4":
                    await self.delete_memory()
                elif choice == "5":
                    await self.search_with_filters()
                elif choice == "6":
                    await self.view_statistics()
                elif choice == "7":
                    await self.export_memories()
                elif choice == "8":
                    print("❌ Import not yet implemented")
                elif choice == "9":
                    await self.load_sample_data()
                elif choice == "10":
                    await self.clear_all()
                else:
                    print("\n❌ Invalid option")

                if self.running and choice != "0":
                    input("\nPress Enter to continue...")

            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("\nPress Enter to continue...")


async def main():
    """Run the interactive demo application."""
    print("\n" + "=" * 60)
    print("🎮 AXONML INTERACTIVE DEMO")
    print("   Powered by Qdrant Vector Database")
    print("=" * 60)

    demo = InteractiveDemo()
    await demo.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
