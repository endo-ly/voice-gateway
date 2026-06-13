"""Irodori-TTS-Server managed process factory."""

from app.infrastructure.config.settings import Settings
from app.infrastructure.runtime.managed_http_engine_process import ManagedHttpEngineProcess

IRODORI_SERVER_HEALTH_PATH = "/health"


def create_irodori_tts_server_process(settings: Settings) -> ManagedHttpEngineProcess:
    """Create the managed process definition for Irodori-TTS-Server."""
    return ManagedHttpEngineProcess(
        name="Irodori-TTS-Server",
        base_url=settings.irodori_server_base_url,
        health_path=IRODORI_SERVER_HEALTH_PATH,
        cwd=settings.irodori_server_dir,
        command=[
            "uv",
            "run",
            "python",
            "-m",
            "irodori_openai_tts",
            "--host",
            settings.irodori_server_host,
            "--port",
            str(settings.irodori_server_port),
        ],
        startup_timeout_sec=settings.irodori_server_startup_timeout_sec,
    )
