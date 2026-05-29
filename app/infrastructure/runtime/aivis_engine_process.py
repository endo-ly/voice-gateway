"""Managed AivisSpeech Engine process."""

import asyncio
import os
import signal
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.infrastructure.logging.logger import logger


class AivisEngineProcess:
    def __init__(
        self,
        engine_dir: str,
        base_url: str,
        startup_timeout_sec: int = 180,
    ) -> None:
        self._engine_dir = Path(engine_dir)
        self._base_url = base_url.rstrip("/")
        self._startup_timeout_sec = startup_timeout_sec
        self._process: subprocess.Popen[str] | None = None

    async def start(self) -> None:
        if await self._is_ready():
            logger.info("AivisSpeech Engine is already available at %s", self._base_url)
            return

        if not self._engine_dir.is_dir():
            raise RuntimeError(f"AivisSpeech Engine directory not found: {self._engine_dir}")

        parsed = urlparse(self._base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 10101

        logger.info("Starting managed AivisSpeech Engine at %s", self._base_url)
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        self._process = subprocess.Popen(
            [
                "uv",
                "run",
                "run.py",
                "--host",
                host,
                "--port",
                str(port),
                "--no-use_gpu",
                "--output_log_utf8",
            ],
            cwd=self._engine_dir,
            env=env,
            text=True,
            start_new_session=True,
        )
        await self._wait_until_ready()

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is not None:
            self._process = None
            return

        logger.info("Stopping managed AivisSpeech Engine")
        os.killpg(self._process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(asyncio.to_thread(self._process.wait), timeout=15)
        except TimeoutError:
            os.killpg(self._process.pid, signal.SIGKILL)
            await asyncio.to_thread(self._process.wait)
        finally:
            self._process = None

    async def _wait_until_ready(self) -> None:
        deadline = asyncio.get_running_loop().time() + self._startup_timeout_sec
        while asyncio.get_running_loop().time() < deadline:
            if self._process and self._process.poll() is not None:
                raise RuntimeError(f"AivisSpeech Engine exited early with code {self._process.returncode}")
            if await self._is_ready():
                return
            await asyncio.sleep(1)
        raise RuntimeError(f"AivisSpeech Engine did not become ready within {self._startup_timeout_sec}s")

    async def _is_ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self._base_url}/version")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
