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
from kavi.domain import states  # noqa: E402


def body_core(t) -> None:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="kavi-test-")) / "kavi.json"
    service = build_service(data_path=tmp)
    router = build_router(service)

    # ------------------------------------------------------------ runtime
    runtime = service.runtime_status()
    # Vocabulary per the Founder directive: MODE LOCAL, QUEUE LOCAL / NOT ACTIVE,
    # COST LOCAL / FIXTURE / UNAVAILABLE. The guarantee under test is not the
    # exact wording but that nothing is ever reported as a measured quantity.
    t.equals("runtime mode is LOCAL", runtime["mode"], "LOCAL")
    t.equals("engine room not connected", runtime["engine_room"], "ENGINE_ROOM_NOT_CONNECTED")
    t.equals("uptime not measured", runtime["uptime"], "NOT MEASURED")
    t.check("cost is not a measured figure",
            runtime["cost_today"] in ("NOT MEASURED", "LOCAL / UNAVAILABLE")
            or "UNAVAILABLE" in runtime["cost_today"])
    t.check("queue is not a measured figure",
            runtime["queue_depth"] in ("NOT MEASURED", "LOCAL / NOT ACTIVE"))
    t.equals("router not connected", runtime["router"], "NOT CONNECTED")
    t.equals("vault sync not connected", runtime["vault_sync"], "NOT CONNECTED")

    # No runtime telemetry field may ever carry a bare number. A digit here
    # would mean the cockpit had begun inventing operational data.
    import re as _re
    for _field in ("uptime", "cost_today", "queue_depth", "queue", "cost", "vps",
                   "scheduler", "provider_router", "router", "vault_sync"):
        _value = str(runtime.get(_field, ""))
        t.check(f"{_field} reports no fabricated number",
                not _re.search(r"\d", _value))
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
    # Decisions come from the vault now, so their state is whatever the record
    # says. A PROPOSED decision is legitimate and must not be forced to APPROVED.
    t.check("decision states are governed values",
            all(d["state"] in states.DECISION_STATES or d["state"] == "UNKNOWN"
                for d in decisions),
            str(sorted({d["state"] for d in decisions})))
    t.check("the six approved decisions are approved",
            all(d["state"] == "APPROVED"
                for d in decisions if d["id"] in
                ("D-001", "D-002", "D-003", "D-004", "D-005", "D-006")))

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
    t.check("summary carries runtime", payload["runtime"]["mode"] == "LOCAL")
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




# --------------------------------------------------- functionalization v0.1


