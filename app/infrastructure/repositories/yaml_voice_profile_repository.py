"""YAML-backed VoiceProfileRepository."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.domain.entities.voice_profile import VoiceProfile
from app.domain.errors import InvalidProfileError, VoiceNotFoundError
from app.domain.interfaces.voice_profile_repository import VoiceProfileRepository


class YamlVoiceProfileRepository:
    def __init__(self, voices_dir: str) -> None:
        self._voices_dir = Path(voices_dir)
        self._cache: list[VoiceProfile] | None = None

    def _load(self) -> list[VoiceProfile]:
        if self._cache is not None:
            return self._cache

        profiles: list[VoiceProfile] = []

        if not self._voices_dir.exists():
            self._cache = profiles
            return self._cache

        for subdir in sorted(self._voices_dir.iterdir()):
            if not subdir.is_dir():
                continue
            yaml_path = subdir / "profile.yaml"
            if not yaml_path.exists():
                continue

            try:
                with open(yaml_path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise InvalidProfileError(
                    f"Invalid YAML in {yaml_path}: {e}"
                ) from e

            try:
                profiles.append(VoiceProfile.model_validate(raw))
            except ValidationError as e:
                raise InvalidProfileError(
                    f"Invalid voice profile in {yaml_path}: {e}"
                ) from e

        ids = [v.voice_id for v in profiles]
        duplicate_ids = sorted({voice_id for voice_id in ids if ids.count(voice_id) > 1})
        if duplicate_ids:
            raise InvalidProfileError(
                f"Duplicate voice id(s): {', '.join(duplicate_ids)}"
            )

        self._cache = profiles
        return self._cache

    def list_all(self) -> list[VoiceProfile]:
        return list(self._load())

    def get_by_id(self, voice_id: str) -> VoiceProfile:
        for voice in self._load():
            if voice.voice_id == voice_id:
                return voice
        raise VoiceNotFoundError(voice_id)

    def get_profile_path(self, voice_id: str) -> Path:
        return self._voices_dir / voice_id / "profile.yaml"

    def register(self, profile: VoiceProfile) -> bool:
        """Append a runtime-constructed profile. Returns False if a profile
        with the same voice_id already exists (static YAML wins)."""
        profiles = self._load()
        for existing in profiles:
            if existing.voice_id == profile.voice_id:
                return False
        profiles.append(profile)
        return True
