"""Composition root. Wires infrastructure into the application layer."""

from __future__ import annotations

import pathlib

from kavi.application.services import CockpitService
from kavi.infrastructure.execution import get_adapter
from kavi.infrastructure.repository import Repository
from kavi.infrastructure.runtime_status import LocalRuntimeStatusProvider
from kavi.infrastructure.store import JsonStore
from kavi.infrastructure.vault import VaultReader
from kavi.infrastructure.vecyra_repo import VecyraReader


def build_service(
    *,
    data_path: pathlib.Path | str | None = None,
    vault_path: str | None = None,
    include_fixtures: bool = True,
    execution_adapter: str = "null",
) -> CockpitService:
    store = JsonStore(data_path)
    repository = Repository(store, include_fixtures=include_fixtures)
    return CockpitService(
        repository=repository,
        runtime=LocalRuntimeStatusProvider(),
        vault=VaultReader(vault_path),
        vecyra=VecyraReader(),
        execution=get_adapter(execution_adapter),
    )
