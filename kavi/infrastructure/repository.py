"""Repository: merges fixture data with locally created records.

Fixture rows are read-only and always carry ``origin: FIXTURE``. Locally created
rows live in the JSON store and carry ``origin: LOCAL``. The two never blend
silently — every row that reaches the interface states its origin.
"""

from __future__ import annotations

from typing import Any

from kavi.infrastructure import fixtures
from kavi.infrastructure.store import JsonStore


class Repository:
    def __init__(self, store: JsonStore, *, include_fixtures: bool = True) -> None:
        self.store = store
        self.include_fixtures = include_fixtures
        self._fixtures = fixtures.all_fixtures() if include_fixtures else {}

    # -------------------------------------------------------------- reading

    def fixture_rows(self, collection: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._fixtures.get(collection, [])]

    def local_rows(self, collection: str) -> list[dict[str, Any]]:
        return self.store.all(collection)

    def list(self, collection: str) -> list[dict[str, Any]]:
        """Fixtures first, then locally created rows."""
        return self.fixture_rows(collection) + self.local_rows(collection)

    def get(self, collection: str, identifier: str) -> dict[str, Any] | None:
        for row in self.list(collection):
            if row.get("id") == identifier:
                return row
        return None

    def find(self, collection: str, **criteria: Any) -> list[dict[str, Any]]:
        rows = self.list(collection)
        for key, value in criteria.items():
            rows = [row for row in rows if row.get(key) == value]
        return rows

    # -------------------------------------------------------------- writing

    def add(self, collection: str, row: dict[str, Any]) -> dict[str, Any]:
        if row.get("origin") == "FIXTURE":
            raise ValueError("fixture rows are read-only and may not be persisted")
        return self.store.insert(collection, row)

    def update(self, collection: str, identifier: str, row: dict[str, Any]) -> dict[str, Any]:
        if self.store.get(collection, identifier) is None:
            raise PermissionError(
                f"{identifier} is fixture data and cannot be modified. "
                "Fixture records are development material, not company records."
            )
        return self.store.replace(collection, identifier, row)

    def next_id(self, collection: str, namespace: str, year: int) -> str:
        from kavi.domain import ids

        prefix = ids.prefix_of(namespace)
        seq = self.store.next_sequence(collection, prefix, year)
        # Do not collide with fixture identifiers.
        taken = {row.get("id") for row in self.fixture_rows(collection)}
        candidate = ids.new_id(namespace, year=year, seq=seq)
        while candidate in taken:
            seq += 1
            candidate = ids.new_id(namespace, year=year, seq=seq)
        return candidate

    # ----------------------------------------------------------------- meta

    def counts(self) -> dict[str, dict[str, int]]:
        from kavi.infrastructure.store import COLLECTIONS

        out: dict[str, dict[str, int]] = {}
        for collection in COLLECTIONS:
            fixture_count = len(self.fixture_rows(collection))
            local_count = len(self.local_rows(collection))
            out[collection] = {
                "fixture": fixture_count,
                "local": local_count,
                "total": fixture_count + local_count,
            }
        return out
