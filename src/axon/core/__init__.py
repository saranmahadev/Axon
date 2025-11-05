"""Core functionality including MemorySystem, Router, and Policy Engine.

This module will contain:
- MemorySystem (Sprint 3.1-3.2)
- Router and Policy Engine (Sprint 2.4)
- Summarizer and Compactor (Sprint 3.3)
- Policy configuration (Sprint 2.3) ✅
"""

from .policy import Policy
from .config import MemoryConfig
from .policies import EphemeralPolicy, SessionPolicy, PersistentPolicy
from .adapter_registry import AdapterRegistry
from .router import Router
from .scoring import ScoringEngine, ScoringConfig
from .policy_engine import PolicyEngine
from . import templates

__all__ = [
    "Policy",
    "MemoryConfig",
    "EphemeralPolicy",
    "SessionPolicy",
    "PersistentPolicy",
    "AdapterRegistry",
    "Router",
    "ScoringEngine",
    "ScoringConfig",
    "PolicyEngine",
    "templates",
]

