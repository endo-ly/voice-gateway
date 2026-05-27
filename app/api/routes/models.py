"""Models list route."""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_model_repo
from app.application.use_cases.list_models import ListModels
from app.infrastructure.repositories.yaml_model_profile_repository import YamlModelProfileRepository

router = APIRouter()


@router.get("/v1/models")
async def list_models(
    direction: Literal["tts", "stt"] | None = Query(None, description="Filter by direction: tts or stt"),
    repo: YamlModelProfileRepository = Depends(get_model_repo),
) -> dict:
    uc = ListModels(model_repo=repo)
    models = uc.execute()
    if direction:
        models = [m for m in models if m.direction == direction]
    return {
        "object": "list",
        "data": [
            {
                "id": m.id,
                "object": m.object,
                "display_name": m.display_name,
                "direction": m.direction,
            }
            for m in models
        ],
    }
