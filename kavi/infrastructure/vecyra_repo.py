"""Reads the VECYRA product roadmap where it actually lives.

The Founder could not tell what phase VECYRA was in, because the answer was
written in a third repository the cockpit never opened:

    Kimi_Agent_Aplikasi VECYRA Terpadu/product-docs/ROADMAP.md
    Kimi_Agent_Aplikasi VECYRA Terpadu/product-docs/SESSION-HANDOFF.md

This reads those files. It does not copy them, mirror them, or write to them.
The product repo stays the single source of truth for product state, exactly
as the vault is for governance (D-005).

If the repo is absent, every field reads UNKNOWN. It never guesses a phase.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import re
from typing import Any

UNKNOWN = "UNKNOWN"

# Phase states that appear in the roadmap table, mapped to a stable vocabulary
# so the cockpit can colour them without string-matching in the view layer.
_STATE_ORDER = ("DONE", "IN PROGRESS", "PARTIAL", "PENDING", "POST-BETA", UNKNOWN)


@dataclasses.dataclass(frozen=True)
class Phase:
    """One row of the roadmap's phase table."""
    id: str
    scope: str
    state: str
    origin: str = "VECYRA"

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _default_root() -> pathlib.Path:
    override = os.environ.get("VECYRA_REPO")
    if override:
        return pathlib.Path(override)
    return (pathlib.Path.home() / "Desktop" / "AI Workspace" / "PCOS"
            / "Kimi_Agent_Aplikasi VECYRA Terpadu")


class VecyraReader:
    """Read-only view of the VECYRA product repository."""

    def __init__(self, root: str | pathlib.Path | None = None) -> None:
        self.root = pathlib.Path(root) if root else _default_root()
        self.docs = self.root / "product-docs"

    # ------------------------------------------------------------- status

    def available(self) -> bool:
        return (self.docs / "ROADMAP.md").is_file()

    def describe(self) -> dict[str, Any]:
        if not self.available():
            return {
                "source": "VECYRA PRODUCT REPO",
                "available": False,
                "access": "NOT FOUND",
                "path": str(self.root),
                "detail": (
                    "The VECYRA product repository was not found, so phase and "
                    "gate state are UNKNOWN. Set VECYRA_REPO to point at it."
                ),
            }
        return {
            "source": "VECYRA PRODUCT REPO",
            "available": True,
            "access": "READ ONLY",
            "path": str(self.root),
            "detail": (
                "Phases are read from product-docs/ROADMAP.md and the gate from "
                "SESSION-HANDOFF.md. The cockpit never writes to this repo."
            ),
        }

    # ------------------------------------------------------------- phases

    def phases(self) -> list[Phase]:
        """Parse the roadmap's phase table. Returns [] when unavailable."""
        path = self.docs / "ROADMAP.md"
        if not path.is_file():
            return []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        block = text.split("## Program phases", 1)
        if len(block) < 2:
            return []
        body = block[1].split("\n## ", 1)[0]

        found: list[Phase] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            identifier, scope, state = cells[0], cells[1], cells[2]
            if identifier.lower() == "phase":       # header row
                continue
            found.append(Phase(
                id=_plain(identifier),
                scope=_plain(scope),
                state=_normalise_state(state),
            ))
        return found

    # -------------------------------------------------------------- gate

    def gate(self) -> dict[str, Any]:
        """The Beta gate, read from the handoff note rather than assumed."""
        path = self.docs / "SESSION-HANDOFF.md"
        result: dict[str, Any] = {
            "name": "BETA GATE",
            "status": UNKNOWN,
            "as_of": UNKNOWN,
            "source": "product-docs/SESSION-HANDOFF.md",
            "origin": "VECYRA",
        }
        if not path.is_file():
            return result
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return result

        heading = re.search(r"#\s*SESSION HANDOFF\s*[—-]\s*([0-9-]+)", text)
        if heading:
            result["as_of"] = heading.group(1)

        # The document states the gate in capitals; trust that, not a guess.
        if re.search(r"BETA GATE\s+BELUM PASS", text, re.I):
            result["status"] = "NOT PASSED"
        elif re.search(r"BETA GATE\s+(PASS|LULUS)", text, re.I):
            result["status"] = "PASSED"

        blockers = re.findall(r"^\s*-\s*(?:BLOCKER|Blocker)[:\s]+(.+)$", text, re.M)
        result["blockers"] = [b.strip() for b in blockers]
        return result

    # ------------------------------------------------------------ rollup

    def summary(self) -> dict[str, Any]:
        """Everything the cockpit needs for a phase panel, in one call."""
        status = self.describe()
        rows = self.phases()
        counts: dict[str, int] = {}
        for phase in rows:
            counts[phase.state] = counts.get(phase.state, 0) + 1

        current = next((p for p in rows if p.state == "IN PROGRESS"), None)
        return {
            **status,
            "phases": [p.as_dict() for p in rows],
            "phase_count": len(rows),
            "counts": {k: counts.get(k, 0) for k in _STATE_ORDER if counts.get(k)},
            "current_phase": current.id if current else UNKNOWN,
            "current_scope": current.scope if current else UNKNOWN,
            "gate": self.gate(),
        }


# --------------------------------------------------------------- helpers

def _plain(cell: str) -> str:
    """Strip markdown emphasis and links, keep the words."""
    cell = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell)
    cell = cell.replace("**", "").replace("*", "").replace("`", "")
    return cell.strip()


def _normalise_state(cell: str) -> str:
    """Map a table cell to one stable state token, or UNKNOWN."""
    plain = _plain(cell).upper()
    if not plain:
        return UNKNOWN
    if plain.startswith("DONE"):
        return "DONE"
    if "IN PROGRESS" in plain:
        return "IN PROGRESS"
    if plain.startswith("PARTIAL"):
        return "PARTIAL"
    if "POST-BETA" in plain:
        return "POST-BETA"
    if plain.startswith("PENDING"):
        return "PENDING"
    return UNKNOWN
