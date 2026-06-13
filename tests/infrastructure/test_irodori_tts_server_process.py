"""Tests for Irodori-TTS-Server managed process factory."""

from app.infrastructure.config.settings import Settings
from app.infrastructure.runtime.irodori_tts_server_process import (
    IRODORI_SERVER_HEALTH_PATH,
    create_irodori_tts_server_process,
)


def test_create_irodori_tts_server_process_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("IRODORI_SERVER_DIR", str(tmp_path))
    settings = Settings(_env_file=None)

    process = create_irodori_tts_server_process(settings)

    assert process._base_url == "http://127.0.0.1:18790"
    assert process._health_path == IRODORI_SERVER_HEALTH_PATH
    assert process._cwd == tmp_path
    assert process._command == [
        "uv",
        "run",
        "--no-sync",
        "python",
        "-m",
        "irodori_openai_tts",
        "--host",
        "127.0.0.1",
        "--port",
        "18790",
    ]
    assert process._startup_timeout_sec == 300


def test_create_irodori_tts_server_process_custom_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("IRODORI_SERVER_DIR", str(tmp_path))
    monkeypatch.setenv("IRODORI_SERVER_BASE_URL", "http://127.0.0.1:19000")
    monkeypatch.setenv("IRODORI_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("IRODORI_SERVER_PORT", "19000")
    monkeypatch.setenv("IRODORI_SERVER_STARTUP_TIMEOUT_SEC", "600")
    settings = Settings(_env_file=None)

    process = create_irodori_tts_server_process(settings)

    assert process._base_url == "http://127.0.0.1:19000"
    assert process._command == [
        "uv",
        "run",
        "--no-sync",
        "python",
        "-m",
        "irodori_openai_tts",
        "--host",
        "0.0.0.0",
        "--port",
        "19000",
    ]
    assert process._startup_timeout_sec == 600
