"""Axon exception hierarchy.

Every error Axon raises deliberately derives from :class:`AxonError`, so applications can
catch one base class (``except AxonError``) or a specific failure (``except
TierNotFoundError``).

Backward compatibility: each class also inherits the builtin exception Axon used to raise
for the same situation (``KeyError``, ``ValueError`` or ``RuntimeError``), so existing
``except KeyError:`` / ``pytest.raises(RuntimeError)`` code keeps working unchanged.

Hierarchy::

    AxonError
    ├── ConfigurationError (ValueError)       invalid or incomplete configuration
    ├── TierNotFoundError (KeyError)          tier not configured / registered
    ├── EntryNotFoundError (KeyError)         no entry with that id
    ├── AdapterError (RuntimeError)           a storage backend operation failed
    │   └── ForgetIncompleteError             forget() deleted from some tiers, not all
    ├── EmbeddingError (RuntimeError)         an embedder failed
    ├── SummarizationError (RuntimeError)     LLM summarization failed
    ├── TransactionError (RuntimeError)       a multi-tier transaction failed
    └── AuditError (RuntimeError)             audit logging/export failed or is not configured

Errors that mean "the caller passed a bad argument" (e.g. ``k <= 0``, a missing embedding)
remain plain ``ValueError``, which is the documented contract of the adapter interface.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

__all__ = [
    "AdapterError",
    "AuditError",
    "AxonError",
    "ConfigurationError",
    "EmbeddingError",
    "EntryNotFoundError",
    "ForgetIncompleteError",
    "SummarizationError",
    "TierNotFoundError",
    "TransactionError",
]


class AxonError(Exception):
    """Base class for all errors raised deliberately by Axon."""


class ConfigurationError(AxonError, ValueError):
    """The memory system, a tier or a policy is configured incorrectly."""


class _KeyLookupError(AxonError, KeyError):
    """Base for "not found" errors.

    ``KeyError.__str__`` wraps the message in quotes; show it plainly instead.
    """

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


class TierNotFoundError(_KeyLookupError):
    """A tier name is not configured or has no registered adapter.

    Attributes:
        tier: The tier that was requested
        available: Tiers that do exist, when known
    """

    def __init__(
        self, tier: str, available: Iterable[str] | None = None, message: str | None = None
    ) -> None:
        self.tier = tier
        self.available = list(available) if available is not None else None
        if message is None:
            message = f"Tier '{tier}' not found"
            if self.available is not None:
                message += f". Available tiers: {', '.join(self.available) or '(none)'}"
        super().__init__(message)


class EntryNotFoundError(_KeyLookupError):
    """No entry with the given id exists in the queried store.

    Attributes:
        entry_id: The id that was requested
    """

    def __init__(self, entry_id: str, message: str | None = None) -> None:
        self.entry_id = entry_id
        super().__init__(message or f"Entry '{entry_id}' not found")


class AdapterError(AxonError, RuntimeError):
    """A storage backend operation failed.

    Attributes:
        tier: The tier whose adapter failed, when known
    """

    def __init__(self, message: str, tier: str | None = None) -> None:
        self.tier = tier
        super().__init__(message)


class ForgetIncompleteError(AdapterError):
    """forget() removed data from some tiers but failed on others.

    The entries counted in ``deleted_count`` are gone; the tiers in ``failures`` still hold
    matching data and the call should be retried. Never treat this as success.

    Attributes:
        deleted_count: Entries deleted from the tiers that succeeded
        failures: Mapping of tier name to the exception that tier raised
    """

    def __init__(self, deleted_count: int, failures: Mapping[str, Exception]) -> None:
        self.deleted_count = deleted_count
        self.failures = dict(failures)
        details = "; ".join(f"{tier}: {err}" for tier, err in self.failures.items())
        super().__init__(
            f"Forget incomplete: {deleted_count} entries deleted, but "
            f"{len(self.failures)} tier(s) failed ({details})"
        )


class EmbeddingError(AxonError, RuntimeError):
    """An embedding provider failed to embed text."""


class SummarizationError(AxonError, RuntimeError):
    """LLM-based summarization failed (after retries)."""


class TransactionError(AxonError, RuntimeError):
    """A multi-tier transaction could not be prepared or committed."""


class AuditError(AxonError, RuntimeError):
    """Audit logging or export failed, or audit logging is not configured."""
