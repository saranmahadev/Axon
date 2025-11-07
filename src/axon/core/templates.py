"""
Configuration Templates for Memory System.

This module provides pre-configured templates for common use cases,
making it easy to get started with different deployment scenarios.
"""

from .config import MemoryConfig
from .policies.ephemeral import EphemeralPolicy
from .policies.persistent import PersistentPolicy
from .policies.session import SessionPolicy

# Template 1: Minimal Configuration
# Single persistent tier only (simplest setup)
MINIMAL_CONFIG = MemoryConfig(
    persistent=PersistentPolicy(
        adapter_type="chroma",
        ttl_seconds=None,  # No expiration
        compaction_threshold=10000,
        compaction_strategy="count",
    ),
    default_tier="persistent",
)


# Template 2: Lightweight Configuration
# Redis for both session and persistent (no vector DBs needed)
# Good for development or small-scale deployments
LIGHTWEIGHT_CONFIG = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=300,  # 5 minutes
        max_entries=500,
        overflow_to_persistent=True,
        enable_vector_search=False,
    ),
    persistent=PersistentPolicy(
        adapter_type="memory",  # Using InMemory for lightweight setup
        ttl_seconds=None,
        compaction_threshold=5000,
        compaction_strategy="count",
    ),
    default_tier="session",
)


# Template 3: Standard Configuration
# Redis for cache tiers + Chroma for persistent vector storage
# Balanced setup for most applications
STANDARD_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=60),  # 1 minute
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=600,  # 10 minutes
        max_entries=1000,
        overflow_to_persistent=True,
        enable_vector_search=False,
    ),
    persistent=PersistentPolicy(
        adapter_type="chroma",
        ttl_seconds=None,
        compaction_threshold=10000,
        compaction_strategy="importance",
    ),
    default_tier="session",
    enable_promotion=True,
)


# Template 4: Production Configuration
# Redis for cache + Pinecone for production-scale vector storage
# Optimized for high-scale production deployments
PRODUCTION_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=30),  # 30 seconds
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=1800,  # 30 minutes
        max_entries=2000,
        overflow_to_persistent=True,
        enable_vector_search=False,
    ),
    persistent=PersistentPolicy(
        adapter_type="pinecone",
        ttl_seconds=None,
        compaction_threshold=50000,
        compaction_strategy="semantic",
        archive_adapter="s3",
    ),
    default_tier="session",
    enable_promotion=True,
    enable_demotion=True,
)


# Template 5: Development Configuration
# All in-memory adapters for fast local development/testing
# No external dependencies required
DEVELOPMENT_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="memory", ttl_seconds=60),
    session=SessionPolicy(
        adapter_type="memory", ttl_seconds=600, max_entries=100, enable_vector_search=True
    ),
    persistent=PersistentPolicy(
        adapter_type="memory",
        ttl_seconds=None,
        compaction_threshold=1000,
        compaction_strategy="count",
    ),
    default_tier="session",
)


# Template 6: Qdrant Configuration
# Redis for cache + Qdrant for persistent vector storage
# Alternative to Chroma with better performance characteristics
QDRANT_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(adapter_type="redis", ttl_seconds=60),
    session=SessionPolicy(
        adapter_type="redis",
        ttl_seconds=900,  # 15 minutes
        max_entries=1500,
        overflow_to_persistent=True,
        enable_vector_search=False,
    ),
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        ttl_seconds=None,
        compaction_threshold=20000,
        compaction_strategy="importance",
    ),
    default_tier="session",
    enable_promotion=True,
)


# Export all templates
__all__ = [
    "MINIMAL_CONFIG",
    "LIGHTWEIGHT_CONFIG",
    "STANDARD_CONFIG",
    "PRODUCTION_CONFIG",
    "DEVELOPMENT_CONFIG",
    "QDRANT_CONFIG",
]


# Template metadata for documentation
TEMPLATE_METADATA = {
    "MINIMAL_CONFIG": {
        "name": "Minimal",
        "description": "Single persistent tier only",
        "use_case": "Simplest setup, testing, small projects",
        "dependencies": ["chroma-db"],
        "tiers": 1,
    },
    "LIGHTWEIGHT_CONFIG": {
        "name": "Lightweight",
        "description": "Redis only (no vector DBs)",
        "use_case": "Development, small-scale deployments",
        "dependencies": ["redis"],
        "tiers": 2,
    },
    "STANDARD_CONFIG": {
        "name": "Standard",
        "description": "Redis cache + Chroma vectors",
        "use_case": "Most applications, balanced performance",
        "dependencies": ["redis", "chroma-db"],
        "tiers": 3,
    },
    "PRODUCTION_CONFIG": {
        "name": "Production",
        "description": "Redis cache + Pinecone vectors",
        "use_case": "High-scale production deployments",
        "dependencies": ["redis", "pinecone"],
        "tiers": 3,
    },
    "DEVELOPMENT_CONFIG": {
        "name": "Development",
        "description": "All in-memory adapters",
        "use_case": "Local development, testing, CI/CD",
        "dependencies": [],
        "tiers": 3,
    },
    "QDRANT_CONFIG": {
        "name": "Qdrant",
        "description": "Redis cache + Qdrant vectors",
        "use_case": "Alternative to Chroma, better performance",
        "dependencies": ["redis", "qdrant-client"],
        "tiers": 3,
    },
}
