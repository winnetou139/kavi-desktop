"""HTTP server. Loopback only. Transport plumbing, nothing else."""

from __future__ import annotations

import http.server
import json
import mimetypes
import pathlib
import socketserver
import urllib.parse
from typing import Any

from kavi.api.routes import Router
from kavi.infrastructure.auth import Auth
from kavi.application.services import UseCaseError

STATIC_ROOT = pathlib.Path(__file__).parent / "static"
MAX_BODY = 1 << 20  # 1 MiB


# Endpoints reachable without a session: the login page must render, and the
# client must be able to ask whether a password is required at all.
OPEN_PATHS = ("/api/auth/status", "/api/auth/login")
OPEN_STATIC = ("/login.html", "/logo.svg", "/favicon.ico")


class _Handler(http.server.BaseHTTPRequestHandler):
    router: Router
    auth: Auth
    server_version = "KAVI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # keep the console clean
        return

    # ------------------------------------------------------------- helpers

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status=status)

    def _cookie(self, name: str) -> str | None:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None

    def _source(self) -> str:
        return self.headers.get("X-Real-IP") or self.client_address[0]

    def _authorised(self, path: str) -> bool:
        """Whether this request may proceed.

        In LOCAL MODE (no password set) everything is allowed, so the desktop
        workflow is unchanged. Once a password exists, every path except the
        login surface requires a valid session.
        """
        if not self.auth.enabled():
            return True
        if path in OPEN_PATHS or path in OPEN_STATIC:
            return True
        if path.startswith("/css/") or path.startswith("/js/"):
            return True          # the login page needs its own assets
        return self.auth.valid(self._cookie("kavi_session"))

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        return origin.endswith(host)

    def _static(self, path: str) -> None:
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (STATIC_ROOT / relative).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self._send_error_json("not found", 404)
            return
        if not target.is_file():
            self._send_error_json("not found", 404)
            return
        content_type, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # -------------------------------------------------------------- verbs

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if not self._authorised(parsed.path):
            if parsed.path.startswith("/api/"):
                self._send_error_json("authentication required", 401)
            else:
                self.send_response(302)
                self.send_header("Location", "/login.html")
                self.end_headers()
            return
        if not parsed.path.startswith("/api/"):
            self._static(parsed.path)
            return
        handler = self.router.resolve("GET", parsed.path)
        if handler is None:
            self._send_error_json("unknown endpoint", 404)
            return
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        try:
            self._send_json(handler(query, {}))
        except UseCaseError as exc:
            self._send_error_json(str(exc), 400)
        except Exception:  # noqa: BLE001 - never leak a traceback
            self._send_error_json("internal error", 500)

    def _handle_auth(self, path: str, body: dict) -> bool:
        """Login and logout live here because they must set a cookie."""
        if path == "/api/auth/login":
            if not self.auth.enabled():
                self._send_json({"ok": True, "mode": "LOCAL MODE"})
                return True
            if self.auth.verify(str(body.get("password", "")), self._source()):
                token = self.auth.issue()
                payload = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                # HttpOnly: unreadable from JavaScript, so an injected script
                # cannot steal the session. SameSite=Strict blocks CSRF.
                self.send_header(
                    "Set-Cookie",
                    f"kavi_session={token}; HttpOnly; SameSite=Strict; Path=/; "
                    f"Max-Age={14 * 24 * 3600}")
                self.end_headers()
                self.wfile.write(payload)
            else:
                # One message for wrong password and for rate limiting: telling
                # an attacker which one it was is free information.
                self._send_error_json("wrong password, or too many attempts", 401)
            return True

        if path == "/api/auth/logout":
            self.auth.revoke(self._cookie("kavi_session"))
            payload = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Set-Cookie",
                             "kavi_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            self.end_headers()
            self.wfile.write(payload)
            return True
        return False

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if not self._origin_ok():
            self._send_error_json("origin not allowed", 403)
            return
        if not self._authorised(parsed.path):
            self._send_error_json("authentication required", 401)
            return
        handler = self.router.resolve("POST", parsed.path)
        if handler is None and parsed.path not in (
                "/api/auth/login", "/api/auth/logout"):
            self._send_error_json("unknown endpoint", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_json("bad content length", 400)
            return
        if length > MAX_BODY:
            self._send_error_json("payload too large", 413)
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error_json("invalid JSON body", 400)
            return
        if not isinstance(body, dict):
            self._send_error_json("body must be a JSON object", 400)
            return
        if self._handle_auth(parsed.path, body):
            return
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        try:
            self._send_json(handler(query, body))
        except UseCaseError as exc:
            self._send_error_json(str(exc), 400)
        except PermissionError as exc:
            self._send_error_json(str(exc), 403)
        except Exception:  # noqa: BLE001
            self._send_error_json("internal error", 500)


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(router: Router, host: str = "127.0.0.1", port: int = 8760,
                  auth: Auth | None = None) -> _Server:
    handler = type("BoundHandler", (_Handler,),
                   {"router": router, "auth": auth or Auth()})
    return _Server((host, port), handler)
