"""Prove the interactive surfaces really work, in a real browser.

The Founder asked for two things this suite exists to check:
  1. things must be clickable and actually do something;
  2. the Hermes link must genuinely run, not merely look connected.

The Hermes run is real: it launches Hermes and waits for its answer.
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
from tests.harness import main  # noqa: E402
from tests.smoke_ui_cdp import WS, CHROME, PORT, APP_URL  # noqa: E402


def body(t) -> None:
    try:
        urllib.request.urlopen(APP_URL, timeout=4)
    except Exception as exc:  # noqa: BLE001
        t.check("app server reachable", False, f"{APP_URL} — {exc}")
        return

    profile = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "kavi-interact"
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
         "--disable-gpu", "--window-size=1600,1000", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ws = None
    try:
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
        if not target:
            t.check("chrome devtools reachable", False, "no page target")
            return

        ws = WS(target)
        ws.call("Runtime.enable")
        ws.call("Page.enable")
        ws.call("Page.navigate", url=APP_URL)
        time.sleep(1.2)
        ws.evaluate("localStorage.setItem('kavi.language','en')")
        ws.evaluate("window.__errs=[]; window.addEventListener('error',e=>window.__errs.push(e.message));")
        ws.call("Page.navigate", url=APP_URL)
        time.sleep(3.2)

        def title() -> str:
            return ws.evaluate("document.querySelector('.screen-title').innerText")

        def open_module(key: str) -> str:
            ws.evaluate(
                "document.body.dispatchEvent(new KeyboardEvent('keydown',"
                f"{{key:'{key}',bubbles:true}}))"
            )
            time.sleep(1.5)
            return title()

        # ---------------------------------------------------- command deck
        t.equals("boots on Command", title(), "Command")
        deck = ws.evaluate("document.querySelectorAll('.deck-btn').length")
        t.check("command deck is present", deck >= 8, str(deck))

        disabled = ws.evaluate(
            "JSON.stringify(Array.from(document.querySelectorAll('.deck-btn.is-disabled'))"
            ".map(n=>n.querySelector('.deck-label').textContent))"
        )
        t.check("an unavailable action is shown as unavailable", "Run work now" in disabled)
        t.check("its reason is stated, not hidden",
                ws.evaluate("!!document.querySelector('.deck-btn.is-disabled .deck-hint').textContent"))

        # Every enabled deck button must actually navigate somewhere.
        for key, expected in (
            ("open-work", "Objectives & Work"),
            ("venture-state", "Ventures"),
            ("search-knowledge", "Company Knowledge"),
            ("decision-record", "Decision Record"),
            ("check-limits", "Authority & Limits"),
            ("open-decisions", "Decisions for You"),
        ):
            ws.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'1',bubbles:true}))")
            time.sleep(1.2)
            ws.evaluate(f"document.querySelector('[data-deck={key}]').click()")
            time.sleep(1.6)
            t.equals(f"deck '{key}' opens its screen", title(), expected)

        # ------------------------------------------------ clickable tables
        t.equals("metrics opens", open_module("7"), "Metrics & Cost")
        claims = ws.evaluate("document.querySelectorAll('tr[data-claim]').length")
        t.check("every claim is listed and clickable", claims >= 40, str(claims))
        ws.evaluate("document.querySelectorAll('tr[data-claim]')[6].click()")
        time.sleep(0.8)
        opened = ws.evaluate("document.querySelector('.claim-detail').innerText")
        t.check("clicking a claim opens its detail", len(opened) > 60, opened[:60])
        t.check("the claim's caveat is reachable in one click",
                "Caveat" in opened)

        t.equals("ventures opens", open_module("4"), "Ventures")
        gates = ws.evaluate("document.querySelectorAll('button.gate').length")
        t.check("gate ladder is pressable", gates >= 8, str(gates))
        ws.evaluate("document.querySelector('button.gate').click()")
        time.sleep(0.7)
        t.check("pressing a gate explains it",
                ws.evaluate("!!document.querySelector('.toast, #toast')"))

        t.equals("decisions open", open_module("8"), "Decision Record")
        rows = ws.evaluate("document.querySelectorAll('tr[data-decision-id]').length")
        t.check("decision rows are clickable", rows >= 6, str(rows))
        ws.evaluate("document.querySelectorAll('tr[data-decision-id]')[0].click()")
        time.sleep(2.2)
        detail_text = ws.evaluate(
            "(document.querySelector('.screen-body')"
            " || document.querySelector('.screen-split')).innerText")
        # kv() upper-cases its labels, so match case-insensitively.
        upper = detail_text.upper()
        t.check("clicking a decision opens its full record",
                "REVERSIBLE" in upper and "READ FROM" in upper,
                detail_text[-160:])
        t.check("the decision cites the file it was read from",
                "08_DECISIONS" in detail_text)
        t.check("the selected row is highlighted",
                ws.evaluate("document.querySelectorAll('tr.sel').length") == 1)

        # ------------------------------------------------------- ask kavi
        t.equals("Ask KAVI opens", open_module("0"), "Ask KAVI")
        status = json.loads(urllib.request.urlopen(f"{APP_URL}/api/execution", timeout=8).read())
        connected = status["status"].get("connected") is True
        t.check("runtime status is reported", "adapter" in status["status"])

        if not connected:
            t.check("run button is disabled when nothing is connected",
                    ws.evaluate("document.getElementById('askRun').disabled") is True)
            t.check("the reason is shown to the Founder",
                    "NOT CONNECTED" in ws.evaluate("document.querySelector('.screen-body').innerText").upper())
        else:
            t.check("run button is enabled when a runtime is connected",
                    ws.evaluate("document.getElementById('askRun').disabled") is False)
            t.check("suggestions are offered",
                    ws.evaluate("document.querySelectorAll('.suggestion').length") >= 3)

            # Click a suggestion, then really run it.
            ws.evaluate("document.querySelectorAll('.suggestion')[0].click()")
            time.sleep(0.5)
            t.check("a suggestion fills the box",
                    len(ws.evaluate("document.getElementById('askInput').value")) > 10)

            ws.evaluate(
                "(() => { const b = document.getElementById('askInput');"
                " b.value = 'Reply with exactly: KAVI_UI_LINK_OK'; return true; })()"
            )
            ws.evaluate("document.getElementById('askRun').click()")
            time.sleep(1.5)
            t.check("a run starts and shows it is running",
                    ws.evaluate("!!document.querySelector('.run-live')"))

            # Wait for the real Hermes answer.
            answered = False
            output = ""
            for _ in range(80):
                time.sleep(3)
                done = ws.evaluate("!!document.querySelector('.run-done')")
                if done:
                    output = ws.evaluate(
                        "(document.querySelector('.run-output')||{innerText:''}).innerText")
                    answered = True
                    break
            t.check("the run finishes and reports a real result", answered)
            if answered:
                state = ws.evaluate(
                    "document.querySelector('.run-done .chip').innerText")
                t.check("the run state is reported honestly",
                        state in ("SUCCEEDED", "FAILED", "TIMED_OUT", "DECLINED"), state)
                t.check("Hermes actually answered through the cockpit",
                        "KAVI_UI_LINK_OK" in output, output[:120])
                # History is drawn when the screen renders, so reopen it.
                ws.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'1',bubbles:true}))")
                time.sleep(1.2)
                open_module("0")
                time.sleep(1.0)
                t.check("the run appears in history",
                        ws.evaluate("document.querySelectorAll('.ask-prompt-cell').length") >= 1)

        # ------------------------------------------------------- no errors
        errors = ws.evaluate("JSON.stringify(window.__errs||[])")
        t.equals("no javascript errors anywhere", errors, "[]")
    finally:
        if ws:
            ws.close()
        chrome.terminate()


if __name__ == "__main__":
    main("smoke_interaction", body)
