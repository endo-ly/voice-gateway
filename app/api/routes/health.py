"""Health check route."""

import asyncio

from fastapi import APIRouter, Request

router = APIRouter()


async def _provider_status(registry, names):
    """Build per-provider registered/loaded/engineReachable status dict."""
    status = {}
    for name in names:
        try:
            provider = registry.get(name)
        except Exception:
            provider = None
        if provider is None:
            status[name] = {"registered": False, "loaded": False}
        else:
            info: dict = {"registered": True}
            loaded = getattr(provider, "is_loaded", None)
            if callable(loaded):
                info["loaded"] = loaded()
            else:
                info["loaded"] = True
            health = getattr(provider, "health", None)
            if asyncio.iscoroutinefunction(health):
                engine_status = await health()
                info.update(engine_status)
            status[name] = info
    return status


@router.get("/health")
async def health(request: Request) -> dict:
    mode = getattr(request.app.state, "mode", "all")

    providers = {}
    if mode in ("tts", "all"):
        registry = getattr(request.app.state, "tts_registry", None)
        names = getattr(request.app.state, "tts_provider_names", [])
        providers["tts"] = {
            "enabled": True,
            "providers": await _provider_status(registry, names),
        }
    else:
        providers["tts"] = {"enabled": False, "providers": {}}

    if mode in ("stt", "all"):
        registry = getattr(request.app.state, "stt_registry", None)
        names = getattr(request.app.state, "stt_provider_names", [])
        providers["stt"] = {
            "enabled": True,
            "providers": await _provider_status(registry, names),
        }
    else:
        providers["stt"] = {"enabled": False, "providers": {}}

    result: dict = {"status": "ok", "mode": mode, "providers": providers}
    return result
