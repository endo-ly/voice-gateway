"""Application settings loaded from environment variables."""

from pathlib import Path, PureWindowsPath
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONTROL_CHARS = frozenset("\a\b\f\n\r\t\v")


def _has_windows_drive(path: str) -> bool:
    return bool(PureWindowsPath(path).drive)


def _normalize_path(path: str, base_dir: str) -> str:
    p = Path(path).expanduser()
    if p.is_absolute() or _has_windows_drive(path):
        return str(p)
    return str((Path(base_dir) / p).resolve())


class Settings(BaseSettings):
    project_root: str = str(_PROJECT_ROOT)
    log_level: str = "INFO"
    mode: Literal["tts", "stt", "all"] = Field(default="all", validation_alias="VOICE_GATEWAY_MODE")
    assets_dir: str = "assets"
    tmp_dir: str = "tmp"
    timeout_sec: int = 120
    max_concurrency: int = 1
    irodori_repo_dir: str | None = None
    irodori_backend: Literal["server", "cli"] = Field(default="server", validation_alias="IRODORI_BACKEND")
    irodori_manage_server: bool = Field(default=False, validation_alias="IRODORI_MANAGE_SERVER")
    irodori_server_base_url: str = Field(default="http://127.0.0.1:18790", validation_alias="IRODORI_SERVER_BASE_URL")
    irodori_server_dir: str | None = Field(default=None, validation_alias="IRODORI_SERVER_DIR")
    irodori_server_host: str = Field(default="127.0.0.1", validation_alias="IRODORI_SERVER_HOST")
    irodori_server_port: int = Field(default=18790, validation_alias="IRODORI_SERVER_PORT")
    irodori_server_startup_timeout_sec: int = Field(default=300, validation_alias="IRODORI_SERVER_STARTUP_TIMEOUT_SEC")
    irodori_server_api_key: str = Field(default="", validation_alias="IRODORI_SERVER_API_KEY")
    irodori_server_model: str = Field(default="irodori", validation_alias="IRODORI_SERVER_MODEL")
    aivis_base_url: str = Field(default="http://127.0.0.1:10101", validation_alias="AIVIS_BASE_URL")
    aivis_manage_engine: bool = Field(default=False, validation_alias="AIVIS_MANAGE_ENGINE")
    aivis_engine_dir: str = ".vendor/AivisSpeech-Engine"
    aivis_engine_bind_host: str | None = Field(default=None, validation_alias="AIVIS_ENGINE_BIND_HOST")
    aivis_engine_port: int | None = Field(default=None, validation_alias="AIVIS_ENGINE_PORT")
    aivis_use_gpu: bool = Field(default=False, validation_alias="AIVIS_USE_GPU")
    aivis_startup_timeout_sec: int = 180

    # ── STT ──
    reazonspeech_repo_dir: str = ".vendor/ReazonSpeech"
    stt_callback_url: str | None = None
    stt_callback_timeout_ms: int = 3000

    @field_validator(
        "project_root",
        "assets_dir",
        "tmp_dir",
        "irodori_repo_dir",
        "irodori_server_dir",
        "aivis_engine_dir",
        "reazonspeech_repo_dir",
        mode="before",
    )
    @classmethod
    def reject_escaped_path_control_chars(cls, value: str | None) -> str | None:
        if isinstance(value, str) and any(c in value for c in _CONTROL_CHARS):
            raise ValueError(
                "Path settings must not contain control characters; "
                "use forward slashes or single quotes for Windows paths in .env"
            )
        return value

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        self.project_root = _normalize_path(self.project_root, str(_PROJECT_ROOT))
        self.assets_dir = _normalize_path(self.assets_dir, self.project_root)
        self.tmp_dir = _normalize_path(self.tmp_dir, self.project_root)
        if self.irodori_repo_dir:
            self.irodori_repo_dir = _normalize_path(self.irodori_repo_dir, self.project_root)
        if self.irodori_server_dir:
            self.irodori_server_dir = _normalize_path(self.irodori_server_dir, self.project_root)
        self.aivis_engine_dir = _normalize_path(self.aivis_engine_dir, self.project_root)
        self.reazonspeech_repo_dir = _normalize_path(self.reazonspeech_repo_dir, self.project_root)
        return self

    @field_validator("stt_callback_timeout_ms")
    @classmethod
    def validate_callback_timeout(cls, v):
        if v <= 0:
            raise ValueError("stt_callback_timeout_ms must be a positive integer")
        return v

    @field_validator("aivis_startup_timeout_sec")
    @classmethod
    def validate_aivis_startup_timeout(cls, v):
        if v <= 0:
            raise ValueError("aivis_startup_timeout_sec must be a positive integer")
        return v

    @field_validator("irodori_server_startup_timeout_sec")
    @classmethod
    def validate_irodori_server_startup_timeout(cls, v):
        if v <= 0:
            raise ValueError("irodori_server_startup_timeout_sec must be a positive integer")
        return v

    @field_validator("irodori_server_port")
    @classmethod
    def validate_irodori_server_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("irodori_server_port must be between 1 and 65535")
        return v

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
