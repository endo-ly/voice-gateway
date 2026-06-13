"""Tests for Irodori CLI Builder."""

import pytest

from app.infrastructure.providers.irodori.cli_builder import IrodoriCliBuilder


class TestIrodoriCliBuilder:
    def test_build_base_command_returns_list_str(self):
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="Aratako/Irodori-TTS-500M-v2",
            text="こんにちは",
            ref_latent_path="assets/voices/egopulse/ref_latent.pt",
            output_wav_path="tmp/out.wav",
            model_device="cuda",
            codec_device="cuda",
            model_precision="bf16",
            codec_precision="bf16",
            num_steps=28,
            seed=42,
            speaker_kv_scale=1.1,
        )
        assert isinstance(cmd, list)
        for part in cmd:
            assert isinstance(part, str)
        assert "shell" not in str(cmd).lower()

    def test_build_base_command_includes_all_flags(self):
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="Aratako/Irodori-TTS-500M-v2",
            text="こんにちは",
            ref_latent_path="assets/voices/egopulse/ref_latent.pt",
            output_wav_path="tmp/out.wav",
            model_device="cuda",
            codec_device="cuda",
            model_precision="bf16",
            codec_precision="bf16",
            num_steps=28,
            seed=42,
            speaker_kv_scale=1.1,
            max_text_len=1024,
            max_caption_len=512,
        )
        cmd_str = " ".join(cmd)
        assert "--hf-checkpoint" in cmd_str
        assert "Aratako/Irodori-TTS-500M-v2" in cmd_str
        assert "--text" in cmd_str
        assert "こんにちは" in cmd_str
        assert "--ref-latent" in cmd_str
        assert "--output-wav" in cmd_str
        assert "--num-steps" in cmd_str
        assert "--seed" in cmd_str
        assert "--speaker-kv-scale" in cmd_str
        assert "--model-device" in cmd_str
        assert "--codec-device" in cmd_str
        assert "--model-precision" in cmd_str
        assert "--codec-precision" in cmd_str
        assert "--max-text-len" in cmd_str
        assert "1024" in cmd_str
        assert "--max-caption-len" in cmd_str
        assert "512" in cmd_str

    def test_build_base_command_starts_with_uv_run(self):
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="x",
            text="test",
            ref_latent_path="ref.pt",
            output_wav_path="out.wav",
            model_device="cpu",
            codec_device="cpu",
            model_precision="fp32",
            codec_precision="fp32",
            num_steps=10,
            seed=1,
            speaker_kv_scale=1.0,
        )
        assert cmd[0] == "uv"
        assert cmd[1] == "run"
        assert cmd[2] == "--no-sync"

    # --- WAV support ---

    def test_build_base_command_uses_ref_latent_when_both_provided(self):
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="x",
            text="test",
            ref_latent_path="ref.pt",
            ref_wav_path="ref.wav",
            output_wav_path="out.wav",
            model_device="cpu",
            codec_device="cpu",
            model_precision="fp32",
            codec_precision="fp32",
            num_steps=10,
            seed=1,
            speaker_kv_scale=1.0,
        )
        cmd_str = " ".join(cmd)
        assert "--ref-latent" in cmd_str
        assert "ref.pt" in cmd_str
        assert "--ref-wav" not in cmd_str

    def test_build_base_command_uses_ref_wav_when_no_ref_latent(self):
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="x",
            text="test",
            ref_wav_path="ref.wav",
            output_wav_path="out.wav",
            model_device="cpu",
            codec_device="cpu",
            model_precision="fp32",
            codec_precision="fp32",
            num_steps=10,
            seed=1,
            speaker_kv_scale=1.0,
        )
        cmd_str = " ".join(cmd)
        assert "--ref-wav" in cmd_str
        assert "ref.wav" in cmd_str
        assert "--ref-latent" not in cmd_str

    def test_build_base_command_raises_when_no_ref_at_all(self):
        with pytest.raises(ValueError, match="ref_latent_path or ref_wav_path"):
            IrodoriCliBuilder.build_base_command(
                checkpoint="x",
                text="test",
                output_wav_path="out.wav",
                model_device="cpu",
                codec_device="cpu",
                model_precision="fp32",
                codec_precision="fp32",
                num_steps=10,
                seed=1,
                speaker_kv_scale=1.0,
            )

    # --- VoiceDesign (unchanged) ---

    def test_build_voicedesign_command_includes_caption_and_no_ref(self):
        cmd = IrodoriCliBuilder.build_voicedesign_command(
            checkpoint="Aratako/Irodori-TTS-500M-v2-VoiceDesign",
            text="こんにちは",
            caption="20代前半の男性",
            output_wav_path="tmp/out.wav",
            model_device="cuda",
            codec_device="cuda",
            model_precision="bf16",
            codec_precision="bf16",
            num_steps=28,
            seed=42,
            max_text_len=1024,
            max_caption_len=512,
        )
        cmd_str = " ".join(cmd)
        assert "--caption" in cmd_str
        assert "20代前半の男性" in cmd_str
        assert "--no-ref" in cmd_str
        assert "--max-text-len" in cmd_str
        assert "1024" in cmd_str
        assert "--max-caption-len" in cmd_str
        assert "512" in cmd_str
        # voicedesign should NOT have --ref-latent or --speaker-kv-scale
        assert "--ref-latent" not in cmd_str
        assert "--speaker-kv-scale" not in cmd_str

    def test_build_base_command_no_shell_injection_vector(self):
        """Ensure command is list[str], not a single shell string."""
        cmd = IrodoriCliBuilder.build_base_command(
            checkpoint="x",
            text="test; rm -rf /",
            ref_latent_path="ref.pt",
            output_wav_path="out.wav",
            model_device="cpu",
            codec_device="cpu",
            model_precision="fp32",
            codec_precision="fp32",
            num_steps=10,
            seed=1,
            speaker_kv_scale=1.0,
        )
        # The text "test; rm -rf /" should be a single element, not split
        assert any("test; rm -rf /" in part for part in cmd)
