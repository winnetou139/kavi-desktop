"""Run every suite. Exit non-zero if any fails.

The browser suites drive a live server, and that server writes to the local
store. Tests must never write into the Founder's real data, so this runner
starts its own server against a throwaway directory and points the browser
suites at it. Earlier runs leaked ~20 "CDP verification objective" records into
the real cockpit; this is the fix for that class of problem, not a cleanup.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Suites that only exercise Python, with no live server involved.
OFFLINE_SUITES = (
    "tests/smoke_domain.py",
    "tests/smoke_application.py",
    "tests/smoke_architecture.py",
    "tests/smoke_http.py",
)

# Suites that drive a real browser against a real server.
BROWSER_SUITES = (
    "tests/smoke_ui_cdp.py",
    "tests/acceptance_v01.py",
)

TEST_PORT = 8761  # deliberately not the default 8760 the Founder uses


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _wait_ready(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/runtime", timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    return False


def _run(suite: str, env: dict[str, str]) -> int:
    result = subprocess.run(
        [sys.executable, suite], cwd=str(ROOT), capture_output=True, text=True, env=env
    )
    sys.stdout.write(result.stdout)
    if result.stderr.strip():
        sys.stderr.write(result.stderr)
    return result.returncode


def main() -> int:
    failures = 0
    base_env = dict(os.environ)

    for suite in OFFLINE_SUITES:
        if _run(suite, base_env) != 0:
            failures += 1

    # A disposable data directory, thrown away afterwards.
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="kavi-test-data-"))
    server = None
    try:
        if not _port_free(TEST_PORT):
            print(f"  port {TEST_PORT} is busy; browser suites skipped")
            failures += 1
        else:
            server_env = dict(base_env)
            server_env["KAVI_DATA_DIR"] = str(scratch)
            server = subprocess.Popen(
                [sys.executable, "run.py", "--port", str(TEST_PORT), "--no-browser"],
                cwd=str(ROOT), env=server_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            url = f"http://127.0.0.1:{TEST_PORT}"
            if not _wait_ready(url):
                print("  test server never became ready; browser suites skipped")
                failures += 1
            else:
                suite_env = dict(base_env)
                suite_env["KAVI_URL"] = url
                suite_env["KAVI_DATA_DIR"] = str(scratch)
                for suite in BROWSER_SUITES:
                    if _run(suite, suite_env) != 0:
                        failures += 1
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        shutil.rmtree(scratch, ignore_errors=True)

    print("-" * 52)
    print("ALL SUITES PASSED" if not failures else f"{failures} SUITE(S) FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
