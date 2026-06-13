"""Tests for Settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.infrastructure.config.settings import Settings


@pytest.fixture(autouse=True)
def _clear_settings_env(monkeypatch):
    for key in (
        "PROJECT_ROOT",
        "ASSETS_DIR",
        "TMP_DIR",
        "IRODORI_REPO_DIR",
        "IRODORI_BACKEND",
        "IRODORI_MANAGE_SERVER",
        "IRODORI_SERVER_BASE_URL",
        "IRODORI_SERVER_DIR",
        "IRODORI_SERVER_HOST",
        "IRODORI_SERVER_PORT",
        "IRODORI_SERVER_STARTUP_TIMEOUT_SEC",
        "IRODORI_SERVER_API_KEY",
        "IRODORI_SERVER_MODEL",
        "AIVIS_BASE_URL",
        "AIVIS_MANAGE_ENGINE",
        "AIVIS_ENGINE_DIR",
        "AIVIS_ENGINE_BIND_HOST",
        "AIVIS_ENGINE_PORT",
        "AIVIS_USE_GPU",
        "AIVIS_STARTUP_TIMEOUT_SEC",
        "REAZONSPEECH_REPO_DIR",
    ):
        monkeypatch.delenv(key, raising=False)


class TestSettingsDefaults:
    def test_default_assets_dir(self):
        s = Settings()
        assert Path(s.assets_dir).is_absolute()
        assert s.assets_dir.endswith("assets")

    def test_default_tmp_dir(self):
        s = Settings()
        assert Path(s.tmp_dir).is_absolute()
        assert s.tmp_dir.endswith("tmp")

    def test_default_timeout_sec(self):
        s = Settings()
        assert s.timeout_sec == 120

    def test_default_max_concurrency(self):
        s = Settings()
        assert s.max_concurrency == 1

    def test_default_reazonspeech_repo_dir(self):
        s = Settings()
        assert Path(s.reazonspeech_repo_dir).is_absolute()
        assert s.reazonspeech_repo_dir.endswith(".vendor/ReazonSpeech")


class TestSettingsFromEnv:
    def test_irodori_repo_dir_from_env(self):
        with patch.dict(os.environ, {"IRODORI_REPO_DIR": "/opt/irodori"}):
            s = Settings()
            assert s.irodori_repo_dir == "/opt/irodori"

    def test_aivis_settings_from_env(self):
        with patch.dict(
            os.environ,
            {
                "AIVIS_BASE_URL": "http://127.0.0.1:10102",
                "AIVIS_MANAGE_ENGINE": "true",
                "AIVIS_ENGINE_DIR": ".vendor/aivis",
                "AIVIS_STARTUP_TIMEOUT_SEC": "60",
            },
        ):
            s = Settings()
            assert s.aivis_base_url == "http://127.0.0.1:10102"
            assert s.aivis_manage_engine is True
            assert Path(s.aivis_engine_dir).is_absolute()
            assert s.aivis_engine_dir.endswith(".vendor/aivis")
            assert s.aivis_startup_timeout_sec == 60

    def test_aivis_engine_bind_settings_from_env(self):
        with patch.dict(
            os.environ,
            {
                "AIVIS_ENGINE_BIND_HOST": "0.0.0.0",
                "AIVIS_ENGINE_PORT": "10102",
            },
        ):
            s = Settings()
            assert s.aivis_engine_bind_host == "0.0.0.0"
            assert s.aivis_engine_port == 10102

    def test_aivis_bind_settings_default_to_none(self):
        s = Settings()
        assert s.aivis_engine_bind_host is None
        assert s.aivis_engine_port is None

    def test_aivis_use_gpu_from_env(self):
        with patch.dict(os.environ, {"AIVIS_USE_GPU": "true"}):
            s = Settings()
            assert s.aivis_use_gpu is True

    def test_aivis_use_gpu_defaults_to_false(self):
        s = Settings()
        assert s.aivis_use_gpu is False

    def test_aivis_startup_timeout_must_be_positive(self):
        with patch.dict(os.environ, {"AIVIS_STARTUP_TIMEOUT_SEC": "0"}):
            with pytest.raises(ValidationError, match="aivis_startup_timeout_sec"):
                Settings()

    def test_reazonspeech_repo_dir_from_env(self):
        with patch.dict(os.environ, {"REAZONSPEECH_REPO_DIR": ".vendor/reazon"}):
            s = Settings()
            assert Path(s.reazonspeech_repo_dir).is_absolute()
            assert s.reazonspeech_repo_dir.endswith(".vendor/reazon")

    def test_irodori_repo_dir_default_is_none(self):
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("IRODORI_REPO_DIR", None)
            with patch.dict(os.environ, env, clear=True):
                s = Settings()
                assert s.irodori_repo_dir is None

    def test_irodori_backend_defaults_to_server(self):
        s = Settings()
        assert s.irodori_backend == "server"

    def test_irodori_backend_from_env(self):
        with patch.dict(os.environ, {"IRODORI_BACKEND": "cli"}):
            s = Settings()
            assert s.irodori_backend == "cli"

    def test_irodori_manage_server_defaults_to_false(self):
        s = Settings()
        assert s.irodori_manage_server is False

    def test_irodori_server_settings_from_env(self):
        with patch.dict(
            os.environ,
            {
                "IRODORI_SERVER_BASE_URL": "http://127.0.0.1:19000",
                "IRODORI_SERVER_DIR": ".vendor/Irodori-TTS-Server",
                "IRODORI_SERVER_HOST": "0.0.0.0",
                "IRODORI_SERVER_PORT": "19000",
                "IRODORI_SERVER_STARTUP_TIMEOUT_SEC": "600",
                "IRODORI_SERVER_API_KEY": "secret",
                "IRODORI_SERVER_MODEL": "irodori-tts",
            },
        ):
            s = Settings()
            assert s.irodori_server_base_url == "http://127.0.0.1:19000"
            assert Path(s.irodori_server_dir).is_absolute()
            assert Path(s.irodori_server_dir).name == "Irodori-TTS-Server"
            assert s.irodori_server_host == "0.0.0.0"
            assert s.irodori_server_port == 19000
            assert s.irodori_server_startup_timeout_sec == 600
            assert s.irodori_server_api_key == "secret"
            assert s.irodori_server_model == "irodori-tts"

    def test_irodori_server_defaults(self):
        s = Settings()
        assert s.irodori_server_base_url == "http://127.0.0.1:18790"
        assert s.irodori_server_host == "127.0.0.1"
        assert s.irodori_server_port == 18790
        assert s.irodori_server_startup_timeout_sec == 300
        assert s.irodori_server_api_key == ""
        assert s.irodori_server_model == "irodori"
        assert s.irodori_server_dir is None

    def test_irodori_server_startup_timeout_must_be_positive(self):
        with patch.dict(os.environ, {"IRODORI_SERVER_STARTUP_TIMEOUT_SEC": "0"}):
            with pytest.raises(ValidationError, match="irodori_server_startup_timeout_sec"):
                Settings()

    def test_irodori_server_port_must_be_valid(self):
        with patch.dict(os.environ, {"IRODORI_SERVER_PORT": "0"}):
            with pytest.raises(ValidationError, match="irodori_server_port"):
                Settings()

    def test_irodori_server_port_must_be_in_range(self):
        with patch.dict(os.environ, {"IRODORI_SERVER_PORT": "70000"}):
            with pytest.raises(ValidationError, match="irodori_server_port"):
                Settings()

    def test_irodori_repo_dir_from_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("IRODORI_REPO_DIR", raising=False)
        (tmp_path / ".env").write_text(
            "IRODORI_REPO_DIR='C:\\svc\\runtimes\\Irodori-TTS'\n",
            encoding="utf-8",
        )

        s = Settings()

        assert s.irodori_repo_dir == "C:\\svc\\runtimes\\Irodori-TTS"

    def test_quoted_windows_path_with_control_character_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("IRODORI_REPO_DIR", raising=False)
        (tmp_path / ".env").write_text(
            'IRODORI_REPO_DIR="C:\\svc\\runtimes\\Irodori-TTS"\n',
            encoding="utf-8",
        )

        with pytest.raises(ValidationError, match="control characters"):
            Settings()
