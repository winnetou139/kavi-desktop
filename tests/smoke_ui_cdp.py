"""Headless UI verification over CDP. Zero dependencies (stdlib websocket client).

Boots headless Chrome, loads the cockpit, walks every module, and asserts the
rendered text — proving the interface actually works rather than assuming it.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import socket
import struct
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.harness import main  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
APP_URL = os.environ.get("KAVI_URL", "http://127.0.0.1:8760")
PORT = 9223


# ------------------------------------------------------------ tiny ws client

class WS:
    def __init__(self, url: str) -> None:
        _, rest = url.split("://", 1)
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode())
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            buffer += self.sock.recv(4096)
        self.buffer = buffer.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _send(self, payload: bytes) -> None:
        header = bytearray([0x81])
        mask = os.urandom(4)
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _read(self, count: int) -> bytes:
        while len(self.buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    def _recv(self) -> dict:
        while True:
            first = self._read(2)
            opcode = first[0] & 0x0F
            length = first[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(length)
            if opcode == 1:
                return json.loads(payload.decode("utf-8"))

    def call(self, method: str, **params) -> dict:
        self.next_id += 1
        message_id = self.next_id
        self._send(json.dumps({"id": message_id, "method": method, "params": params}).encode())
        deadline = time.time() + 25
        while time.time() < deadline:
            message = self._recv()
            if message.get("id") == message_id:
                return message
        raise TimeoutError(method)

    def evaluate(self, expression: str):
        result = self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        payload = result.get("result", {})
        if "exceptionDetails" in payload:
            raise RuntimeError(payload["exceptionDetails"].get("text", "js error"))
        return payload.get("result", {}).get("value")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def body(t) -> None:
    try:
        urllib.request.urlopen(APP_URL, timeout=4)
    except Exception as exc:  # noqa: BLE001
        t.check("app server reachable", False, f"{APP_URL} — {exc}. Start it with: python run.py")
        return

    profile = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "kavi-cdp-profile"
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
         "--disable-gpu", "--window-size=1600,1000", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ws = None
    try:
        target = None
        for _ in range(50):
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
        ws.evaluate("window.__errs = []; window.addEventListener('error', e => window.__errs.push(e.message));")
        ws.call("Page.navigate", url=APP_URL)
        time.sleep(3.5)

        # ------------------------------------------------------------ shell
        t.equals("document title", ws.evaluate("document.title"), "KAVI — Founder Cockpit")
        mode = ws.evaluate("document.getElementById('modePill').innerText")
        t.check("titlebar states LOCAL MODE", "LOCAL MODE" in mode, mode)
        t.check("titlebar states engine room not connected", "NOT CONNECTED" in mode, mode)

        statusbar = ws.evaluate("document.getElementById('statusbar').innerText.replace(/\\n/g,' ')")
        for token in ("SCHEDULER", "QUEUE", "ROUTER", "VAULT SYNC", "UPTIME", "COST TODAY"):
            t.check(f"statusbar shows {token}", token in statusbar, statusbar[:180])
        t.check("statusbar reports NOT MEASURED", "NOT MEASURED" in statusbar)
        t.check("statusbar never claims online", "ONLINE" not in statusbar.upper(), statusbar[:180])
        t.check("statusbar has no fabricated cost", "$" not in statusbar, statusbar[:180])

        nav = ws.evaluate(
            "Array.from(document.querySelectorAll('.nav-item')).map(n=>n.innerText.trim().split('\\n')[0])"
        )
        for expected in ("Command", "CEO Inbox", "Objectives & Tasks", "Ventures",
                         "Organization", "Memory / Vault", "Metrics & Cost",
                         "Decision Log", "Authority & Policy"):
            t.check(f"rail lists {expected}", expected in nav, str(nav))
        t.equals("rail has exactly nine modules", len(nav), 9)

        founder = ws.evaluate("document.querySelector('.rail-foot').innerText.replace(/\\n/g,' ')")
        t.check("founder identity shown", "Founder" in founder, founder)
        t.check("human authority explicit", "EXPLICIT" in founder, founder)

        # ------------------------------------------------------ each module
        def open_module(key: str) -> str:
            ws.evaluate(
                f"document.dispatchEvent(new KeyboardEvent('keydown',{{key:'{key}',bubbles:true}}))"
            )
            time.sleep(1.4)
            return ws.evaluate("document.querySelector('.screen-title').innerText")

        t.equals("boots on Command", ws.evaluate("document.querySelector('.screen-title').innerText"), "Command")
        command_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        t.check("command warns LOCAL MODE", "LOCAL / DEVELOPMENT MODE" in command_text)
        t.check("command has objective intake",
                ws.evaluate("!!document.getElementById('objectiveQuick')"))
        t.check("command shows VECYRA venture", "VECYRA" in command_text, command_text[:200])
        t.check("command shows FIXTURE label", "FIXTURE" in command_text)

        t.equals("key 2 opens CEO Inbox", open_module("2"), "CEO Inbox")
        inbox_text = ws.evaluate("document.querySelector('.inbox-detail').innerText")
        t.check("inbox shows a recommendation", "RECOMMENDATION" in inbox_text.upper())
        t.check("inbox shows an evidence trail", "EVIDENCE TRAIL" in inbox_text.upper())
        t.check("inbox surfaces a contradiction", "Contradiction" in inbox_text)
        t.check("inbox shows authority condition", "AUTHORITY CONDITION" in inbox_text.upper())
        t.check("inbox actions disabled not simulated",
                ws.evaluate("Array.from(document.querySelectorAll('.action-row .btn')).every(b=>b.disabled)"))
        t.check("inbox list populated",
                ws.evaluate("document.querySelectorAll('.inbox-item').length") >= 4)

        t.equals("key 3 opens Objectives", open_module("3"), "Objectives & Tasks")
        t.check("objective cards render",
                ws.evaluate("document.querySelectorAll('.obj-card').length") >= 1)
        t.check("task board renders columns",
                ws.evaluate("document.querySelectorAll('.board .col').length") >= 6)
        board_text = ws.evaluate("document.querySelector('.board').innerText")
        for state in ("BACKLOG", "READY", "RUNNING", "BLOCKED", "REVIEW", "APPROVAL"):
            t.check(f"board column {state}", state in board_text)

        t.equals("key 4 opens Ventures", open_module("4"), "Ventures")
        venture_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        t.check("venture shows VALIDATE", "VALIDATE" in venture_text)
        t.check("venture shows G2", "G2" in venture_text)
        t.check("venture shows NOT PASSED", "NOT PASSED" in venture_text)
        t.check("venture commercial evidence unknown", "UNKNOWN" in venture_text)
        t.check("KAVI may not approve gate", "Founder approval" in venture_text)
        t.check("gate ladder renders",
                ws.evaluate("document.querySelectorAll('.gate').length") >= 8)
        t.check("exactly one current gate",
                ws.evaluate("document.querySelectorAll('.gate.current').length") == 1)

        t.equals("key 5 opens Organization", open_module("5"), "Organization")
        org_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        for division in ("INTEL", "PRODUCT", "BUILD", "GROW", "OPERATE", "CONTROL"):
            t.check(f"division {division} shown", division in org_text)
        t.check("actor kinds shown", "AGENT_INSTANCE" in org_text and "SERVICE_ACCOUNT" in org_text)
        t.check("provider marked as capability", "PROVIDER" in org_text)

        t.equals("key 6 opens Memory", open_module("6"), "Memory / Vault")
        t.check("vault notes listed",
                ws.evaluate("document.querySelectorAll('.mem-note').length") >= 20)
        mem_text = ws.evaluate("document.querySelector('.mem-body').innerText")
        t.check("vault marked read only", "READ ONLY" in mem_text.upper())
        t.check("vault sync not connected", "NOT CONNECTED" in mem_text.upper())
        ws.evaluate("document.querySelectorAll('.mem-note')[0].click()")
        time.sleep(1.2)
        note_text = ws.evaluate("document.querySelector('.mem-body').innerText")
        t.check("a vault note opens and shows content", len(note_text) > 300, str(len(note_text)))

        t.equals("key 7 opens Metrics", open_module("7"), "Metrics & Cost")
        metrics_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        t.check("metrics says no commercial figure", "No commercial figure exists" in metrics_text)
        t.check("metrics reports NOT MEASURED", "NOT MEASURED" in metrics_text)
        t.check("metrics reports UNKNOWN revenue", "UNKNOWN" in metrics_text)
        t.check("metrics separates fixture and local",
                "FIXTURE" in metrics_text.upper() and "LOCAL" in metrics_text.upper())
        t.check("metrics has no fabricated currency", "$" not in metrics_text, metrics_text[:200])

        t.equals("key 8 opens Decision Log", open_module("8"), "Decision Log")
        decision_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        for decision in ("D-001", "D-002", "D-003", "D-004", "D-005", "D-006"):
            t.check(f"{decision} listed", decision in decision_text)
        t.check("decisions show APPROVED state", "APPROVED" in decision_text)

        t.equals("key 9 opens Authority", open_module("9"), "Authority & Policy")
        auth_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        t.check("human authority explicit", "HUMAN AUTHORITY — EXPLICIT" in auth_text)
        t.check("separation of duties stated", "may not approve it" in auth_text)
        t.check("service account cannot approve", "Service Account" in auth_text)
        t.check("grants listed", "GNT-" in auth_text)
        t.check("revoked grant visible", "REVOKED" in auth_text)
        t.check("execution adapter shown", "null" in auth_text.lower())
        t.check("providers all not connected",
                auth_text.count("NOT CONNECTED") >= 5, str(auth_text.count("NOT CONNECTED")))

        # ------------------------------------------------- create objective
        open_module("1")
        ws.evaluate(
            "(() => { const i = document.getElementById('objectiveQuick');"
            " i.value = 'CDP verification objective'; return true; })()"
        )
        ws.evaluate("document.querySelector('.panel-head .btn.primary').click()")
        time.sleep(1.0)
        t.check("objective modal opens",
                ws.evaluate("document.getElementById('modalVeil').classList.contains('on')"))
        modal_text = ws.evaluate("document.getElementById('modalBody').innerText")
        for label in ("TITLE", "OUTCOME REQUIRED", "OWNER ACTOR ID", "PERMISSION GRANT ID",
                      "CONSTRAINTS", "EVIDENCE REQUIREMENTS", "INITIAL STATE"):
            t.check(f"objective form field {label}", label in modal_text.upper(), modal_text[:250])
        t.equals("title prefilled from intake",
                 ws.evaluate("document.querySelector('#modalBody input[name=title]').value"),
                 "CDP verification objective")

        ws.evaluate(
            "(() => { const b = document.getElementById('modalBody');"
            " const o = b.querySelector('textarea[name=outcome]');"
            " if (o) o.value = 'Proof the cockpit creates real records';"
            " const c = b.querySelector('textarea[name=constraints]');"
            " if (c) c.value = 'no external action';"
            " return true; })()"
        )
        ws.evaluate(
            "Array.from(document.querySelectorAll('#modalFoot .btn'))"
            ".find(b => b.innerText.includes('Create objective')).click()"
        )
        time.sleep(2.0)
        t.check("modal closed after create",
                not ws.evaluate("document.getElementById('modalVeil').classList.contains('on')"))
        t.equals("navigated to Objectives after create",
                 ws.evaluate("document.querySelector('.screen-title').innerText"),
                 "Objectives & Tasks")
        objectives_text = ws.evaluate("document.querySelector('.screen-body').innerText")
        t.check("new objective visible in Objectives",
                "CDP verification objective" in objectives_text, objectives_text[:300])
        t.check("new objective is not labelled FIXTURE",
                ws.evaluate(
                    "(() => { const c = Array.from(document.querySelectorAll('.obj-card'))"
                    ".find(n => n.innerText.includes('CDP verification objective'));"
                    " return c ? !c.innerText.includes('FIXTURE') : false; })()"
                ))

        # ------------------------------------------------------- palette
        ws.evaluate(
            "document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}))"
        )
        time.sleep(0.8)
        t.check("Ctrl+K opens the command palette",
                ws.evaluate("document.getElementById('paletteVeil').classList.contains('on')"))
        palette_text = ws.evaluate("document.getElementById('paletteBody').innerText")
        t.check("palette offers module jumps", "Ventures" in palette_text, palette_text[:200])
        t.check("palette offers objective creation", "New objective" in palette_text)
        ws.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        time.sleep(0.5)
        t.check("Escape closes the palette",
                not ws.evaluate("document.getElementById('paletteVeil').classList.contains('on')"))

        # ------------------------------------------------- console clean
        errors = ws.evaluate("window.__errs") or []
        t.check("no uncaught JS errors", len(errors) == 0, str(errors[:3]))

    finally:
        if ws:
            ws.close()
        chrome.terminate()
        try:
            chrome.wait(timeout=8)
        except subprocess.TimeoutExpired:
            chrome.kill()


if __name__ == "__main__":
    main("smoke_ui_cdp", body)
