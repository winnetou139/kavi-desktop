"""API routes.

Transport only: parse the request, call one use case, return a payload.
No validation rule, no state machine, no domain decision lives here.
"""

from __future__ import annotations

from typing import Any, Callable

from kavi.application.services import CockpitService, UseCaseError

Handler = Callable[[dict[str, Any], dict[str, Any]], Any]


class Router:
    def __init__(self) -> None:
        self._get: dict[str, Handler] = {}
        self._post: dict[str, Handler] = {}

    def get(self, path: str) -> Callable[[Handler], Handler]:
        def register(handler: Handler) -> Handler:
            self._get[path] = handler
            return handler

        return register

    def post(self, path: str) -> Callable[[Handler], Handler]:
        def register(handler: Handler) -> Handler:
            self._post[path] = handler
            return handler

        return register

    def resolve(self, method: str, path: str) -> Handler | None:
        table = self._get if method == "GET" else self._post
        return table.get(path)

    def paths(self) -> dict[str, list[str]]:
        return {"GET": sorted(self._get), "POST": sorted(self._post)}


def build_router(service: CockpitService) -> Router:
    router = Router()

    # ------------------------------------------------------------- cockpit

    @router.get("/api/summary")
    def summary(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.cockpit_summary()

    @router.get("/api/runtime")
    def runtime(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.runtime_status()

    @router.get("/api/authority")
    def authority(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.authority_summary()

    # ---------------------------------------------------------- objectives

    @router.get("/api/objectives")
    def objectives(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {"objectives": service.list_objectives()}

    @router.get("/api/objective")
    def objective(query: dict[str, Any], body: dict[str, Any]) -> Any:
        identifier = query.get("id", "")
        if not identifier:
            raise UseCaseError("id is required")
        return service.get_objective(identifier)

    @router.post("/api/objectives/create")
    def create_objective(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.create_objective(body)

    @router.post("/api/objectives/transition")
    def transition_objective(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.transition_objective(
            str(body.get("id", "")), str(body.get("state", ""))
        )

    # --------------------------------------------------------------- tasks

    @router.get("/api/tasks")
    def tasks(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {"tasks": service.list_tasks(query.get("objective_id") or None)}

    @router.get("/api/tasks/board")
    def task_board(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.task_board(query.get("objective_id") or None)

    @router.post("/api/tasks/create")
    def create_task(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.create_task(body)

    @router.post("/api/tasks/transition")
    def transition_task(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.transition_task(
            str(body.get("id", "")),
            str(body.get("state", "")),
            reason=str(body.get("reason", "")),
        )

    @router.post("/api/tasks/dispatch")
    def dispatch_task(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.dispatch_task(str(body.get("id", "")))

    # --------------------------------------------------------------- inbox

    @router.get("/api/inbox")
    def inbox(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {"items": service.list_inbox(), "counts": service.inbox_counts()}

    @router.post("/api/inbox/create")
    def create_inbox(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.create_inbox_item(body)

    @router.post("/api/inbox/decide")
    def decide_inbox(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.decide_inbox_item(
            str(body.get("id", "")),
            str(body.get("disposition", "")),
            note=str(body.get("note", "")),
        )

    # ---------------------------------------------------------- execution

    @router.get("/api/execution")
    def execution(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {
            "status": service.execution_status(),
            "runs": service.recent_runs(),
        }

    @router.post("/api/execution/run")
    def execution_run(query: dict[str, Any], body: dict[str, Any]) -> Any:
        timeout = body.get("timeout")
        return service.run_prompt(
            str(body.get("prompt", "")),
            timeout=int(timeout) if timeout else None,
        )

    @router.get("/api/execution/status")
    def execution_status(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.run_status(str(query.get("run_id", "")))

    @router.get("/api/storage")
    def storage(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.storage_info()

    # ------------------------------------------------------------ ventures

    @router.get("/api/ventures")
    def ventures(query: dict[str, Any], body: dict[str, Any]) -> Any:
        rows = service.list_ventures()
        for row in rows:
            row["gates"] = service.gate_ladder(row)
        return {"ventures": rows}

    @router.get("/api/venture")
    def venture(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.venture_detail(str(query.get("id", "")))

    # -------------------------------------------------------- organization

    @router.get("/api/organization")
    def organization(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.organization()

    # -------------------------------------------------------------- memory

    @router.get("/api/memory")
    def memory(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.memory_index(
            section=query.get("section") or None, query=query.get("q") or None
        )

    @router.get("/api/memory/note")
    def memory_note(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.memory_note(str(query.get("path", "")))

    # ------------------------------------------------------------- metrics

    @router.get("/api/metrics")
    def metrics(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.metrics()

    # ----------------------------------------------------------- decisions

    @router.get("/api/decisions")
    def decisions(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {
            "decisions": service.list_decisions(),
            "status": service.decisions_status(),
        }

    # ------------------------------------------------------- vecyra program

    @router.get("/api/programme")
    def programme(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.kavi_programme()

    @router.get("/api/vecyra")
    def vecyra(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return service.vecyra_program()

    # ----------------------------------------------- telemetry and ledger

    @router.get("/api/ledger")
    def ledger(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {
            "ledger": service.execution_ledger(),
            "runs": service.execution_runs(50),
        }

    # ------------------------------------------------------------ evidence

    @router.get("/api/evidence")
    def evidence(query: dict[str, Any], body: dict[str, Any]) -> Any:
        return {
            "evidence": service.list_evidence(),
            "summary": service.evidence_summary(),
            "status": service.evidence_status(),
        }

    return router
