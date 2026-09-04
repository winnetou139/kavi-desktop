"""Stable ID namespaces for KAVI domain objects.

Mirrors the namespaces declared in the canonical vault contract
`03_KAVI_OS/Canonical State and Synchronization.md`.
"""

from __future__ import annotations

import datetime as _dt
import itertools
import threading

# namespace -> prefix
NAMESPACES = {
    "objective": "OBJ",
    "task": "TASK",
    "run": "RUN",
    "event": "EVT",
    "approval": "APR",
    "review": "REV",
    "grant": "GNT",
    "claim": "CLM",
    "decision": "D",
    "experiment": "EXP",
    "spec": "SPEC",
    "actor": "ACT",
    "venture": "VEN",
    "memory": "MEM",
    "inbox": "INB",
}

_lock = threading.Lock()
_counters: dict[str, itertools.count] = {}


def reset_counters() -> None:
    """Test hook. Clears in-process sequence state."""
    with _lock:
        _counters.clear()


def _next(prefix: str, year: int) -> int:
    key = f"{prefix}-{year}"
    with _lock:
        if key not in _counters:
            _counters[key] = itertools.count(1)
        return next(_counters[key])


def new_id(namespace: str, *, year: int | None = None, seq: int | None = None) -> str:
    """Return a stable ID such as ``OBJ-2026-001``.

    ``seq`` may be supplied by a store that knows the highest existing sequence,
    so IDs survive process restarts.
    """
    if namespace not in NAMESPACES:
        raise ValueError(f"unknown ID namespace: {namespace}")
    prefix = NAMESPACES[namespace]
    year = year if year is not None else _dt.date.today().year
    n = seq if seq is not None else _next(prefix, year)
    return f"{prefix}-{year}-{n:03d}"


def prefix_of(namespace: str) -> str:
    if namespace not in NAMESPACES:
        raise ValueError(f"unknown ID namespace: {namespace}")
    return NAMESPACES[namespace]


def namespace_of(identifier: str) -> str | None:
    """Reverse lookup: ``OBJ-2026-001`` -> ``objective``."""
    head = identifier.split("-", 1)[0]
    for ns, prefix in NAMESPACES.items():
        if prefix == head:
            return ns
    return None
