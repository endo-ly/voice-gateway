"""Capabilities route."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.schemas.capabilities import CapabilitiesResponse, DirectionCapabilities

router = APIRouter()


@router.get("/v1/capabilities")
async def capabilities(request: Request) -> JSONResponse:
    mode = getattr(request.app.state, "mode", "all")
    tts_providers = getattr(request.app.state, "tts_provider_names", [])
    stt_providers = getattr(request.app.state, "stt_provider_names", [])

    response = CapabilitiesResponse(
        tts=DirectionCapabilities(
            enabled=mode in ("tts", "all"),
            providers=tts_providers,
        ),
        stt=DirectionCapabilities(
            enabled=mode in ("stt", "all"),
            providers=stt_providers,
        ),
    )
    return JSONResponse(content=response.model_dump())