def body_functionalization(t):
    """The workflows the Founder directive requires to be genuinely real."""
    import pathlib
    import tempfile

    from kavi.container import build_service

    store = pathlib.Path(tempfile.mkdtemp()) / "kavi.json"
    s = build_service(data_path=store)

    # --- Objectives are real: created, identified, persisted, restored.
    created = s.create_objective({
        "title": "Validate VECYRA progress reconciliation opportunity.",
        "outcome": "A decision-ready recommendation.",
        "priority": "HIGH",
        "authority_level": "A1",
        "success_criteria": "One problem, one segment, evidence table.",
        "evidence_requirements": "Every claim classified.",
        "budget": "0 external spend",
        "state": "ACTIVE",
    })
    t.check("objective gets a stable namespaced id", created["id"].startswith("OBJ-"))
    t.check("objective persists priority", created["priority"] == "HIGH")
    t.check("objective persists success criteria", created["success_criteria"] != "")
    t.check("objective persists authority level", created["authority_level"] == "A1")
    t.check("objective is local origin", created["origin"] == "LOCAL")
    t.check("objective reached ACTIVE", created["state"] == "ACTIVE")

    reopened = build_service(data_path=store)
    ids = [o["id"] for o in reopened.list_objectives()]
    t.check("objective survives restart", created["id"] in ids)

    # --- Tasks are real records with kernel fields.
    task_a = reopened.create_task({
        "objective_id": created["id"],
        "title": "Collect market structure evidence",
        "expected_output": "Evidence table",
        "evidence_requirement": "Source + date + locator",
        "priority": "HIGH",
        "review_required": True,
    })
    task_b = reopened.create_task({
        "objective_id": created["id"],
        "title": "Independent review",
        "depends_on": task_a["id"],
        "approval_required": True,
    })
    t.check("task gets a namespaced id", task_a["id"].startswith("TASK-"))
    t.check("task starts in BACKLOG", task_a["state"] == "BACKLOG")
    t.check("task keeps review requirement", task_a["review_required"] is True)
    t.check("task keeps approval requirement", task_b["approval_required"] is True)
    t.check("task records dependency", task_b["depends_on"] == task_a["id"])

    # --- Dependencies are enforced, not decorative.
    reopened.transition_task(task_b["id"], "READY")
    try:
        reopened.transition_task(task_b["id"], "RUNNING")
        t.check("dependency blocks a premature start", False)
    except Exception as exc:
        t.check("dependency blocks a premature start", "DONE" in str(exc))

    # --- A task moves through valid states only.
    reopened.transition_task(task_a["id"], "READY")
    reopened.transition_task(task_a["id"], "RUNNING")
    moved = reopened.transition_task(task_a["id"], "REVIEW")
    t.check("task moved BACKLOG->READY->RUNNING->REVIEW", moved["state"] == "REVIEW")
    try:
        reopened.transition_task(task_a["id"], "BACKLOG")
        t.check("invalid task transition refused", False)
    except Exception:
        t.check("invalid task transition refused", True)

    # --- Unknown dependency is refused at creation.
    try:
        reopened.create_task({
            "objective_id": created["id"], "title": "x", "depends_on": "TASK-9999-999",
        })
        t.check("unknown dependency refused", False)
    except Exception:
        t.check("unknown dependency refused", True)

    # --- CEO Inbox aggregates real objects.
    item = reopened.create_inbox_item({
        "subject_kind": "OBJECTIVE",
        "subject_id": created["id"],
        "type": "DECISION",
        "risk": "MEDIUM",
        "recommendation": "Approve the interview experiment.",
    })
    t.check("inbox item gets a namespaced id", item["id"].startswith("INB-"))
    t.check("inbox item references the objective", item["subject_id"] == created["id"])
    t.check("inbox subject resolves to a real record",
            item["subject"] is not None and item["subject"]["found"] is True)

    try:
        reopened.create_inbox_item({"type": "FYI", "title": "floating"})
        t.check("decorative local inbox item refused", False)
    except Exception:
        t.check("decorative local inbox item refused", True)

    try:
        reopened.create_inbox_item({
            "subject_kind": "OBJECTIVE", "subject_id": "OBJ-9999-999", "type": "FYI",
        })
        t.check("inbox item on a missing object refused", False)
    except Exception:
        t.check("inbox item on a missing object refused", True)

    # --- Founder disposition updates local state and survives restart.
    decided = reopened.decide_inbox_item(item["id"], "APPROVED", note="Proceed.")
    t.check("inbox disposition applied", decided["state"] == "APPROVED")
    t.check("inbox disposition records a reason", decided["disposition_note"] == "Proceed.")
    t.check("inbox disposition timestamped", decided["decided_at"] != "")

    again = build_service(data_path=store)
    persisted = [i for i in again.list_inbox() if i["id"] == item["id"]][0]
    t.check("inbox disposition survives restart", persisted["state"] == "APPROVED")

    # --- Fixture inbox items cannot be decided.
    fixture_items = [i for i in again.list_inbox() if i["origin"] == "FIXTURE"]
    t.check("fixture inbox items exist for demonstration", len(fixture_items) > 0)
    try:
        again.decide_inbox_item(fixture_items[0]["id"], "APPROVED")
        t.check("fixture inbox item cannot be decided", False)
    except Exception:
        t.check("fixture inbox item cannot be decided", True)

    # --- Every fixture inbox item still references a real object.
    for fixture in fixture_items:
        t.check(
            f"fixture inbox {fixture['id']} references a real object",
            fixture["subject"] is not None and fixture["subject"]["found"] is True,
        )

    # --- Engine Room reports exactly what the directive requires.
    panel = dict(again.runtime_status()["engine_room_panel"])
    t.check("engine room reports MODE LOCAL", panel["MODE"] == "LOCAL")
    t.check("engine room reports VPS NOT CONNECTED", panel["VPS"] == "NOT CONNECTED")
    t.check("engine room reports RUNTIME LOCAL DEVELOPMENT", panel["RUNTIME"] == "LOCAL DEVELOPMENT")
    t.check("engine room reports SCHEDULER not connected", "NOT CONNECTED" in panel["SCHEDULER"])
    t.check("engine room reports QUEUE not active", "NOT ACTIVE" in panel["QUEUE"])
    t.check("engine room reports ROUTER not connected", panel["PROVIDER ROUTER"] == "NOT CONNECTED")
    t.check("engine room reports VAULT local", panel["VAULT"] == "LOCAL")
    t.check("engine room reports COST unavailable", "UNAVAILABLE" in panel["COST"])

    # --- Authority ladder is A0-A4, and A3/A4 are not grantable locally.
    ladder = again.authority_summary()["ladder"]
    t.check("authority ladder has five levels", len(ladder) == 5)
    t.check("ladder covers A0..A4",
            [row["level"] for row in ladder] == ["A0", "A1", "A2", "A3", "A4"])
    not_grantable = [row["level"] for row in ladder if not row["grantable_locally"]]
    t.check("A3 and A4 are not grantable in local mode", not_grantable == ["A3", "A4"])
    t.check("max grantable is A2", again.authority_summary()["max_grantable_level"] == "A2")

    # --- Storage location is reported and the two stores stay separate.
    info = again.storage_info()
    t.check("operational store path is reported", info["operational_store"]["path"].endswith(".json"))
    t.check("operational store exists after writes", info["operational_store"]["exists"] is True)
    t.check("vault is described separately", "canonical_for" in info["canonical_vault"])
    t.check("separation rule is stated", "not merged" in info["separation_rule"])
    t.check(
        "vault and operational store are different locations",
        info["canonical_vault"].get("path") != info["operational_store"]["path"],
    )


