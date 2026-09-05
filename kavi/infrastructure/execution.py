"""Execution adapters — how KAVI asks something else to do work.

KAVI Desktop must not depend on Hermes implementation details, so execution
sits behind this interface. Hermes is one capability; other runtimes can be
added later without the cockpit changing.

Safety posture for v0.1:
  - Nothing runs unless the Founder presses a button. There is no scheduler,
    no queue, no background trigger.
  - Every run is bounded by a timeout and produces a written transcript.
  - The adapter reports honestly when it is not connected, rather than
    pretending work happened.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import os
import pathlib
import shutil
import subprocess
import threading
import uuid
from typing import Any, Callable

DEFAULT_TIMEOUT = 300
MAX_TIMEOUT = 1800


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


@dataclasses.dataclass
class ExecutionRequest:
    """What the cockpit is asking a runtime to do."""

    task_id: str = ""
    instruction: str = ""
    permission_grant_id: str = ""
    idempotency_key: str = ""
    timeout: int | None = None

    def prompt(self) -> str:
        return (self.instruction or "").strip()


@dataclasses.dataclass
class ExecutionResult:
    """What came back from a run. Never fabricated."""

    run_id: str
    state: str          # DECLINED | RUNNING | SUCCEEDED | FAILED | TIMED_OUT
    detail: str = ""
    output: str = ""
    adapter: str = ""
    started_at: str = ""
    finished_at: str = ""
    exit_code: int | None = None
    prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class ExecutionCapability:
    """Interface every execution adapter implements."""

    name = "none"

    def describe(self) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def submit(self, request: "ExecutionRequest | str", **kwargs: Any) -> ExecutionResult:  # pragma: no cover
        raise NotImplementedError


class NullExecutionAdapter(ExecutionCapability):
    """The honest default: refuses, and says why."""

    name = "null"

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": "NONE",
            "connected": False,
            "state": "NOT CONNECTED",
            "detail": (
                "No execution runtime is connected. KAVI Desktop records work; "
                "it does not run it."
            ),
        }

    def submit(self, request: "ExecutionRequest | str", **kwargs: Any) -> ExecutionResult:
        prompt = request if isinstance(request, str) else request.prompt()
        return ExecutionResult(
            run_id=f"RUN-{uuid.uuid4().hex[:8]}",
            state="DECLINED",
            adapter="NONE",
            prompt=prompt,
            detail=(
                "Declined: no execution runtime is connected. Nothing was run, "
                "sent, or spent."
            ),
        )


class HermesExecutionAdapter(ExecutionCapability):
    """Runs a bounded, one-shot Hermes prompt on this machine.

    Deliberate limits:
      - one-shot only (``hermes -z``); no interactive session is held open;
      - the Founder starts every run explicitly; nothing is scheduled;
      - a timeout always applies, so a run cannot hang forever;
      - stdout and stderr are captured to a transcript the Founder can read.

    This adapter never edits the vault. Hermes may write files if the prompt
    asks it to, which is why the cockpit shows the prompt before running and
    keeps the full transcript afterwards.
    """

    name = "hermes"

    def __init__(
        self,
        *,
        executable: str | None = None,
        workdir: str | pathlib.Path | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        transcript_dir: str | pathlib.Path | None = None,
    ) -> None:
        self.executable = executable or os.environ.get("KAVI_HERMES_BIN") or "hermes"
        self.workdir = pathlib.Path(workdir) if workdir else pathlib.Path.home()
        self.timeout = max(10, min(int(timeout), MAX_TIMEOUT))
        base = transcript_dir or (
            pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
            / "kavi-desktop" / "runs"
        )
        self.transcript_dir = pathlib.Path(base)

    # ------------------------------------------------------------ status

    def resolved_path(self) -> str | None:
        found = shutil.which(self.executable)
        return found

    def available(self) -> bool:
        return self.resolved_path() is not None

    def describe(self) -> dict[str, Any]:
        path = self.resolved_path()
        if path is None:
            return {
                "adapter": "HERMES",
                "connected": False,
                "state": "NOT FOUND",
                "detail": (
                    f"'{self.executable}' is not on PATH, so nothing can be run. "
                    "Set KAVI_HERMES_BIN to its full path."
                ),
            }
        return {
            "adapter": "HERMES",
            "connected": True,
            "state": "READY",
            "path": path,
            "workdir": str(self.workdir),
            "timeout_seconds": self.timeout,
            "transcripts": str(self.transcript_dir),
            "detail": (
                "Hermes runs one bounded prompt at a time, only when you press "
                "Run. Nothing is scheduled and nothing runs in the background."
            ),
        }

    # ------------------------------------------------------------- runs

    def submit(
        self,
        request: "ExecutionRequest | str",
        *,
        timeout: int | None = None,
        on_finish: Callable[[ExecutionResult], None] | None = None,
        **kwargs: Any,
    ) -> ExecutionResult:
        if isinstance(request, str):
            prompt, requested_timeout = request.strip(), None
        else:
            prompt, requested_timeout = request.prompt(), request.timeout
        timeout = timeout or requested_timeout
        run_id = f"RUN-{_dt.date.today().year}-{uuid.uuid4().hex[:6].upper()}"

        if not prompt:
            return ExecutionResult(
                run_id=run_id, state="DECLINED", adapter="HERMES",
                detail="Declined: the prompt was empty.",
            )
        path = self.resolved_path()
        if path is None:
            return ExecutionResult(
                run_id=run_id, state="DECLINED", adapter="HERMES", prompt=prompt,
                detail=self.describe()["detail"],
            )

        limit = max(10, min(int(timeout or self.timeout), MAX_TIMEOUT))
        result = ExecutionResult(
            run_id=run_id, state="RUNNING", adapter="HERMES", prompt=prompt,
            started_at=_now(),
            detail=f"Running. It will stop by itself after {limit} seconds.",
        )

        def _run() -> None:
            try:
                completed = subprocess.run(
                    [path, "-z", prompt],
                    cwd=str(self.workdir),
                    capture_output=True,
                    text=True,
                    timeout=limit,
                )
                output = (completed.stdout or "") + (
                    f"\n[stderr]\n{completed.stderr}" if completed.stderr.strip() else ""
                )
                result.exit_code = completed.returncode
                result.output = output.strip()
                result.state = "SUCCEEDED" if completed.returncode == 0 else "FAILED"
                result.detail = (
                    "Finished." if completed.returncode == 0
                    else f"Hermes exited with code {completed.returncode}."
                )
            except subprocess.TimeoutExpired:
                result.state = "TIMED_OUT"
                result.detail = f"Stopped after {limit} seconds without finishing."
            except OSError as error:
                result.state = "FAILED"
                result.detail = f"Could not start Hermes: {error}"
            finally:
                result.finished_at = _now()
                self._write_transcript(result)
                if on_finish is not None:
                    on_finish(result)

        threading.Thread(target=_run, daemon=True).start()
        return result

    def _write_transcript(self, result: ExecutionResult) -> None:
        """Every run leaves a readable record, successful or not."""
        try:
            self.transcript_dir.mkdir(parents=True, exist_ok=True)
            path = self.transcript_dir / f"{result.run_id}.txt"
            path.write_text(
                f"run_id      {result.run_id}\n"
                f"adapter     {result.adapter}\n"
                f"state       {result.state}\n"
                f"started     {result.started_at}\n"
                f"finished    {result.finished_at}\n"
                f"exit_code   {result.exit_code}\n"
                f"detail      {result.detail}\n"
                f"\n--- prompt ---\n{result.prompt}\n"
                f"\n--- output ---\n{result.output}\n",
                encoding="utf-8",
            )
        except OSError:
            pass  # a failed transcript must not break the run itself


def get_adapter(kind: str = "null", **kwargs: Any) -> ExecutionCapability:
    if kind == "hermes":
        return HermesExecutionAdapter(**kwargs)
    return NullExecutionAdapter()
