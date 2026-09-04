"""Run every suite. Exit non-zero if any fails."""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

SUITES = (
    "tests/smoke_domain.py",
    "tests/smoke_application.py",
    "tests/smoke_architecture.py",
    "tests/smoke_http.py",
    "tests/smoke_ui_cdp.py",
    "tests/acceptance_v01.py",
)


def main() -> int:
    failures = 0
    for suite in SUITES:
        result = subprocess.run(
            [sys.executable, suite],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout)
        if result.stderr.strip():
            sys.stderr.write(result.stderr)
        if result.returncode != 0:
            failures += 1
    print("-" * 52)
    print("ALL SUITES PASSED" if not failures else f"{failures} SUITE(S) FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
