"""AivisSpeech Engine managed process factory."""

from urllib.parse import urlparse

from app.infrastructure.config.settings import Settings
from app.infrastructure.providers.aivis_speech.constants import AIVIS_HEALTH_PATH
from app.infrastructure.runtime.managed_http_engine_process import ManagedHttpEngineProcess


def create_aivis_speech_engine_process(settings: Settings) -> ManagedHttpEngineProcess:
    """Create the managed process definition for AivisSpeech Engine."""
    parsed = urlparse(settings.aivis_base_url)
    bind_host = settings.aivis_engine_bind_host or parsed.hostname or "127.0.0.1"
    port = settings.aivis_engine_port or parsed.port or 10101
    gpu_flag = "--use_gpu" if settings.aivis_use_gpu else "--no-use_gpu"

    return ManagedHttpEngineProcess(
        name="AivisSpeech Engine",
        base_url=settings.aivis_base_url,
        health_path=AIVIS_HEALTH_PATH,
        cwd=settings.aivis_engine_dir,
        command=[
            "uv",
            "run",
            "run.py",
            "--host",
            bind_host,
            "--port",
            str(port),
            gpu_flag,
            "--output_log_utf8",
        ],
        startup_timeout_sec=settings.aivis_startup_timeout_sec,
    )