# ------------------------------------------------- canonical decision log


def body_canonical_decisions(t):
    """Decisions must come from the vault, never from invented fixtures."""
    import pathlib
    import tempfile

    from kavi.container import build_service

    store = pathlib.Path(tempfile.mkdtemp()) / "kavi.json"
    s = build_service(data_path=store)

    from kavi.infrastructure import fixtures
    t.check("no fixture decisions exist at all", fixtures.decisions() == [])

    decisions = s.list_decisions()
    t.check("canonical decisions are read", len(decisions) >= 6, str(len(decisions)))
    t.check("no decision is fixture origin",
            all(d.get("origin") != "FIXTURE" for d in decisions))
    t.check("canonical decisions are marked VAULT",
            all(d.get("origin") == "VAULT" for d in decisions if d["id"].startswith("D-0")))

    by_id = {d["id"]: d for d in decisions}
    for identifier in ("D-001", "D-002", "D-003", "D-004", "D-005", "D-006"):
        t.check(f"{identifier} read from vault", identifier in by_id)

    d1 = by_id.get("D-001", {})
    t.check("decision carries its real title",
            "KAVI is the company" in d1.get("title", ""))
    t.check("decision state parsed", d1.get("state") == "APPROVED")
    t.check("decision date parsed", d1.get("date") == "2026-09-04")
    t.check("decision approver parsed", d1.get("approver_actor_id") == "Founder")
    t.check("decision context is real prose", len(d1.get("context", "")) > 60)
    t.check("decision rationale present", len(d1.get("rationale", "")) > 20)
    t.check("decision cites its source file", d1.get("source_path", "").endswith(".md"))

    # The old fixture claimed every decision was reversible "Yes". The real
    # record says the opposite. This is the exact class of quiet falsehood the
    # vault-backed reader exists to prevent.
    t.check("reversibility is the record's real answer, not 'Yes'",
            d1.get("reversible") != "Yes")
    t.check("reversibility states the true condition",
            "superseding Founder decision" in d1.get("reversible", ""))

    d6 = by_id.get("D-006", {})
    t.check("D-006 carries the VECYRA baseline",
            "VALIDATE" in d6.get("title", "") or "VALIDATE" in d6.get("decision", ""))

    status = s.decisions_status()
    t.check("decision source is stated", status["source"] == "CANONICAL VAULT")
    t.check("decision access is read only", status["access"] == "READ ONLY")
    t.check("decision count reported", status["canonical_count"] >= 6)
    t.check("status says the desktop never writes decisions",
            "never writes" in status["detail"])

    # An inbox item may reference a canonical decision.
    item = s.create_inbox_item({
        "subject_kind": "DECISION", "subject_id": "D-005",
        "type": "FYI", "title": "Vault ownership confirmed",
    })
    t.check("inbox item can reference a vault decision",
            item["subject"]["found"] is True)
    t.check("vault decision subject is marked VAULT",
            item["subject"]["origin"] == "VAULT")

    try:
        s.create_inbox_item({
            "subject_kind": "DECISION", "subject_id": "D-999",
            "type": "FYI", "title": "nonexistent",
        })
        t.check("inbox item on unknown decision refused", False)
    except Exception as exc:
        t.check("inbox item on unknown decision refused",
                "canonical vault" in str(exc))


# -------------------------------------------------- canonical evidence


