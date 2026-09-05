"""Answers 'what is the state of things?' for the Founder, from anywhere.

The Founder's complaint was concrete: he could not tell what phase VECYRA was
in, or whether progress was measurable. The facts existed, but were spread
across three repositories that never spoke to each other.

This composes one short readout from the real sources:

    VECYRA product repo -> build phase and Beta gate
    KAVI vault          -> approved decisions, venture gate
    Operational store   -> objectives and tasks the Founder created

It reads. It never writes, never scores, never estimates a percentage that
nobody measured. Where a source is missing, it says so rather than guessing.

Run:
    python3 status.py            plain text, for a terminal
    python3 status.py --telegram markdown, for the phone
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

COCKPIT = os.environ.get("KAVI_URL", "http://127.0.0.1:8760")
UNKNOWN = "UNKNOWN"


def _get(path: str, timeout: int = 10) -> dict | None:
    """Fetch one cockpit endpoint. Returns None instead of raising."""
    try:
        with urllib.request.urlopen(f"{COCKPIT}{path}", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def _read_vault_directly() -> dict | None:
    """Read the programme roadmap when the cockpit is not running."""
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from kavi.infrastructure.vault import VaultReader
        result = VaultReader().programme()
        return result if result.get("available") else None
    except Exception:
        return None


def _read_repo_directly() -> dict | None:
    """Fall back to reading the product repo when the cockpit is not running.

    The Founder should be able to ask for status from his phone whether or not
    a desktop app happens to be open on a laptop somewhere.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from kavi.infrastructure.vecyra_repo import VecyraReader
    except Exception:
        return None
    try:
        reader = VecyraReader()
        return reader.summary() if reader.available() else None
    except Exception:
        return None


def build() -> dict:
    """Collect everything, tolerating any source being unavailable."""
    program = _get("/api/vecyra") or _read_repo_directly()
    programme = _get("/api/programme") or _read_vault_directly()
    decisions = _get("/api/decisions")
    objectives = _get("/api/objectives")
    execution = _get("/api/execution")
    ledger = _get("/api/ledger")
    return {
        "program": program,
        "programme": programme,
        "decisions": decisions,
        "objectives": objectives,
        "execution": execution,
        "ledger": ledger,
        "cockpit_up": _get("/api/runtime") is not None,
        "at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def render(data: dict, telegram: bool = False) -> str:
    b = "*" if telegram else ""
    lines: list[str] = [f"{b}KAVI — STATUS{b}   {data['at']}", ""]

    # ---- the Founder's own programme, first ----------------------------
    prog = data.get("programme")
    if prog and prog.get("available"):
        lines += [
            f"{b}RENCANA KAVI{b}",
            f"  Fase kini : {prog.get('current_phase', UNKNOWN)}",
            f"  Isi       : {str(prog.get('current_scope', UNKNOWN)).split(':')[0][:52]}",
        ]
        blocked = prog.get("blocked") or []
        if blocked:
            lines.append(f"  Tertahan  : {', '.join(blocked)}")
        lines.append("")
        for phase in prog.get("phases", []):
            mark = {"DONE": "[x]", "IN PROGRESS": "[>]",
                    "BLOCKED": "[!]"}.get(phase["state"], "[ ]")
            lines.append(f"  {mark} {phase['id']:4} {phase['state']}")
        lines.append("")
    else:
        lines += ["RENCANA KAVI", "  vault tidak terbaca — fase UNKNOWN", ""]

    # ---- VECYRA build programme ----------------------------------------
    program = data["program"]
    if not program or not program.get("available"):
        lines += ["VECYRA BUILD", "  product repo not reachable — phase UNKNOWN", ""]
    else:
        gate = program.get("gate", {})
        scope = str(program.get("current_scope", UNKNOWN))
        # Keep the first clause only: the full roadmap sentence is long and
        # slicing it mid-word looks like a defect on a phone.
        short = scope.split(",")[0].strip()
        lines += [
            f"{b}VECYRA BUILD{b}",
            f"  Phase now : {program.get('current_phase', UNKNOWN)}",
            f"  Scope     : {short}",
            f"  {gate.get('name', 'GATE')} : {gate.get('status', UNKNOWN)}"
            f" (as of {gate.get('as_of', UNKNOWN)})",
            "",
        ]
        for phase in program.get("phases", []):
            mark = {"DONE": "[x]", "IN PROGRESS": "[>]",
                    "PARTIAL": "[~]"}.get(phase["state"], "[ ]")
            lines.append(f"  {mark} {phase['id']:5} {phase['state']}")
        lines.append("")

    # ---- venture gate (governance, not build) ---------------------------
    decisions = data["decisions"]
    if decisions and decisions.get("decisions"):
        rows = decisions["decisions"]
        approved = sum(1 for d in rows if str(d.get("status", "")).upper() == "APPROVED")
        lines += [
            f"{b}GOVERNANCE{b}",
            f"  Decisions : {len(rows)} recorded, {approved} approved",
            "",
        ]

    # ---- the Founder's own work ----------------------------------------
    objectives = data["objectives"]
    if objectives and objectives.get("objectives") is not None:
        rows = objectives["objectives"]
        active = [o for o in rows if str(o.get("status", "")).upper() == "ACTIVE"]
        lines += [f"{b}YOUR WORK{b}",
                  f"  Objectives: {len(rows)} total, {len(active)} active"]
        for objective in active[:5]:
            lines.append(f"    - {str(objective.get('title', ''))[:52]}")
        lines.append("")

    # ---- execution capability ------------------------------------------
    execution = data["execution"]
    if execution:
        lines += [
            f"{b}ENGINE ROOM{b}",
            f"  Adapter   : {execution.get('adapter', UNKNOWN)}"
            f" · {execution.get('state', UNKNOWN)}",
            "",
        ]

    # ---- execution economics -------------------------------------------
    payload = data.get("ledger") or {}
    L = payload.get("ledger") if isinstance(payload, dict) else None
    if L and L.get("runs"):
        rate = L.get("success_rate")
        lines += [
            f"{b}RUNS{b}",
            f"  Recorded  : {L['runs']}"
            f" ({L.get('succeeded', 0)} ok, {L.get('failed', 0)} failed)",
            f"  Success   : {round(rate * 100)}%" if rate is not None
            else "  Success   : NOT MEASURED",
            f"  Median    : {L.get('active_seconds_median', 'NOT MEASURED')}s",
            f"  Cost      : {L.get('cost_basis', UNKNOWN)}",
            "",
        ]

    # Never invent a completion percentage. Nobody measured one.
    lines.append("Phases and gate are read from the VECYRA repo; nothing here")
    lines.append("is estimated. Cost and runtime remain NOT MEASURED.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true",
                        help="format for a phone rather than a terminal")
    args = parser.parse_args()
    print(render(build(), telegram=args.telegram))


if __name__ == "__main__":
    main()
