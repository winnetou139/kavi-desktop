"""Use cases for the Founder Cockpit.

This layer owns orchestration. It knows about domain objects and repositories;
it knows nothing about HTTP or HTML. Every rule the interface appears to enforce
is enforced here or in the domain layer.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
from typing import Any

from kavi.domain import states
from kavi.domain.models import (
    Actor,
    Approval,
    Decision,
    Evidence,
    Objective,
    Permission,
    Review,
    Task,
    Venture,
)
from kavi.infrastructure.execution import ExecutionCapability, ExecutionRequest
from kavi.infrastructure.repository import Repository
from kavi.infrastructure.runtime_status import RuntimeStatusProvider
from kavi.infrastructure.vault import VaultReader


class UseCaseError(Exception):
    """A use case refused an action. The message is safe to show the Founder."""


class CockpitService:
    def __init__(
        self,
        repository: Repository,
        runtime: RuntimeStatusProvider,
        vault: VaultReader,
        execution: ExecutionCapability,
    ) -> None:
        self.repo = repository
        self.runtime = runtime
        self.vault = vault
        self.execution = execution

    # ------------------------------------------------------------- identity

    def founder(self) -> dict[str, Any]:
        for row in self.repo.list("actors"):
            if row.get("kind") == "HUMAN" and row.get("may_approve"):
                return row
        return {
            "id": "",
            "name": "Founder",
            "kind": "HUMAN",
            "role": "CEO / Approver",
            "may_approve": True,
            "origin": "LOCAL",
            "notes": "",
        }

    def authority_summary(self) -> dict[str, Any]:
        permissions = self.repo.list("permissions")
        actors = self.repo.list("actors")
        approvals = self.repo.list("approvals")
        return {
            "founder": self.founder(),
            "human_authority": "EXPLICIT",
            "actors": actors,
            "permissions": permissions,
            "pending_approvals": [a for a in approvals if a.get("state") == "PENDING"],
            "rules": [
                "Providers and Tools are capabilities, never authority-bearing actors.",
                "Organizational Roles constrain actors; they cannot hold an executable grant.",
                "A Service Account may execute under a grant but can never issue an Approval.",
                "The requester, preparer, executor or reviewer of an action may not approve it.",
                "Founder-reserved actions remain human-approved.",
            ],
            "emergency_stop": {
                "available": False,
                "detail": "Nothing is executing. No runtime is connected in LOCAL MODE.",
            },
        }

    # -------------------------------------------------------------- runtime

    def runtime_status(self) -> dict[str, Any]:
        status = self.runtime.status().to_dict()
        status["execution"] = self.execution.describe()
        status["vault"] = self.vault.status()
        return status

    # ----------------------------------------------------------- objectives

    def list_objectives(self) -> list[dict[str, Any]]:
        rows = self.repo.list("objectives")
        tasks = self.repo.list("tasks")
        for row in rows:
            related = [t for t in tasks if t.get("objective_id") == row["id"]]
            done = [t for t in related if t.get("state") == "DONE"]
            row["task_count"] = len(related)
            row["task_done"] = len(done)
            row["progress"] = (
                round(100 * len(done) / len(related)) if related else None
            )
        return rows

    def get_objective(self, objective_id: str) -> dict[str, Any]:
        row = self.repo.get("objectives", objective_id)
        if row is None:
            raise UseCaseError(f"objective {objective_id} not found")
        row["tasks"] = self.repo.find("tasks", objective_id=objective_id)
        row["evidence"] = self.repo.find("evidence", objective_id=objective_id)
        row["reviews"] = [
            r for r in self.repo.list("reviews") if r.get("subject_id") == objective_id
        ]
        return row

    def create_objective(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise UseCaseError("An objective needs a title stating the intended outcome.")

        year = _dt.date.today().year
        objective = Objective(
            id=self.repo.next_id("objectives", "objective", year),
            title=title,
            outcome=str(payload.get("outcome", "")).strip(),
            state="DRAFT",
            owner_actor_id=str(payload.get("owner_actor_id", "")).strip(),
            sponsor_actor_id=str(payload.get("sponsor_actor_id", "")).strip()
            or self.founder().get("id", ""),
            permission_grant_id=str(payload.get("permission_grant_id", "")).strip(),
            constraints=str(payload.get("constraints", "")).strip(),
            evidence_requirements=str(payload.get("evidence_requirements", "")).strip(),
            budget=str(payload.get("budget", "")).strip(),
            deadline=str(payload.get("deadline", "")).strip(),
            venture_id=str(payload.get("venture_id", "")).strip(),
            origin="LOCAL",
        )

        requested_state = str(payload.get("state", "DRAFT")).strip().upper() or "DRAFT"
        if requested_state != "DRAFT":
            objective.transition(requested_state)

        stored = self.repo.add("objectives", objective.to_dict())
        stored["task_count"] = 0
        stored["task_done"] = 0
        stored["progress"] = None
        return stored

    def transition_objective(self, objective_id: str, target: str) -> dict[str, Any]:
        row = self.repo.get("objectives", objective_id)
        if row is None:
            raise UseCaseError(f"objective {objective_id} not found")
        if row.get("origin") == "FIXTURE":
            raise UseCaseError(
                "This objective is development fixture data and cannot be modified."
            )
        objective = Objective(**{k: v for k, v in row.items() if k in _objective_fields()})
        try:
            objective.transition(target.upper())
        except states.TransitionError as exc:
            raise UseCaseError(str(exc)) from exc
        return self.repo.update("objectives", objective_id, objective.to_dict())

    # ---------------------------------------------------------------- tasks

    def list_tasks(self, objective_id: str | None = None) -> list[dict[str, Any]]:
        if objective_id:
            return self.repo.find("tasks", objective_id=objective_id)
        return self.repo.list("tasks")

    def task_board(self, objective_id: str | None = None) -> dict[str, Any]:
        tasks = self.list_tasks(objective_id)
        columns = []
        for state in states.TASK_STATES:
            columns.append(
                {
                    "state": state,
                    "terminal": states.is_terminal_task_state(state),
                    "tasks": [t for t in tasks if t.get("state") == state],
                }
            )
        return {"columns": columns, "total": len(tasks)}

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        objective_id = str(payload.get("objective_id", "")).strip()
        if not objective_id:
            raise UseCaseError("A task must belong to an objective.")
        if self.repo.get("objectives", objective_id) is None:
            raise UseCaseError(f"objective {objective_id} not found")
        title = str(payload.get("title", "")).strip()
        if not title:
            raise UseCaseError("A task needs a title.")

        year = _dt.date.today().year
        task = Task(
            id=self.repo.next_id("tasks", "task", year),
            objective_id=objective_id,
            title=title,
            state="BACKLOG",
            owner_actor_id=str(payload.get("owner_actor_id", "")).strip(),
            assignee_actor_id=str(payload.get("assignee_actor_id", "")).strip(),
            assigned_role_id=str(payload.get("assigned_role_id", "")).strip(),
            permission_grant_id=str(payload.get("permission_grant_id", "")).strip(),
            expected_output=str(payload.get("expected_output", "")).strip(),
            estimated_cost=str(payload.get("estimated_cost", "")).strip(),
            origin="LOCAL",
        )
        return self.repo.add("tasks", task.to_dict())

    def transition_task(self, task_id: str, target: str, *, reason: str = "") -> dict[str, Any]:
        row = self.repo.get("tasks", task_id)
        if row is None:
            raise UseCaseError(f"task {task_id} not found")
        if row.get("origin") == "FIXTURE":
            raise UseCaseError("This task is development fixture data and cannot be modified.")
        task = Task(**{k: v for k, v in row.items() if k in _task_fields()})
        try:
            task.transition(target.upper(), reason=reason)
        except states.TransitionError as exc:
            raise UseCaseError(str(exc)) from exc
        return self.repo.update("tasks", task_id, task.to_dict())

    def dispatch_task(self, task_id: str) -> dict[str, Any]:
        """Attempt to execute a task through the execution seam.

        In LOCAL MODE this always declines. It never simulates execution.
        """
        row = self.repo.get("tasks", task_id)
        if row is None:
            raise UseCaseError(f"task {task_id} not found")
        result = self.execution.submit(
            ExecutionRequest(
                task_id=task_id,
                instruction=row.get("title", ""),
                permission_grant_id=row.get("permission_grant_id", ""),
                idempotency_key=row.get("idempotency_key", ""),
            )
        )
        return result.to_dict()

    # -------------------------------------------------------------- inbox

    def list_inbox(self) -> list[dict[str, Any]]:
        items = self.repo.list("inbox")
        evidence_by_id = {e["id"]: e for e in self.repo.list("evidence")}
        for item in items:
            item["evidence"] = [
                evidence_by_id[e] for e in item.get("evidence_ids", []) if e in evidence_by_id
            ]
        return items

    def inbox_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {t: 0 for t in states.INBOX_TYPES}
        open_total = 0
        for item in self.repo.list("inbox"):
            if item.get("state") != "OPEN":
                continue
            open_total += 1
            kind = item.get("type", "FYI")
            counts[kind] = counts.get(kind, 0) + 1
        counts["OPEN"] = open_total
        return counts

    # ----------------------------------------------------------- ventures

    def list_ventures(self) -> list[dict[str, Any]]:
        return self.repo.list("ventures")

    def gate_ladder(self, venture: dict[str, Any]) -> list[dict[str, Any]]:
        """Gate positions G0..G7 relative to the venture's current gate."""
        gates = [
            ("G0", "Thesis → Discover"),
            ("G1", "Discover → Validate"),
            ("G2", "Validate → Offer"),
            ("G3", "Offer → Sell"),
            ("G4", "Sell → Deliver"),
            ("G5", "Deliver → Productize"),
            ("G6", "Productize → Scale"),
            ("G7", "Scale → Autonomize"),
        ]
        current = str(venture.get("gate", "")).split(" ")[0].strip().upper()
        ladder = []
        seen_current = False
        for code, name in gates:
            if code == current:
                position = "current"
                seen_current = True
            elif not seen_current:
                position = "passed"
            else:
                position = "future"
            ladder.append({"gate": code, "name": name, "position": position})
        return ladder

    def venture_detail(self, venture_id: str) -> dict[str, Any]:
        row = self.repo.get("ventures", venture_id)
        if row is None:
            raise UseCaseError(f"venture {venture_id} not found")
        row["gates"] = self.gate_ladder(row)
        row["objectives"] = self.repo.find("objectives", venture_id=venture_id)
        return row

    # ---------------------------------------------------------- decisions

    def list_decisions(self) -> list[dict[str, Any]]:
        return self.repo.list("decisions")

    # ---------------------------------------------------------- evidence

    def list_evidence(self) -> list[dict[str, Any]]:
        return self.repo.list("evidence")

    def evidence_summary(self) -> dict[str, Any]:
        rows = self.list_evidence()
        by_class: dict[str, int] = {c: 0 for c in states.EVIDENCE_CLASSES}
        contradictions = 0
        for row in rows:
            by_class[row.get("classification", "UNKNOWN")] = (
                by_class.get(row.get("classification", "UNKNOWN"), 0) + 1
            )
            if str(row.get("contradiction", "")).strip():
                contradictions += 1
        return {
            "total": len(rows),
            "by_classification": by_class,
            "with_contradiction": contradictions,
        }

    # ---------------------------------------------------- organization

    def organization(self) -> dict[str, Any]:
        actors = self.repo.list("actors")
        divisions = [
            ("INTEL", "Research, evidence, market and problem intelligence"),
            ("PRODUCT", "Product definition, specification, experiments"),
            ("BUILD", "Implementation and delivery"),
            ("GROW", "Offer, outreach, commercial motion"),
            ("OPERATE", "Runtime, infrastructure, operations"),
            ("CONTROL", "Review, governance, audit"),
        ]
        rows = []
        for code, mandate in divisions:
            members = [a for a in actors if a.get("role") == code]
            rows.append(
                {
                    "code": code,
                    "mandate": mandate,
                    "members": members,
                    "state": "STAFFED" if members else "STANDBY",
                }
            )
        return {
            "office": [a for a in actors if a.get("role") in ("KAVI Office", "CEO / Approver")],
            "divisions": rows,
            "note": (
                "Organization is an organizational abstraction. It does not imply a "
                "permanent agent per division in v0.1."
            ),
        }

    # -------------------------------------------------------------- memory

    def memory_index(self, section: str | None = None, query: str | None = None) -> dict[str, Any]:
        notes = self.vault.index()
        if section:
            notes = [n for n in notes if n["section"] == section]
        if query:
            needle = query.lower()
            notes = [
                n
                for n in notes
                if needle in n["title"].lower() or needle in n["summary"].lower()
            ]
        return {
            "status": self.vault.status(),
            "sections": self.vault.sections(),
            "notes": notes[:400],
            "shown": min(len(notes), 400),
            "matched": len(notes),
        }

    def memory_note(self, path: str) -> dict[str, Any]:
        note = self.vault.read(path)
        if note is None:
            raise UseCaseError("Note not found, or outside the canonical vault.")
        return note

    # ------------------------------------------------------ metrics & cost

    def metrics(self) -> dict[str, Any]:
        counts = self.repo.counts()
        runtime = self.runtime.status()
        objectives = self.repo.list("objectives")
        tasks = self.repo.list("tasks")
        return {
            "runtime": {
                "mode": runtime.mode,
                "cost_today": runtime.cost_today,
                "uptime": runtime.uptime,
                "queue_depth": runtime.queue_depth,
                "detail": (
                    "Cost, uptime and queue are not measured in LOCAL MODE. "
                    "No runtime is connected to measure them."
                ),
            },
            "work": {
                "objectives_total": len(objectives),
                "objectives_active": len([o for o in objectives if o.get("state") == "ACTIVE"]),
                "tasks_total": len(tasks),
                "tasks_open": len(
                    [t for t in tasks if not states.is_terminal_task_state(t.get("state", ""))]
                ),
                "tasks_blocked": len([t for t in tasks if t.get("state") == "BLOCKED"]),
            },
            "evidence": self.evidence_summary(),
            "records": counts,
            "commercial": {
                "revenue": "UNKNOWN / REQUIRES VALIDATION",
                "venture_spend": "0 external spend authorized",
                "provider_cost": "NOT MEASURED",
                "detail": "No commercial figure exists. None may be inferred from fixture data.",
            },
        }

    # -------------------------------------------------------------- summary

    def cockpit_summary(self) -> dict[str, Any]:
        inbox = self.inbox_counts()
        objectives = self.list_objectives()
        tasks = self.repo.list("tasks")
        ventures = self.list_ventures()
        return {
            "founder": self.founder(),
            "runtime": self.runtime_status(),
            "inbox": inbox,
            "objectives": {
                "total": len(objectives),
                "active": len([o for o in objectives if o.get("state") == "ACTIVE"]),
            },
            "tasks": {
                "total": len(tasks),
                "open": len(
                    [t for t in tasks if not states.is_terminal_task_state(t.get("state", ""))]
                ),
                "blocked": len([t for t in tasks if t.get("state") == "BLOCKED"]),
            },
            "ventures": [
                {
                    "id": v["id"],
                    "name": v["name"],
                    "stage": v["stage"],
                    "gate": v["gate"],
                    "gate_status": v["gate_status"],
                    "recommendation": v["recommendation"],
                    "origin": v["origin"],
                }
                for v in ventures
            ],
            "evidence": self.evidence_summary(),
            "vocabularies": {k: list(v) for k, v in states.vocabularies().items()},
        }


def _objective_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(Objective)}


def _task_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(Task)}
