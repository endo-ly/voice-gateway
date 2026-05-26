"""Health check route."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    mode = getattr(request.app.state, "mode", "all")
    tts_providers = getattr(request.app.state, "tts_provider_names", [])
    stt_providers = getattr(request.app.state, "stt_provider_names", [])

    providers = {}
    if mode in ("tts", "all"):
        providers["tts"] = {
            "enabled": True,
            "providers": {name: {"loaded": True} for name in tts_providers},
        }
    else:
        providers["tts"] = {"enabled": False, "providers": {}}

    if mode in ("stt", "all"):
        providers["stt"] = {
            "enabled": True,
            "providers": {name: {"loaded": True} for name in stt_providers},
        }
    else:
        providers["stt"] = {"enabled": False, "providers": {}}

    result: dict = {"status": "ok", "mode": mode, "providers": providers}
    return result
