"""ReazonSpeech K2 STT provider."""

import asyncio
from pathlib import Path

from app.domain.errors import ModelNotLoadedError, TranscriptionFailedError
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult
from app.infrastructure.providers.reazonspeech_k2.audio_validator import inspect_wav


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
        self._model_id = model_id
        self._language = language
        self._max_audio_seconds = max_audio_seconds
        self._auto_convert = auto_convert
        self._accepted_formats = accepted_formats
        self._preferred_sample_rate = preferred_sample_rate
        self._preferred_channels = preferred_channels
        self._model = None

    def is_loaded(self) -> bool:
        return self._model is not None

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, request)

    def capabilities(self) -> dict:
        return {
            "provider": "reazonspeech_k2",
            "model_id": self._model_id,
            "language": self._language,
            "max_audio_seconds": self._max_audio_seconds,
            "accepted_formats": list(self._accepted_formats),
            "streaming": False,
        }

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from reazonspeech.k2.asr import load_model
        except ImportError as error:
            raise ModelNotLoadedError(self._model_id) from error
        try:
            self._model = load_model(language=self._language)
        except Exception as error:
            raise ModelNotLoadedError(self._model_id) from error

    def _transcribe_sync(self, request: TranscriptionRequest) -> TranscriptionResult:
        path = Path(request.audio_path)
        info = inspect_wav(
            path,
            max_audio_seconds=self._max_audio_seconds,
            accepted_formats=self._accepted_formats,
            auto_convert=self._auto_convert,
            preferred_sample_rate=self._preferred_sample_rate,
            preferred_channels=self._preferred_channels,
        )

        self._load_model()

        try:
            from reazonspeech.k2.asr import audio_from_path, transcribe
            audio = audio_from_path(str(path))
            result = transcribe(self._model, audio)
        except Exception as error:
            raise TranscriptionFailedError(
                provider_name=self.provider_name, detail=str(error)
            ) from error

        return TranscriptionResult(
            text=str(result.text),
            language=self._language,
            duration_sec=round(info.duration_sec, 3),
            processing_ms=0,
            provider=self.provider_name,
            model=self._model_id,
        )
