"""Domain contract tests: states, transitions, separation of duties."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.harness import main  # noqa: E402

from kavi.domain import ids, states  # noqa: E402
from kavi.domain.models import (  # noqa: E402
    Actor, Approval, Evidence, Objective, Review, Task, Venture,
)


def body(t) -> None:
    # ---------------------------------------------------------------- ids
    ids.reset_counters()
    t.equals("id format", ids.new_id("objective", year=2026, seq=1), "OBJ-2026-001")
    t.equals("id namespace reverse", ids.namespace_of("TASK-2026-007"), "task")
    t.equals("review namespace exists", ids.prefix_of("review"), "REV")
    t.equals("grant namespace exists", ids.prefix_of("grant"), "GNT")
    t.raises("unknown namespace rejected", ValueError, ids.new_id, "nonsense")

    # ------------------------------------------------------- vocabularies
    t.check("BLOCKED is a task state", "BLOCKED" in states.TASK_STATES)
    t.check("venture SELL not SELL_PILOT", "SELL" in states.VENTURE_STATES)
    t.check("SELL_PILOT absent", "SELL_PILOT" not in states.VENTURE_STATES)
    t.check("epistemic classes present",
            {"FACT", "INFERENCE", "HYPOTHESIS", "UNKNOWN"} <= set(states.EVIDENCE_CLASSES))
    # D-006 requires the Founder's domain knowledge to be its own class so it
    # can never be quietly counted as external market validation.
    t.check("founder/domain evidence is a distinct class",
            "FOUNDER / DOMAIN EVIDENCE" in states.EVIDENCE_CLASSES)
    t.check("founder/domain evidence is non-market",
            "FOUNDER / DOMAIN EVIDENCE" in states.NON_MARKET_EVIDENCE_CLASSES)
    t.check("FACT is never non-market",
            "FACT" not in states.NON_MARKET_EVIDENCE_CLASSES)
    t.equals("review results include conditions",
             "PASS_WITH_CONDITIONS" in states.REVIEW_RESULTS, True)

    # -------------------------------------------------- objective states
    objective = Objective(id="OBJ-2026-900", title="Test objective")
    t.equals("objective starts DRAFT", objective.state, "DRAFT")
    objective.transition("ACTIVE")
    t.equals("draft to active", objective.state, "ACTIVE")
    objective.transition("PAUSED")
    objective.transition("ACTIVE")
    t.equals("pause and resume", objective.state, "ACTIVE")
    objective.transition("COMPLETED")
    t.raises("completed is terminal", states.TransitionError, objective.transition, "ACTIVE")
    t.raises("empty title rejected", ValueError, Objective, id="X", title="  ")

    # ------------------------------------------------------- task states
    task = Task(id="TASK-2026-900", objective_id="OBJ-2026-900", title="Test task")
    t.equals("task starts BACKLOG", task.state, "BACKLOG")
    t.raises("cannot skip to DONE", states.TransitionError, task.transition, "DONE")
    task.transition("READY")
    task.transition("RUNNING")
    t.check("started_at stamped", bool(task.started_at))
    task.transition("BLOCKED")
    t.equals("BLOCKED is reachable as an exception", task.state, "BLOCKED")
    task.transition("READY")
    t.equals("BLOCKED is not a mandatory phase — returns to READY", task.state, "READY")
    task.transition("RUNNING")
    task.transition("FAILED", reason="provider timeout")
    t.equals("failure reason recorded", task.failure_reason, "provider timeout")
    t.check("terminal task", task.is_terminal)
    t.raises("terminal task frozen", states.TransitionError, task.transition, "READY")

    # retry path: RUNNING -> READY (new run), not straight back to RUNNING
    retry = Task(id="TASK-2026-901", objective_id="OBJ-2026-900", title="Retry", state="RUNNING")
    retry.transition("READY")
    t.equals("retry returns to READY", retry.state, "READY")

    # ------------------------------------------------------------- actor
    founder = Actor(id="ACT-1", name="Founder", kind="HUMAN", may_approve=True)
    t.check("human may hold a grant", founder.can_hold_grant)
    agent = Actor(id="ACT-2", name="Worker", kind="AGENT_INSTANCE")
    t.check("agent instance may hold a grant", agent.can_hold_grant)
    role = Actor(id="ACT-3", name="INTEL Lead", kind="ROLE")
    t.check("role may NOT hold a grant", not role.can_hold_grant)
    provider = Actor(id="ACT-4", name="Hermes", kind="PROVIDER")
    t.check("provider may NOT hold a grant", not provider.can_hold_grant)
    t.raises("service account may not approve", ValueError,
             Actor, id="ACT-5", name="Svc", kind="SERVICE_ACCOUNT", may_approve=True)
    t.raises("provider may not approve", ValueError,
             Actor, id="ACT-6", name="OpenAI", kind="PROVIDER", may_approve=True)

    # ---------------------------------------------------------- evidence
    fact = Evidence(id="CLM-1", claim="x", classification="FACT", source="Arcadis", confidence="HIGH")
    t.check("fact with source accepted", fact.classification == "FACT")
    t.raises("FACT without source rejected", ValueError,
             Evidence, id="CLM-2", claim="y", classification="FACT")
    unknown = Evidence(id="CLM-3", claim="willingness to pay", classification="UNKNOWN")
    t.check("UNKNOWN needs no source", not unknown.is_decision_grade)
    t.raises("bad classification rejected", ValueError,
             Evidence, id="CLM-4", claim="z", classification="PROBABLY")

    # ------------------------------------------------------------ review
    t.raises("self review rejected", ValueError,
             Review, id="REV-1", subject_id="OBJ-1",
             reviewer_actor_id="ACT-2", producer_actor_id="ACT-2")
    review = Review(id="REV-2", subject_id="OBJ-1",
                    reviewer_actor_id="ACT-5", producer_actor_id="ACT-2")
    t.check("distinct reviewer is independent", review.is_independent)

    # ---------------------------------------------------------- approval
    t.raises("requester cannot approve", ValueError,
             Approval, id="APR-1", subject_id="T-1",
             approver_actor_id="ACT-2", requester_actor_id="ACT-2")
    t.raises("executor cannot approve", ValueError,
             Approval, id="APR-2", subject_id="T-1",
             approver_actor_id="ACT-2", executor_actor_id="ACT-2")
    t.raises("reviewer cannot approve", ValueError,
             Approval, id="APR-3", subject_id="T-1",
             approver_actor_id="ACT-2", reviewer_actor_id="ACT-2")
    approval = Approval(id="APR-4", subject_id="T-1", approver_actor_id="ACT-1",
                        requester_actor_id="ACT-2", executor_actor_id="ACT-3")
    approval.transition("APPROVED")
    t.equals("approval approved", approval.state, "APPROVED")
    approval.transition("REVOKED")
    t.raises("revoked is terminal", states.TransitionError, approval.transition, "APPROVED")
    expired = Approval(id="APR-5", subject_id="T-2", approver_actor_id="ACT-1")
    expired.transition("EXPIRED")
    t.equals("timeout expires, never approves", expired.state, "EXPIRED")

    # ----------------------------------------------------------- venture
    venture = Venture(id="VEN-1", name="VECYRA", stage="VALIDATE",
                      gate="G2", gate_status="NOT PASSED", recommendation="INVESTIGATE")
    t.equals("venture stage", venture.stage, "VALIDATE")
    t.raises("bad gate status rejected", ValueError,
             Venture, id="VEN-2", name="X", gate_status="MAYBE")
    t.raises("bad stage rejected", ValueError, Venture, id="VEN-3", name="X", stage="LAUNCH")

    # ------------------------------------------------------------ origin
    t.raises("bad origin rejected", ValueError,
             Objective, id="OBJ-X", title="x", origin="REAL")


main("smoke_domain", body)
