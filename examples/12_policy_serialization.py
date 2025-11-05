"""
Example: Policy Serialization

Demonstrates saving and loading memory configurations
to/from JSON files for deployment and version control.
"""

import json
from pathlib import Path
from axon.core.config import MemoryConfig
from axon.core.policies import EphemeralPolicy, SessionPolicy, PersistentPolicy
from axon.core import templates


def example_1_save_config_to_json():
    """Create a config and save it to JSON."""
    print("\n" + "="*60)
    print("Example 1: Save Configuration to JSON")
    print("="*60)
    
    # Create a production configuration
    config = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",
            ttl_seconds=30,
            max_entries=500
        ),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=1800,
            max_entries=10000,
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="pinecone",
            compaction_threshold=100000,
            compaction_strategy="importance",
            archive_adapter="s3"
        ),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True
    )
    
    # Save to JSON file
    output_file = Path("config_production.json")
    json_str = config.to_json(indent=2)
    output_file.write_text(json_str)
    
    print(f"✅ Configuration saved to: {output_file}")
    print(f"\nJSON Preview:")
    print(json_str[:500] + "...")
    
    return output_file


def example_2_load_config_from_json():
    """Load a configuration from JSON file."""
    print("\n" + "="*60)
    print("Example 2: Load Configuration from JSON")
    print("="*60)
    
    input_file = Path("config_production.json")
    
    if not input_file.exists():
        print(f"⚠️  File not found, creating sample first...")
        example_1_save_config_to_json()
    
    # Load from file
    json_str = input_file.read_text()
    config = MemoryConfig.from_json(json_str)
    
    print(f"✅ Configuration loaded from: {input_file}")
    print(f"\nLoaded configuration:")
    print(f"  Tiers: {config.get_tier_names()}")
    print(f"  Default: {config.default_tier}")
    print(f"  Promotion: {config.enable_promotion}")
    print(f"  Demotion: {config.enable_demotion}")
    
    print(f"\nEphemeral: {config.ephemeral}")
    print(f"Session: {config.session}")
    print(f"Persistent: {config.persistent}")
    
    return config


def example_3_save_all_templates():
    """Save all pre-configured templates to JSON files."""
    print("\n" + "="*60)
    print("Example 3: Export All Templates to JSON")
    print("="*60)
    
    template_configs = {
        "minimal": templates.MINIMAL_CONFIG,
        "lightweight": templates.LIGHTWEIGHT_CONFIG,
        "standard": templates.STANDARD_CONFIG,
        "production": templates.PRODUCTION_CONFIG,
        "development": templates.DEVELOPMENT_CONFIG,
        "qdrant": templates.QDRANT_CONFIG
    }
    
    output_dir = Path("configs")
    output_dir.mkdir(exist_ok=True)
    
    for name, config in template_configs.items():
        output_file = output_dir / f"config_{name}.json"
        json_str = config.to_json(indent=2)
        output_file.write_text(json_str)
        print(f"✅ Saved: {output_file}")
    
    print(f"\n✅ All {len(template_configs)} templates saved to {output_dir}/")
    return output_dir


def example_4_config_versioning():
    """Demonstrate configuration versioning for deployments."""
    print("\n" + "="*60)
    print("Example 4: Configuration Versioning")
    print("="*60)
    
    # Create v1 config
    config_v1 = MemoryConfig(
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=600
        ),
        persistent=PersistentPolicy(
            adapter_type="chroma"
        ),
        default_tier="session"
    )
    
    # Save v1
    v1_file = Path("config_v1.0.json")
    v1_file.write_text(config_v1.to_json(indent=2))
    print(f"✅ Saved v1.0: {v1_file}")
    
    # Create v2 with enhancements
    config_v2 = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",
            ttl_seconds=30
        ),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=1800,  # Increased from 600
            max_entries=10000  # Added capacity limit
        ),
        persistent=PersistentPolicy(
            adapter_type="chroma",
            compaction_threshold=50000  # Added compaction
        ),
        default_tier="ephemeral",
        enable_promotion=True  # Added promotion
    )
    
    # Save v2
    v2_file = Path("config_v2.0.json")
    v2_file.write_text(config_v2.to_json(indent=2))
    print(f"✅ Saved v2.0: {v2_file}")
    
    print(f"\nChanges in v2.0:")
    print(f"  • Added ephemeral tier (30s TTL)")
    print(f"  • Increased session TTL: 600s → 1800s")
    print(f"  • Added session capacity limit: 10,000 entries")
    print(f"  • Added persistent compaction: 50,000 threshold")
    print(f"  • Enabled tier promotion")
    
    return v1_file, v2_file


