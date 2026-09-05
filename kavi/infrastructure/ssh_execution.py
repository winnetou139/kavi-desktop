"""Remote execution over an SSH tunnel.

The engine room runs on a VPS. The cockpit stays on the Founder's laptop.
They talk over SSH, which is already authenticated, already encrypted, and
already the only port open on the server.

Why a tunnel rather than a public port:
  - nothing new is exposed to the internet; the firewall stays closed;
  - access is proven by the SSH key the Founder already holds;
  - if the key is revoked, access dies with it.

This adapter runs one bounded prompt at a time, exactly like the local one.
It never opens an interactive session and never schedules anything.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import os
import pathlib
import shlex
import shutil
import subprocess
import threading
import uuid
from typing import Any, Callable

from kavi.infrastructure.execution import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    ExecutionCapability,
    ExecutionRequest,
    ExecutionResult,
)


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


class SSHExecutionAdapter(ExecutionCapability):
    """Runs a Hermes prompt on the engine room, over SSH.

    Configuration comes from the environment so no server address is ever
    committed to the repository:

        KAVI_VPS_HOST   user@host of the engine room
        KAVI_VPS_KEY    path to the private key
        KAVI_VPS_HERMES path to hermes on the server
    """

    name = "ssh"

    def __init__(
        self,
        *,
        host: str | None = None,
        key: str | None = None,
        remote_hermes: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        transcript_dir: str | pathlib.Path | None = None,
    ) -> None:
        self.host = host or os.environ.get("KAVI_VPS_HOST", "")
        self.key = key or os.environ.get("KAVI_VPS_KEY", "")
        self.remote_hermes = (
            remote_hermes
            or os.environ.get("KAVI_VPS_HERMES")
            or "~/hermes-agent/.venv/bin/hermes"
        )
        self.timeout = max(10, min(int(timeout), MAX_TIMEOUT))
        base = transcript_dir or (
            pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
            / "kavi-desktop" / "runs"
        )
        self.transcript_dir = pathlib.Path(base)

    # ------------------------------------------------------------ status

    def _ssh_base(self) -> list[str] | None:
        ssh = shutil.which("ssh")
        if not ssh or not self.host:
            return None
        command = [ssh, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
        if self.key:
            command += ["-i", self.key]
        return command + [self.host]

    def _remote_path_expr(self) -> str:
        """The remote path, safe to embed in a remote shell command.

        A configured path may legitimately start with ``~``. Quoting it whole
        would make the tilde literal and a working install would look missing,
        so expand the tilde against $HOME and quote only the remainder.
        """
        path = self.remote_hermes
        if path.startswith("~/"):
            return '"$HOME"/' + shlex.quote(path[2:])
        return shlex.quote(path)

    def reachable(self) -> tuple[bool, str]:
        """Ask the server whether Hermes is actually there. No guessing."""
        base = self._ssh_base()
        if base is None:
            return False, "ssh is unavailable, or KAVI_VPS_HOST is not set."
        try:
            probe = subprocess.run(
                base + [f"test -x {self._remote_path_expr()} && echo READY"],
                capture_output=True, text=True, timeout=25,
            )
        except subprocess.TimeoutExpired:
            return False, "The engine room did not answer within 25 seconds."
        except OSError as error:
            return False, f"Could not reach the engine room: {error}"
        if "READY" in probe.stdout:
            return True, "Engine room reachable over SSH."
        detail = (probe.stderr or probe.stdout).strip().splitlines()
        return False, detail[-1] if detail else "Hermes was not found on the server."

    def describe(self) -> dict[str, Any]:
        if not self.host:
            return {
                "adapter": "SSH",
                "connected": False,
                "state": "NOT CONFIGURED",
                "detail": (
                    "No engine room is configured. Set KAVI_VPS_HOST to use one."
                ),
            }
        ok, detail = self.reachable()
        return {
            "adapter": "SSH",
            "connected": ok,
            "state": "READY" if ok else "UNREACHABLE",
            "host": self.host.split("@")[-1],
            "remote_hermes": self.remote_hermes,
            "timeout_seconds": self.timeout,
            "transcripts": str(self.transcript_dir),
            "detail": (
                detail + " Work runs on the server, so it continues even if this "
                "laptop sleeps. Nothing is scheduled; a run starts only when you "
                "press Run."
                if ok else detail
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
            prompt, requested = request.strip(), None
        else:
            prompt, requested = request.prompt(), request.timeout
        limit = max(10, min(int(timeout or requested or self.timeout), MAX_TIMEOUT))
        run_id = f"RUN-{_dt.date.today().year}-{uuid.uuid4().hex[:6].upper()}"

        if not prompt:
            return ExecutionResult(
                run_id=run_id, state="DECLINED", adapter="SSH",
                detail="Declined: the prompt was empty.",
            )

        base = self._ssh_base()
        if base is None:
            return ExecutionResult(
                run_id=run_id, state="DECLINED", adapter="SSH", prompt=prompt,
                detail="Declined: no engine room is configured.",
            )

        result = ExecutionResult(
            run_id=run_id, state="RUNNING", adapter="SSH", prompt=prompt,
            started_at=_now(),
            detail=f"Running on the engine room. It stops by itself after {limit}s.",
        )

        # The remote command is quoted as a single argument, so the prompt
        # cannot break out of it and become shell syntax.
        remote = f"{self._remote_path_expr()} -z {shlex.quote(prompt)}"

        def _run() -> None:
            try:
                completed = subprocess.run(
                    base + [remote], capture_output=True, text=True, timeout=limit + 15,
                )
                output = (completed.stdout or "")
                if completed.stderr.strip():
                    output += f"\n[stderr]\n{completed.stderr}"
                result.exit_code = completed.returncode
                result.output = output.strip()
                result.state = "SUCCEEDED" if completed.returncode == 0 else "FAILED"
                result.detail = (
                    "Finished on the engine room." if completed.returncode == 0
                    else f"The engine room returned exit code {completed.returncode}."
                )
            except subprocess.TimeoutExpired:
                result.state = "TIMED_OUT"
                result.detail = f"Stopped after {limit}s without finishing."
            except OSError as error:
                result.state = "FAILED"
                result.detail = f"Could not reach the engine room: {error}"
            finally:
                result.finished_at = _now()
                self._write_transcript(result)
                if on_finish is not None:
                    on_finish(result)

        threading.Thread(target=_run, daemon=True).start()
        return result

    def _write_transcript(self, result: ExecutionResult) -> None:
        try:
            self.transcript_dir.mkdir(parents=True, exist_ok=True)
            (self.transcript_dir / f"{result.run_id}.txt").write_text(
                f"run_id      {result.run_id}\n"
                f"adapter     {result.adapter} (engine room)\n"
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
            pass
