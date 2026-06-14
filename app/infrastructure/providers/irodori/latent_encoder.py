"""Irodori latent encoder — converts ref.wav to ref_latent.pt via Irodori subprocess."""

from pathlib import Path

from app.infrastructure.providers.irodori.subprocess_runner import SubprocessRunner

_BRIDGE_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "irodori_encode_latent.py"


class IrodoriLatentEncoder:
    def __init__(self, irodori_repo_dir: str, timeout_sec: int = 300) -> None:
        self._irodori_repo_dir = irodori_repo_dir
        self._runner = SubprocessRunner(timeout_sec=timeout_sec)

    async def encode(
        self,
        ref_wav_path: str,
        output_pt_path: str,
        checkpoint: str,
        codec_repo: str = "Aratako/Semantic-DACVAE-Japanese-32dim",
        model_device: str = "cpu",
        codec_device: str = "cpu",
        model_precision: str = "fp32",
        codec_precision: str = "fp32",
    ) -> None:
        cmd = [
            "uv", "run", "--no-sync", "python", str(_BRIDGE_SCRIPT),
            "--input-wav", ref_wav_path,
            "--output-pt", output_pt_path,
            "--checkpoint", checkpoint,
            "--codec-repo", codec_repo,
            "--model-device", model_device,
            "--codec-device", codec_device,
            "--model-precision", model_precision,
            "--codec-precision", codec_precision,
        ]
        await self._runner.run(cmd, cwd=self._irodori_repo_dir)
