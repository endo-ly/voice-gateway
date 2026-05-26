"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.application.services.model_resolver import ModelResolver
from app.application.services.option_merger import OptionMerger
from app.application.services.tts_profile_resolver import TTSProfileResolver
from app.application.services.tts_provider_registry import TTSProviderRegistry
from app.application.services.stt_profile_resolver import STTProfileResolver
from app.application.services.stt_provider_registry import STTProviderRegistry
from app.application.use_cases.synthesize_speech import SynthesizeSpeech
from app.application.use_cases.transcribe_audio import TranscribeAudio
from app.application.use_cases.get_latest_transcription import GetLatestTranscription
from app.infrastructure.config.settings import Settings
from app.infrastructure.logging.logger import setup_logging
from app.infrastructure.providers.fake.provider import FakeProvider
from app.infrastructure.providers.irodori.provider import IrodoriProvider
from app.infrastructure.repositories.yaml_model_profile_repository import YamlModelProfileRepository
from app.infrastructure.repositories.yaml_voice_profile_repository import YamlVoiceProfileRepository
from app.infrastructure.repositories.in_memory_transcription_store import InMemoryTranscriptionStore

app = FastAPI(title="voice-gateway", version="0.1.0")

# ── Common ──
app.include_router(health_router)
app.include_router(models_router)

_settings = Settings()
setup_logging(_settings.log_level)

_model_repo = YamlModelProfileRepository(
    yaml_path=f"{_settings.assets_dir}/models/models.yaml"
)
_voice_repo = YamlVoiceProfileRepository(
    voices_dir=f"{_settings.assets_dir}/voices"
)
_model_resolver = ModelResolver(_model_repo)

_mode = _settings.mode  # "tts" | "stt" | "all"
app.state.mode = _mode
app.state.tts_provider_names = []
app.state.stt_provider_names = []

# ── TTS Providers & Routes ──
_tts_registry = TTSProviderRegistry()
if _mode in ("tts", "all"):
    from app.api.routes.voices import router as voices_router
    from app.api.routes.openai_speech import router as openai_speech_router
    from app.api.routes.native_speech import router as native_speech_router

    tts_models = [m for m in _model_repo.list_all() if m.direction == "tts"]
    configured_tts_providers = {m.provider for m in tts_models}

    if "fake" in configured_tts_providers:
        _tts_registry.register(FakeProvider())

    if "irodori" in configured_tts_providers:
        if not _settings.irodori_repo_dir:
            raise RuntimeError("IRODORI_REPO_DIR is required when irodori models are configured")
        if not Path(_settings.irodori_repo_dir).is_dir():
            raise RuntimeError(f"IRODORI_REPO_DIR is not a directory: {_settings.irodori_repo_dir}")
        _tts_registry.register(
            IrodoriProvider(
                irodori_repo_dir=_settings.irodori_repo_dir,
                tmp_dir=_settings.tmp_dir,
                base_dir=_settings.project_root,
                timeout_sec=_settings.timeout_sec,
                max_concurrency=_settings.max_concurrency,
            )
        )

    _tts_resolver = TTSProfileResolver(
        model_resolver=_model_resolver, voice_repo=_voice_repo, option_merger=OptionMerger()
    )

    app.include_router(voices_router)
    app.include_router(openai_speech_router)
    app.include_router(native_speech_router)

    app.state.synthesize_speech = SynthesizeSpeech(
        profile_resolver=_tts_resolver,
        provider_registry=_tts_registry,
    )
    app.state.tts_provider_names = sorted(configured_tts_providers)

# Backward-compat alias for existing tests
_provider_registry = _tts_registry

# ── STT Providers & Routes ──
_stt_registry = STTProviderRegistry()
if _mode in ("stt", "all"):
    from app.api.routes.openai_transcriptions import router as openai_transcriptions_router
    from app.api.routes.transcriptions import router as transcriptions_router
    from app.api.routes.transcriptions_latest import router as transcriptions_latest_router
    from app.api.routes.capabilities import router as capabilities_router

    from app.infrastructure.providers.reazonspeech_k2.provider import ReazonSpeechK2Provider

    stt_models = [m for m in _model_repo.list_all() if m.direction == "stt"]
    configured_stt_providers = {m.provider for m in stt_models}

    if "reazonspeech_k2" in configured_stt_providers:
        stt_model = stt_models[0]
        defaults = stt_model.defaults
        _stt_registry.register(
            ReazonSpeechK2Provider(
                model_id=stt_model.provider_config.get("model_id", "reazon-research/reazonspeech-k2-v2"),
                language=defaults.language if hasattr(defaults, "language") else "ja",
                max_audio_seconds=defaults.max_audio_seconds if hasattr(defaults, "max_audio_seconds") else 30.0,
            )
        )

    _stt_resolver = STTProfileResolver(_model_resolver)
    _transcription_store = InMemoryTranscriptionStore()

    app.include_router(capabilities_router)
    app.include_router(openai_transcriptions_router)
    app.include_router(transcriptions_router)
    app.include_router(transcriptions_latest_router)

    app.state.transcribe_audio = TranscribeAudio(
        profile_resolver=_stt_resolver,
        provider_registry=_stt_registry,
        transcription_store=_transcription_store,
    )
    app.state.get_latest_transcription = GetLatestTranscription(
        transcription_store=_transcription_store,
    )
    app.state.stt_provider_names = sorted(configured_stt_providers)
    app.state.stt_callback_url = _settings.stt_callback_url
    app.state.stt_callback_timeout_ms = _settings.stt_callback_timeout_ms

# ── Common state ──
app.state.model_repo = _model_repo
app.state.voice_repo = _voice_repo
