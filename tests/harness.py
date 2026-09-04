"""Minimal test harness. Zero dependencies, deterministic, prints a pass count."""

from __future__ import annotations

import sys
import traceback


class Suite:
    def __init__(self, name: str) -> None:
        self.name = name
        self.passed = 0
        self.failed: list[str] = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
        else:
            self.failed.append(f"{label}{(' — ' + detail) if detail else ''}")

    def equals(self, label: str, actual, expected) -> None:
        self.check(label, actual == expected, f"expected {expected!r}, got {actual!r}")

    def raises(self, label: str, exc_type, fn, *args, **kwargs) -> None:
        try:
            fn(*args, **kwargs)
        except exc_type:
            self.passed += 1
            return
        except Exception as exc:  # noqa: BLE001
            self.failed.append(f"{label} — raised {type(exc).__name__}, expected {exc_type.__name__}")
            return
        self.failed.append(f"{label} — no exception raised, expected {exc_type.__name__}")

    def report(self) -> int:
        total = self.passed + len(self.failed)
        if self.failed:
            print(f"{self.name}: {self.passed}/{total} FAILED")
            for failure in self.failed:
                print(f"  x {failure}")
            return 1
        print(f"{self.name}: {self.passed}/{total} passed")
        return 0


def run(name: str, body) -> int:
    suite = Suite(name)
    try:
        body(suite)
    except Exception:  # noqa: BLE001
        print(f"{name}: crashed")
        traceback.print_exc()
        return 1
    return suite.report()


def main(name: str, body) -> None:
    sys.exit(run(name, body))
