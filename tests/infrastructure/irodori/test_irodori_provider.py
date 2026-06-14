"""Tests for IrodoriProvider."""

import os
from pathlib import Path

import pytest

from app.domain.errors import InvalidProviderConfigError, ProviderExecutionError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.infrastructure.providers.irodori.provider import IrodoriProvider


def _make_request(**overrides) -> ProviderSynthesisRequest:
    defaults: dict = {
        "model_id": "tts-default",
        "voice_id": "egopulse",
        "text": "こんにちは",
        "provider": "irodori",
        "engine": "base",
        "provider_config": {
            "checkpoint": "Aratako/Irodori-TTS-500M-v2",
            "ref_latent_path": "assets/voices/egopulse/ref_latent.pt",
            "seed": 42,
            "num_steps": 28,
            "max_text_len": 1024,
            "max_caption_len": 512,
            "speaker_kv_scale": 1.1,
            "model_device": "cpu",
            "codec_device": "cpu",
            "model_precision": "fp32",
            "codec_precision": "fp32",
        },
    }
    defaults.update(overrides)
    return ProviderSynthesisRequest(**defaults)


class FakeSubprocessRunner:
    """Test double for SubprocessRunner that creates wav files."""

    def __init__(self, wav_bytes: bytes | None = None) -> None:
        self._wav_bytes = wav_bytes
        self.cmd: list[str] | None = None
        self.cwd: str | None = None

    async def run(self, cmd: list[str], cwd: str | None = None) -> str:
        self.cmd = cmd
        self.cwd = cwd
        if self._wav_bytes is None:
            return ""
        for i, part in enumerate(cmd):
            if part == "--output-wav" and i + 1 < len(cmd):
                with open(cmd[i + 1], "wb") as f:
                    f.write(self._wav_bytes)
        return ""


WAV_HEADER = (
    b"RIFF\x24\x00\x00\x00WAVEfmt "
    b"\x10\x00\x00\x00\x01\x00\x01\x00"
    b"D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00"
    b"data\x00\x00\x00\x00"
)


class TestIrodoriProvider:
    def test_provider_name(self, tmp_path):
        p = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        assert p.provider_name == "irodori"

    async def test_synthesize_with_mock_subprocess(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        provider._client._runner = FakeSubprocessRunner(wav_bytes=WAV_HEADER)

        result = await provider.synthesize(_make_request())
        assert result.audio_bytes.startswith(b"RIFF")
        assert result.media_type == "audio/wav"

    async def test_synthesize_resolves_relative_paths_for_irodori_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir="tmp",
            base_dir=str(tmp_path),
            backend="cli",
        )
        runner = FakeSubprocessRunner(wav_bytes=WAV_HEADER)
        provider._client._runner = runner

        await provider.synthesize(_make_request())

        assert runner.cmd is not None
        assert runner.cwd == "/opt/irodori"
        cmd = runner.cmd
        assert cmd[cmd.index("--ref-latent") + 1] == str(
            (tmp_path / "assets/voices/egopulse/ref_latent.pt").resolve()
        )
        assert cmd[cmd.index("--max-text-len") + 1] == "1024"
        assert cmd[cmd.index("--max-caption-len") + 1] == "512"
        assert Path(cmd[cmd.index("--output-wav") + 1]).is_absolute()

    async def test_tmp_wav_deleted_after_synthesize(self, tmp_path):
        created_files: list[str] = []

        class TrackingRunner(FakeSubprocessRunner):
            async def run(self, cmd, cwd=None):  # type: ignore[override]
                for i, part in enumerate(cmd):
                    if part == "--output-wav" and i + 1 < len(cmd):
                        created_files.append(cmd[i + 1])
                return await super().run(cmd)

        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        provider._client._runner = TrackingRunner(wav_bytes=WAV_HEADER)
        await provider.synthesize(_make_request())

        for f in created_files:
            assert not os.path.exists(f), f"tmp wav should be deleted: {f}"

    async def test_synthesize_missing_output_raises(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        provider._client._runner = FakeSubprocessRunner(wav_bytes=None)

        with pytest.raises(ProviderExecutionError):
            await provider.synthesize(_make_request())

    async def test_synthesize_empty_output_raises(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        provider._client._runner = FakeSubprocessRunner(wav_bytes=b"")

        with pytest.raises(ProviderExecutionError):
            await provider.synthesize(_make_request())

    def test_concurrency_limit_is_1(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        assert provider._semaphore._value == 1

    def test_backend_server_creates_server_client(self, tmp_path):
        from app.infrastructure.providers.irodori.server_client import IrodoriServerClient

        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="server",
        )
        assert isinstance(provider._client, IrodoriServerClient)

    def test_backend_cli_creates_cli_client(self, tmp_path):
        from app.infrastructure.providers.irodori.cli_client import IrodoriCliClient

        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        assert isinstance(provider._client, IrodoriCliClient)

    def test_concurrency_limit_custom(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            max_concurrency=4,
            backend="cli",
        )
        assert provider._semaphore._value == 4

    async def test_missing_checkpoint_raises_config_error(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        with pytest.raises(InvalidProviderConfigError, match="checkpoint"):
            await provider.synthesize(
                _make_request(provider_config={"ref_latent_path": "ref.pt"})
            )

    async def test_base_missing_ref_raises_config_error(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        with pytest.raises(InvalidProviderConfigError, match="ref_latent_path"):
            await provider.synthesize(
                _make_request(provider_config={"checkpoint": "Aratako/x"})
            )

    async def test_voicedesign_missing_caption_raises_config_error(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        with pytest.raises(InvalidProviderConfigError, match="caption"):
            await provider.synthesize(
                _make_request(
                    engine="voicedesign",
                    provider_config={"checkpoint": "Aratako/x"},
                )
            )

    async def test_valid_config_does_not_raise(self, tmp_path):
        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="cli",
        )
        provider._client._runner = FakeSubprocessRunner(wav_bytes=WAV_HEADER)
        result = await provider.synthesize(_make_request())
        assert result.audio_bytes.startswith(b"RIFF")

    async def test_server_backend_does_not_require_checkpoint(self, tmp_path, monkeypatch):
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=WAV_HEADER)

        transport = httpx.MockTransport(handler)
        original = httpx.AsyncClient

        def factory(*args, **kwargs):
            kwargs["transport"] = transport
            return original(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", factory)

        provider = IrodoriProvider(
            irodori_repo_dir="/opt/irodori",
            tmp_dir=str(tmp_path),
            base_dir=str(tmp_path),
            backend="server",
        )
        result = await provider.synthesize(
            _make_request(
                provider_config={
                    "ref_wav_path": "/abs/ref.wav",
                    "num_steps": 28,
                    "seed": 0,
                }
            )
        )
        assert result.audio_bytes.startswith(b"RIFF")
