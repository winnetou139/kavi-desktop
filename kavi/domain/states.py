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

# Epistemic classification of a claim.
# FOUNDER / DOMAIN EVIDENCE is deliberately its own class: D-006 forbids
# treating the Founder's domain knowledge as external market validation, so it
# must never be silently folded into FACT.
EVIDENCE_CLASSES = (
    "FACT",
    "INFERENCE",
    "HYPOTHESIS",
    "UNKNOWN",
    "FOUNDER / DOMAIN EVIDENCE",
)

# Classes that may never be cited as external market validation.
NON_MARKET_EVIDENCE_CLASSES = ("FOUNDER / DOMAIN EVIDENCE", "HYPOTHESIS", "UNKNOWN")

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

PRIORITY_LEVELS = ("LOW", "NORMAL", "HIGH", "CRITICAL")

INBOX_TYPES = ("DECISION", "APPROVAL", "RISK", "OPPORTUNITY", "FYI")

INBOX_STATES = ("OPEN", "APPROVED", "REJECTED", "DEFERRED", "EVIDENCE_REQUESTED")

# Authority ladder. A3+ is not grantable in LOCAL MODE — nothing can execute.
AUTHORITY_LEVELS = {
    "A0": {
        "name": "Observe",
        "detail": "Read only. May report what it sees. No state change of any kind.",
        "grantable_locally": True,
    },
    "A1": {
        "name": "Recommend",
        "detail": "May analyse and propose. The recommendation itself changes nothing.",
        "grantable_locally": True,
    },
    "A2": {
        "name": "Prepare",
        "detail": "May draft an action and stage it for approval. May not commit it.",
        "grantable_locally": True,
    },
    "A3": {
        "name": "Execute Within Policy",
        "detail": "May commit reversible actions inside an explicit policy envelope.",
        "grantable_locally": False,
    },
    "A4": {
        "name": "Bounded Autonomous Workflow",
        "detail": "May run a defined multi-step workflow within budget, scope and expiry.",
        "grantable_locally": False,
    },
}

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

# Founder disposition of an inbox item. DEFERRED and EVIDENCE_REQUESTED
# return to OPEN; APPROVED/REJECTED are terminal for the item itself.
INBOX_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "OPEN": ("APPROVED", "REJECTED", "DEFERRED", "EVIDENCE_REQUESTED"),
    "DEFERRED": ("OPEN", "APPROVED", "REJECTED", "EVIDENCE_REQUESTED"),
    "EVIDENCE_REQUESTED": ("OPEN", "APPROVED", "REJECTED", "DEFERRED"),
    "APPROVED": (),
    "REJECTED": (),
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


def check_inbox_transition(current: str, target: str) -> None:
    _check(INBOX_TRANSITIONS, "inbox item", current, target)


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
        "priority": PRIORITY_LEVELS,
        "inbox_type": INBOX_TYPES,
        "inbox_state": INBOX_STATES,
        "runtime_state": RUNTIME_STATES,
        "authority_level": tuple(AUTHORITY_LEVELS),
    }
