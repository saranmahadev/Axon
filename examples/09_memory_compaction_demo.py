"""
Memory Compaction Demo
======================

This example demonstrates Axon's intelligent memory compaction system:

1. **Automatic Summarization**: Older entries are summarized to save space
2. **Embedding Preservation**: Vector embeddings enable semantic search
3. **Provenance Tracking**: Full audit trail of compaction operations
4. **Storage Optimization**: Reduce memory footprint while retaining key information

The compaction system uses LLMs to create intelligent summaries that preserve
the semantic meaning of multiple memory entries.

Requirements:
- OPENAI_API_KEY in .env file
- ChromaDB installed (pip install chromadb)
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from axon.core.memory_system import MemorySystem
from axon.core.config import AdapterConfig, PersistentPolicy, TierConfig
from axon.core.summarizer import LLMSummarizer
from axon.embedders import OpenAIEmbedder
from axon.models import MemoryEntry, MemoryEntryType

# Load environment variables
load_dotenv()

console = Console()


def create_sample_memories() -> List[dict]:
    """
    Create sample memory entries representing a user's authentication journey.
    
    These entries simulate a realistic conversation about implementing authentication.
    """
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    
    memories = [
        {
            "content": "User asked about implementing JWT authentication in the application",
            "offset": timedelta(hours=0),
            "tags": ["authentication", "jwt", "security"]
        },
        {
            "content": "Explained the basics of JWT tokens: header, payload, and signature",
            "offset": timedelta(hours=1),
            "tags": ["authentication", "jwt", "tutorial"]
        },
        {
            "content": "User decided to use RS256 algorithm for better security",
            "offset": timedelta(hours=2),
            "tags": ["authentication", "jwt", "security", "algorithms"]
        },
        {
            "content": "Implemented token generation endpoint with 1-hour expiration",
            "offset": timedelta(hours=3),
            "tags": ["authentication", "implementation", "api"]
        },
        {
            "content": "Added refresh token mechanism with 7-day expiration",
            "offset": timedelta(hours=4),
            "tags": ["authentication", "refresh-token", "api"]
        },
        {
            "content": "Discussed storing tokens securely in httpOnly cookies",
            "offset": timedelta(hours=5),
            "tags": ["authentication", "security", "cookies"]
        },
        {
            "content": "Implemented middleware for token validation on protected routes",
            "offset": timedelta(hours=6),
            "tags": ["authentication", "middleware", "implementation"]
        },
        {
            "content": "Added role-based access control (RBAC) using token claims",
            "offset": timedelta(hours=7),
            "tags": ["authentication", "authorization", "rbac"]
        },
        {
            "content": "Created user registration endpoint with password hashing using bcrypt",
            "offset": timedelta(hours=8),
            "tags": ["authentication", "registration", "security", "password"]
        },
        {
            "content": "Implemented login endpoint that returns JWT tokens",
            "offset": timedelta(hours=9),
            "tags": ["authentication", "login", "api"]
        },
        {
            "content": "Added logout functionality that invalidates tokens",
            "offset": timedelta(hours=10),
            "tags": ["authentication", "logout", "api"]
        },
        {
            "content": "Discussed token blacklisting strategy for enhanced security",
            "offset": timedelta(hours=11),
            "tags": ["authentication", "security", "tokens"]
        },
        {
            "content": "User asked about OAuth2 integration with Google",
            "offset": timedelta(days=1),
            "tags": ["authentication", "oauth2", "google"]
        },
        {
            "content": "Explained OAuth2 flow: authorization code grant",
            "offset": timedelta(days=1, hours=1),
            "tags": ["authentication", "oauth2", "tutorial"]
        },
        {
            "content": "Implemented OAuth2 client using passport.js",
            "offset": timedelta(days=1, hours=2),
            "tags": ["authentication", "oauth2", "implementation"]
        },
        {
            "content": "Added social login buttons for Google and GitHub",
            "offset": timedelta(days=1, hours=3),
            "tags": ["authentication", "oauth2", "ui"]
        },
        {
            "content": "Discussed handling OAuth2 callback and user creation",
            "offset": timedelta(days=1, hours=4),
            "tags": ["authentication", "oauth2", "users"]
        },
        {
            "content": "Implemented account linking for users with multiple auth methods",
            "offset": timedelta(days=1, hours=5),
            "tags": ["authentication", "oauth2", "users"]
        },
        {
            "content": "User reported issue with token expiration handling",
            "offset": timedelta(days=2),
            "tags": ["authentication", "debugging", "tokens"]
        },
        {
            "content": "Fixed token refresh logic to handle expiration edge cases",
            "offset": timedelta(days=2, hours=1),
            "tags": ["authentication", "bugfix", "tokens"]
        },
        {
            "content": "Added comprehensive error messages for authentication failures",
            "offset": timedelta(days=2, hours=2),
            "tags": ["authentication", "error-handling", "ux"]
        },
        {
            "content": "Implemented rate limiting on login endpoint to prevent brute force",
            "offset": timedelta(days=2, hours=3),
            "tags": ["authentication", "security", "rate-limiting"]
        },
        {
            "content": "Added email verification for new user registrations",
            "offset": timedelta(days=3),
            "tags": ["authentication", "registration", "email"]
        },
        {
            "content": "Implemented password reset flow with time-limited tokens",
            "offset": timedelta(days=3, hours=1),
            "tags": ["authentication", "password", "security"]
        },
        {
            "content": "User asked about two-factor authentication (2FA)",
            "offset": timedelta(days=4),
            "tags": ["authentication", "2fa", "security"]
        },
        {
            "content": "Explained TOTP algorithm for 2FA implementation",
            "offset": timedelta(days=4, hours=1),
            "tags": ["authentication", "2fa", "totp", "tutorial"]
        },
        {
            "content": "Implemented 2FA using speakeasy library for TOTP",
            "offset": timedelta(days=4, hours=2),
            "tags": ["authentication", "2fa", "implementation"]
        },
        {
            "content": "Added QR code generation for 2FA setup",
            "offset": timedelta(days=4, hours=3),
            "tags": ["authentication", "2fa", "qrcode"]
        },
        {
            "content": "Implemented backup codes for 2FA recovery",
            "offset": timedelta(days=4, hours=4),
            "tags": ["authentication", "2fa", "recovery"]
        },
        {
            "content": "Added SMS-based 2FA as alternative to TOTP",
            "offset": timedelta(days=4, hours=5),
            "tags": ["authentication", "2fa", "sms"]
        },
        {
            "content": "Discussed session management and concurrent login policies",
            "offset": timedelta(days=5),
            "tags": ["authentication", "sessions", "security"]
        },
        {
            "content": "Implemented device tracking for security monitoring",
            "offset": timedelta(days=5, hours=1),
            "tags": ["authentication", "security", "monitoring"]
        },
        {
            "content": "Added suspicious activity alerts for login anomalies",
            "offset": timedelta(days=5, hours=2),
            "tags": ["authentication", "security", "alerts"]
        },
        {
            "content": "User asked about API key management for service accounts",
            "offset": timedelta(days=6),
            "tags": ["authentication", "api-keys", "services"]
        },
        {
            "content": "Implemented API key generation and validation system",
            "offset": timedelta(days=6, hours=1),
            "tags": ["authentication", "api-keys", "implementation"]
        },
        {
            "content": "Added API key rotation mechanism for enhanced security",
            "offset": timedelta(days=6, hours=2),
            "tags": ["authentication", "api-keys", "security"]
        },
        {
            "content": "Implemented scope-based permissions for API keys",
            "offset": timedelta(days=6, hours=3),
            "tags": ["authentication", "api-keys", "authorization"]
        },
        {
            "content": "Added comprehensive audit logging for all auth events",
            "offset": timedelta(days=7),
            "tags": ["authentication", "audit", "logging", "security"]
        },
        {
            "content": "Implemented security dashboard showing recent auth activity",
            "offset": timedelta(days=7, hours=1),
            "tags": ["authentication", "security", "dashboard", "monitoring"]
        },
        {
            "content": "User completed authentication system with all features working",
            "offset": timedelta(days=7, hours=2),
            "tags": ["authentication", "completion", "success"]
        },
    ]
    
    return [
        {
            "content": m["content"],
            "timestamp": base_time + m["offset"],
            "tags": m["tags"]
        }
        for m in memories
    ]


async def main():
    """Run the memory compaction demonstration."""
    
    console.print(Panel.fit(
        "[bold cyan]Axon Memory Compaction Demo[/bold cyan]\n"
        "Intelligent summarization with semantic search preservation",
        border_style="cyan"
    ))
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY not found in .env file")
        return
    
    # Step 1: Initialize components
    console.print("\n[bold]Step 1:[/bold] Initializing memory system with compaction")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Setting up components...", total=None)
        
        # Initialize embedder
        embedder = OpenAIEmbedder(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="text-embedding-3-small"
        )
        
        # Initialize summarizer
        summarizer = LLMSummarizer(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            max_tokens=200
        )
        
        # Create ChromaDB storage directory
        chroma_path = Path("./demo_chroma_db")
        chroma_path.mkdir(exist_ok=True)
        
        # Configure persistent storage with compaction
        config = PersistentPolicy(
            adapter=AdapterConfig(
                type="chroma",
                connection_string=str(chroma_path),
                collection_name="compaction_demo"
            ),
            compaction_threshold=100,  # Compact when >100 entries
            summarizer=summarizer
        )
        
        # Create memory system
        system = MemorySystem(config=config, embedder=embedder)
        
        progress.update(task, completed=True)
    
    console.print("  ✓ Embedder: OpenAI text-embedding-3-small")
    console.print("  ✓ Summarizer: GPT-3.5-turbo")
    console.print("  ✓ Storage: ChromaDB (persistent)")
    console.print(f"  ✓ Compaction threshold: {config.compaction_threshold} entries")
    
    # Step 2: Load sample memories
    console.print("\n[bold]Step 2:[/bold] Loading sample authentication journey")
    
    memories = create_sample_memories()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Storing {len(memories)} memory entries...", total=None)
        
        for memory_data in memories:
            await system.store(
                content=memory_data["content"],
                metadata={
                    "tags": memory_data["tags"],
                    "timestamp": memory_data["timestamp"].isoformat(),
                    "source": "demo"
                }
            )
        
        progress.update(task, completed=True)
    
    # Get initial storage stats
    adapter = await system.registry.get_adapter("persistent")
    initial_count = adapter.count()
    
    console.print(f"  ✓ Stored {initial_count} entries")
    console.print("  ✓ Each entry has vector embedding for semantic search")
    
    # Step 3: Test search before compaction
    console.print("\n[bold]Step 3:[/bold] Testing semantic search (before compaction)")
    
    search_query = "How did we implement two-factor authentication?"
    results = await system.recall(
        query=search_query,
        tiers=["persistent"],
        top_k=3
    )
    
    console.print(f"\n  Query: [italic]\"{search_query}\"[/italic]")
    console.print(f"  Found {len(results)} relevant entries:\n")
    
    for i, entry in enumerate(results[:3], 1):
        console.print(f"  {i}. {entry.content[:80]}...")
        console.print(f"     [dim]Similarity: {entry.score:.3f}[/dim]")
    
    # Step 4: Dry run compaction
    console.print("\n[bold]Step 4:[/bold] Dry run compaction (preview)")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing what would be compacted...", total=None)
        
        dry_run_stats = await system.compact(dry_run=True)
        
        progress.update(task, completed=True)
    
    console.print("\n  Preview of compaction:")
    console.print(f"  • Would process: {dry_run_stats.get('entries_processed', 0)} entries")
    console.print(f"  • Would create: {dry_run_stats.get('summaries_created', 0)} summaries")
    console.print(f"  • Would remove: {dry_run_stats.get('entries_removed', 0)} entries")
    console.print(f"  • Storage reduction: {dry_run_stats.get('storage_reduction', 0):.1%}")
    console.print("\n  [dim]No actual changes made (dry run)[/dim]")
    
    # Step 5: Perform actual compaction
    console.print("\n[bold]Step 5:[/bold] Performing compaction")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Compacting memories (calling LLM)...", total=None)
        
        compact_stats = await system.compact(dry_run=False)
        
        progress.update(task, completed=True)
    
    # Get final storage stats
    final_count = adapter.count()
    
    # Create results table
    table = Table(title="Compaction Results", border_style="green")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    table.add_row("Entries Before", str(initial_count))
    table.add_row("Entries After", str(final_count))
    table.add_row("Entries Removed", str(compact_stats.get('entries_removed', 0)))
    table.add_row("Summaries Created", str(compact_stats.get('summaries_created', 0)))
    table.add_row("Storage Reduction", f"{compact_stats.get('storage_reduction', 0):.1%}")
    table.add_row("Processing Time", f"{compact_stats.get('duration_seconds', 0):.2f}s")
    
    console.print(table)
    
    # Step 6: Test search after compaction
    console.print("\n[bold]Step 6:[/bold] Testing semantic search (after compaction)")
    
    results_after = await system.recall(
        query=search_query,
        tiers=["persistent"],
        top_k=5
    )
    
    console.print(f"\n  Same query: [italic]\"{search_query}\"[/italic]")
    console.print(f"  Found {len(results_after)} results (mix of originals and summaries):\n")
    
    for i, entry in enumerate(results_after[:5], 1):
        entry_type = "📄 Summary" if entry.type == MemoryEntryType.EMBEDDING_SUMMARY else "💬 Original"
        console.print(f"  {i}. {entry_type}")
        console.print(f"     {entry.content[:100]}...")
        console.print(f"     [dim]Similarity: {entry.score:.3f}[/dim]\n")
    
    # Step 7: Show provenance
    console.print("[bold]Step 7:[/bold] Provenance tracking")
    
    # Find a summary entry
    all_entries = await system.recall(query="", tiers=["persistent"], top_k=100)
    summary_entry = next(
        (e for e in all_entries if e.type == MemoryEntryType.EMBEDDING_SUMMARY),
        None
    )
    
    if summary_entry:
        console.print("\n  Sample summary provenance:")
        console.print(f"  • Summary ID: {summary_entry.id}")
        console.print(f"  • Created: {summary_entry.created_at}")
        
        if summary_entry.metadata and "source_entry_ids" in summary_entry.metadata:
            source_ids = summary_entry.metadata["source_entry_ids"]
            console.print(f"  • Consolidated {len(source_ids)} original entries")
            console.print(f"  • Source IDs: {', '.join(source_ids[:3])}...")
        
        console.print(f"\n  Summary content:")
        console.print(f"  [italic]{summary_entry.content}[/italic]")
    
    # Summary
    console.print(Panel.fit(
        "[bold green]✓ Demo Complete![/bold green]\n\n"
        f"• Reduced storage from {initial_count} → {final_count} entries ({compact_stats.get('storage_reduction', 0):.1%} reduction)\n"
        "• Semantic search still works perfectly\n"
        "• Full provenance trail maintained\n"
        "• Summaries preserve key information",
        border_style="green",
        title="Summary"
    ))
    
    console.print("\n[dim]Tip: Check the ChromaDB storage at ./demo_chroma_db[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
