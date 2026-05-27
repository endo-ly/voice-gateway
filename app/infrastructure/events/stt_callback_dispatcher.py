"""STT callback dispatcher for fire-and-forget event notifications."""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.domain.value_objects.transcription_result import TranscriptionResult


@dataclass(frozen=True)
class CallbackWarning:
    callback_name: str
    message: str


def dispatch_stt_callbacks(
    result: TranscriptionResult,
    callback_url: str,
    timeout_ms: int = 3000,
) -> CallbackWarning | None:
    """Dispatch a single STT callback.

    Runs synchronously; callers should use asyncio.to_thread() for non-blocking dispatch.
    Returns CallbackWarning on failure, None on success.
    """
    if not callback_url:
        return CallbackWarning(
            callback_name="unknown",
            message="callback url is empty",
        )

    payload = json.dumps(result.model_dump()).encode("utf-8")
    request = Request(
        callback_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_ms / 1000) as response:
            if response.status < 200 or response.status >= 300:
                return CallbackWarning(
                    callback_name="stt_callback",
                    message=f"HTTP {response.status}",
                )
    except HTTPError as error:
        return CallbackWarning(callback_name="stt_callback", message=f"HTTP {error.code}")
    except URLError as error:
        return CallbackWarning(callback_name="stt_callback", message=str(error.reason))
    except TimeoutError:
        return CallbackWarning(callback_name="stt_callback", message="callback timed out")
    return None
