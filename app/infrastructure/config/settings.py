"""Application settings loaded from environment variables."""

from pathlib import Path, PureWindowsPath

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
    mode: str = Field(default="all", validation_alias="VOICE_GATEWAY_MODE")
    host: str = "127.0.0.1"
    port: int = 8012
    assets_dir: str = "assets"
    tmp_dir: str = "tmp"
    timeout_sec: int = 120
    max_concurrency: int = 1
    irodori_repo_dir: str | None = None

    # ── STT ──
    stt_vendor_dir: str = ".vendor"
    stt_callback_url: str | None = None
    stt_callback_timeout_ms: int = 3000

    @field_validator("project_root", "assets_dir", "tmp_dir", "irodori_repo_dir", "stt_vendor_dir", mode="before")
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
        self.stt_vendor_dir = _normalize_path(self.stt_vendor_dir, self.project_root)
        return self

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