def example_5_environment_configs():
    """Create environment-specific configurations."""
    print("\n" + "="*60)
    print("Example 5: Environment-Specific Configurations")
    print("="*60)
    
    # Development environment - all in-memory
    dev_config = MemoryConfig(
        ephemeral=EphemeralPolicy(adapter_type="memory", ttl_seconds=30),
        session=SessionPolicy(adapter_type="memory", ttl_seconds=300),
        persistent=PersistentPolicy(adapter_type="memory"),
        default_tier="session"
    )
    
    # Staging environment - lightweight production-like
    staging_config = MemoryConfig(
        ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=30),
        session=SessionPolicy(adapter_type="redis", ttl_seconds=1800),
        persistent=PersistentPolicy(adapter_type="chroma"),
        default_tier="session",
        enable_promotion=True
    )
    
    # Production environment - full scale
    prod_config = MemoryConfig(
        ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=30),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=1800,
            max_entries=50000,
            overflow_to_persistent=True
        ),
        persistent=PersistentPolicy(
            adapter_type="pinecone",
            compaction_threshold=500000,
            compaction_strategy="importance",
            archive_adapter="s3"
        ),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True
    )
    
    # Save all environments
    env_dir = Path("configs/environments")
    env_dir.mkdir(parents=True, exist_ok=True)
    
    configs = {
        "development": dev_config,
        "staging": staging_config,
        "production": prod_config
    }
    
    for env_name, config in configs.items():
        env_file = env_dir / f"config_{env_name}.json"
        env_file.write_text(config.to_json(indent=2))
        print(f"✅ {env_name.upper():12} → {env_file}")
        print(f"   Tiers: {', '.join(config.get_tier_names())}")
    
    print(f"\n✅ All environment configs saved to {env_dir}/")
    
    return env_dir


def example_6_roundtrip_validation():
    """Validate that serialization preserves all data."""
    print("\n" + "="*60)
    print("Example 6: Roundtrip Serialization Validation")
    print("="*60)
    
    # Create a complex config
    original = MemoryConfig(
        ephemeral=EphemeralPolicy(
            adapter_type="redis",
            ttl_seconds=60,
            max_entries=1000,
            eviction_strategy="ttl"
        ),
        session=SessionPolicy(
            adapter_type="redis",
            ttl_seconds=3600,
            max_entries=20000,
            eviction_strategy="lru",
            overflow_to_persistent=True,
            enable_vector_search=True
        ),
        persistent=PersistentPolicy(
            adapter_type="pinecone",
            ttl_seconds=None,
            max_entries=None,
            compaction_threshold=100000,
            compaction_strategy="semantic",
            archive_adapter="s3",
            enable_vector_search=True
        ),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True
    )
    
    # Serialize and deserialize
    json_str = original.to_json(indent=2)
    restored = MemoryConfig.from_json(json_str)
    
    # Validate equality
    checks = [
        ("Default tier", original.default_tier == restored.default_tier),
        ("Promotion", original.enable_promotion == restored.enable_promotion),
        ("Demotion", original.enable_demotion == restored.enable_demotion),
        ("Ephemeral TTL", original.ephemeral.ttl_seconds == restored.ephemeral.ttl_seconds),
        ("Session capacity", original.session.max_entries == restored.session.max_entries),
        ("Session overflow", original.session.overflow_to_persistent == restored.session.overflow_to_persistent),
        ("Persistent strategy", original.persistent.compaction_strategy == restored.persistent.compaction_strategy),
        ("Persistent archive", original.persistent.archive_adapter == restored.persistent.archive_adapter)
    ]
    
    print("Roundtrip validation:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    all_passed = all(result for _, result in checks)
    if all_passed:
        print("\n✅ Perfect roundtrip - all data preserved!")
    else:
        print("\n❌ Roundtrip validation failed!")
    
    return all_passed


def main():
    """Run all serialization examples."""
    print("\n" + "="*60)
    print("POLICY SERIALIZATION EXAMPLES")
    print("="*60)
    
    example_1_save_config_to_json()
    example_2_load_config_from_json()
    example_3_save_all_templates()
    example_4_config_versioning()
    example_5_environment_configs()
    example_6_roundtrip_validation()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
Key Capabilities Demonstrated:
1. ✅ Save configurations to JSON files
2. ✅ Load configurations from JSON files
3. ✅ Export all templates for comparison
4. ✅ Version configurations for deployment tracking
5. ✅ Create environment-specific configs (dev/staging/prod)
6. ✅ Validate perfect roundtrip serialization

Use Cases:
• Store configs in version control (git)
• Deploy different configs per environment
• Share configurations between team members
• Backup and restore memory system settings
• A/B test different memory configurations

File Structure Created:
  config_production.json          - Production config
  config_v1.0.json                - Version 1
  config_v2.0.json                - Version 2
  configs/
    config_minimal.json           - Template: Minimal
    config_lightweight.json       - Template: Lightweight
    config_standard.json          - Template: Standard
    config_production.json        - Template: Production
    config_development.json       - Template: Development
    config_qdrant.json            - Template: Qdrant
    environments/
      config_development.json     - Dev environment
      config_staging.json         - Staging environment
      config_production.json      - Prod environment
""")
    
    print("\n✅ All serialization examples completed!\n")


if __name__ == "__main__":
    main()
