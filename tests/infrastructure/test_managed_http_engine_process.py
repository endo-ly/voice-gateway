"""Tests for ManagedHttpEngineProcess."""

import signal
import subprocess
import sys

import pytest

from app.infrastructure.runtime.managed_http_engine_process import ManagedHttpEngineProcess

_IS_WINDOWS = sys.platform == "win32"


@pytest.mark.asyncio
async def test_engine_does_not_start_when_already_ready(monkeypatch, tmp_path):
    started = False

    async def ready(_self):
        return True

    def fake_popen(*_args, **_kwargs):
        nonlocal started
        started = True

    monkeypatch.setattr(ManagedHttpEngineProcess, "_is_ready", ready)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    process = ManagedHttpEngineProcess(
        name="test-engine",
        base_url="http://127.0.0.1:10101",
        health_path="/version",
        cwd=str(tmp_path),
        command=["echo", "hello"],
    )
    await process.start()

    assert started is False


@pytest.mark.asyncio
async def test_engine_starts_with_configured_command(monkeypatch, tmp_path):
    calls = []
    ready_checks = 0

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None

    async def ready(_self):
        nonlocal ready_checks
        ready_checks += 1
        return ready_checks >= 2

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(ManagedHttpEngineProcess, "_is_ready", ready)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    command = ["uv", "run", "run.py", "--host", "127.0.0.1", "--port", "10101", "--no-use_gpu", "--output_log_utf8"]
    process = ManagedHttpEngineProcess(
        name="AivisSpeech Engine",
        base_url="http://127.0.0.1:10101",
        health_path="/version",
        cwd=str(tmp_path),
        command=command,
        startup_timeout_sec=1,
    )
    await process.start()

    argv = calls[0][0][0]
    assert argv == command
    assert calls[0][1]["cwd"] == tmp_path
    assert calls[0][1]["env"].get("VIRTUAL_ENV") is None

    if _IS_WINDOWS:
        assert calls[0][1].get("creationflags") == subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert calls[0][1].get("start_new_session") is True


@pytest.mark.asyncio
async def test_engine_uses_custom_health_path(monkeypatch, tmp_path):
    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None

    async def patched_is_ready(self):
        assert self._health_path == "/custom/health"
        return True

    monkeypatch.setattr(ManagedHttpEngineProcess, "_is_ready", patched_is_ready)

    def fake_popen(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    process = ManagedHttpEngineProcess(
        name="custom-engine",
        base_url="http://127.0.0.1:9999",
        health_path="/custom/health",
        cwd=str(tmp_path),
        command=["echo"],
        startup_timeout_sec=1,
    )
    await process.start()


# ── stop() tests ──

@pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only: os.killpg")
@pytest.mark.asyncio
async def test_engine_stop_sends_sigterm(monkeypatch):
    killed = []

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None

        def wait(self):
            self.returncode = 0

    def fake_killpg(pid, sig):
        killed.append((pid, sig))

    monkeypatch.setattr("os.killpg", fake_killpg)

    process = ManagedHttpEngineProcess(
        name="test-engine",
        base_url="http://127.0.0.1:10101",
        health_path="/version",
        cwd="/tmp",
        command=["echo"],
    )
    process._process = FakeProcess()
    await process.stop()

    assert len(killed) == 1
    assert killed[0] == (12345, signal.SIGTERM)
    assert process._process is None


@pytest.mark.skipif(not _IS_WINDOWS, reason="Windows-only: CTRL_BREAK_EVENT")
@pytest.mark.asyncio
async def test_engine_stop_sends_ctrl_break_on_windows():
    signals_sent = []

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None

        def wait(self):
            self.returncode = 0

        def send_signal(self, sig):
            signals_sent.append(sig)

    process = ManagedHttpEngineProcess(
        name="test-engine",
        base_url="http://127.0.0.1:10101",
        health_path="/version",
        cwd="C:/tmp",
        command=["echo"],
    )
    process._process = FakeProcess()
    await process.stop()

    assert len(signals_sent) == 1
    assert signals_sent[0] == signal.CTRL_BREAK_EVENT
    assert process._process is None


@pytest.mark.asyncio
async def test_engine_raises_on_missing_cwd(monkeypatch, tmp_path):
    async def not_ready(_self):
        return False

    monkeypatch.setattr(ManagedHttpEngineProcess, "_is_ready", not_ready)

    process = ManagedHttpEngineProcess(
        name="test-engine",
        base_url="http://127.0.0.1:10101",
        health_path="/version",
        cwd=str(tmp_path / "nonexistent"),
        command=["echo"],
    )
    with pytest.raises(RuntimeError, match="directory not found"):
        await process.start()
