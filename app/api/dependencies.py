"""FastAPI dependency injection."""

from fastapi import Request

from app.application.use_cases.synthesize_speech import SynthesizeSpeech
from app.application.use_cases.stream_speech import StreamSpeech
from app.application.use_cases.transcribe_audio import TranscribeAudio
from app.application.use_cases.get_latest_transcription import GetLatestTranscription
from app.infrastructure.repositories.yaml_model_profile_repository import YamlModelProfileRepository
from app.infrastructure.repositories.yaml_voice_profile_repository import YamlVoiceProfileRepository


def get_model_repo(request: Request) -> YamlModelProfileRepository:
    return request.app.state.model_repo


def get_voice_repo(request: Request) -> YamlVoiceProfileRepository:
    return request.app.state.voice_repo


def get_synthesize_speech(request: Request) -> SynthesizeSpeech:
    return request.app.state.synthesize_speech


def get_stream_speech(request: Request) -> StreamSpeech:
    return request.app.state.stream_speech


def get_transcribe_audio(request: Request) -> TranscribeAudio:
    return request.app.state.transcribe_audio


def get_latest_transcription(request: Request) -> GetLatestTranscription:
    return request.app.state.get_latest_transcription


def get_stt_callback_url(request: Request) -> str | None:
    return request.app.state.stt_callback_url


def get_stt_callback_timeout_ms(request: Request) -> int:
    return request.app.state.stt_callback_timeout_ms
