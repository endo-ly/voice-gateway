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
        "AIVIS_BASE_URL",
        "AIVIS_MANAGE_ENGINE",
        "AIVIS_ENGINE_DIR",
        "AIVIS_STARTUP_TIMEOUT_SEC",
        "REAZONSPEECH_REPO_DIR",
        "HOST",
        "PORT",
    ):
        monkeypatch.delenv(key, raising=False)


class TestSettingsDefaults:
    def test_default_host(self):
        s = Settings()
        assert s.host == "127.0.0.1"

    def test_default_port(self):
        s = Settings()
        assert s.port == 8012

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

    def test_aivis_startup_timeout_must_be_positive(self):
        with patch.dict(os.environ, {"AIVIS_STARTUP_TIMEOUT_SEC": "0"}):
            with pytest.raises(ValidationError, match="aivis_startup_timeout_sec"):
                Settings()

    def test_irodori_repo_dir_default_is_none(self):
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("IRODORI_REPO_DIR", None)
            with patch.dict(os.environ, env, clear=True):
                s = Settings()
                assert s.irodori_repo_dir is None

    def test_custom_port_from_env(self):
        with patch.dict(os.environ, {"PORT": "9000"}):
            s = Settings()
            assert s.port == 9000

    def test_custom_host_from_env(self):
        with patch.dict(os.environ, {"HOST": "0.0.0.0"}):
            s = Settings()
            assert s.host == "0.0.0.0"

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
