"""Core functionality including MemorySystem, Router, and Policy Engine.

This module will contain:
- MemorySystem (Sprint 3.1-3.2) ✅
- Router and Policy Engine (Sprint 2.4) ✅
- Summarizer and Compactor (Sprint 3.3)
- Policy configuration (Sprint 2.3) ✅
"""

from . import templates
from .adapter_registry import AdapterRegistry
from .audit import AuditLogger
from .config import MemoryConfig
from .memory_system import MemorySystem, TraceEvent
from .policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from .policy import Policy
from .policy_engine import PolicyEngine
from .privacy import PIIDetector, PIIDetectionResult
from .router import Router
from .scoring import ScoringConfig, ScoringEngine
from .summarizer import LLMSummarizer, Summarizer

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
    "MemorySystem",
    "TraceEvent",
    "Summarizer",
    "LLMSummarizer",
    "AuditLogger",
    "PIIDetector",
    "PIIDetectionResult",
    "templates",
]
