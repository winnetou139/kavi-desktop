"""Execution capability interface and adapters.

KAVI Desktop must not depend on Hermes implementation details. It depends on
``ExecutionCapability``. Hermes — or any other runtime — is one adapter behind
that interface.

    KAVI Desktop
         |
    ExecutionCapability      <- this module
         |
    HermesAdapter / future adapters

v0.1 ships only ``NullExecutionAdapter``: it declines every request and says so.
It never simulates execution.
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class ExecutionRequest:
    task_id: str
    instruction: str
    capability: str = "REASONING"
    budget: str = ""
    permission_grant_id: str = ""
    idempotency_key: str = ""


@dataclasses.dataclass
class ExecutionResult:
    accepted: bool
    state: str  # DECLINED | ACCEPTED | FAILED
    detail: str
    adapter: str
    run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class ExecutionCapability:
    """The seam. Presentation and application never import an adapter directly."""

    name = "abstract"

    def describe(self) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def submit(self, request: ExecutionRequest) -> ExecutionResult:  # pragma: no cover
        raise NotImplementedError


class NullExecutionAdapter(ExecutionCapability):
    """LOCAL MODE. Declines everything, honestly."""

    name = "null"

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "connected": False,
            "state": "NOT CONNECTED",
            "capabilities": [],
            "detail": (
                "No execution runtime is connected. KAVI Desktop v0.1 records "
                "structured work; it does not execute it."
            ),
        }

    def submit(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            state="DECLINED",
            detail=(
                "No execution capability is connected in LOCAL MODE. "
                "Connect an execution adapter before dispatching work."
            ),
            adapter=self.name,
        )


class HermesExecutionAdapter(ExecutionCapability):
    """Placeholder for the future Hermes adapter.

    Deliberately unimplemented. It exists to prove the seam is real and to fix
    the shape a future adapter must satisfy. It declines rather than pretending.
    """

    name = "hermes"

    def __init__(self, endpoint: str = "") -> None:
        self.endpoint = endpoint

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "connected": False,
            "state": "NOT IMPLEMENTED",
            "capabilities": ["ORCHESTRATION", "TOOL_EXECUTION", "DELEGATION"],
            "detail": (
                "Hermes is one execution capability among several (D-002). "
                "The adapter is declared, not implemented, in v0.1."
            ),
        }

    def submit(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            state="DECLINED",
            detail="Hermes adapter is not implemented in v0.1.",
            adapter=self.name,
        )


_REGISTRY: dict[str, type[ExecutionCapability]] = {
    NullExecutionAdapter.name: NullExecutionAdapter,
    HermesExecutionAdapter.name: HermesExecutionAdapter,
}


def available_adapters() -> list[dict[str, Any]]:
    return [cls().describe() for cls in _REGISTRY.values()]


def get_adapter(name: str = "null") -> ExecutionCapability:
    if name not in _REGISTRY:
        raise ValueError(f"unknown execution adapter: {name}")
    return _REGISTRY[name]()
