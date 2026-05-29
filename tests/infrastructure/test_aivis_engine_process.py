import subprocess

import pytest

from app.infrastructure.runtime.aivis_engine_process import AivisEngineProcess


@pytest.mark.asyncio
async def test_aivis_engine_process_does_not_start_when_ready(monkeypatch, tmp_path):
    started = False

    async def ready(_self):
        return True

    def fake_popen(*_args, **_kwargs):
        nonlocal started
        started = True

    monkeypatch.setattr(AivisEngineProcess, "_is_ready", ready)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    process = AivisEngineProcess(str(tmp_path), "http://127.0.0.1:10101")
    await process.start()

    assert started is False


@pytest.mark.asyncio
async def test_aivis_engine_process_starts_uv_run_command(monkeypatch, tmp_path):
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

    monkeypatch.setattr(AivisEngineProcess, "_is_ready", ready)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    process = AivisEngineProcess(str(tmp_path), "http://127.0.0.1:10101", startup_timeout_sec=1)
    await process.start()

    argv = calls[0][0][0]
    assert argv[:3] == ["uv", "run", "run.py"]
    assert "--no-use_gpu" in argv
    assert calls[0][1]["cwd"] == tmp_path
    assert calls[0][1]["env"].get("VIRTUAL_ENV") is None