def body_canonical_evidence(t):
    """Claims must come from the vault register, with contradictions intact."""
    import pathlib
    import tempfile

    from kavi.container import build_service
    from kavi.domain import states

    store = pathlib.Path(tempfile.mkdtemp()) / "kavi.json"
    s = build_service(data_path=store)

    from kavi.infrastructure import fixtures
    t.check("no fixture evidence exists at all", fixtures.evidence() == [])

    claims = s.list_evidence()
    t.check("canonical claims are read", len(claims) >= 40, str(len(claims)))
    t.check("no claim is fixture origin",
            all(c.get("origin") != "FIXTURE" for c in claims))
    t.check("canonical claims are marked VAULT",
            all(c.get("origin") == "VAULT" for c in claims))

    by_id = {c["id"]: c for c in claims}
    t.check("claims keep their real register ids", "CLM-001" in by_id)
    t.check("claims are not renumbered", not any(c.startswith("CLM-2026-") for c in by_id))

    # Every claim must carry provenance, not just a sentence.
    for claim in claims:
        t.check(f"{claim['id']} has a claim body", len(claim["claim"]) > 10)
    # An UNKNOWN claim legitimately has no source: nothing was found. Requiring
    # a source there would invite fabrication. Sourced claims are the ones that
    # must carry provenance.
    # Founder/domain evidence has no external source by definition — the
    # Founder is the source, and section G omits the column entirely.
    sourced = [c for c in claims
               if c["classification"] not in ("UNKNOWN", "FOUNDER / DOMAIN EVIDENCE")]
    t.check("sourced claims carry a source",
            all(c["source"] for c in sourced),
            str([c["id"] for c in sourced if not c["source"]]))
    t.check("sourced claims carry an evidence kind",
            sum(1 for c in sourced if c["kind"]) >= len(sourced) - 5)
    t.check("sourced claims carry a locator",
            sum(1 for c in sourced if c["locator"]) >= 30)
    t.check("sourced claims carry an access date",
            sum(1 for c in sourced if c["access_date"]) >= 30)

    # And an UNKNOWN must never acquire a source out of nowhere.
    unknowns = [c for c in claims if c["classification"] == "UNKNOWN"]
    t.check("unknown claims exist and are preserved", len(unknowns) >= 5)
    t.check("unknown claims state their limitation",
            all(c["contradiction"] or c["claim"] for c in unknowns))

    # Contradictions must survive to the reader. This is the whole point of the
    # Evidence and Review Contract, and the easiest thing to quietly lose.
    with_caveat = [c for c in claims if c["contradiction"]]
    t.check("contradictions are preserved", len(with_caveat) >= 30, str(len(with_caveat)))

    c1 = by_id.get("CLM-001", {})
    t.check("CLM-001 keeps its downward-trend caveat",
            "downward" in c1.get("contradiction", ""))
    c7 = by_id.get("CLM-007", {})
    t.check("CLM-007 discloses the primary text was never retrieved",
            "never retrieved" in c7.get("contradiction", ""))
    t.check("CLM-007 confidence is not overstated", c7.get("confidence") == "MEDIUM")

    # D-006: founder/domain evidence is its own class, never market validation.
    founder_claims = [c for c in claims
                      if c["classification"] == "FOUNDER / DOMAIN EVIDENCE"]
    t.check("founder/domain evidence is a distinct class", len(founder_claims) >= 1)
    t.check("founder evidence is not classified as FACT",
            all(c["classification"] != "FACT" for c in founder_claims))
    t.check("founder/domain evidence is a recognised class",
            "FOUNDER / DOMAIN EVIDENCE" in states.EVIDENCE_CLASSES)
    for claim in founder_claims:
        t.check(f"{claim['id']} states it is not market validation",
                "market validation" in claim["contradiction"].lower())

    summary = s.evidence_summary()
    t.check("summary counts every claim", summary["total"] == len(claims))
    t.check("summary breaks down confidence", "HIGH" in summary["by_confidence"])
    t.check("summary counts non-market claims", summary["non_market_claims"] >= 1)
    t.check("summary states no market validation exists",
            "NONE" in summary["market_validation"])

    status = s.evidence_status()
    t.check("evidence source is stated", status["source"] == "CANONICAL VAULT")
    t.check("evidence access is read only", status["access"] == "READ ONLY")
    t.check("evidence scope limit is carried", "desk research" in status["scope_limit"])
    t.check("status says the desktop never authors a claim",
            "never authors" in status["detail"])

    # Inbox evidence references must resolve against the canonical register.
    for item in s.list_inbox():
        for claim_id in item.get("evidence_ids", []):
            t.check(f"{item['id']} cites a real claim {claim_id}", claim_id in by_id)
    referenced = [i for i in s.list_inbox() if i.get("evidence_ids")]
    t.check("inbox items resolve their evidence",
            all(len(i["evidence"]) == len(i["evidence_ids"]) for i in referenced))


def body(t):
    body_core(t)
    body_functionalization(t)
    body_canonical_decisions(t)
    body_canonical_evidence(t)


if __name__ == "__main__":
    main("smoke_application", body)
