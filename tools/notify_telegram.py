#!/usr/bin/env python3
"""Send the KAVI status readout to the Founder's Telegram.

Runs on the engine room, because the office network blocks api.telegram.org.
Used by the /status command and by scheduled digests.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.request

HOME = pathlib.Path.home()
ENV = HOME / ".hermes" / ".env"
CHAT_ID = "5437216857"


def token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("TELEGRAM_BOT_TOKEN not found")


def status_text() -> str:
    env = dict(os.environ, VECYRA_REPO=str(HOME / "vecyra-mirror"))
    done = subprocess.run(
        [sys.executable, str(HOME / "kavi-status" / "status.py")],
        capture_output=True, text=True, timeout=60, env=env,
    )
    return (done.stdout or done.stderr or "status unavailable").strip()


def send(text: str) -> bool:
    payload = json.dumps({"chat_id": CHAT_ID, "text": text}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token()}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response).get("ok", False)


if __name__ == "__main__":
    body = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else status_text()
    print("SENT" if send(body) else "FAILED")
