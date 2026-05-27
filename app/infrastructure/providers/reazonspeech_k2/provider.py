"""ReazonSpeech K2 STT provider."""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

from app.domain.errors import ModelNotLoadedError, TranscriptionFailedError
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult
from app.infrastructure.providers.reazonspeech_k2.audio_validator import inspect_wav

logger = logging.getLogger(__name__)


def _cache_key(model_id: str, language: str) -> str:
    return f"{model_id}:{language}"


class ReazonSpeechK2Provider:
    provider_name: str = "reazonspeech_k2"

    def __init__(
        self,
        model_id: str,
        language: str = "ja",
        max_audio_seconds: float = 30.0,
        auto_convert: bool = True,
        accepted_formats: tuple[str, ...] = ("wav",),
        preferred_sample_rate: int = 16000,
        preferred_channels: int = 1,
    ) -> None:
        self._default_model_id = model_id
        self._default_language = language
        self._default_max_audio_seconds = max_audio_seconds
        self._auto_convert = auto_convert
        self._accepted_formats = accepted_formats
        self._preferred_sample_rate = preferred_sample_rate
        self._preferred_channels = preferred_channels
        self._models: dict[str, Any] = {}
        self._load_lock = threading.Lock()

    def is_loaded(self) -> bool:
        return len(self._models) > 0

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, request)

    def capabilities(self) -> dict:
        return {
            "provider": "reazonspeech_k2",
            "default_model_id": self._default_model_id,
            "default_language": self._default_language,
            "max_audio_seconds": self._default_max_audio_seconds,
            "accepted_formats": list(self._accepted_formats),
            "streaming": False,
            "loaded_models": list(self._models.keys()),
        }

    def _load_model(self, model_id: str, language: str) -> None:
        key = _cache_key(model_id, language)
        with self._load_lock:
            if key in self._models:
                return
            logger.info("Loading ReazonSpeech K2 model: %s (language=%s)", model_id, language)
            try:
                from reazonspeech.k2.asr import load_model
            except ImportError as error:
                raise ModelNotLoadedError(model_id) from error
            try:
                self._models[key] = load_model(language=language)
            except Exception as error:
                raise ModelNotLoadedError(model_id) from error

    def _resolve_config(self, request: TranscriptionRequest) -> tuple[str, str, float]:
        config = request.provider_config
        model_id = config.get("model_id", self._default_model_id)
        language = config.get("language", self._default_language)
        max_audio_seconds = config.get("max_audio_seconds", self._default_max_audio_seconds)
        return model_id, str(language), float(max_audio_seconds)

    def _transcribe_sync(self, request: TranscriptionRequest) -> TranscriptionResult:
        model_id, language, max_audio_seconds = self._resolve_config(request)

        path = Path(request.audio_path)
        info = inspect_wav(
            path,
            max_audio_seconds=max_audio_seconds,
            accepted_formats=self._accepted_formats,
            auto_convert=self._auto_convert,
            preferred_sample_rate=self._preferred_sample_rate,
            preferred_channels=self._preferred_channels,
        )

        self._load_model(model_id, language)
        key = _cache_key(model_id, language)
        model = self._models[key]

        try:
            from reazonspeech.k2.asr import audio_from_path, transcribe
            audio = audio_from_path(str(path))
            result = transcribe(model, audio)
        except Exception as error:
            raise TranscriptionFailedError(
                provider_name=self.provider_name, detail=str(error)
            ) from error

        return TranscriptionResult(
            text=str(result.text),
            language=language,
            duration_sec=round(info.duration_sec, 3),
            processing_ms=0,
            provider=self.provider_name,
            model=model_id,
            audio_info={
                "sampleRate": info.sample_rate,
                "channels": info.channels,
                "format": info.format,
            },
        )
