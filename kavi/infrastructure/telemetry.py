"""Execution telemetry and the economic ledger.

Brief §10 asks for structured telemetry on every execution, and §15 for an
economic ledger. This records both -- and is deliberate about the difference
between the two, because they are not equally knowable.

WHAT IS MEASURED
    run id, adapter, model, state, exit code
    started / finished timestamps
    active seconds (wall clock the machine actually worked)
    waiting seconds (time the Founder was not waiting on the machine)
    retries, failures
    prompt and output length

WHAT IS NOT MEASURED, AND WHY
    Rupiah per run. The Founder runs Claude Max, ChatGPT Pro and a Kimi
    Coding Plan -- three subscriptions, not metered API credit. A run has no
    marginal price. Multiplying tokens by a public API rate would produce a
    number that looks authoritative and is fiction, because that money was
    never spent.

    §16 and §20 of the brief (cost of intelligence, return on intelligence
    cost) need a real denominator. Until usage is metered, the ledger reports
    SUBSCRIPTION / NOT METERED rather than inventing one.

    Token counts. The subscription transports do not return usage, so tokens
    stay None rather than being estimated from character counts.

WHAT CAN BE ALLOCATED, IF ASKED
    A monthly subscription bill divided across the runs it covered is an
    allocation, not a measurement. `allocate_monthly()` will do it, and
    labels every figure ALLOCATED so it can never be mistaken for a metered
    cost.

The store is one JSONL file, appended to, never rewritten -- so a crash
loses at most the run in flight.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
import pathlib
import threading
from typing import Any, Iterator

NOT_METERED = "SUBSCRIPTION / NOT METERED"
UNKNOWN = "UNKNOWN"

_lock = threading.Lock()


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _parse(stamp: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.fromisoformat(stamp)
    except (ValueError, TypeError):
        return None


@dataclasses.dataclass
class RunRecord:
    """One execution, as it actually happened.

    Fields that were not observed stay None. None means 'not measured'; it
    must never be filled in with a plausible-looking default.
    """

    run_id: str
    adapter: str = UNKNOWN
    model: str = UNKNOWN
    state: str = UNKNOWN
    started_at: str = ""
    finished_at: str = ""
    exit_code: int | None = None

    # Timing. §12 insists these are different kinds of time.
    active_seconds: float | None = None
    waiting_seconds: float | None = None

    # Volume. Characters are counted because they are observable; tokens are
    # not, because the subscription transports do not report them.
    prompt_chars: int | None = None
    output_chars: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None

    retries: int = 0
    failures: int = 0

    # Economics. Left as NOT_METERED on purpose -- see the module docstring.
    cost_basis: str = NOT_METERED
    cost_idr: float | None = None

    # Attribution (§14): venture -> workflow -> task -> run.
    venture: str = UNKNOWN
    objective_id: str = UNKNOWN
    task_id: str = UNKNOWN
    trigger: str = UNKNOWN          # FOUNDER | SCHEDULE | SYSTEM

    # Outcome. Only the Founder can judge these, so they stay empty until
    # he says otherwise. A machine-assigned quality score would be invented.
    quality_score: int | None = None
    human_corrections: int | None = None
    business_outcome: str = ""

    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _default_path() -> pathlib.Path:
    override = os.environ.get("KAVI_TELEMETRY")
    if override:
        return pathlib.Path(override)
    base = pathlib.Path(os.environ.get("KAVI_DATA_DIR") or
                        (pathlib.Path(os.environ.get("LOCALAPPDATA",
                                                     pathlib.Path.home()))
                         / "kavi-desktop"))
    return base / "telemetry.jsonl"


class TelemetryLog:
    """Append-only record of every execution the cockpit started."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else _default_path()

    # ------------------------------------------------------------- writing

    def record(self, run: RunRecord) -> RunRecord:
        """Append one run. Derives active_seconds only when both stamps exist."""
        if run.active_seconds is None:
            start, finish = _parse(run.started_at), _parse(run.finished_at)
            if start and finish:
                run.active_seconds = round((finish - start).total_seconds(), 2)

        try:
            with _lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(run.as_dict(), ensure_ascii=False) + "\n")
        except OSError:
            # Telemetry must never break the run it is describing.
            pass
        return run

    def from_result(self, result: Any, **extra: Any) -> RunRecord:
        """Build a record from an ExecutionResult, measuring nothing extra."""
        prompt = getattr(result, "prompt", "") or ""
        output = getattr(result, "output", "") or ""
        run = RunRecord(
            run_id=getattr(result, "run_id", UNKNOWN),
            adapter=getattr(result, "adapter", UNKNOWN) or UNKNOWN,
            state=getattr(result, "state", UNKNOWN) or UNKNOWN,
            started_at=getattr(result, "started_at", "") or "",
            finished_at=getattr(result, "finished_at", "") or "",
            exit_code=getattr(result, "exit_code", None),
            prompt_chars=len(prompt) or None,
            output_chars=len(output) or None,
            failures=1 if getattr(result, "state", "") in
                     ("FAILED", "TIMED_OUT", "DECLINED") else 0,
        )
        for key, value in extra.items():
            if hasattr(run, key):
                setattr(run, key, value)
        return self.record(run)

    # ------------------------------------------------------------- reading

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        out: list[dict[str, Any]] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue        # one bad line must not hide the good ones
        except OSError:
            return []
        return out

    # ------------------------------------------------------------ ledger

    def ledger(self) -> dict[str, Any]:
        """The economic ledger (§15), reporting only what is knowable."""
        rows = self.rows()
        if not rows:
            return {
                "runs": 0,
                "cost_basis": NOT_METERED,
                "cost_idr": None,
                "detail": (
                    "No runs recorded yet. Cost per run is not metered: the "
                    "engine runs on subscriptions, so a run has no marginal "
                    "price."
                ),
            }

        succeeded = [r for r in rows if r.get("state") == "SUCCEEDED"]
        failed = [r for r in rows if r.get("state") in ("FAILED", "TIMED_OUT")]
        timings = [r["active_seconds"] for r in rows
                   if isinstance(r.get("active_seconds"), (int, float))]

        by_adapter: dict[str, int] = {}
        by_model: dict[str, int] = {}
        for row in rows:
            by_adapter[row.get("adapter", UNKNOWN)] = \
                by_adapter.get(row.get("adapter", UNKNOWN), 0) + 1
            by_model[row.get("model", UNKNOWN)] = \
                by_model.get(row.get("model", UNKNOWN), 0) + 1

        # Only count tokens that were actually reported.
        reported = [r for r in rows
                    if isinstance(r.get("tokens_in"), int)
                    or isinstance(r.get("tokens_out"), int)]

        return {
            "runs": len(rows),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "success_rate": round(len(succeeded) / len(rows), 3),
            "active_seconds_total": round(sum(timings), 1) if timings else None,
            "active_seconds_median": _median(timings),
            "runs_timed": len(timings),
            "by_adapter": by_adapter,
            "by_model": by_model,
            "tokens_reported_for": len(reported),
            "tokens_total": (
                sum((r.get("tokens_in") or 0) + (r.get("tokens_out") or 0)
                    for r in reported) if reported else None
            ),
            "cost_basis": NOT_METERED,
            "cost_idr": None,
            "quality_scored": len([r for r in rows
                                   if isinstance(r.get("quality_score"), int)]),
            "detail": (
                "Cost per run is NOT METERED. The engine runs on Claude Max, "
                "ChatGPT Pro and a Kimi Coding Plan -- subscriptions, not "
                "metered credit -- so a run has no marginal price. Deriving "
                "one from public API rates would report money that was never "
                "spent. Duration and success rate are measured; quality is "
                "scored only by the Founder."
            ),
        }

    def allocate_monthly(self, subscriptions_idr: float,
                         month: str | None = None) -> dict[str, Any]:
        """Spread a month's subscription bill across that month's runs.

        This is an ALLOCATION, not a measurement: the money was spent whether
        or not any run happened. Every figure is labelled so, because an
        allocated cost presented as a metered one is a lie with a decimal
        point.
        """
        month = month or _dt.date.today().strftime("%Y-%m")
        rows = [r for r in self.rows()
                if str(r.get("started_at", "")).startswith(month)]
        if not rows:
            return {
                "month": month, "runs": 0, "basis": "ALLOCATED",
                "subscriptions_idr": subscriptions_idr,
                "per_run_idr": None,
                "detail": (f"No runs recorded in {month}, so the subscription "
                           "cost cannot be spread across anything."),
            }
        return {
            "month": month,
            "runs": len(rows),
            "basis": "ALLOCATED",
            "subscriptions_idr": subscriptions_idr,
            "per_run_idr": round(subscriptions_idr / len(rows), 2),
            "detail": (
                f"{subscriptions_idr:,.0f} IDR of subscriptions divided across "
                f"{len(rows)} runs in {month}. This is an allocation, not a "
                "measured cost: the subscriptions were paid whether or not "
                "these runs happened. Running more does not cost more."
            ),
        }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 2)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 2)
