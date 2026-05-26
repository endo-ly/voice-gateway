"""Shared model resolution service."""

from app.domain.entities.model_profile import ModelProfile
from app.domain.errors import ModelNotFoundError
from app.domain.interfaces.model_profile_repository import ModelProfileRepository


class ModelResolver:
    def __init__(self, model_repo: ModelProfileRepository) -> None:
        self._model_repo = model_repo

    def get_model(self, model_id: str, direction: str | None = None) -> ModelProfile:
        model = self._model_repo.get_by_id(model_id)
        if direction is not None and model.direction != direction:
            raise ModelNotFoundError(model_id)
        return model
