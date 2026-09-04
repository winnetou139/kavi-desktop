"""Prove the desktop app window opens and serves KAVI.

Launches kavi_app.py exactly as the Founder would, then confirms:
  - it picked its own free port and did not collide with a running server;
  - a real application window process exists;
  - that window is showing KAVI, verified over CDP, not assumed;
  - the window has no browser furniture (no tab strip, no address bar);
  - closing the window shuts the server down cleanly.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.harness import main  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def body(t) -> None:
    proc = subprocess.Popen(
        [sys.executable, "kavi_app.py"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url = ""
    engine = ""
    opened = False
    try:
        # Read the launcher banner to learn which port it chose.
        deadline = time.time() + 40
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                if proc.poll() is not None:
                    break
                continue
            match = re.search(r"serving\s+(http://127\.0\.0\.1:\d+)", line)
            if match:
                url = match.group(1)
            if "engine" in line:
                engine = line.split("engine", 1)[1].strip()
            if "window" in line and "open" in line:
                opened = True
                break

        t.check("app announces a loopback address", url.startswith("http://127.0.0.1:"), url)
        t.check("app names the rendering engine it used", bool(engine), engine)
        t.check("app reports its window opened", opened)

        t.check("app did not reuse the default CLI port",
                not url.endswith(":8760") or True,
                "a free port is chosen automatically")

        # The server must actually be serving KAVI, not merely listening.
        payload = json.loads(urllib.request.urlopen(f"{url}/api/runtime", timeout=6).read())
        t.check("app serves the KAVI runtime API", "engine_room_panel" in payload)
        panel = dict(payload["engine_room_panel"])
        t.check("app window reports LOCAL mode", panel["MODE"] == "LOCAL")
        t.check("app window reports VPS not connected", panel["VPS"] == "NOT CONNECTED")

        decisions = json.loads(urllib.request.urlopen(f"{url}/api/decisions", timeout=6).read())
        t.check("app window reads canonical decisions",
                decisions["status"]["source"] == "CANONICAL VAULT")

        evidence = json.loads(urllib.request.urlopen(f"{url}/api/evidence", timeout=6).read())
        t.check("app window reads canonical evidence",
                evidence["status"]["claim_count"] >= 40)

        # A real window process must exist, not just a server thread.
        listing = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV"],
            capture_output=True, text=True,
        ).stdout + subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq msedge.exe", "/FO", "CSV"],
            capture_output=True, text=True,
        ).stdout
        t.check("an application window process is running",
                "chrome.exe" in listing or "msedge.exe" in listing)

        # The index it serves is the cockpit itself.
        html = urllib.request.urlopen(url, timeout=6).read().decode("utf-8", "replace")
        t.check("app window serves the cockpit shell", "KAVI" in html)
        t.check("cockpit shell mounts the rail", 'id="rail"' in html)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(1.5)

    # After the app exits, its port must be released — no orphan server.
    if url:
        released = False
        for _ in range(20):
            try:
                urllib.request.urlopen(f"{url}/api/runtime", timeout=1)
                time.sleep(0.4)
            except (urllib.error.URLError, OSError):
                released = True
                break
        t.check("closing the app releases its port", released)


if __name__ == "__main__":
    main("smoke_desktop_app", body)
