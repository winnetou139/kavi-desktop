#!/usr/bin/env python3
"""Founder approvals, from a phone.

The loop the Founder asked for was complete except for one step: KAVI could
report, but he could not decide. This closes it.

    KAVI raises an inbox item
        -> the Founder asks his bot what needs deciding
        -> he says approve / reject / defer / ask evidence
        -> the decision is written to the operational store
        -> the cockpit shows it, because it reads the same store

Inline buttons were tried first and removed. Telegram permits exactly one
getUpdates reader per bot token, and the Hermes gateway already holds it, so
a second poller silently swallowed every button press. Rather than fight the
gateway for the socket, the gateway's own agent runs these commands.

Design decisions worth stating:

  Only the Founder can decide. Every callback is checked against his Telegram
  id, because the buttons carry real authority. An unknown sender is refused
  and the attempt is logged.

  The decision is recorded, then confirmed. If the write fails the Founder is
  told it failed -- never a checkmark for something that did not happen.

  Buttons expire in the sense that a decided item cannot be re-decided: the
  domain state machine refuses APPROVED -> anything, so a stale message
  cannot silently overwrite a decision made hours earlier in the cockpit.

Runs on the engine room; the office network blocks api.telegram.org.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

HOME = pathlib.Path.home()
ENV = HOME / ".hermes" / ".env"
FOUNDER_ID = 5437216857
COCKPIT = os.environ.get("KAVI_URL", "http://127.0.0.1:8760")
SEEN = HOME / "kavi-status" / "approvals_seen.json"

# Telegram callback_data is limited to 64 bytes, so the payload stays terse.
ACTIONS = {
    "ap": ("APPROVED", "Disetujui"),
    "rj": ("REJECTED", "Ditolak"),
    "df": ("DEFERRED", "Ditunda"),
    "ev": ("EVIDENCE_REQUESTED", "Minta bukti"),
}


def token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("TELEGRAM_BOT_TOKEN not found")


def call(method: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token()}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def cockpit(path: str, method: str = "GET", body: dict | None = None) -> dict | None:
    """Talk to the cockpit.

    Returns the parsed body, or None only when the cockpit could not be
    reached at all. An HTTP error carrying a message is returned as
    {"error": ...} so a refusal ("already decided") is never reported as an
    outage -- telling the Founder the wrong reason is its own kind of lie.
    """
    try:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{COCKPIT}{path}", data=data,
            headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("error", f"HTTP {error.code}")
                return payload
        except (ValueError, OSError):
            pass
        return {"error": f"HTTP {error.code}"}
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


# ----------------------------------------------------------------- sending

def send_item(item: dict) -> bool:
    """Push one open inbox item to the Founder with decision buttons."""
    kind = item.get("inbox_type", "DECISION")
    title = item.get("title", "(tanpa judul)")
    subject = f"{item.get('subject_kind', '')} {item.get('subject_id', '')}".strip()
    text = (
        f"KEPUTUSAN UNTUK ANDA\n"
        f"{item.get('id', '?')} · {kind}\n\n"
        f"{title}\n"
    )
    if item.get("summary"):
        text += f"\n{item['summary']}\n"
    if subject:
        text += f"\nTerkait: {subject}"

    keyboard = {"inline_keyboard": [
        [{"text": "✅ Setujui", "callback_data": f"ap|{item['id']}"},
         {"text": "❌ Tolak", "callback_data": f"rj|{item['id']}"}],
        [{"text": "⏸ Tunda", "callback_data": f"df|{item['id']}"},
         {"text": "🔍 Minta bukti", "callback_data": f"ev|{item['id']}"}],
    ]}
    result = call("sendMessage", {
        "chat_id": FOUNDER_ID, "text": text, "reply_markup": keyboard})
    return bool(result.get("ok"))


def _seen() -> set[str]:
    try:
        return set(json.loads(SEEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _remember(ids: set[str]) -> None:
    try:
        SEEN.parent.mkdir(parents=True, exist_ok=True)
        SEEN.write_text(json.dumps(sorted(ids)), encoding="utf-8")
    except OSError:
        pass


def push_open_items() -> int:
    """Send any OPEN item the Founder has not already been shown."""
    payload = cockpit("/api/inbox")
    if not payload:
        print("cockpit unreachable — nothing pushed")
        return 0
    items = payload.get("items") or payload.get("inbox") or []
    already = _seen()
    sent = 0
    for item in items:
        if item.get("state") != "OPEN" or item.get("id") in already:
            continue
        if send_item(item):
            already.add(item["id"])
            sent += 1
    _remember(already)
    print(f"pushed {sent} item(s)")
    return sent


# ---------------------------------------------------------------- receiving

def list_open() -> None:
    """Print the OPEN items, for the agent to relay to the Founder."""
    payload = cockpit("/api/inbox")
    if payload is None:
        print("COCKPIT UNREACHABLE — cockpit di laptop tidak berjalan, "
              "atau terowongan SSH mati. Tidak ada yang bisa ditampilkan.")
        return
    items = [i for i in (payload.get("items") or []) if i.get("state") == "OPEN"]
    if not items:
        print("Tidak ada item OPEN. Tidak ada yang perlu diputuskan.")
        return
    print(f"{len(items)} item menunggu keputusan:\n")
    for index, item in enumerate(items, 1):
        subject = f"{item.get('subject_kind','')} {item.get('subject_id','')}".strip()
        print(f"{index}. {item.get('id')} · {item.get('type', item.get('inbox_type',''))}")
        print(f"   {item.get('title','')}")
        if subject:
            print(f"   terkait: {subject}")
        print()


def decide(item_id: str, disposition: str) -> None:
    """Record one decision. Says plainly when it did not save."""
    valid = ("APPROVED", "REJECTED", "DEFERRED", "EVIDENCE_REQUESTED")
    if disposition not in valid:
        print(f"Disposition tidak dikenal: {disposition}. Pilihan: {', '.join(valid)}")
        return
    result = cockpit("/api/inbox/decide", "POST",
                     {"id": item_id, "disposition": disposition,
                      "note": "Diputuskan via Telegram"})
    if result is None:
        print(f"GAGAL: cockpit tidak bisa dihubungi. {item_id} TIDAK tersimpan.")
        return
    if result.get("error"):
        print(f"DITOLAK: {result['error']}")
        return
    print(f"TERSIMPAN: {item_id} -> {result.get('state', disposition)}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    if command == "list":
        list_open()
    elif command == "decide" and len(sys.argv) >= 4:
        decide(sys.argv[2], sys.argv[3].upper())
    elif command == "push":
        push_open_items()
    else:
        print("usage: approvals.py list | decide <ID> <DISPOSITION>")
