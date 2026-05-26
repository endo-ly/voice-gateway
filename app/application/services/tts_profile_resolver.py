"""Resolves model + voice profiles and merges config."""

from app.domain.entities.model_profile import ModelProfile
from app.domain.entities.voice_profile import VoiceProfile
from app.domain.errors import ModelNotFoundError, VoiceBindingNotFoundError, VoiceNotFoundError
from app.domain.interfaces.voice_profile_repository import VoiceProfileRepository
from app.application.services.model_resolver import ModelResolver
from app.application.services.option_merger import OptionMerger


class TTSProfileResolver:
    def __init__(
        self,
        model_resolver: ModelResolver,
        voice_repo: VoiceProfileRepository,
        option_merger: OptionMerger | None = None,
    ) -> None:
        self._model_resolver = model_resolver
        self._voice_repo = voice_repo
        self._merger = option_merger or OptionMerger()

    def resolve(
        self,
        model_id: str,
        voice_id: str,
        request_options: dict | None = None,
    ) -> tuple[ModelProfile, VoiceProfile, dict]:
        model = self._model_resolver.get_model(model_id, direction="tts")
        voice = self._voice_repo.get_by_id(voice_id)

        binding = voice.bindings.get(model_id)
        if binding is None:
            raise VoiceBindingNotFoundError(voice_id, model_id)

        config = self._merger.merge(
            model_defaults=model.defaults.model_dump(),
            voice_defaults=voice.defaults.model_dump(),
            model_provider_config=model.provider_config,
            voice_binding_config=binding.provider_config,
            request_options=request_options or {},
        )

        return model, voice, config
