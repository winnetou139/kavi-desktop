"""Application and API tests: use cases, routes, fixture/local separation."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.harness import main  # noqa: E402

from kavi.api.routes import build_router  # noqa: E402
from kavi.application.services import UseCaseError  # noqa: E402
from kavi.container import build_service  # noqa: E402


def body(t) -> None:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="kavi-test-")) / "kavi.json"
    service = build_service(data_path=tmp)
    router = build_router(service)

    # ------------------------------------------------------------ runtime
    runtime = service.runtime_status()
    t.equals("runtime mode is LOCAL", runtime["mode"], "LOCAL_MODE")
    t.equals("engine room not connected", runtime["engine_room"], "ENGINE_ROOM_NOT_CONNECTED")
    t.equals("uptime not measured", runtime["uptime"], "NOT MEASURED")
    t.equals("cost not measured", runtime["cost_today"], "NOT MEASURED")
    t.equals("queue not measured", runtime["queue_depth"], "NOT MEASURED")
    t.equals("router not connected", runtime["router"], "NOT CONNECTED")
    t.equals("vault sync not connected", runtime["vault_sync"], "NOT CONNECTED")
    t.check("no provider claims to be online",
            all(p["state"] == "NOT CONNECTED" for p in runtime["providers"]))
    t.equals("execution adapter not connected", runtime["execution"]["connected"], False)

    # ----------------------------------------------------- create objective
    created = service.create_objective({
        "title": "Test the cockpit end to end",
        "outcome": "A structured objective exists and is visible",
        "constraints": "no external action",
    })
    t.check("objective id namespaced", created["id"].startswith("OBJ-"))
    t.equals("created objective is LOCAL", created["origin"], "LOCAL")
    t.equals("created objective starts DRAFT", created["state"], "DRAFT")
    t.raises("blank title refused", UseCaseError, service.create_objective, {"title": "  "})

    listed = service.list_objectives()
    t.check("created objective is listed", any(o["id"] == created["id"] for o in listed))
    t.check("fixtures also listed", any(o["origin"] == "FIXTURE" for o in listed))

    # id must not collide with fixture OBJ-2026-001
    t.check("no id collision with fixtures",
            len({o["id"] for o in listed}) == len(listed))

    # ------------------------------------------------------ state machine
    activated = service.transition_objective(created["id"], "ACTIVE")
    t.equals("objective activated", activated["state"], "ACTIVE")
    t.raises("illegal objective transition refused", UseCaseError,
             service.transition_objective, created["id"], "DRAFT")

    # ---------------------------------------------------- fixture immutable
    t.raises("fixture objective cannot transition", UseCaseError,
             service.transition_objective, "OBJ-2026-001", "PAUSED")
    t.raises("fixture task cannot transition", UseCaseError,
             service.transition_task, "TASK-2026-001", "READY")

    # ---------------------------------------------------------- create task
    task = service.create_task({
        "objective_id": created["id"],
        "title": "Prove the board renders",
        "expected_output": "A card in BACKLOG",
    })
    t.check("task id namespaced", task["id"].startswith("TASK-"))
    t.equals("task starts BACKLOG", task["state"], "BACKLOG")
    t.equals("task is LOCAL", task["origin"], "LOCAL")
    t.raises("task needs an objective", UseCaseError,
             service.create_task, {"title": "orphan"})
    t.raises("task needs a real objective", UseCaseError,
             service.create_task, {"objective_id": "OBJ-9999-999", "title": "ghost"})

    moved = service.transition_task(task["id"], "READY")
    t.equals("task ready", moved["state"], "READY")
    t.raises("illegal task transition refused", UseCaseError,
             service.transition_task, task["id"], "DONE")

    detail = service.get_objective(created["id"])
    t.equals("objective carries its tasks", len(detail["tasks"]), 1)

    # ------------------------------------------------------------ dispatch
    result = service.dispatch_task(task["id"])
    t.equals("dispatch declined in LOCAL MODE", result["accepted"], False)
    t.equals("dispatch state DECLINED", result["state"], "DECLINED")
    t.check("dispatch explains itself", len(result["detail"]) > 20)

    # --------------------------------------------------------------- board
    board = service.task_board(created["id"])
    states_present = {c["state"]: len(c["tasks"]) for c in board["columns"]}
    t.equals("board has a READY card", states_present.get("READY"), 1)
    t.equals("board total", board["total"], 1)

    # -------------------------------------------------------------- inbox
    counts = service.inbox_counts()
    t.check("inbox has open items", counts["OPEN"] >= 1)
    items = service.list_inbox()
    t.check("inbox items carry resolved evidence",
            any(item.get("evidence") for item in items))
    t.check("all inbox fixtures labelled",
            all(item["origin"] == "FIXTURE" for item in items))

    # ------------------------------------------------------------ ventures
    ventures = service.list_ventures()
    vecyra = next(v for v in ventures if v["name"] == "VECYRA")
    t.equals("VECYRA stage matches the Founder baseline", vecyra["stage"], "VALIDATE")
    t.check("VECYRA gate is G2", vecyra["gate"].startswith("G2"))
    t.equals("VECYRA gate not passed", vecyra["gate_status"], "NOT PASSED")
    t.equals("commercial evidence unknown", vecyra["commercial_evidence"],
             "UNKNOWN / REQUIRES VALIDATION")

    ladder = service.gate_ladder(vecyra)
    current = [g for g in ladder if g["position"] == "current"]
    t.equals("exactly one current gate", len(current), 1)
    t.equals("current gate is G2", current[0]["gate"], "G2")
    t.equals("G0 and G1 shown passed",
             [g["position"] for g in ladder[:2]], ["passed", "passed"])

    # ------------------------------------------------------------ evidence
    summary = service.evidence_summary()
    t.check("evidence counted", summary["total"] >= 8)
    t.check("unknowns are represented", summary["by_classification"]["UNKNOWN"] >= 2)
    t.check("contradictions preserved", summary["with_contradiction"] >= 5)

    # ----------------------------------------------------------- authority
    authority = service.authority_summary()
    t.equals("human authority explicit", authority["human_authority"], "EXPLICIT")
    t.equals("emergency stop unavailable in local mode",
             authority["emergency_stop"]["available"], False)
    t.check("separation-of-duties rules present", len(authority["rules"]) >= 4)
    service_accounts = [a for a in authority["actors"] if a["kind"] == "SERVICE_ACCOUNT"]
    t.check("no service account may approve",
            all(not a["may_approve"] for a in service_accounts))
    providers = [a for a in authority["actors"] if a["kind"] in ("PROVIDER", "TOOL")]
    t.check("no provider or tool may approve",
            all(not a["may_approve"] for a in providers))

    # ------------------------------------------------------------- metrics
    metrics = service.metrics()
    t.equals("revenue unknown", metrics["commercial"]["revenue"], "UNKNOWN / REQUIRES VALIDATION")
    t.equals("provider cost not measured", metrics["commercial"]["provider_cost"], "NOT MEASURED")
    t.check("records split fixture from local",
            metrics["records"]["objectives"]["local"] >= 1
            and metrics["records"]["objectives"]["fixture"] >= 1)

    # -------------------------------------------------------------- vault
    vault = service.vault.status()
    t.equals("vault access is read only", vault["access"], "READ ONLY")
    t.equals("vault sync not connected", vault["sync"], "NOT CONNECTED")
    if vault["available"]:
        t.check("vault notes indexed", vault["note_count"] > 0)
        index = service.memory_index()
        t.check("memory index returns notes", len(index["notes"]) > 0)
        t.check("memory sections listed", len(index["sections"]) > 0)
        first = index["notes"][0]["path"]
        note = service.memory_note(first)
        t.check("note content readable", len(note["content"]) > 0)
        t.equals("note is read only", note["access"], "READ ONLY")
        t.raises("path traversal refused", UseCaseError,
                 service.memory_note, "../../../etc/passwd")
        t.raises("absolute path refused", UseCaseError,
                 service.memory_note, "C:/Windows/win.ini")
    else:
        t.check("vault absence reported honestly", vault["detail"].startswith("Canonical vault not found"))

    # ---------------------------------------------------------- decisions
    decisions = service.list_decisions()
    t.check("D-006 present", any(d["id"] == "D-006" for d in decisions))
    t.check("all fixture decisions approved",
            all(d["state"] == "APPROVED" for d in decisions))

    # ------------------------------------------------------ organization
    org = service.organization()
    t.equals("six divisions", len(org["divisions"]), 6)
    t.check("organization disclaims permanent agents", "abstraction" in org["note"])

    # -------------------------------------------------------------- routes
    expected_get = [
        "/api/summary", "/api/runtime", "/api/authority", "/api/objectives",
        "/api/objective", "/api/tasks", "/api/tasks/board", "/api/inbox",
        "/api/ventures", "/api/venture", "/api/organization", "/api/memory",
        "/api/memory/note", "/api/metrics", "/api/decisions", "/api/evidence",
    ]
    paths = router.paths()
    for path in expected_get:
        t.check(f"GET {path} registered", path in paths["GET"])
    for path in ["/api/objectives/create", "/api/objectives/transition",
                 "/api/tasks/create", "/api/tasks/transition", "/api/tasks/dispatch"]:
        t.check(f"POST {path} registered", path in paths["POST"])

    handler = router.resolve("GET", "/api/summary")
    payload = handler({}, {})
    t.check("summary carries vocabularies", "vocabularies" in payload)
    t.check("summary carries runtime", payload["runtime"]["mode"] == "LOCAL_MODE")
    t.check("summary is JSON serializable", isinstance(json.dumps(payload), str))

    # ------------------------------------------------------- persistence
    reopened = build_service(data_path=tmp)
    persisted = reopened.list_objectives()
    t.check("local objective survives restart",
            any(o["id"] == created["id"] for o in persisted))
    t.check("restart does not duplicate fixtures",
            len([o for o in persisted if o["origin"] == "FIXTURE"]) == 1)

    # ----------------------------------------------- fixtures can be hidden
    clean = build_service(data_path=tmp, include_fixtures=False)
    t.check("no fixture rows when disabled",
            all(o["origin"] == "LOCAL" for o in clean.list_objectives()))
    t.check("local rows still present without fixtures",
            len(clean.list_objectives()) >= 1)


main("smoke_application", body)
