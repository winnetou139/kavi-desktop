"""Runtime status abstraction.

The UI concept displayed a live Engine Room: VPS online, queue depth, provider
router, uptime, vault sync, cost today. None of that exists in v0.1.

This module reports what is actually true. A future VPS integration replaces the
provider without the interface changing shape — the UI already renders the
``NOT_CONNECTED`` case as a first-class state rather than a missing value.
"""

from __future__ import annotations

import dataclasses
from typing import Any

NOT_CONNECTED = "NOT CONNECTED"
NOT_MEASURED = "NOT MEASURED"


@dataclasses.dataclass
class RuntimeStatus:
    mode: str = "LOCAL_MODE"
    engine_room: str = "ENGINE_ROOM_NOT_CONNECTED"
    label: str = "LOCAL MODE / ENGINE ROOM NOT CONNECTED"
    scheduler: str = NOT_CONNECTED
    queue_depth: str = NOT_MEASURED
    router: str = NOT_CONNECTED
    vault_sync: str = NOT_CONNECTED
    uptime: str = NOT_MEASURED
    cost_today: str = NOT_MEASURED
    providers: list[dict[str, str]] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class RuntimeStatusProvider:
    """Interface. A future VPS/engine-room adapter implements this."""

    def status(self) -> RuntimeStatus:  # pragma: no cover - interface
        raise NotImplementedError


class LocalRuntimeStatusProvider(RuntimeStatusProvider):
    """The only provider shipped in v0.1.

    Reports LOCAL mode honestly. It never fabricates uptime, queue, or cost.
    """

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(
            providers=[
                {"name": "Hermes", "category": "Agent / Orchestration Runtime", "state": NOT_CONNECTED},
                {"name": "OpenAI", "category": "Intelligence / Model Provider", "state": NOT_CONNECTED},
                {"name": "Anthropic", "category": "Intelligence / Model Provider", "state": NOT_CONNECTED},
                {"name": "Kimi", "category": "Intelligence / Model Provider", "state": NOT_CONNECTED},
                {"name": "Local Models", "category": "Intelligence / Model Provider", "state": NOT_CONNECTED},
            ],
            warnings=[
                "No autonomous runtime is running. Nothing executes on your behalf.",
                "Uptime, queue depth, router state and cost are not measured in LOCAL MODE.",
            ],
        )
