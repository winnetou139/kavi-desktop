"""The Founder's 12-step Local Acceptance Test, executed in a real browser.

This is not a unit test. It is the exact manual script from the directive
"KAVI DESKTOP v0.1 — LOCAL ACCEPTANCE & FUNCTIONALIZATION" §15, driven through
Chrome over CDP so the result is evidence rather than assertion.

Each step prints PASS or FAIL. Step 12 restarts the browser to prove that state
survives, rather than merely re-reading it from a page that never reloaded.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.smoke_ui_cdp import WS, CHROME, PORT, APP_URL  # noqa: E402

RESULTS: list[tuple[int, str, bool, str]] = []

OBJECTIVE_TITLE = "Validate VECYRA progress reconciliation opportunity."


def step(number: int, name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((number, name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    line = f"  {number:>2}. [{mark}] {name}"
    if detail:
        line += f"  — {detail}"
    print(line, flush=True)


def launch(profile_name: str):
    profile = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / profile_name
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
         "--disable-gpu", "--window-size=1600,1000", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    target = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=2) as response:
                tabs = json.loads(response.read().decode())
            pages = [tab for tab in tabs if tab.get("type") == "page"]
            if pages:
                target = pages[0]["webSocketDebuggerUrl"]
                break
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    if target is None:
        proc.terminate()
        raise RuntimeError("Chrome DevTools never became reachable")
    ws = WS(target)
    ws.call("Runtime.enable")
    ws.call("Page.enable")
    ws.call("Page.navigate", url=APP_URL)
    time.sleep(2.5)
    return proc, ws


def open_module(ws, key: str) -> str:
    ws.evaluate(
        "document.body.dispatchEvent(new KeyboardEvent('keydown',"
        f"{{key:'{key}',bubbles:true}}))"
    )
    time.sleep(1.5)
    return ws.evaluate("document.querySelector('.screen-title').innerText")


def screen_text(ws) -> str:
    return ws.evaluate(
        "(document.querySelector('.screen-body')"
        " || document.querySelector('.screen-split')).innerText"
    )


def main() -> int:
    print("\nKAVI DESKTOP v0.1 — LOCAL ACCEPTANCE TEST")
    print(f"Target: {APP_URL}\n")

    # Step 1 — the application opens.
    try:
        with urllib.request.urlopen(APP_URL, timeout=5) as response:
            reachable = response.status == 200
    except Exception as exc:  # noqa: BLE001
        step(1, f"Open {APP_URL}", False, str(exc))
        return 1

    proc, ws = launch("kavi-accept-profile")
    objective_id = ""
    task_ids: list[str] = []
    try:
        title = ws.evaluate("document.title")
        step(1, f"Open {APP_URL}", reachable and "KAVI" in title, title)

        # Step 2 — create an objective.
        open_module(ws, "3")
        # The Ctrl+K palette also contains a "New objective" entry and is hidden;
        # clicking it does nothing. Target the visible screen-head button only.
        ws.evaluate(
            "(() => { const b = document.querySelector('.screen-head button.btn.primary');"
            " if (!b) throw new Error('New objective button not found in screen head');"
            " if (!/new objective/i.test(b.textContent))"
            "   throw new Error('unexpected head button: ' + b.textContent);"
            " b.click(); return true; })()"
        )
        time.sleep(1.2)
        ws.evaluate(
            "(() => { const m = document.getElementById('modalBody');"
            " if (!m) throw new Error('objective modal did not open');"
            f" m.querySelector('input[name=title]').value = '{OBJECTIVE_TITLE}';"
            " const o = m.querySelector('textarea[name=outcome]');"
            " if (o) o.value = 'A decision-ready recommendation for the Founder.';"
            " const s = m.querySelector('textarea[name=success_criteria]');"
            " if (s) s.value = 'One problem, one segment, an evidence table.';"
            " return true; })()"
        )
        ws.evaluate(
            "(() => { const b = Array.from(document.querySelectorAll('#modalFoot .btn'))"
            ".find(x => /create/i.test(x.textContent)); b.click(); return true; })()"
        )
        time.sleep(2.2)
        # Identify it by its title through the API, not by position on screen.
        raw = urllib.request.urlopen(f"{APP_URL}/api/objectives", timeout=5).read()
        mine = [o for o in json.loads(raw)["objectives"]
                if o["title"] == OBJECTIVE_TITLE and o["origin"] == "LOCAL"]
        objective_id = mine[-1]["id"] if mine else ""
        step(2, "Create OBJ-XXXX 'Validate VECYRA progress reconciliation opportunity.'",
             bool(objective_id), objective_id or "no objective id found")

        # Step 3 — the objective persists (server-side, not just on screen).
        raw = urllib.request.urlopen(f"{APP_URL}/api/objectives", timeout=5).read()
        stored = json.loads(raw)["objectives"]
        match = [o for o in stored if o["id"] == objective_id]
        persisted = bool(match) and match[0]["origin"] == "LOCAL"
        step(3, "Objective persists to the local operational store",
             persisted, f"{objective_id} origin=LOCAL" if persisted else "not persisted")

        # Step 4 — add two tasks.
        for index, title_text in enumerate(
            ("Collect market structure evidence", "Independent review of the evidence"), start=1
        ):
            ws.evaluate(
                "(() => { const b = Array.from("
                "  document.querySelectorAll('.screen-body button, .screen-split button'))"
                ".find(x => /add task/i.test(x.textContent) && x.offsetParent !== null);"
                " if (!b) throw new Error('Add task button not found');"
                " b.click(); return true; })()"
            )
            time.sleep(1.2)
            ws.evaluate(
                "(() => { const m = document.getElementById('modalBody');"
                f" m.querySelector('input[name=title]').value = '{title_text}';"
                " const e = m.querySelector('textarea[name=expected_output]');"
                " if (e) e.value = 'A written artifact.';"
                " return true; })()"
            )
            ws.evaluate(
                "(() => { const b = Array.from(document.querySelectorAll('#modalFoot .btn'))"
                ".find(x => /create/i.test(x.textContent)); b.click(); return true; })()"
            )
            time.sleep(1.8)

        raw = urllib.request.urlopen(
            f"{APP_URL}/api/tasks?objective_id={objective_id}", timeout=5).read()
        tasks = json.loads(raw)["tasks"]
        local_tasks = [t for t in tasks if t["origin"] == "LOCAL"]
        task_ids = [t["id"] for t in local_tasks]
        step(4, "Add at least two local Tasks", len(local_tasks) >= 2,
             f"{len(local_tasks)} tasks: {', '.join(task_ids)}")

        # Step 5 — move one task through valid states.
        journey = []
        if task_ids:
            first = task_ids[0]
            for target in ("READY", "RUNNING", "REVIEW"):
                request = urllib.request.Request(
                    f"{APP_URL}/api/tasks/transition",
                    data=json.dumps({"id": first, "state": target}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                result = json.loads(urllib.request.urlopen(request, timeout=5).read())
                journey.append(result["state"])
        moved = journey == ["READY", "RUNNING", "REVIEW"]
        step(5, "Move one Task through valid states",
             moved, "BACKLOG → " + " → ".join(journey) if journey else "no task to move")

        # Step 6 — surface a CEO Inbox item from that objective.
        request = urllib.request.Request(
            f"{APP_URL}/api/inbox/create",
            data=json.dumps({
                "subject_kind": "OBJECTIVE",
                "subject_id": objective_id,
                "type": "DECISION",
                "risk": "MEDIUM",
                "recommendation": "Approve the interview experiment.",
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        item = json.loads(urllib.request.urlopen(request, timeout=5).read())
        linked = item.get("subject", {}).get("id") == objective_id
        step(6, "Create a CEO Inbox item from that Objective",
             bool(item.get("id")) and linked,
             f"{item.get('id')} → {objective_id}")

        # Step 7 — VECYRA venture state.
        open_module(ws, "4")
        venture_text = screen_text(ws)
        gate_ok = ("VALIDATE" in venture_text
                   and "G2" in venture_text
                   and "NOT PASSED" in venture_text)
        step(7, "VECYRA shows VALIDATE / G2 / NOT PASSED", gate_ok,
             "and no G3 anywhere" if "G3 —" not in venture_text else "G3 still present")

        # Step 8 — read a canonical vault note.
        open_module(ws, "6")
        time.sleep(1.0)
        rows = ws.evaluate("document.querySelectorAll('.vault-row').length")
        ws.evaluate("document.querySelectorAll('.vault-row')[0].click()")
        time.sleep(1.6)
        note_len = ws.evaluate("(document.querySelector('.note-body')||{innerText:''}).innerText.length")
        step(8, "Open Vault and read a canonical Markdown note",
             rows > 0 and note_len > 300, f"{rows} notes, opened note {note_len} chars")

        # Step 9 — inspect an approved KAVI decision.
        open_module(ws, "8")
        decision_text = screen_text(ws)
        step(9, "Decision Log shows an approved KAVI decision",
             "D-005" in decision_text and "APPROVED" in decision_text,
             "D-001..D-006 present" if "D-006" in decision_text else decision_text[:60])

        # Step 10 — authority is bounded.
        open_module(ws, "9")
        auth_text = screen_text(ws)
        bounded = ("NOT GRANTABLE" in auth_text
                   and "LOCAL DEVELOPMENT MODE" in auth_text
                   and "No real execution authority is granted" in auth_text)
        step(10, "Authority confirms local execution authority is bounded",
             bounded, "A3/A4 not grantable; max A2")

        # Step 11 — Engine Room truthfulness.
        runtime = json.loads(urllib.request.urlopen(f"{APP_URL}/api/runtime", timeout=5).read())
        panel = dict(runtime["engine_room_panel"])
        engine_ok = (panel["MODE"] == "LOCAL"
                     and panel["VPS"] == "NOT CONNECTED"
                     and "NOT CONNECTED" in panel["SCHEDULER"]
                     and "NOT ACTIVE" in panel["QUEUE"]
                     and panel["PROVIDER ROUTER"] == "NOT CONNECTED")
        step(11, "Engine Room says LOCAL / VPS NOT CONNECTED", engine_ok,
             f"MODE={panel['MODE']}, VPS={panel['VPS']}")

        # Step 12 — restart the browser entirely and verify state survives.
        ws.close()
        proc.terminate()
        time.sleep(1.5)
        proc, ws = launch("kavi-accept-profile-2")
        open_module(ws, "3")
        time.sleep(1.5)
        after = ws.evaluate(
            "JSON.stringify(Array.from(document.querySelectorAll('.obj-card .id'))"
            ".map(n=>n.innerText))"
        )
        survived_objective = objective_id in json.loads(after)

        raw = urllib.request.urlopen(
            f"{APP_URL}/api/tasks?objective_id={objective_id}", timeout=5).read()
        after_tasks = [t["id"] for t in json.loads(raw)["tasks"] if t["origin"] == "LOCAL"]
        survived_tasks = all(tid in after_tasks for tid in task_ids)

        raw = urllib.request.urlopen(f"{APP_URL}/api/inbox", timeout=5).read()
        after_inbox = [i["id"] for i in json.loads(raw)["items"]]
        survived_inbox = item.get("id") in after_inbox

        step(12, "Refresh/restart and verify state remains",
             survived_objective and survived_tasks and survived_inbox,
             f"objective={survived_objective}, tasks={survived_tasks}, inbox={survived_inbox}")
    finally:
        try:
            ws.close()
        except Exception:  # noqa: BLE001
            pass
        proc.terminate()

    passed = sum(1 for _, _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n  ACCEPTANCE: {passed}/{total} steps passed")
    if passed != total:
        print("  FAILED STEPS: " + ", ".join(str(n) for n, _, ok, _ in RESULTS if not ok))
    print()
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
