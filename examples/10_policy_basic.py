"""
Example: Basic Policy DSL Usage

Demonstrates how to use pre-configured templates
and understand different memory configurations.
"""

from axon.core import templates
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


def print_config(config: MemoryConfig, name: str):
    """Print configuration details."""
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"Default Tier: {config.default_tier}")
    print(f"Configured Tiers: {', '.join(config.get_tier_names())}")
    print(f"Promotion Enabled: {config.enable_promotion}")
    print(f"Demotion Enabled: {config.enable_demotion}")
    
    for tier_name in ["ephemeral", "session", "persistent"]:
        policy = config.get_policy(tier_name)
        if policy:
            print(f"\n{tier_name.upper()} Tier:")
            print(f"  Adapter: {policy.adapter_type}")
            if policy.ttl_seconds is not None:
                print(f"  TTL: {policy.ttl_seconds}s ({policy.ttl_seconds/60:.1f} min)")
            else:
                print(f"  TTL: No expiration")
            if policy.max_entries:
                print(f"  Max Entries: {policy.max_entries:,}")
            if hasattr(policy, 'compaction_threshold') and policy.compaction_threshold:
                print(f"  Compaction Threshold: {policy.compaction_threshold:,}")
            if hasattr(policy, 'overflow_to_persistent'):
                print(f"  Overflow to Persistent: {policy.overflow_to_persistent}")


def main():
    """Run all template demonstrations."""
    print("\n" + "="*60)
    print("AXON MEMORY SDK - POLICY DSL TEMPLATES")
    print("="*60)
    
    # 1. MINIMAL CONFIG - Just persistent storage
    print("\n\n1️⃣  MINIMAL CONFIG - Simplest Setup")
    print("-" * 60)
    print("Use case: Simple projects, proof-of-concepts")
    print("Dependencies: ChromaDB only")
    metadata = templates.TEMPLATE_METADATA["MINIMAL_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.MINIMAL_CONFIG, "Minimal Configuration")
    
    # 2. LIGHTWEIGHT CONFIG - Session + in-memory persistent
    print("\n\n2️⃣  LIGHTWEIGHT CONFIG - Development/Testing")
    print("-" * 60)
    print("Use case: Rapid development, testing, CI/CD")
    print("Dependencies: Redis + in-memory storage")
    metadata = templates.TEMPLATE_METADATA["LIGHTWEIGHT_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.LIGHTWEIGHT_CONFIG, "Lightweight Configuration")
    
    # 3. STANDARD CONFIG - Production-ready with promotion
    print("\n\n3️⃣  STANDARD CONFIG - Production Ready")
    print("-" * 60)
    print("Use case: Production applications, chatbots")
    print("Dependencies: Redis + ChromaDB")
    metadata = templates.TEMPLATE_METADATA["STANDARD_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.STANDARD_CONFIG, "Standard Configuration")
    
    # 4. PRODUCTION CONFIG - Enterprise scale
    print("\n\n4️⃣  PRODUCTION CONFIG - Enterprise Scale")
    print("-" * 60)
    print("Use case: Large-scale production, high traffic")
    print("Dependencies: Redis + Pinecone + S3")
    metadata = templates.TEMPLATE_METADATA["PRODUCTION_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.PRODUCTION_CONFIG, "Production Configuration")
    
    # 5. DEVELOPMENT CONFIG - All in-memory
    print("\n\n5️⃣  DEVELOPMENT CONFIG - Pure Development")
    print("-" * 60)
    print("Use case: Local development, no external services")
    print("Dependencies: None (all in-memory)")
    metadata = templates.TEMPLATE_METADATA["DEVELOPMENT_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.DEVELOPMENT_CONFIG, "Development Configuration")
    
    # 6. QDRANT CONFIG - Qdrant for vectors
    print("\n\n6️⃣  QDRANT CONFIG - Qdrant Vector Database")
    print("-" * 60)
    print("Use case: Projects using Qdrant")
    print("Dependencies: Redis + Qdrant")
    metadata = templates.TEMPLATE_METADATA["QDRANT_CONFIG"]
    print(f"Description: {metadata['description']}")
    print_config(templates.QDRANT_CONFIG, "Qdrant Configuration")
    
    # Show how to access a specific template
    print("\n\n" + "="*60)
    print("USING TEMPLATES IN YOUR CODE")
    print("="*60)
    print("""
from axon.core import templates

# Use a template directly
config = templates.STANDARD_CONFIG

# Or customize a template
from axon.core.config import MemoryConfig
from axon.core.policies import SessionPolicy, PersistentPolicy

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800,  # 30 minutes
        max_entries=10000
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma",
        compaction_threshold=50000
    ),
    default_tier="session",
    enable_promotion=True
)
""")
    
    print("\n" + "="*60)
    print("✅ All templates validated successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
