"""Architecture and honesty contract tests.

These are the rules the Founder authorization set. They are enforced as tests so
a later change cannot quietly break them:

  * layering is one-directional (domain knows nothing of infrastructure/api/UI)
  * no domain rule is implemented in the browser
  * fixture data is never presented as company evidence
  * LOCAL MODE is never dressed up as a connected runtime
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.harness import main  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
KAVI = ROOT / "kavi"
STATIC = KAVI / "static"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def body(t) -> None:
    # ------------------------------------------------------------ layering
    for path in (KAVI / "domain").glob("*.py"):
        text = read(path)
        t.check(f"domain/{path.name} imports no infrastructure",
                "kavi.infrastructure" not in text)
        t.check(f"domain/{path.name} imports no api", "kavi.api" not in text)
        t.check(f"domain/{path.name} imports no application",
                "kavi.application" not in text)
        t.check(f"domain/{path.name} imports no http module",
                "import http" not in text and "urllib" not in text)

    application = read(KAVI / "application" / "services.py")
    t.check("application does not import the server", "kavi.server" not in application)
    t.check("application does not build HTTP responses", "send_response" not in application)

    routes = read(KAVI / "api" / "routes.py")
    for forbidden in ("TransitionError", "dataclass", "check_task_transition"):
        t.check(f"api layer contains no domain rule: {forbidden}", forbidden not in routes)

    server = read(KAVI / "server.py")
    t.check("server imports no domain models", "kavi.domain.models" not in server)
    t.check("server never returns exception text",
            "str(exc)" not in server.split("UseCaseError")[-1].split("PermissionError")[0]
            or "internal error" in server)
    t.check("server returns a generic message on unexpected errors",
            '"internal error"' in server)
    t.check("server binds loopback by default", '"127.0.0.1"' in server)
    t.check("server caps request body", "MAX_BODY" in server)
    t.check("server validates origin on POST", "_origin_ok" in server)

    # ------------------------------------------------- no logic in browser
    js_files = list((STATIC / "js").rglob("*.js"))
    t.check("frontend modules exist", len(js_files) >= 10)
    for path in js_files:
        text = read(path)
        rel = path.relative_to(STATIC)
        # The browser may know which transitions to OFFER, but must post them
        # to the server; it must never decide validity locally.
        t.check(f"{rel} does not throw a transition error",
                "TransitionError" not in text)
        t.check(f"{rel} has no hardcoded cost or uptime figure",
                not re.search(r"\$\d|99\.\d\s*%", text))

    # ------------------------------------------- fixture honesty in the UI
    ui = read(STATIC / "js" / "ui.js")
    t.check("ui exposes an origin chip", "originChip" in ui)
    t.check("fixture chip is labelled FIXTURE", "'FIXTURE'" in ui)
    t.check("fixture chip explains itself", "not company evidence" in ui)

    for name in ("command", "inbox", "objectives", "ventures", "organization",
                 "decisions", "authority"):
        text = read(STATIC / "js" / "views" / f"{name}.js")
        t.check(f"view {name} imports the origin chip", "originChip" in text)

    # Metrics does not render individual records; it must instead separate
    # fixture counts from local counts so no fixture row is counted as evidence.
    metrics_js = read(STATIC / "js" / "views" / "metrics.js")
    t.check("metrics separates fixture from local counts",
            "Fixture" in metrics_js and "Local" in metrics_js)
    t.check("metrics warns fixtures are not evidence",
            "never be counted as company evidence" in metrics_js)

    # --------------------------------------------- runtime honesty in code
    runtime = read(KAVI / "infrastructure" / "runtime_status.py")
    t.check("runtime declares NOT CONNECTED", 'NOT_CONNECTED = "NOT CONNECTED"' in runtime)
    t.check("runtime declares NOT MEASURED", 'NOT_MEASURED = "NOT MEASURED"' in runtime)
    t.check("runtime has no fabricated uptime", "99." not in runtime)
    t.check("runtime has no fabricated cost", "$" not in runtime)
    t.check("runtime label states LOCAL MODE", "LOCAL MODE / ENGINE ROOM NOT CONNECTED" in runtime)

    index_html = read(STATIC / "index.html")
    t.check("shell shows LOCAL MODE", "LOCAL MODE / ENGINE ROOM NOT CONNECTED" in index_html)
    t.check("shell does not claim VPS online", "VPS ENGINE ROOM · ONLINE" not in index_html)
    t.check("shell has no hardcoded cost", "$14.82" not in index_html)
    t.check("shell has no hardcoded uptime", "99.2%" not in index_html)
    t.check("shell has no hardcoded queue depth", "QUEUE <b class" not in index_html)

    # ------------------------------------------------- execution seam real
    execution = read(KAVI / "infrastructure" / "execution.py")
    t.check("execution defines a capability interface", "class ExecutionCapability" in execution)
    t.check("null adapter exists", "class NullExecutionAdapter" in execution)
    t.check("hermes adapter is declared", "class HermesExecutionAdapter" in execution)
    t.check("hermes adapter is not implemented", "not implemented in v0.1" in execution)

    # Nothing outside infrastructure may import a concrete adapter.
    for path in list((KAVI / "application").glob("*.py")) + list((KAVI / "api").glob("*.py")):
        text = read(path)
        t.check(f"{path.name} does not import HermesExecutionAdapter",
                "HermesExecutionAdapter" not in text)

    # --------------------------------------------------- vault is read-only
    vault = read(KAVI / "infrastructure" / "vault.py")
    t.check("vault reader has no write method",
            "def write" not in vault and "write_text" not in vault)
    t.check("vault reader guards traversal", '".." in relative_path' in vault)
    t.check("vault reader confines to root", "relative_to(self.root.resolve())" in vault)

    # -------------------------------------------------- fixtures labelled
    fixtures = read(KAVI / "infrastructure" / "fixtures.py")
    t.check("fixture module states it is not evidence",
            "NOT KAVI company evidence" in fixtures)
    origin_count = fixtures.count('"origin": FIXTURE') + fixtures.count('"origin": "FIXTURE"')
    t.check("every fixture row carries an origin", origin_count >= 20)
    t.check("fixture module has no invented revenue",
            "revenue" not in fixtures.lower() or "UNKNOWN" in fixtures)

    repository = read(KAVI / "infrastructure" / "repository.py")
    t.check("repository refuses to persist fixture rows",
            "fixture rows are read-only" in repository)

    # ------------------------------------------------------ modules exist
    for module in ("command", "inbox", "objectives", "ventures", "organization",
                   "memory", "metrics", "decisions", "authority"):
        t.check(f"module {module} implemented", (STATIC / "js" / "views" / f"{module}.js").is_file())

    main_js = read(STATIC / "js" / "main.js")
    for module in ("command", "inbox", "objectives", "ventures", "organization",
                   "memory", "metrics", "decisions", "authority"):
        t.check(f"module {module} registered in the shell", f"views/{module}.js" in main_js)
    t.check("keyboard shortcut handler present", "BY_KEY[event.key]" in main_js)
    t.check("command palette bound to Ctrl+K", "'k'" in main_js)

    # ------------------------------------------------------- css tokens
    css = read(STATIC / "css" / "kavi.css")
    for token in ("--mint", "--red", "--amber", "--blue", "--violet"):
        t.check(f"semantic colour token {token} declared", f"{token}:" in css)
    t.check("focus ring is visible", ":focus-visible" in css)

    # -------------------------------------------------- no build artefacts
    t.check("no package.json", not (ROOT / "package.json").exists())
    t.check("no node_modules", not (ROOT / "node_modules").exists())
    t.check("no requirements file needed", not (ROOT / "requirements.txt").exists())


main("smoke_architecture", body)
