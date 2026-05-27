"""Tests for TTSProfileResolver."""

import pytest

from app.domain.errors import ModelNotFoundError, VoiceNotFoundError, VoiceBindingNotFoundError
from app.application.services.model_resolver import ModelResolver
from app.application.services.option_merger import OptionMerger
from app.application.services.tts_profile_resolver import TTSProfileResolver
from app.infrastructure.repositories.yaml_model_profile_repository import YamlModelProfileRepository
from app.infrastructure.repositories.yaml_voice_profile_repository import YamlVoiceProfileRepository


import yaml


def _write_yaml(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


class TestTTSProfileResolver:
    def test_resolve_returns_merged_config(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {
            "models": [{
                "id": "tts-default",
                "display_name": "Default",
                "provider": "irodori",
                "engine": "base",
                "defaults": {"response_format": "wav", "speed": 1.0, "timeout_sec": 120},
                "provider_config": {"checkpoint": "Aratako/x", "model_device": "cuda"},
            }]
        })

        voices_dir = tmp_path / "voices"
        ego_dir = voices_dir / "egopulse"
        ego_dir.mkdir(parents=True)
        _write_yaml(str(ego_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "defaults": {"preferred_model": "tts-default", "speed": 1.0},
            "bindings": {
                "tts-default": {
                    "provider_config": {"ref_latent_path": "ref.pt", "seed": 42}
                }
            }
        })

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        model, voice, config = resolver.resolve("tts-default", "egopulse")
        assert model.id == "tts-default"
        assert voice.voice_id == "egopulse"
        assert config["checkpoint"] == "Aratako/x"
        assert config["ref_latent_path"] == "ref.pt"
        assert config["seed"] == 42

    def test_resolve_model_not_found_raises(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {"models": []})
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        with pytest.raises(ModelNotFoundError):
            resolver.resolve("nonexistent", "egopulse")

    def test_resolve_voice_not_found_raises(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {
            "models": [{"id": "tts-default", "display_name": "D", "provider": "fake", "engine": "base"}]
        })
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        with pytest.raises(VoiceNotFoundError):
            resolver.resolve("tts-default", "nonexistent")

    def test_resolve_voice_binding_missing_raises(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {
            "models": [{"id": "tts-default", "display_name": "D", "provider": "fake", "engine": "base"}]
        })

        voices_dir = tmp_path / "voices"
        ego_dir = voices_dir / "egopulse"
        ego_dir.mkdir(parents=True)
        _write_yaml(str(ego_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "bindings": {}
        })

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        with pytest.raises(VoiceBindingNotFoundError) as exc_info:
            resolver.resolve("tts-default", "egopulse")
        assert exc_info.value.voice_id == "egopulse"
        assert exc_info.value.model_id == "tts-default"

    def test_resolve_request_options_override(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {
            "models": [{
                "id": "tts-default",
                "display_name": "Default",
                "provider": "irodori",
                "engine": "base",
                "defaults": {"response_format": "wav", "speed": 1.0, "timeout_sec": 120},
                "provider_config": {"checkpoint": "Aratako/x", "seed": 0},
            }]
        })

        voices_dir = tmp_path / "voices"
        ego_dir = voices_dir / "egopulse"
        ego_dir.mkdir(parents=True)
        _write_yaml(str(ego_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "defaults": {"preferred_model": "tts-default", "speed": 0.8},
            "bindings": {
                "tts-default": {
                    "provider_config": {"ref_latent_path": "ref.pt", "seed": 42}
                }
            }
        })

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        _, _, config = resolver.resolve(
            "tts-default", "egopulse",
            request_options={"speed": 1.0, "seed": 99},
        )
        assert config["speed"] == 1.0
        assert config["seed"] == 99
        assert config["checkpoint"] == "Aratako/x"

    def test_resolve_without_request_options_uses_defaults(self, tmp_path):
        models_yaml = tmp_path / "models.yaml"
        _write_yaml(str(models_yaml), {
            "models": [{
                "id": "tts-default",
                "display_name": "Default",
                "provider": "irodori",
                "engine": "base",
                "defaults": {"response_format": "wav", "speed": 1.0},
                "provider_config": {"checkpoint": "Aratako/x"},
            }]
        })

        voices_dir = tmp_path / "voices"
        ego_dir = voices_dir / "egopulse"
        ego_dir.mkdir(parents=True)
        _write_yaml(str(ego_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "bindings": {
                "tts-default": {
                    "provider_config": {"ref_latent_path": "ref.pt", "seed": 42}
                }
            }
        })

        model_repo = YamlModelProfileRepository(yaml_path=str(models_yaml))
        voice_repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        resolver = TTSProfileResolver(model_resolver=ModelResolver(model_repo), voice_repo=voice_repo)

        _, _, config = resolver.resolve("tts-default", "egopulse")
        assert config["seed"] == 42
        assert config["speed"] == 1.0
