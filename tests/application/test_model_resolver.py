"""Tests for ModelResolver."""

import pytest

from app.application.services.model_resolver import ModelResolver
from app.domain.entities.model_profile import ModelProfile
from app.domain.errors import ModelNotFoundError


class FakeModelRepo:
    def __init__(self, models=None):
        self._models = {m.id: m for m in (models or [])}

    def get_by_id(self, model_id):
        if model_id not in self._models:
            raise ModelNotFoundError(model_id)
        return self._models[model_id]

    def list_all(self):
        return list(self._models.values())


class TestModelResolver:
    def test_get_model_no_direction_filter(self):
        model = ModelProfile(id="test", display_name="Test", provider="fake", engine="base")
        resolver = ModelResolver(FakeModelRepo([model]))
        result = resolver.get_model("test")
        assert result.id == "test"

    def test_get_model_with_matching_direction(self):
        model = ModelProfile(id="test", display_name="Test", provider="fake", engine="base", direction="tts")
        resolver = ModelResolver(FakeModelRepo([model]))
        result = resolver.get_model("test", direction="tts")
        assert result.id == "test"

    def test_get_model_rejects_wrong_direction(self):
        model = ModelProfile(id="test", display_name="Test", provider="fake", engine="base", direction="tts")
        resolver = ModelResolver(FakeModelRepo([model]))
        with pytest.raises(ModelNotFoundError):
            resolver.get_model("test", direction="stt")

    def test_get_model_not_found(self):
        resolver = ModelResolver(FakeModelRepo([]))
        with pytest.raises(ModelNotFoundError):
            resolver.get_model("nonexistent")
