"""Runtime status abstraction.

The UI concept displayed a live Engine Room: VPS online, queue depth, provider
router, uptime, vault sync, cost today. None of that exists in v0.1.

This module reports what is actually true. A future VPS integration replaces the
provider without the interface changing shape — the UI already renders the
``NOT CONNECTED`` case as a first-class state rather than a missing value.
"""

from __future__ import annotations

import dataclasses
from typing import Any

NOT_CONNECTED = "NOT CONNECTED"
NOT_MEASURED = "NOT MEASURED"
LOCAL = "LOCAL"
UNAVAILABLE = "UNAVAILABLE"


@dataclasses.dataclass
class RuntimeStatus:
    mode: str = "LOCAL"
    engine_room: str = "ENGINE_ROOM_NOT_CONNECTED"
    label: str = "LOCAL MODE / ENGINE ROOM NOT CONNECTED"
    vps: str = NOT_CONNECTED
    runtime: str = "LOCAL DEVELOPMENT"
    scheduler: str = "NOT CONNECTED / LOCAL"
    queue: str = "LOCAL / NOT ACTIVE"
    provider_router: str = NOT_CONNECTED
    vault: str = LOCAL
    cost: str = "LOCAL / FIXTURE / UNAVAILABLE"
    uptime: str = NOT_MEASURED
    # Legacy field names kept so existing views keep working.
    queue_depth: str = "LOCAL / NOT ACTIVE"
    router: str = NOT_CONNECTED
    vault_sync: str = NOT_CONNECTED
    cost_today: str = "LOCAL / UNAVAILABLE"
    providers: list[dict[str, str]] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def engine_room_panel(self) -> list[tuple[str, str]]:
        """Exactly the Founder-facing Engine Room readout, in order."""
        return [
            ("MODE", self.mode),
            ("VPS", self.vps),
            ("RUNTIME", self.runtime),
            ("SCHEDULER", self.scheduler),
            ("QUEUE", self.queue),
            ("PROVIDER ROUTER", self.provider_router),
            ("VAULT", self.vault),
            ("COST", self.cost),
        ]


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
                "Provider health is not polled. Every provider reads NOT CONNECTED by definition.",
            ],
        )
