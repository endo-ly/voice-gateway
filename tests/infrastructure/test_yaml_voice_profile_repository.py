"""Tests for YAML VoiceProfileRepository."""

import pytest
import yaml

from app.domain.errors import InvalidProfileError, VoiceNotFoundError
from app.domain.entities.voice_profile import VoiceProfile
from app.infrastructure.repositories.yaml_voice_profile_repository import (
    YamlVoiceProfileRepository,
)


def _write_yaml(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


class TestYamlVoiceProfileRepository:
    def test_list_all_scans_subdirs(self, tmp_path):
        voices_dir = tmp_path / "voices"
        egopulse_dir = voices_dir / "egopulse"
        egopulse_dir.mkdir(parents=True)
        _write_yaml(str(egopulse_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
            "description": "静かで知的",
            "bindings": {"tts-default": {"provider_config": {"seed": 42}}},
        })

        lira_dir = voices_dir / "lira"
        lira_dir.mkdir()
        _write_yaml(str(lira_dir / "profile.yaml"), {
            "voice_id": "lira",
            "display_name": "Lira",
        })

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        voices = repo.list_all()
        assert len(voices) == 2
        ids = {v.voice_id for v in voices}
        assert ids == {"egopulse", "lira"}

    def test_get_by_id_found(self, tmp_path):
        voices_dir = tmp_path / "voices"
        egopulse_dir = voices_dir / "egopulse"
        egopulse_dir.mkdir(parents=True)
        _write_yaml(str(egopulse_dir / "profile.yaml"), {
            "voice_id": "egopulse",
            "display_name": "EgoPulse",
        })

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        voice = repo.get_by_id("egopulse")
        assert voice.voice_id == "egopulse"
        assert voice.display_name == "EgoPulse"

    def test_get_by_id_not_found_raises(self, tmp_path):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        with pytest.raises(VoiceNotFoundError) as exc_info:
            repo.get_by_id("nonexistent")
        assert exc_info.value.voice_id == "nonexistent"

    def test_invalid_profile_raises(self, tmp_path):
        voices_dir = tmp_path / "voices"
        bad_dir = voices_dir / "bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / "profile.yaml").write_text("voice_id:", encoding="utf-8")  # missing required

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        with pytest.raises(InvalidProfileError):
            repo.list_all()

    def test_empty_voices_dir_returns_empty_list(self, tmp_path):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        assert repo.list_all() == []

    def test_subdir_without_profile_yaml_is_skipped(self, tmp_path):
        voices_dir = tmp_path / "voices"
        empty_dir = voices_dir / "noyaml"
        empty_dir.mkdir(parents=True)

        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        assert repo.list_all() == []

    def test_duplicate_voice_id_raises(self, tmp_path):
        voices_dir = tmp_path / "voices"
        voice1_dir = voices_dir / "voice-a"
        voice1_dir.mkdir(parents=True)
        _write_yaml(str(voice1_dir / "profile.yaml"), {
            "voice_id": "same-voice",
            "display_name": "Voice A",
        })
        voice2_dir = voices_dir / "voice-b"
        voice2_dir.mkdir()
        _write_yaml(str(voice2_dir / "profile.yaml"), {
            "voice_id": "same-voice",
            "display_name": "Voice B",
        })
        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))
        with pytest.raises(InvalidProfileError, match="Duplicate voice id"):
            repo.list_all()

    def test_register_appends_runtime_profile(self, tmp_path):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))

        from app.domain.entities.voice_profile import (
            VoiceBinding,
            VoiceDefaults,
            VoiceProfile,
        )

        profile = VoiceProfile(
            voice_id="dynamic",
            display_name="Dynamic",
            defaults=VoiceDefaults(preferred_model="aivis-default"),
            bindings={
                "aivis-default": VoiceBinding(provider_config={"speaker": 1})
            },
        )

        assert repo.register(profile) is True
        loaded = repo.get_by_id("dynamic")
        assert loaded.display_name == "Dynamic"
        assert loaded.bindings["aivis-default"].provider_config == {"speaker": 1}

    def test_register_returns_false_when_voice_id_exists_statically(self, tmp_path):
        voices_dir = tmp_path / "voices"
        static_dir = voices_dir / "static"
        static_dir.mkdir(parents=True)
        _write_yaml(str(static_dir / "profile.yaml"), {
            "voice_id": "dup",
            "display_name": "Static",
        })
        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))

        from app.domain.entities.voice_profile import VoiceProfile

        assert repo.register(VoiceProfile(voice_id="dup", display_name="Dynamic")) is False
        assert repo.get_by_id("dup").display_name == "Static"

    def test_register_does_not_trigger_duplicate_error_on_subsequent_list(
        self, tmp_path
    ):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        repo = YamlVoiceProfileRepository(voices_dir=str(voices_dir))

        from app.domain.entities.voice_profile import VoiceProfile

        repo.register(VoiceProfile(voice_id="d1", display_name="D1"))
        repo.register(VoiceProfile(voice_id="d1", display_name="D1-again"))
        assert len(repo.list_all()) == 1
