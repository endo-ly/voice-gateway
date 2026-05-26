"""Tests for ErrorMapper."""

from app.application.services.error_mapper import ErrorMapper
from app.domain.errors import (
    ModelNotFoundError,
    VoiceNotFoundError,
    VoiceBindingNotFoundError,
    UnsupportedResponseFormatError,
    UnsupportedSpeedError,
    ProviderExecutionError,
    ProviderTimeoutError,
    VoiceGatewayError,
)


class TestErrorMapper:
    def test_model_not_found_maps_to_404(self):
        err = ModelNotFoundError("bad-model")
        status, body = ErrorMapper.map(err)
        assert status == 404
        assert body["error"]["code"] == "model_not_found"

    def test_voice_not_found_maps_to_404(self):
        err = VoiceNotFoundError("bad-voice")
        status, body = ErrorMapper.map(err)
        assert status == 404
        assert body["error"]["code"] == "voice_not_found"

    def test_voice_binding_not_found_maps_to_409(self):
        err = VoiceBindingNotFoundError("ego", "qwen")
        status, body = ErrorMapper.map(err)
        assert status == 409
        assert body["error"]["code"] == "voice_binding_not_found"

    def test_unsupported_format_maps_to_400(self):
        err = UnsupportedResponseFormatError("mp3")
        status, body = ErrorMapper.map(err)
        assert status == 400
        assert body["error"]["code"] == "unsupported_response_format"

    def test_unsupported_speed_maps_to_400(self):
        err = UnsupportedSpeedError(2.0)
        status, body = ErrorMapper.map(err)
        assert status == 400
        assert body["error"]["code"] == "unsupported_speed"

    def test_provider_timeout_maps_to_504(self):
        err = ProviderTimeoutError("irodori")
        status, body = ErrorMapper.map(err)
        assert status == 504
        assert body["error"]["code"] == "provider_timeout"

    def test_provider_execution_maps_to_500(self):
        err = ProviderExecutionError("irodori", "exit code 1")
        status, body = ErrorMapper.map(err)
        assert status == 500
        assert body["error"]["code"] == "provider_execution_error"

    def test_unknown_error_maps_to_500(self):
        err = VoiceGatewayError("unknown")
        status, body = ErrorMapper.map(err)
        assert status == 500
        assert body["error"]["code"] == "internal_error"

    def test_error_body_has_openai_compatible_format(self):
        err = ModelNotFoundError("bad-model")
        status, body = ErrorMapper.map(err)
        assert "error" in body
        assert "message" in body["error"]
        assert "type" in body["error"]
        assert body["error"]["type"] == "invalid_request_error"
