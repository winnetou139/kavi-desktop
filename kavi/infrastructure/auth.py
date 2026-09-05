"""Authentication for the cockpit.

Until now the cockpit was safe only because it was bound to 127.0.0.1. Putting
it on a public host without a login would expose the entire canonical vault --
doctrine, evidence register, decisions -- to anyone who learned the address.

This is deliberately small and boring, because auth code that is clever is
auth code that is wrong:

  - one password, hashed with PBKDF2-SHA256 and a per-install salt;
  - the plaintext password is never stored and never logged;
  - sessions are opaque 32-byte tokens in an HttpOnly, SameSite=Strict cookie;
  - constant-time comparison everywhere a secret is checked;
  - failed attempts are rate limited per source address;
  - LOCAL MODE (loopback bind, no password set) stays open, so nothing about
    the desktop workflow changes.

What this is NOT: multi-user, role-based, or an identity provider. There is
one Founder. Adding users would add attack surface for a need that does not
exist.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import threading
import time
from typing import Any

# Cost chosen so a login takes ~100ms on this class of machine: slow enough to
# make offline brute force expensive, fast enough that the Founder does not
# notice.
ITERATIONS = 240_000
SESSION_TTL = 14 * 24 * 3600        # a fortnight; he should not log in daily
MAX_ATTEMPTS = 8
ATTEMPT_WINDOW = 900                # 15 minutes

_lock = threading.Lock()
_sessions: dict[str, float] = {}
_attempts: dict[str, list[float]] = {}


def _config_path() -> pathlib.Path:
    base = os.environ.get("KAVI_DATA_DIR") or (
        pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
        / "kavi-desktop")
    return pathlib.Path(base) / "auth.json"


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


class Auth:
    """One-password gate. Open in LOCAL MODE, closed when a password is set."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else _config_path()

    # ------------------------------------------------------------- state

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def enabled(self) -> bool:
        """True when a password has been set. No password means LOCAL MODE."""
        record = self._load()
        return bool(record.get("hash") and record.get("salt"))

    def describe(self) -> dict[str, Any]:
        if not self.enabled():
            return {
                "enabled": False,
                "mode": "LOCAL MODE",
                "detail": (
                    "No password is set, so the cockpit is open. This is only "
                    "safe while it is bound to 127.0.0.1. Set a password "
                    "before exposing it on any network."
                ),
            }
        return {
            "enabled": True,
            "mode": "PASSWORD REQUIRED",
            "sessions_active": len(self._live_sessions()),
            "detail": "A password is required. Sessions last 14 days.",
        }

    # ---------------------------------------------------------- password

    def set_password(self, password: str) -> None:
        """Store a new password. The plaintext is never written anywhere."""
        password = (password or "").strip()
        if len(password) < 10:
            raise ValueError(
                "Use at least 10 characters. This guards the whole vault.")
        salt = secrets.token_bytes(16)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "salt": base64.b64encode(salt).decode(),
            "hash": base64.b64encode(_hash(password, salt)).decode(),
            "iterations": ITERATIONS,
            "set_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        with _lock:
            _sessions.clear()       # a new password invalidates old sessions

    def verify(self, password: str, source: str = "") -> bool:
        """Check a password. Constant time, and rate limited per source."""
        if self._rate_limited(source):
            return False
        record = self._load()
        if not record.get("hash"):
            return False
        try:
            salt = base64.b64decode(record["salt"])
            expected = base64.b64decode(record["hash"])
        except (ValueError, KeyError):
            return False
        ok = hmac.compare_digest(_hash(password or "", salt), expected)
        if not ok:
            self._record_failure(source)
        return ok

    # ---------------------------------------------------------- sessions

    def _live_sessions(self) -> dict[str, float]:
        now = time.time()
        with _lock:
            for token, expiry in list(_sessions.items()):
                if expiry < now:
                    del _sessions[token]
            return dict(_sessions)

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        with _lock:
            _sessions[token] = time.time() + SESSION_TTL
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        now = time.time()
        with _lock:
            expiry = _sessions.get(token)
            if expiry is None:
                return False
            if expiry < now:
                del _sessions[token]
                return False
        return True

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with _lock:
            _sessions.pop(token, None)

    # ------------------------------------------------------- rate limit

    def _rate_limited(self, source: str) -> bool:
        if not source:
            return False
        now = time.time()
        with _lock:
            hits = [t for t in _attempts.get(source, []) if now - t < ATTEMPT_WINDOW]
            _attempts[source] = hits
            return len(hits) >= MAX_ATTEMPTS

    def _record_failure(self, source: str) -> None:
        if not source:
            return
        with _lock:
            _attempts.setdefault(source, []).append(time.time())
