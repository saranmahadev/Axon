"""Shared helpers for persisting the parts of a MemoryEntry that backends can't model natively.

``MemoryMetadata`` allows arbitrary extra fields (``extra="allow"``), and Axon relies on
them: ``pii_detection``, ``access_count``, ``last_accessed`` and user-supplied custom
metadata all live there. Vector stores only index a fixed set of flat fields, so adapters
store every other metadata field as one JSON string and restore it on read.
"""

from __future__ import annotations

import json
from typing import Any

from ..models import MemoryMetadata

_CORE_METADATA_FIELDS = frozenset(MemoryMetadata.model_fields)


def extra_metadata_to_json(metadata: MemoryMetadata) -> str:
    """Serialize every non-core metadata field to a JSON string ("" when there are none)."""
    extras = {
        key: value
        for key, value in metadata.model_dump(mode="json").items()
        if key not in _CORE_METADATA_FIELDS
    }
    return json.dumps(extras) if extras else ""


def extra_metadata_from_json(raw: str | None) -> dict[str, Any]:
    """Inverse of :func:`extra_metadata_to_json`.

    Raises:
        ValueError: If the stored value is not a JSON object (corrupt data is never
            silently discarded).
    """
    if not raw:
        return {}
    try:
        extras = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt extra metadata in storage: {e}") from e
    if not isinstance(extras, dict):
        raise ValueError("Corrupt extra metadata in storage: expected a JSON object")
    return extras
