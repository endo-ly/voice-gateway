"""Tests for VoiceProfile entity."""

import pytest
from pydantic import ValidationError

from app.domain.entities.voice_profile import VoiceBinding, VoiceDefaults, VoiceProfile


class TestVoiceDefaults:
    def test_default_values(self):
        d = VoiceDefaults()
        assert d.preferred_model == "tts-default"
        assert d.response_format == "wav"
        assert d.speed == 1.0


class TestVoiceBinding:
    def test_with_provider_config(self):
        b = VoiceBinding(
            provider_config={"ref_latent_path": "foo.pt", "seed": 42}
        )
        assert b.provider_config["seed"] == 42

    def test_empty_provider_config(self):
        b = VoiceBinding()
        assert b.provider_config == {}


class TestVoiceProfile:
    def test_valid_minimal(self):
        vp = VoiceProfile(voice_id="test", display_name="Test")
        assert vp.voice_id == "test"
        assert vp.display_name == "Test"

    def test_with_all_fields(self):
        vp = VoiceProfile(
            voice_id="egopulse",
            display_name="EgoPulse",
            description="静かで知的",
            defaults=VoiceDefaults(
                preferred_model="tts-default",
                response_format="wav",
                speed=1.0,
            ),
            bindings={
                "tts-default": VoiceBinding(
                    provider_config={
                        "ref_latent_path": "assets/voices/egopulse/ref_latent.pt",
                        "seed": 42,
                    }
                ),
                "irodori-base": VoiceBinding(
                    provider_config={
                        "ref_latent_path": "assets/voices/egopulse/ref_latent.pt",
                        "seed": 42,
                    }
                ),
            },
        )
        assert vp.voice_id == "egopulse"
        assert "tts-default" in vp.bindings
        assert vp.bindings["tts-default"].provider_config["seed"] == 42

    def test_missing_voice_id_raises(self):
        with pytest.raises(ValidationError):
            VoiceProfile(display_name="Test")

    def test_description_defaults_empty(self):
        vp = VoiceProfile(voice_id="test", display_name="Test")
        assert vp.description == ""

    def test_bindings_can_be_empty(self):
        vp = VoiceProfile(voice_id="test", display_name="Test", bindings={})
        assert vp.bindings == {}

    def test_from_yaml_like_dict(self):
        data = {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "description": "静かで知的な男性声",
            "defaults": {
                "preferred_model": "tts-default",
                "response_format": "wav",
                "speed": 1.0,
            },
            "bindings": {
                "tts-default": {
                    "provider_config": {
                        "ref_latent_path": "assets/voices/egopulse/ref_latent.pt",
                        "seed": 42,
                        "num_steps": 28,
                        "speaker_kv_scale": 1.1,
                    }
                },
                "aivis-default": {
                    "provider_config": {"speaker": 888753760}
                },
            },
        }
        vp = VoiceProfile.model_validate(data)
        assert vp.voice_id == "egopulse"
        assert vp.bindings["tts-default"].provider_config["num_steps"] == 28
        assert vp.bindings["aivis-default"].provider_config["speaker"] == 888753760

    def test_binding_missing_for_model(self):
        vp = VoiceProfile(
            voice_id="test",
            display_name="Test",
            bindings={
                "tts-default": VoiceBinding(provider_config={"seed": 1}),
            },
        )
        assert "irodori-base" not in vp.bindings
