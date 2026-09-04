"""Live HTTP tests. Boots the real server on an ephemeral port and drives it."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import threading
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.harness import main  # noqa: E402

from kavi.api.routes import build_router  # noqa: E402
from kavi.container import build_service  # noqa: E402
from kavi.server import create_server  # noqa: E402


def get(base: str, path: str):
    try:
        with urllib.request.urlopen(base + path, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def post(base: str, path: str, payload: dict, origin: str | None = None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if origin:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def body(t) -> None:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="kavi-http-")) / "kavi.json"
    service = build_service(data_path=tmp)
    router = build_router(service)
    server = create_server(router, "127.0.0.1", 0)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        # ------------------------------------------------------------ static
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        t.equals("index served", response.status, 200)
        t.check("index is the cockpit", "Founder Cockpit" in html)
        t.check("index declares LOCAL MODE", "LOCAL MODE / ENGINE ROOM NOT CONNECTED" in html)

        with urllib.request.urlopen(base + "/js/main.js", timeout=5) as response:
            t.equals("module served", response.status, 200)

        # -------------------------------------------------------------- api
        status, summary = get(base, "/api/summary")
        t.equals("summary 200", status, 200)
        t.equals("summary runtime local", summary["runtime"]["mode"], "LOCAL_MODE")

        status, runtime = get(base, "/api/runtime")
        t.equals("runtime 200", status, 200)
        t.equals("engine room not connected", runtime["engine_room"], "ENGINE_ROOM_NOT_CONNECTED")

        for path in ("/api/inbox", "/api/ventures", "/api/organization",
                     "/api/metrics", "/api/decisions", "/api/evidence",
                     "/api/authority", "/api/objectives", "/api/tasks",
                     "/api/tasks/board", "/api/memory"):
            code, _ = get(base, path)
            t.equals(f"GET {path}", code, 200)

        # --------------------------------------------------------- creation
        code, created = post(base, "/api/objectives/create",
                             {"title": "HTTP created objective", "outcome": "visible"})
        t.equals("create objective 200", code, 200)
        t.check("created id returned", created["id"].startswith("OBJ-"))

        code, objectives = get(base, "/api/objectives")
        t.check("created objective listed",
                any(o["id"] == created["id"] for o in objectives["objectives"]))

        code, activated = post(base, "/api/objectives/transition",
                               {"id": created["id"], "state": "ACTIVE"})
        t.equals("transition 200", code, 200)
        t.equals("state changed", activated["state"], "ACTIVE")

        code, error = post(base, "/api/objectives/transition",
                           {"id": created["id"], "state": "DRAFT"})
        t.equals("illegal transition rejected", code, 400)
        t.check("error is explanatory", "not permitted" in error["error"])

        code, error = post(base, "/api/objectives/create", {"title": ""})
        t.equals("blank title rejected", code, 400)

        code, task = post(base, "/api/tasks/create",
                          {"objective_id": created["id"], "title": "HTTP task"})
        t.equals("create task 200", code, 200)

        code, dispatch = post(base, "/api/tasks/dispatch", {"id": task["id"]})
        t.equals("dispatch 200", code, 200)
        t.equals("dispatch declined", dispatch["accepted"], False)

        # ------------------------------------------------------- guardrails
        code, _ = post(base, "/api/objectives/create",
                       {"title": "x"}, origin="http://evil.example.com")
        t.equals("hostile origin rejected", code, 403)

        try:
            urllib.request.urlopen(base + "/api/nonexistent", timeout=5)
            t.check("unknown endpoint 404", False, "no error raised")
        except urllib.error.HTTPError as error:
            t.equals("unknown endpoint 404", error.code, 404)

        try:
            urllib.request.urlopen(base + "/../run.py", timeout=5)
            t.check("path traversal blocked", False, "served a file outside static")
        except urllib.error.HTTPError as error:
            t.check("path traversal blocked", error.code in (400, 404))

        code, error = get(base, "/api/objective?id=OBJ-9999-999")
        t.equals("missing objective 400", code, 400)
        t.check("no traceback leaked", "Traceback" not in json.dumps(error))

    finally:
        server.shutdown()
        server.server_close()


main("smoke_http", body)
