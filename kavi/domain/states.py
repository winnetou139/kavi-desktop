"""Controlled vocabularies and state transitions.

Sourced from the approved vault contract
`03_KAVI_OS/Work Event and State Model.md`. These are governance rules, not
UI concerns: the browser never decides whether a transition is legal.
"""

from __future__ import annotations


class TransitionError(Exception):
    """Raised when a state transition is not permitted by the contract."""


# ---------------------------------------------------------------- vocabularies

DOCUMENT_STATES = ("DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED")

DECISION_STATES = ("PROPOSED", "APPROVED", "REJECTED", "SUPERSEDED")

VENTURE_STATES = (
    "THESIS",
    "DISCOVER",
    "VALIDATE",
    "OFFER",
    "SELL",
    "DELIVER",
    "PRODUCTIZE",
    "SCALE",
    "AUTONOMIZE",
)

EVIDENCE_CLASSES = ("FACT", "INFERENCE", "HYPOTHESIS", "UNKNOWN")

REVIEW_RESULTS = ("PENDING", "PASS", "PASS_WITH_CONDITIONS", "FAIL")

APPROVAL_STATES = ("PENDING", "APPROVED", "REJECTED", "EXPIRED", "REVOKED")

OBJECTIVE_STATES = ("DRAFT", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED")

TASK_STATES = (
    "BACKLOG",
    "READY",
    "RUNNING",
    "BLOCKED",
    "REVIEW",
    "APPROVAL",
    "DONE",
    "FAILED",
    "CANCELLED",
    "KILLED",
)

TASK_TERMINAL_STATES = ("DONE", "FAILED", "CANCELLED", "KILLED")

CONFIDENCE_LEVELS = ("LOW", "MEDIUM", "HIGH")

INBOX_TYPES = ("DECISION", "APPROVAL", "RISK", "OPPORTUNITY", "FYI")

# Founder-facing states the UI must be able to render truthfully.
RUNTIME_STATES = (
    "LOCAL_MODE",
    "ENGINE_ROOM_NOT_CONNECTED",
    "DEGRADED",
    "CONNECTED",
    "UNKNOWN",
)


# ---------------------------------------------------------------- transitions

OBJECTIVE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "DRAFT": ("ACTIVE", "CANCELLED"),
    "ACTIVE": ("PAUSED", "COMPLETED", "CANCELLED"),
    "PAUSED": ("ACTIVE", "CANCELLED"),
    "COMPLETED": (),
    "CANCELLED": (),
}

TASK_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "BACKLOG": ("READY", "CANCELLED"),
    "READY": ("RUNNING", "BLOCKED", "CANCELLED"),
    "RUNNING": ("REVIEW", "BLOCKED", "FAILED", "READY", "CANCELLED", "KILLED"),
    "BLOCKED": ("READY", "CANCELLED", "KILLED"),
    "REVIEW": ("APPROVAL", "READY", "FAILED", "CANCELLED"),
    "APPROVAL": ("DONE", "READY", "BLOCKED", "CANCELLED"),
    "DONE": (),
    "FAILED": (),
    "CANCELLED": (),
    "KILLED": (),
}

APPROVAL_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "PENDING": ("APPROVED", "REJECTED", "EXPIRED"),
    "APPROVED": ("REVOKED",),
    "REJECTED": (),
    "EXPIRED": (),
    "REVOKED": (),
}


def _check(table: dict[str, tuple[str, ...]], kind: str, current: str, target: str) -> None:
    if current not in table:
        raise TransitionError(f"unknown {kind} state: {current}")
    if target not in table:
        raise TransitionError(f"unknown {kind} state: {target}")
    if target not in table[current]:
        raise TransitionError(
            f"{kind} transition {current} -> {target} is not permitted by contract"
        )


def check_objective_transition(current: str, target: str) -> None:
    _check(OBJECTIVE_TRANSITIONS, "objective", current, target)


def check_task_transition(current: str, target: str) -> None:
    _check(TASK_TRANSITIONS, "task", current, target)


def check_approval_transition(current: str, target: str) -> None:
    _check(APPROVAL_TRANSITIONS, "approval", current, target)


def is_terminal_task_state(state: str) -> bool:
    return state in TASK_TERMINAL_STATES


def vocabularies() -> dict[str, tuple[str, ...]]:
    """Everything the presentation layer may render as a controlled value."""
    return {
        "document_state": DOCUMENT_STATES,
        "decision_state": DECISION_STATES,
        "venture_state": VENTURE_STATES,
        "evidence_class": EVIDENCE_CLASSES,
        "review_result": REVIEW_RESULTS,
        "approval_state": APPROVAL_STATES,
        "objective_state": OBJECTIVE_STATES,
        "task_state": TASK_STATES,
        "confidence": CONFIDENCE_LEVELS,
        "inbox_type": INBOX_TYPES,
        "runtime_state": RUNTIME_STATES,
    }
