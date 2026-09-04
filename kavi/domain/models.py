"""KAVI domain objects.

One dataclass per approved contract in the KAVI Vault. These types carry the
governance rules that the vault states in prose: separation of duties, evidence
classification, permission grants, controlled state values.

Design rules:
  * Pure data + invariants. No persistence, no HTTP, no formatting.
  * ``origin`` distinguishes LOCAL records from FIXTURE development data and is
    preserved all the way to the interface.
  * Validation raises ``ValueError``; illegal transitions raise ``TransitionError``.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
from typing import Any

from kavi.domain import states

# Where a record came from, and therefore how much it may be trusted.
#   LOCAL   — created in this application, machine-operational state
#   FIXTURE — development demo data; never company evidence
#   VAULT   — read from the canonical KAVI Vault; authoritative, read-only
ORIGINS = ("LOCAL", "FIXTURE", "VAULT")

UNKNOWN = "UNKNOWN / REQUIRES VALIDATION"


def _now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def _require(value: str | None, field: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field} is required")
    return str(value).strip()


def _require_in(value: str, allowed: tuple[str, ...], field: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field} must be one of {', '.join(allowed)} (got {value!r})")
    return value


@dataclasses.dataclass
class _Base:
    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# --------------------------------------------------------------------- Actor


@dataclasses.dataclass
class Actor(_Base):
    """Identity that may hold a permission grant.

    Contract: `03_KAVI_OS/Identity and Permission Model.md`.

    Only ``HUMAN``, ``AGENT_INSTANCE`` and ``SERVICE_ACCOUNT`` are actors that
    can receive an executable grant. ``ROLE`` constrains actors but is not one.
    ``PROVIDER`` and ``TOOL`` are capabilities, never authority-bearing.
    """

    id: str
    name: str
    kind: str  # HUMAN | ROLE | AGENT_INSTANCE | SERVICE_ACCOUNT | PROVIDER | TOOL
    role: str = ""
    may_approve: bool = False
    origin: str = "LOCAL"
    notes: str = ""

    KINDS = ("HUMAN", "ROLE", "AGENT_INSTANCE", "SERVICE_ACCOUNT", "PROVIDER", "TOOL")
    GRANTABLE = ("HUMAN", "AGENT_INSTANCE", "SERVICE_ACCOUNT")
    APPROVAL_CAPABLE = ("HUMAN", "AGENT_INSTANCE")

    def __post_init__(self) -> None:
        self.name = _require(self.name, "actor.name")
        _require_in(self.kind, self.KINDS, "actor.kind")
        _require_in(self.origin, ORIGINS, "actor.origin")
        if self.may_approve and self.kind not in self.APPROVAL_CAPABLE:
            raise ValueError(
                f"actor kind {self.kind} may never issue an approval "
                "(Identity and Permission Model: Service Accounts, Providers and "
                "Tools cannot approve)"
            )

    @property
    def can_hold_grant(self) -> bool:
        return self.kind in self.GRANTABLE


# ---------------------------------------------------------------- Permission


@dataclasses.dataclass
class Permission(_Base):
    """An explicit permission grant.

    Contract shape: Actor + Action + Resource + Scope + Conditions + Budget +
    Expiry + Approver.
    """

    id: str
    actor_id: str
    action: str
    resource: str
    scope: str = ""
    conditions: str = ""
    budget: str = ""
    expiry: str = ""
    approver_id: str = ""
    state: str = "ACTIVE"  # ACTIVE | EXPIRED | REVOKED
    origin: str = "LOCAL"

    STATES = ("ACTIVE", "EXPIRED", "REVOKED")

    def __post_init__(self) -> None:
        self.actor_id = _require(self.actor_id, "permission.actor_id")
        self.action = _require(self.action, "permission.action")
        self.resource = _require(self.resource, "permission.resource")
        _require_in(self.state, self.STATES, "permission.state")
        _require_in(self.origin, ORIGINS, "permission.origin")

    @property
    def is_effective(self) -> bool:
        return self.state == "ACTIVE"


# ----------------------------------------------------------------- Objective


@dataclasses.dataclass
class Objective(_Base):
    id: str
    title: str
    outcome: str = ""
    state: str = "DRAFT"
    priority: str = "NORMAL"
    owner_actor_id: str = ""
    sponsor_actor_id: str = ""
    authority_level: str = "A0"
    permission_grant_id: str = ""
    constraints: str = ""
    success_criteria: str = ""
    evidence_requirements: str = ""
    budget: str = ""
    actual_cost: str = ""
    deadline: str = ""
    venture_id: str = ""
    created_at: str = dataclasses.field(default_factory=_now)
    updated_at: str = dataclasses.field(default_factory=_now)
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.title = _require(self.title, "objective.title")
        _require_in(self.state, states.OBJECTIVE_STATES, "objective.state")
        _require_in(self.priority, states.PRIORITY_LEVELS, "objective.priority")
        _require_in(self.authority_level, tuple(states.AUTHORITY_LEVELS), "objective.authority_level")
        _require_in(self.origin, ORIGINS, "objective.origin")
        if not states.AUTHORITY_LEVELS[self.authority_level]["grantable_locally"]:
            raise ValueError(
                f"authority {self.authority_level} "
                f"({states.AUTHORITY_LEVELS[self.authority_level]['name']}) cannot be granted "
                "in LOCAL MODE — no execution runtime is connected"
            )

    def transition(self, target: str) -> None:
        states.check_objective_transition(self.state, target)
        self.state = target
        self.updated_at = _now()


# ---------------------------------------------------------------------- Task


@dataclasses.dataclass
class Task(_Base):
    id: str
    objective_id: str
    title: str
    state: str = "BACKLOG"
    priority: str = "NORMAL"
    parent_task_id: str = ""
    depends_on: str = ""
    owner_actor_id: str = ""
    assignee_actor_id: str = ""
    assigned_role_id: str = ""
    authority_level: str = "A0"
    permission_grant_id: str = ""
    capability_requirements: str = ""
    expected_output: str = ""
    evidence_requirement: str = ""
    review_required: bool = False
    approval_required: bool = False
    estimated_cost: str = ""
    actual_cost: str = ""
    idempotency_key: str = ""
    retry_policy: str = ""
    failure_reason: str = ""
    created_at: str = dataclasses.field(default_factory=_now)
    updated_at: str = dataclasses.field(default_factory=_now)
    started_at: str = ""
    completed_at: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.objective_id = _require(self.objective_id, "task.objective_id")
        self.title = _require(self.title, "task.title")
        _require_in(self.state, states.TASK_STATES, "task.state")
        _require_in(self.priority, states.PRIORITY_LEVELS, "task.priority")
        _require_in(self.authority_level, tuple(states.AUTHORITY_LEVELS), "task.authority_level")
        _require_in(self.origin, ORIGINS, "task.origin")
        if not states.AUTHORITY_LEVELS[self.authority_level]["grantable_locally"]:
            raise ValueError(
                f"authority {self.authority_level} cannot be granted in LOCAL MODE"
            )

    def transition(self, target: str, *, reason: str = "") -> None:
        states.check_task_transition(self.state, target)
        target = target.upper()
        # A task that must be reviewed cannot bypass REVIEW on the way to DONE.
        if target == "DONE" and self.review_required and self.state != "APPROVAL":
            raise states.TransitionError(
                "this task requires review and approval before it can be completed"
            )
        if target == "APPROVAL" and not (self.approval_required or self.review_required):
            raise states.TransitionError(
                "this task declares no approval requirement; move it to DONE via REVIEW instead"
            )
        self.state = target
        self.updated_at = _now()
        if target == "RUNNING" and not self.started_at:
            self.started_at = _now()
        if states.is_terminal_task_state(target):
            self.completed_at = _now()
        if target == "FAILED":
            self.failure_reason = reason or self.failure_reason

    @property
    def is_terminal(self) -> bool:
        return states.is_terminal_task_state(self.state)

    @property
    def dependency_ids(self) -> list[str]:
        return [part.strip() for part in self.depends_on.split(",") if part.strip()]


# ------------------------------------------------------------------ Evidence


@dataclasses.dataclass
class Evidence(_Base):
    """A claim with provenance.

    Contract: `03_KAVI_OS/Evidence and Review Contract.md`. Every material claim
    carries source, date, locator, classification, confidence, freshness and any
    contradicting evidence. Contradictions are preserved, never discarded.
    """

    id: str
    claim: str
    classification: str = "UNKNOWN"
    source: str = ""
    source_date: str = ""
    locator: str = ""
    confidence: str = "LOW"
    freshness: str = ""
    contradiction: str = ""
    objective_id: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.claim = _require(self.claim, "evidence.claim")
        _require_in(self.classification, states.EVIDENCE_CLASSES, "evidence.classification")
        _require_in(self.confidence, states.CONFIDENCE_LEVELS, "evidence.confidence")
        _require_in(self.origin, ORIGINS, "evidence.origin")
        if self.classification == "FACT" and not self.source.strip():
            raise ValueError("evidence classified FACT must carry a source")

    @property
    def is_decision_grade(self) -> bool:
        """A FACT or INFERENCE with a source and a locator."""
        return (
            self.classification in ("FACT", "INFERENCE")
            and bool(self.source.strip())
            and bool(self.locator.strip())
        )


# -------------------------------------------------------------------- Review


@dataclasses.dataclass
class Review(_Base):
    """An independent review record.

    Independence is enforced on identity: the reviewer may not be the producer.
    A new run, task or role label is not sufficient.
    """

    id: str
    subject_id: str
    reviewer_actor_id: str
    producer_actor_id: str = ""
    review_task_id: str = ""
    review_date: str = ""
    independence_conditions: str = ""
    checked_ids: str = ""
    findings: str = ""
    acceptance_criteria: str = ""
    result: str = "PENDING"
    conditions: str = ""
    remediation_task_id: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.subject_id = _require(self.subject_id, "review.subject_id")
        self.reviewer_actor_id = _require(self.reviewer_actor_id, "review.reviewer_actor_id")
        _require_in(self.result, states.REVIEW_RESULTS, "review.result")
        _require_in(self.origin, ORIGINS, "review.origin")
        if self.producer_actor_id and self.producer_actor_id == self.reviewer_actor_id:
            raise ValueError(
                "independent review requires a reviewer identity distinct from the "
                "producer (Evidence and Review Contract)"
            )

    @property
    def is_independent(self) -> bool:
        return bool(self.producer_actor_id) and self.producer_actor_id != self.reviewer_actor_id


# ------------------------------------------------------------------ Approval


@dataclasses.dataclass
class Approval(_Base):
    """An approval for a controlled action.

    Separation of duties: the approver may not have requested, prepared,
    executed or reviewed the same action.
    """

    id: str
    subject_id: str
    approver_actor_id: str
    state: str = "PENDING"
    requester_actor_id: str = ""
    executor_actor_id: str = ""
    reviewer_actor_id: str = ""
    reason: str = ""
    expiry: str = ""
    decided_at: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.subject_id = _require(self.subject_id, "approval.subject_id")
        self.approver_actor_id = _require(self.approver_actor_id, "approval.approver_actor_id")
        _require_in(self.state, states.APPROVAL_STATES, "approval.state")
        _require_in(self.origin, ORIGINS, "approval.origin")
        conflicting = {
            "requester": self.requester_actor_id,
            "executor": self.executor_actor_id,
            "reviewer": self.reviewer_actor_id,
        }
        for role, actor_id in conflicting.items():
            if actor_id and actor_id == self.approver_actor_id:
                raise ValueError(
                    f"separation of duties: the {role} of an action may not approve it "
                    "(Identity and Permission Model)"
                )

    def transition(self, target: str) -> None:
        states.check_approval_transition(self.state, target)
        self.state = target
        self.decided_at = _now()


# ------------------------------------------------------------------ Decision


@dataclasses.dataclass
class Decision(_Base):
    id: str
    title: str
    state: str = "PROPOSED"
    owner_actor_id: str = ""
    approver_actor_id: str = ""
    date: str = ""
    context: str = ""
    decision: str = ""
    rationale: str = ""
    evidence_ids: str = ""
    consequences: str = ""
    reversible: str = UNKNOWN
    supersedes: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.title = _require(self.title, "decision.title")
        _require_in(self.state, states.DECISION_STATES, "decision.state")
        _require_in(self.origin, ORIGINS, "decision.origin")


# ------------------------------------------------------------------- Venture


@dataclasses.dataclass
class Venture(_Base):
    id: str
    name: str
    stage: str = "THESIS"
    gate: str = "G0"
    gate_status: str = "NOT PASSED"
    recommendation: str = UNKNOWN
    problem: str = UNKNOWN
    segment: str = UNKNOWN
    commercial_evidence: str = UNKNOWN
    blockers: str = ""
    next_gate_requirement: str = ""
    next_founder_decision: str = ""
    origin: str = "LOCAL"

    GATE_STATUSES = ("NOT PASSED", "PASSED", "UNKNOWN / REQUIRES VALIDATION")
    RECOMMENDATIONS = (
        "CONTINUE",
        "INVESTIGATE",
        "KILL",
        "SCALE",
        UNKNOWN,
    )

    def __post_init__(self) -> None:
        self.name = _require(self.name, "venture.name")
        _require_in(self.stage, states.VENTURE_STATES, "venture.stage")
        _require_in(self.gate_status, self.GATE_STATUSES, "venture.gate_status")
        _require_in(self.recommendation, self.RECOMMENDATIONS, "venture.recommendation")
        _require_in(self.origin, ORIGINS, "venture.origin")


# ----------------------------------------------------------- InboxItem


@dataclasses.dataclass
class InboxItem(_Base):
    """A Founder-level item that must reference a real underlying object.

    The CEO Inbox is an aggregation, not a record store of its own. Every item
    points at an Objective, Task, Decision, Venture or Approval. Standalone
    decorative items are only permitted when explicitly marked FIXTURE.
    """

    id: str
    type: str
    title: str
    subject_kind: str = ""      # OBJECTIVE | TASK | DECISION | VENTURE | APPROVAL
    subject_id: str = ""
    risk: str = "LOW"
    state: str = "OPEN"
    recommendation: str = ""
    authority_note: str = ""
    evidence_ids: list = dataclasses.field(default_factory=list)
    objective_id: str = ""
    disposition_note: str = ""
    decided_at: str = ""
    created_at: str = dataclasses.field(default_factory=_now)
    origin: str = "LOCAL"

    SUBJECT_KINDS = ("OBJECTIVE", "TASK", "DECISION", "VENTURE", "APPROVAL", "")

    def __post_init__(self) -> None:
        self.title = _require(self.title, "inbox.title")
        _require_in(self.type, states.INBOX_TYPES, "inbox.type")
        _require_in(self.state, states.INBOX_STATES, "inbox.state")
        _require_in(self.risk, ("LOW", "MEDIUM", "HIGH"), "inbox.risk")
        _require_in(self.subject_kind, self.SUBJECT_KINDS, "inbox.subject_kind")
        _require_in(self.origin, ORIGINS, "inbox.origin")
        if self.origin == "LOCAL" and not (self.subject_kind and self.subject_id):
            raise ValueError(
                "a local inbox item must reference a real underlying object "
                "(subject_kind + subject_id); decorative items are fixture-only"
            )

    def decide(self, target: str, *, note: str = "") -> None:
        states.check_inbox_transition(self.state, target.upper())
        self.state = target.upper()
        self.disposition_note = note or self.disposition_note
        self.decided_at = _now()

    @property
    def is_open(self) -> bool:
        return self.state in ("OPEN", "DEFERRED", "EVIDENCE_REQUESTED")


# ----------------------------------------------------------- MemoryRecord


@dataclasses.dataclass
class MemoryRecord(_Base):
    """A pointer into canonical organizational knowledge.

    The vault is canonical. This record is a read-side reference, never a
    second source of truth.
    """

    id: str
    title: str
    section: str = ""
    path: str = ""
    doc_type: str = ""
    document_state: str = "ACTIVE"
    summary: str = ""
    origin: str = "LOCAL"

    def __post_init__(self) -> None:
        self.title = _require(self.title, "memory.title")
        _require_in(self.document_state, states.DOCUMENT_STATES, "memory.document_state")
        _require_in(self.origin, ORIGINS, "memory.origin")
