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
    InboxItem,
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
        ladder = [
            {
                "level": level,
                "name": spec["name"],
                "detail": spec["detail"],
                "grantable_locally": spec["grantable_locally"],
                "status": "AVAILABLE LOCALLY" if spec["grantable_locally"] else "NOT GRANTABLE — LOCAL MODE",
            }
            for level, spec in states.AUTHORITY_LEVELS.items()
        ]
        return {
            "founder": self.founder(),
            "human_authority": "EXPLICIT",
            "mode": "LOCAL DEVELOPMENT MODE",
            "human_approval": "REQUIRED FOR ALL CONTROLLED ACTIONS",
            "ladder": ladder,
            "max_grantable_level": "A2",
            "actors": actors,
            "permissions": permissions,
            "pending_approvals": [a for a in approvals if a.get("state") == "PENDING"],
            "rules": [
                "Providers and Tools are capabilities, never authority-bearing actors.",
                "Organizational Roles constrain actors; they cannot hold an executable grant.",
                "A Service Account may execute under a grant but can never issue an Approval.",
                "The requester, preparer, executor or reviewer of an action may not approve it.",
                "Founder-reserved actions remain human-approved.",
                "A3 and A4 cannot be granted in LOCAL MODE — no execution runtime is connected.",
            ],
            "emergency_stop": {
                "available": False,
                "detail": "Nothing is executing. No runtime is connected in LOCAL MODE.",
            },
        }

    # -------------------------------------------------------------- runtime

    def runtime_status(self) -> dict[str, Any]:
        status = self.runtime.status()
        payload = status.to_dict()
        payload["engine_room_panel"] = status.engine_room_panel()
        payload["execution"] = self.execution.describe()
        payload["vault"] = self.vault.status()
        return payload

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
        try:
            objective = Objective(
                id=self.repo.next_id("objectives", "objective", year),
                title=title,
                outcome=str(payload.get("outcome", "")).strip(),
                state="DRAFT",
                priority=str(payload.get("priority", "NORMAL")).strip().upper() or "NORMAL",
                owner_actor_id=str(payload.get("owner_actor_id", "")).strip(),
                sponsor_actor_id=str(payload.get("sponsor_actor_id", "")).strip()
                or self.founder().get("id", ""),
                authority_level=str(payload.get("authority_level", "A0")).strip().upper() or "A0",
                permission_grant_id=str(payload.get("permission_grant_id", "")).strip(),
                constraints=str(payload.get("constraints", "")).strip(),
                success_criteria=str(payload.get("success_criteria", "")).strip(),
                evidence_requirements=str(payload.get("evidence_requirements", "")).strip(),
                budget=str(payload.get("budget", "")).strip(),
                deadline=str(payload.get("deadline", "")).strip(),
                venture_id=str(payload.get("venture_id", "")).strip(),
                origin="LOCAL",
            )
        except ValueError as exc:
            raise UseCaseError(str(exc)) from exc

        requested_state = str(payload.get("state", "DRAFT")).strip().upper() or "DRAFT"
        if requested_state != "DRAFT":
            try:
                objective.transition(requested_state)
            except states.TransitionError as exc:
                raise UseCaseError(str(exc)) from exc

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

        depends_on = str(payload.get("depends_on", "")).strip()
        for dependency in [d.strip() for d in depends_on.split(",") if d.strip()]:
            if self.repo.get("tasks", dependency) is None:
                raise UseCaseError(f"dependency {dependency} is not an existing task")

        year = _dt.date.today().year
        try:
            task = Task(
                id=self.repo.next_id("tasks", "task", year),
                objective_id=objective_id,
                title=title,
                state="BACKLOG",
                priority=str(payload.get("priority", "NORMAL")).strip().upper() or "NORMAL",
                parent_task_id=str(payload.get("parent_task_id", "")).strip(),
                depends_on=depends_on,
                owner_actor_id=str(payload.get("owner_actor_id", "")).strip(),
                assignee_actor_id=str(payload.get("assignee_actor_id", "")).strip(),
                assigned_role_id=str(payload.get("assigned_role_id", "")).strip(),
                authority_level=str(payload.get("authority_level", "A0")).strip().upper() or "A0",
                permission_grant_id=str(payload.get("permission_grant_id", "")).strip(),
                expected_output=str(payload.get("expected_output", "")).strip(),
                evidence_requirement=str(payload.get("evidence_requirement", "")).strip(),
                review_required=_as_bool(payload.get("review_required")),
                approval_required=_as_bool(payload.get("approval_required")),
                estimated_cost=str(payload.get("estimated_cost", "")).strip(),
                origin="LOCAL",
            )
        except ValueError as exc:
            raise UseCaseError(str(exc)) from exc
        return self.repo.add("tasks", task.to_dict())

    def transition_task(self, task_id: str, target: str, *, reason: str = "") -> dict[str, Any]:
        row = self.repo.get("tasks", task_id)
        if row is None:
            raise UseCaseError(f"task {task_id} not found")
        if row.get("origin") == "FIXTURE":
            raise UseCaseError("This task is development fixture data and cannot be modified.")
        task = Task(**{k: v for k, v in row.items() if k in _task_fields()})

        # Dependencies must be terminal-complete before work may start.
        if target.upper() == "RUNNING":
            for dependency_id in task.dependency_ids:
                dependency = self.repo.get("tasks", dependency_id)
                if dependency and dependency.get("state") != "DONE":
                    raise UseCaseError(
                        f"blocked by {dependency_id}, which is {dependency.get('state')} — "
                        "dependencies must be DONE before this task can run"
                    )
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

    def list_inbox(self, *, include_closed: bool = True) -> list[dict[str, Any]]:
        items = self.repo.list("inbox")
        evidence_by_id = {e["id"]: e for e in self.list_evidence()}
        for item in items:
            item["evidence"] = [
                evidence_by_id[e] for e in item.get("evidence_ids", []) if e in evidence_by_id
            ]
            item["subject"] = self._resolve_subject(item)
        if not include_closed:
            items = [i for i in items if i.get("state") in ("OPEN", "DEFERRED", "EVIDENCE_REQUESTED")]
        return items

    def _resolve_subject(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve the real underlying object an inbox item points at."""
        collection_for = {
            "OBJECTIVE": "objectives",
            "TASK": "tasks",
            "DECISION": "decisions",
            "VENTURE": "ventures",
            "APPROVAL": "approvals",
        }
        kind = item.get("subject_kind") or ""
        subject_id = item.get("subject_id") or item.get("objective_id") or ""
        if not kind and subject_id.startswith("OBJ-"):
            kind = "OBJECTIVE"

        # Decisions live in the canonical vault, not the operational store.
        if kind == "DECISION":
            decision = self.get_decision(subject_id)
            if decision is None:
                return {
                    "kind": kind, "id": subject_id, "found": False,
                    "detail": "No such decision in the canonical vault.",
                }
            return {
                "kind": kind,
                "id": subject_id,
                "found": True,
                "title": decision.get("title", subject_id),
                "state": decision.get("state", ""),
                "origin": decision.get("origin", "VAULT"),
            }
        collection = collection_for.get(kind)
        if not collection or not subject_id:
            return None
        row = self.repo.get(collection, subject_id)
        if row is None:
            return {
                "kind": kind,
                "id": subject_id,
                "found": False,
                "detail": "Referenced object not found in the local store.",
            }
        return {
            "kind": kind,
            "id": subject_id,
            "found": True,
            "title": row.get("title") or row.get("name") or subject_id,
            "state": row.get("state") or row.get("gate_status") or "",
            "origin": row.get("origin", "LOCAL"),
        }

    def inbox_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {t: 0 for t in states.INBOX_TYPES}
        open_total = 0
        for item in self.repo.list("inbox"):
            if item.get("state") not in ("OPEN", "DEFERRED", "EVIDENCE_REQUESTED"):
                continue
            open_total += 1
            kind = item.get("type", "FYI")
            counts[kind] = counts.get(kind, 0) + 1
        counts["OPEN"] = open_total
        return counts

    def create_inbox_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Raise a Founder-level item from a real underlying object."""
        subject_kind = str(payload.get("subject_kind", "")).strip().upper()
        subject_id = str(payload.get("subject_id", "")).strip()
        if not subject_kind or not subject_id:
            raise UseCaseError(
                "An inbox item must reference a real object: give subject_kind and subject_id."
            )
        collection_for = {
            "OBJECTIVE": "objectives", "TASK": "tasks", "DECISION": "decisions",
            "VENTURE": "ventures", "APPROVAL": "approvals",
        }
        collection = collection_for.get(subject_kind)
        if collection is None:
            raise UseCaseError(f"unknown subject kind: {subject_kind}")

        # A decision is canonical vault knowledge, not an operational record.
        if subject_kind == "DECISION":
            subject = self.get_decision(subject_id)
            if subject is None:
                raise UseCaseError(
                    f"decision {subject_id} is not in the canonical vault"
                )
        else:
            subject = self.repo.get(collection, subject_id)
            if subject is None:
                raise UseCaseError(f"{subject_kind.lower()} {subject_id} not found")

        objective_id = ""
        if subject_kind == "OBJECTIVE":
            objective_id = subject_id
        elif subject_kind == "TASK":
            objective_id = subject.get("objective_id", "")

        year = _dt.date.today().year
        try:
            item = InboxItem(
                id=self.repo.next_id("inbox", "inbox", year),
                type=str(payload.get("type", "DECISION")).strip().upper() or "DECISION",
                title=str(payload.get("title", "")).strip()
                or f"Review required: {subject.get('title') or subject.get('name') or subject_id}",
                subject_kind=subject_kind,
                subject_id=subject_id,
                risk=str(payload.get("risk", "MEDIUM")).strip().upper() or "MEDIUM",
                state="OPEN",
                recommendation=str(payload.get("recommendation", "")).strip(),
                authority_note=str(payload.get("authority_note", "")).strip()
                or "Local decision only. No external action is taken in LOCAL MODE.",
                evidence_ids=payload.get("evidence_ids") or [],
                objective_id=objective_id,
                origin="LOCAL",
            )
        except ValueError as exc:
            raise UseCaseError(str(exc)) from exc
        stored = self.repo.add("inbox", item.to_dict())
        stored["subject"] = self._resolve_subject(stored)
        stored["evidence"] = []
        return stored

    def decide_inbox_item(self, item_id: str, disposition: str, *, note: str = "") -> dict[str, Any]:
        """Founder disposition. Updates local state only — no external action."""
        row = self.repo.get("inbox", item_id)
        if row is None:
            raise UseCaseError(f"inbox item {item_id} not found")
        if row.get("origin") == "FIXTURE":
            raise UseCaseError(
                "This inbox item is development fixture data. Create a local item from a "
                "real object to exercise decisioning."
            )
        item = InboxItem(**{k: v for k, v in row.items() if k in _inbox_fields()})
        try:
            item.decide(disposition, note=note)
        except states.TransitionError as exc:
            raise UseCaseError(str(exc)) from exc
        updated = self.repo.update("inbox", item_id, item.to_dict())
        updated["subject"] = self._resolve_subject(updated)
        updated["evidence"] = []
        return updated

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
        """Canonical decisions, read from the vault.

        The vault owns decisions (D-005). Any local decision record is merged in
        and stays clearly marked LOCAL so it is never mistaken for canon. If the
        vault cannot be reached, this returns whatever is local rather than
        inventing a decision log.
        """
        canonical = self.vault.decisions()
        local = [d for d in self.repo.list("decisions") if d.get("origin") != "FIXTURE"]
        known = {d["id"] for d in canonical}
        merged = canonical + [d for d in local if d["id"] not in known]
        merged.sort(key=lambda row: row.get("id", ""))
        return merged

    def decisions_status(self) -> dict[str, Any]:
        """Where the decision log is being read from, stated plainly."""
        status = self.vault.status()
        canonical = self.vault.decisions()
        return {
            "source": "CANONICAL VAULT" if canonical else "VAULT NOT AVAILABLE",
            "path": status.get("path", ""),
            "access": "READ ONLY",
            "canonical_count": len(canonical),
            "detail": (
                "Decisions are read from 08_DECISIONS/ in the canonical vault. "
                "The desktop never writes a decision record."
                if canonical else
                "The canonical vault could not be read, so no canonical decision "
                "is shown. Nothing is substituted in its place."
            ),
        }

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        for row in self.list_decisions():
            if row.get("id") == decision_id:
                return row
        return None

    # ---------------------------------------------------------- evidence

    def list_evidence(self) -> list[dict[str, Any]]:
        """Canonical claims, read from the vault's evidence register.

        Local claims are merged in and stay marked LOCAL. If the vault cannot be
        read, this returns whatever is local rather than inventing evidence.
        """
        canonical = self.vault.evidence()
        local = [e for e in self.repo.list("evidence") if e.get("origin") != "FIXTURE"]
        known = {e["id"] for e in canonical}
        return canonical + [e for e in local if e["id"] not in known]

    def evidence_status(self) -> dict[str, Any]:
        return self.vault.evidence_status()

    def get_evidence(self, claim_id: str) -> dict[str, Any] | None:
        for row in self.list_evidence():
            if row.get("id") == claim_id:
                return row
        return None

    def evidence_summary(self) -> dict[str, Any]:
        rows = self.list_evidence()
        by_class: dict[str, int] = {c: 0 for c in states.EVIDENCE_CLASSES}
        by_confidence: dict[str, int] = {}
        contradictions = 0
        for row in rows:
            classification = row.get("classification", "UNKNOWN")
            by_class[classification] = by_class.get(classification, 0) + 1
            confidence = str(row.get("confidence", "")).strip() or "NOT STATED"
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
            if str(row.get("contradiction", "")).strip():
                contradictions += 1

        # D-006: founder/domain evidence is never external market validation.
        non_market = sum(
            by_class.get(c, 0) for c in states.NON_MARKET_EVIDENCE_CLASSES
        )
        return {
            "total": len(rows),
            "by_classification": by_class,
            "by_confidence": by_confidence,
            "with_contradiction": contradictions,
            "non_market_claims": non_market,
            "market_validation": "NONE — no buyer-side evidence exists",
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
        if query and query.strip():
            notes = self.vault.search(query)
            if section:
                notes = [n for n in notes if n["section"] == section]
            mode = "SEARCH"
        else:
            notes = self.vault.index()
            if section:
                notes = [n for n in notes if n["section"] == section]
            mode = "BROWSE"
        return {
            "status": self.vault.status(),
            "sections": self.vault.sections(),
            "notes": notes[:400],
            "shown": min(len(notes), 400),
            "matched": len(notes),
            "mode": mode,
        }

    def memory_note(self, path: str) -> dict[str, Any]:
        note = self.vault.read(path)
        if note is None:
            raise UseCaseError("Note not found, or outside the canonical vault.")
        return note

    # ------------------------------------------------------------- storage

    def storage_info(self) -> dict[str, Any]:
        """Where local operational state actually lives. Never merged with the vault."""
        path = self.repo.store.path
        exists = path.exists()
        return {
            "operational_store": {
                "path": str(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else 0,
                "format": "JSON document, atomic replace on write",
                "scope": "machine-operational state created in this application",
                "canonical_for": "running objectives, tasks, inbox dispositions",
            },
            "canonical_vault": {
                **self.vault.status(),
                "canonical_for": "organizational knowledge: doctrine, decisions, ventures, research",
            },
            "separation_rule": (
                "KAVI Vault is canonical organizational knowledge. The local store holds "
                "machine-operational development state. They are not merged and not synchronized."
            ),
        }

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


def _inbox_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(InboxItem)}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")
