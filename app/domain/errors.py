"""Domain errors for voice-gateway."""


class VoiceGatewayError(Exception):
    """Base error for all voice-gateway domain errors."""


class ModelNotFoundError(VoiceGatewayError):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"Model not found: {model_id}")


class VoiceNotFoundError(VoiceGatewayError):
    def __init__(self, voice_id: str) -> None:
        self.voice_id = voice_id
        super().__init__(f"Voice not found: {voice_id}")


class VoiceBindingNotFoundError(VoiceGatewayError):
    def __init__(self, voice_id: str, model_id: str) -> None:
        self.voice_id = voice_id
        self.model_id = model_id
        super().__init__(
            f"Voice '{voice_id}' does not support model '{model_id}'"
        )


class UnsupportedResponseFormatError(VoiceGatewayError):
    def __init__(self, response_format: str) -> None:
        self.format = response_format
        super().__init__(f"Unsupported response format: {response_format}")


class UnsupportedSpeedError(VoiceGatewayError):
    def __init__(self, speed: float) -> None:
        self.speed = speed
        super().__init__(f"Unsupported speed: {speed}")


class ProviderNotFoundError(VoiceGatewayError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Provider not found: {provider}")


class ProviderExecutionError(VoiceGatewayError):
    def __init__(self, provider_name: str, detail: str) -> None:
        self.provider_name = provider_name
        self.detail = detail
        super().__init__(
            f"Provider '{provider_name}' execution failed: {detail}"
        )


class ProviderTimeoutError(VoiceGatewayError):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(f"Provider '{provider_name}' timed out")


class InvalidProfileError(VoiceGatewayError):
    pass


class InvalidProviderConfigError(VoiceGatewayError):
    def __init__(self, provider_name: str, engine: str, detail: str) -> None:
        self.provider_name = provider_name
        self.engine = engine
        super().__init__(
            f"Invalid provider_config for '{provider_name}' engine '{engine}': {detail}"
        )


# ── STT ──

class AudioValidationError(VoiceGatewayError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class AudioTooLargeError(VoiceGatewayError):
    def __init__(self, max_size_mb: int) -> None:
        self.max_size_mb = max_size_mb
        super().__init__(f"Audio file exceeds size limit of {max_size_mb}MB")


class AudioTooLongError(VoiceGatewayError):
    def __init__(self, max_seconds: float, actual_seconds: float) -> None:
        self.max_seconds = max_seconds
        self.actual_seconds = actual_seconds
        super().__init__(f"Audio duration {actual_seconds}s exceeds limit of {max_seconds}s")


class TranscriptionFailedError(VoiceGatewayError):
    def __init__(self, provider_name: str, detail: str) -> None:
        self.provider_name = provider_name
        self.detail = detail
        super().__init__(f"Transcription failed from '{provider_name}': {detail}")


class ModelNotLoadedError(VoiceGatewayError):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"Model not loaded: {model_id}")
