"""Tests for AivisSpeech Engine managed process factory."""

from app.infrastructure.config.settings import Settings
from app.infrastructure.providers.aivis_speech.constants import AIVIS_HEALTH_PATH
from app.infrastructure.runtime.aivis_speech_engine_process import create_aivis_speech_engine_process


def test_create_aivis_speech_engine_process_uses_base_url_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("AIVIS_BASE_URL", "http://127.0.0.1:10102")
    monkeypatch.setenv("AIVIS_ENGINE_DIR", str(tmp_path))
    settings = Settings(_env_file=None)

    process = create_aivis_speech_engine_process(settings)

    assert process._base_url == "http://127.0.0.1:10102"
    assert process._health_path == AIVIS_HEALTH_PATH
    assert process._cwd == tmp_path
    assert process._command == [
        "uv",
        "run",
        "run.py",
        "--host",
        "127.0.0.1",
        "--port",
        "10102",
        "--no-use_gpu",
        "--output_log_utf8",
    ]


def test_create_aivis_speech_engine_process_allows_bind_override_and_gpu(monkeypatch, tmp_path):
    monkeypatch.setenv("AIVIS_BASE_URL", "http://127.0.0.1:10101")
    monkeypatch.setenv("AIVIS_ENGINE_DIR", str(tmp_path))
    monkeypatch.setenv("AIVIS_ENGINE_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("AIVIS_ENGINE_PORT", "10103")
    monkeypatch.setenv("AIVIS_USE_GPU", "true")
    settings = Settings(_env_file=None)

    process = create_aivis_speech_engine_process(settings)

    assert process._command == [
        "uv",
        "run",
        "run.py",
        "--host",
        "0.0.0.0",
        "--port",
        "10103",
        "--use_gpu",
        "--output_log_utf8",
    ]
