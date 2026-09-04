"""Local JSON store for KAVI Desktop.

Deliberately simple: one JSON document under the application data directory,
written atomically. v0.1 is single-user, local, and small. The store is an
infrastructure detail behind ``Repository`` — no domain rule lives here.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import threading
from typing import Any

APP_DIR_NAME = "kavi-desktop"

COLLECTIONS = (
    "actors",
    "permissions",
    "objectives",
    "tasks",
    "evidence",
    "reviews",
    "approvals",
    "decisions",
    "ventures",
    "inbox",
)


def default_data_dir() -> pathlib.Path:
    override = os.environ.get("KAVI_DATA_DIR")
    if override:
        return pathlib.Path(override)
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if base:
        return pathlib.Path(base) / APP_DIR_NAME
    return pathlib.Path.home() / f".{APP_DIR_NAME}"


class JsonStore:
    """Thread-safe atomic JSON document store."""

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        self.path = pathlib.Path(path) if path else default_data_dir() / "kavi.json"
        self._lock = threading.RLock()
        self._data: dict[str, Any] | None = None

    # ------------------------------------------------------------- internals

    def _empty(self) -> dict[str, Any]:
        return {"schema_version": 1, **{name: [] for name in COLLECTIONS}}

    def _load(self) -> dict[str, Any]:
        if self._data is not None:
            return self._data
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                loaded = self._empty()
        else:
            loaded = self._empty()
        for name in COLLECTIONS:
            loaded.setdefault(name, [])
        loaded.setdefault("schema_version", 1)
        self._data = loaded
        return loaded

    def _flush(self) -> None:
        assert self._data is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ------------------------------------------------------------------- API

    def all(self, collection: str) -> list[dict[str, Any]]:
        if collection not in COLLECTIONS:
            raise ValueError(f"unknown collection: {collection}")
        with self._lock:
            return [dict(row) for row in self._load()[collection]]

    def get(self, collection: str, identifier: str) -> dict[str, Any] | None:
        for row in self.all(collection):
            if row.get("id") == identifier:
                return row
        return None

    def insert(self, collection: str, row: dict[str, Any]) -> dict[str, Any]:
        if collection not in COLLECTIONS:
            raise ValueError(f"unknown collection: {collection}")
        with self._lock:
            data = self._load()
            data[collection].append(dict(row))
            self._flush()
            return dict(row)

    def replace(self, collection: str, identifier: str, row: dict[str, Any]) -> dict[str, Any]:
        if collection not in COLLECTIONS:
            raise ValueError(f"unknown collection: {collection}")
        with self._lock:
            data = self._load()
            for index, existing in enumerate(data[collection]):
                if existing.get("id") == identifier:
                    data[collection][index] = dict(row)
                    self._flush()
                    return dict(row)
        raise KeyError(f"{collection}/{identifier} not found")

    def next_sequence(self, collection: str, prefix: str, year: int) -> int:
        """Highest existing sequence for ``PREFIX-YEAR-NNN`` in a collection, plus one."""
        head = f"{prefix}-{year}-"
        highest = 0
        for row in self.all(collection):
            identifier = str(row.get("id", ""))
            if identifier.startswith(head):
                tail = identifier[len(head):]
                if tail.isdigit():
                    highest = max(highest, int(tail))
        return highest + 1

    def reset(self) -> None:
        """Test hook. Drops all rows in memory and on disk."""
        with self._lock:
            self._data = self._empty()
            self._flush()
