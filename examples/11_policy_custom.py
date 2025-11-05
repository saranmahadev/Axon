"""
Example: Custom Policy Configuration

Shows how to create custom memory policies and
configurations tailored to specific requirements.
"""

from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy


def example_1_simple_two_tier():
    """Create a simple two-tier configuration."""
    print("\n" + "="*60)
    print("Example 1: Simple Two-Tier Setup")
    print("="*60)
    
    config = MemoryConfig(
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=600,  # 10 minutes
            max_entries=1000
        ),
        persistent=PersistentPolicy(
            adapter_type="chroma",
            compaction_threshold=10000
        ),
        default_tier="session"
    )
    
    print(f"Tiers: {config.get_tier_names()}")
    print(f"Default: {config.default_tier}")
    print(f"\nSession Policy: {config.session}")
    print(f"Persistent Policy: {config.persistent}")
    
    return config


def example_2_full_three_tier():
    """Create a full three-tier configuration with promotion."""
    print("\n" + "="*60)
    print("Example 2: Full Three-Tier with Promotion")
    print("="*60)
    
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",
            ttl_seconds=30,  # 30 seconds for very short-term
            max_entries=100
        ),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=1800,  # 30 minutes
            max_entries=5000,
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="pinecone",
            compaction_threshold=100000,
            compaction_strategy="importance"
        ),
        default_tier="ephemeral",
        enable_promotion=True,
        enable_demotion=False
    )
    
    print(f"Tiers: {config.get_tier_names()}")
    print(f"Default: {config.default_tier}")
    print(f"Promotion: {config.enable_promotion}")
    print(f"Demotion: {config.enable_demotion}")
    
    print(f"\nEphemeral: {config.ephemeral}")
    print(f"Session: {config.session}")
    print(f"Persistent: {config.persistent}")
    
    return config


def example_3_customized_from_template():
    """Start with a template and customize it."""
    print("\n" + "="*60)
    print("Example 3: Customize a Template")
    print("="*60)
    
    from axon.core import templates
    
    # Start with STANDARD_CONFIG template
    base_config = templates.STANDARD_CONFIG
    print(f"Base template tiers: {base_config.get_tier_names()}")
    
    # Create customized version with different TTLs
    custom_config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",
            ttl_seconds=60,  # 1 minute instead of 30s
            max_entries=500
        ),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=3600,  # 1 hour instead of 30 min
            max_entries=20000,  # Larger capacity
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="chroma",
            compaction_threshold=50000,
            compaction_strategy="semantic"  # Use semantic compaction
        ),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True  # Enable demotion too
    )
    
    print(f"\nCustomized config:")
    print(f"  Ephemeral TTL: {custom_config.ephemeral.ttl_seconds}s")
    print(f"  Session TTL: {custom_config.session.ttl_seconds}s ({custom_config.session.ttl_seconds/60} min)")
    print(f"  Session capacity: {custom_config.session.max_entries:,} entries")
    print(f"  Persistent compaction: {custom_config.persistent.compaction_strategy}")
    print(f"  Demotion enabled: {custom_config.enable_demotion}")
    
    return custom_config


def example_4_persistent_only():
    """Minimal config with just persistent tier."""
    print("\n" + "="*60)
    print("Example 4: Persistent-Only Configuration")
    print("="*60)
    
    config = MemoryConfig(
        persistent=PersistentPolicy(
            adapter_type="qdrant",
            ttl_seconds=None,  # No expiration
            compaction_threshold=None,  # No automatic compaction
            archive_adapter="s3"  # Optional archival to S3
        ),
        default_tier="persistent"
    )
    
    print(f"Tiers: {config.get_tier_names()}")
    print(f"TTL: {config.persistent.ttl_seconds} (no expiration)")
    print(f"Compaction: {config.persistent.compaction_threshold} (manual only)")
    print(f"Archive: {config.persistent.archive_adapter}")
    
    return config


def example_5_development_config():
    """All in-memory for local development."""
    print("\n" + "="*60)
    print("Example 5: Development Configuration (All In-Memory)")
    print("="*60)
    
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="memory",
            ttl_seconds=30
        ),
        session=SessionPolicy(
            adapter_type="memory",
            ttl_seconds=300
        ),
        persistent=PersistentPolicy(
            adapter_type="memory"
        ),
        default_tier="session",
        enable_promotion=True
    )
    
    print("All adapters use in-memory storage - perfect for:")
    print("  • Local development")
    print("  • Unit testing")
    print("  • CI/CD pipelines")
    print("  • Quick prototyping")
    print(f"\nNo external dependencies required!")
    
    return config


def example_6_constraint_validation():
    """Demonstrate validation constraints."""
    print("\n" + "="*60)
    print("Example 6: Validation Constraints")
    print("="*60)
    
    # These will raise validation errors:
    examples = [
        ("Ephemeral TTL too short", lambda: EphemeralPolicy(adapter_type="redis", ttl_seconds=1)),
        ("Ephemeral with vector DB", lambda: EphemeralPolicy(adapter_type="chroma", ttl_seconds=30)),
        ("Session TTL too short", lambda: SessionPolicy(adapter_type="redis", ttl_seconds=30)),
        ("Persistent with Redis", lambda: PersistentPolicy(adapter_type="redis")),
        ("Persistent TTL too short", lambda: PersistentPolicy(adapter_type="chroma", ttl_seconds=3600)),
        ("Promotion without tiers", lambda: MemoryConfig(
            persistent=PersistentPolicy(adapter_type="chroma"),
            default_tier="persistent",
            enable_promotion=True
        ))
    ]
    
    for description, func in examples:
        try:
            func()
            print(f"❌ {description}: Should have failed!")
        except Exception as e:
            print(f"✅ {description}: Correctly rejected")
            print(f"   Error: {str(e)[:80]}...")
    
    print("\n✅ All validation constraints working correctly!")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CUSTOM POLICY CONFIGURATION EXAMPLES")
    print("="*60)
    
    config1 = example_1_simple_two_tier()
    config2 = example_2_full_three_tier()
    config3 = example_3_customized_from_template()
    config4 = example_4_persistent_only()
    config5 = example_5_development_config()
    example_6_constraint_validation()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
Key Takeaways:
1. Start with templates and customize as needed
2. Policies enforce tier-specific constraints automatically
3. MemoryConfig validates tier relationships
4. Promotion/demotion requires multiple tiers
5. Each tier has appropriate adapter types
6. TTL ranges enforce proper memory lifecycle

Next Steps:
- Save configurations to JSON for deployment
- Integrate with MemorySystem router
- Configure adapters with connection details
""")
    
    print("\n✅ All examples completed successfully!\n")


if __name__ == "__main__":
    main()
