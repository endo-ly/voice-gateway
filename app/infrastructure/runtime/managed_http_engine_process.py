"""Generic managed HTTP engine process."""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

import httpx

from app.infrastructure.logging.logger import logger

_IS_WINDOWS = sys.platform == "win32"


class ManagedHttpEngineProcess:
    """Manages the lifecycle of an external HTTP engine subprocess.

    Parameters:
        name: Human-readable engine name (used in logs).
        base_url: URL where the gateway connects to the engine.
        health_path: HTTP path for readiness checks (e.g. ``"/version"``).
        cwd: Working directory for the engine process.
        command: Command-line arguments to start the engine.
        startup_timeout_sec: Maximum seconds to wait for the engine to become ready.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        health_path: str,
        cwd: str | Path,
        command: list[str],
        startup_timeout_sec: int = 180,
    ) -> None:
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._health_path = health_path
        self._cwd = Path(cwd)
        self._command = list(command)
        self._startup_timeout_sec = startup_timeout_sec
        self._process: subprocess.Popen[str] | None = None

    # ── Lifecycle ──

    async def start(self) -> None:
        if await self._is_ready():
            logger.info("%s is already available at %s", self._name, self._base_url)
            return

        if not self._cwd.is_dir():
            raise RuntimeError(f"{self._name} directory not found: {self._cwd}")

        logger.info("Starting managed %s at %s", self._name, self._base_url)
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        popen_kwargs: dict[str, object] = {"text": True}
        if _IS_WINDOWS:
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        self._process = subprocess.Popen(
            self._command,
            cwd=self._cwd,
            env=env,
            **popen_kwargs,
        )
        await self._wait_until_ready()

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is not None:
            self._process = None
            return

        logger.info("Stopping managed %s", self._name)
        pid = self._process.pid

        self._send_terminate()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._process.wait), timeout=15
            )
        except TimeoutError:
            self._send_kill(pid)
            await asyncio.to_thread(self._process.wait)
        finally:
            self._process = None

    # ── Platform-specific signal helpers ──

    def _send_terminate(self) -> None:
        """Send a graceful-termination signal to the process group."""
        assert self._process is not None
        if _IS_WINDOWS:
            try:
                self._process.send_signal(signal.CTRL_BREAK_EVENT)
            except (OSError, ValueError):
                self._process.terminate()
        else:
            os.killpg(self._process.pid, signal.SIGTERM)

    def _send_kill(self, pid: int) -> None:
        """Force-kill the entire process tree."""
        if _IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
            )
        else:
            os.killpg(pid, signal.SIGKILL)

    # ── Health ──

    async def is_reachable(self) -> bool:
        """Check whether the engine responds to its health endpoint."""
        return await self._is_ready()

    # ── Internals ──

    async def _wait_until_ready(self) -> None:
        deadline = asyncio.get_running_loop().time() + self._startup_timeout_sec
        while asyncio.get_running_loop().time() < deadline:
            if self._process and self._process.poll() is not None:
                raise RuntimeError(
                    f"{self._name} exited early with code {self._process.returncode}"
                )
            if await self._is_ready():
                return
            await asyncio.sleep(1)
        raise RuntimeError(
            f"{self._name} did not become ready within {self._startup_timeout_sec}s"
        )

    async def _is_ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self._base_url}{self._health_path}")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
