"""Maps domain errors to HTTP status codes and response bodies."""

from app.domain.errors import (
    VoiceGatewayError,
    ModelNotFoundError,
    VoiceNotFoundError,
    VoiceBindingNotFoundError,
    UnsupportedResponseFormatError,
    UnsupportedSpeedError,
    ProviderExecutionError,
    ProviderTimeoutError,
    InvalidProviderConfigError,
    AudioValidationError,
    AudioTooLargeError,
    AudioTooLongError,
    TranscriptionFailedError,
    ModelNotLoadedError,
)


class ErrorMapper:
    @staticmethod
    def map(error: VoiceGatewayError) -> tuple[int, dict]:
        mapping: dict[type, tuple[int, str, str]] = {
            ModelNotFoundError: (404, "model_not_found", "model"),
            VoiceNotFoundError: (404, "voice_not_found", "voice"),
            VoiceBindingNotFoundError: (409, "voice_binding_not_found", "voice"),
            UnsupportedResponseFormatError: (400, "unsupported_response_format", "response_format"),
            UnsupportedSpeedError: (400, "unsupported_speed", "speed"),
            ProviderTimeoutError: (504, "provider_timeout", None),
            ProviderExecutionError: (500, "provider_execution_error", None),
            InvalidProviderConfigError: (400, "invalid_provider_config", None),
            AudioValidationError: (400, "audio_validation_error", "file"),
            AudioTooLargeError: (400, "audio_too_large", "file"),
            AudioTooLongError: (400, "audio_too_long", "file"),
            TranscriptionFailedError: (500, "transcription_failed", None),
            ModelNotLoadedError: (503, "model_not_loaded", None),
        }

        for error_type, (status, code, param) in mapping.items():
            if isinstance(error, error_type):
                return status, {
                    "error": {
                        "message": str(error),
                        "type": "server_error" if status >= 500 else "invalid_request_error",
                        "param": param,
                        "code": code,
                    }
                }

        return 500, {
            "error": {
                "message": str(error),
                "type": "internal_error",
                "param": None,
                "code": "internal_error",
            }
        }
