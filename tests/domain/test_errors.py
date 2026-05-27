"""Tests for domain errors."""

from app.domain.errors import (
    InvalidProfileError,
    ModelNotFoundError,
    ProviderExecutionError,
    ProviderNotFoundError,
    ProviderTimeoutError,
    VoiceGatewayError,
    UnsupportedResponseFormatError,
    UnsupportedSpeedError,
    VoiceBindingNotFoundError,
    VoiceNotFoundError,
)


class TestVoiceGatewayErrorBase:
    def test_inherits_exception(self):
        assert issubclass(VoiceGatewayError, Exception)

    def test_can_construct_with_message(self):
        err = VoiceGatewayError("something broke")
        assert str(err) == "something broke"


class TestModelNotFoundError:
    def test_stores_model_id(self):
        err = ModelNotFoundError("bad-model")
        assert err.model_id == "bad-model"

    def test_message_contains_model_id(self):
        err = ModelNotFoundError("bad-model")
        assert "bad-model" in str(err)

    def test_inherits_base(self):
        assert issubclass(ModelNotFoundError, VoiceGatewayError)


class TestVoiceNotFoundError:
    def test_stores_voice_id(self):
        err = VoiceNotFoundError("bad-voice")
        assert err.voice_id == "bad-voice"

    def test_message_contains_voice_id(self):
        err = VoiceNotFoundError("bad-voice")
        assert "bad-voice" in str(err)

    def test_inherits_base(self):
        assert issubclass(VoiceNotFoundError, VoiceGatewayError)


class TestVoiceBindingNotFoundError:
    def test_stores_voice_and_model_id(self):
        err = VoiceBindingNotFoundError("egopulse", "qwen-tts")
        assert err.voice_id == "egopulse"
        assert err.model_id == "qwen-tts"

    def test_message_contains_both_ids(self):
        err = VoiceBindingNotFoundError("egopulse", "qwen-tts")
        msg = str(err)
        assert "egopulse" in msg
        assert "qwen-tts" in msg

    def test_inherits_base(self):
        assert issubclass(VoiceBindingNotFoundError, VoiceGatewayError)


class TestUnsupportedResponseFormatError:
    def test_stores_format(self):
        err = UnsupportedResponseFormatError("mp3")
        assert err.format == "mp3"

    def test_message_contains_format(self):
        err = UnsupportedResponseFormatError("mp3")
        assert "mp3" in str(err)

    def test_inherits_base(self):
        assert issubclass(UnsupportedResponseFormatError, VoiceGatewayError)


class TestUnsupportedSpeedError:
    def test_stores_speed(self):
        err = UnsupportedSpeedError(2.0)
        assert err.speed == 2.0

    def test_message_contains_speed(self):
        err = UnsupportedSpeedError(2.0)
        assert "2.0" in str(err)

    def test_inherits_base(self):
        assert issubclass(UnsupportedSpeedError, VoiceGatewayError)


class TestProviderNotFoundError:
    def test_stores_provider(self):
        err = ProviderNotFoundError("unknown")
        assert err.provider == "unknown"

    def test_message_contains_provider(self):
        err = ProviderNotFoundError("unknown")
        assert "unknown" in str(err)

    def test_inherits_base(self):
        assert issubclass(ProviderNotFoundError, VoiceGatewayError)


class TestProviderExecutionError:
    def test_stores_provider_name_and_detail(self):
        err = ProviderExecutionError("irodori", "exit code 1")
        assert err.provider_name == "irodori"
        assert err.detail == "exit code 1"

    def test_message_contains_context(self):
        err = ProviderExecutionError("irodori", "exit code 1")
        msg = str(err)
        assert "irodori" in msg
        assert "exit code 1" in msg

    def test_inherits_base(self):
        assert issubclass(ProviderExecutionError, VoiceGatewayError)


class TestProviderTimeoutError:
    def test_stores_provider_name(self):
        err = ProviderTimeoutError("irodori")
        assert err.provider_name == "irodori"

    def test_message_contains_provider(self):
        err = ProviderTimeoutError("irodori")
        assert "irodori" in str(err)

    def test_inherits_base(self):
        assert issubclass(ProviderTimeoutError, VoiceGatewayError)


class TestInvalidProfileError:
    def test_construct_with_message(self):
        err = InvalidProfileError("bad yaml")
        assert "bad yaml" in str(err)

    def test_inherits_base(self):
        assert issubclass(InvalidProfileError, VoiceGatewayError)
