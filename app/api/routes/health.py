"""Health check route."""

from fastapi import APIRouter, Request

router = APIRouter()


def _provider_status(registry, names):
    """Build per-provider registered/loaded status dict."""
    status = {}
    for name in names:
        try:
            provider = registry.get(name)
        except Exception:
            provider = None
        if provider is None:
            status[name] = {"registered": False, "loaded": False}
        else:
            loaded = getattr(provider, "is_loaded", lambda: True)()
            status[name] = {"registered": True, "loaded": loaded}
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
            "providers": _provider_status(registry, names),
        }
    else:
        providers["tts"] = {"enabled": False, "providers": {}}

    if mode in ("stt", "all"):
        registry = getattr(request.app.state, "stt_registry", None)
        names = getattr(request.app.state, "stt_provider_names", [])
        providers["stt"] = {
            "enabled": True,
            "providers": _provider_status(registry, names),
        }
    else:
        providers["stt"] = {"enabled": False, "providers": {}}

    result: dict = {"status": "ok", "mode": mode, "providers": providers}
    return result
