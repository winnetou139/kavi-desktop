"""Capture screenshots of every KAVI Desktop module over CDP."""

from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.smoke_ui_cdp import WS, CHROME, APP_URL  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "screenshots"
PORT = 9224

MODULES = [
    ("1", "01-command"), ("2", "02-ceo-inbox"), ("3", "03-objectives-tasks"),
    ("4", "04-ventures"), ("5", "05-organization"), ("6", "06-memory-vault"),
    ("7", "07-metrics-cost"), ("8", "08-decision-log"), ("9", "09-authority-policy"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    profile = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "kavi-shot-profile"
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={profile}", "--no-first-run", "--disable-gpu",
         "--window-size=1680,1020", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ws = None
    try:
        target = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=2) as response:
                    pages = [t for t in json.loads(response.read()) if t.get("type") == "page"]
                if pages:
                    target = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        if not target:
            print("no chrome target")
            return 1

        ws = WS(target)
        ws.call("Runtime.enable")
        ws.call("Page.enable")
        ws.call("Emulation.setDeviceMetricsOverride",
                width=1680, height=1020, deviceScaleFactor=1, mobile=False)
        ws.call("Page.navigate", url=APP_URL)
        time.sleep(3.5)

        for key, name in MODULES:
            ws.evaluate(
                f"document.dispatchEvent(new KeyboardEvent('keydown',{{key:'{key}',bubbles:true}}))"
            )
            time.sleep(1.6)
            if name == "06-memory-vault":
                ws.evaluate("document.querySelectorAll('.mem-note')[0]?.click()")
                time.sleep(1.2)
            shot = ws.call("Page.captureScreenshot", format="png")
            data = shot["result"]["data"]
            path = OUT / f"{name}.png"
            path.write_bytes(base64.b64decode(data))
            print(f"saved {path}")
        return 0
    finally:
        if ws:
            ws.close()
        chrome.terminate()
        try:
            chrome.wait(timeout=8)
        except subprocess.TimeoutExpired:
            chrome.kill()


if __name__ == "__main__":
    raise SystemExit(main())
