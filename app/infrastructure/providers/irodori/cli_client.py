"""Irodori CLI client — invokes infer.py via subprocess."""

import os
from pathlib import Path

from app.domain.errors import ProviderExecutionError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult
from app.infrastructure.logging.logger import logger
from app.infrastructure.providers.irodori.cli_builder import IrodoriCliBuilder
from app.infrastructure.providers.irodori.subprocess_runner import SubprocessRunner
from app.infrastructure.tempfiles.manager import TempFileManager


class IrodoriCliClient:
    """CLI subprocess client for Irodori-TTS infer.py."""

    def __init__(
        self,
        irodori_repo_dir: str,
        tmp_dir: str,
        base_dir: str,
        timeout_sec: int = 120,
    ) -> None:
        self._irodori_repo_dir = irodori_repo_dir
        self._base_dir = Path(base_dir)
        self._tmp_manager = TempFileManager(tmp_dir=tmp_dir)
        self._runner: SubprocessRunner = SubprocessRunner(timeout_sec=timeout_sec)

    def _resolve_for_subprocess(self, path: str) -> str:
        p = Path(path).expanduser()
        if p.is_absolute():
            return str(p)
        return str((self._base_dir / p).resolve())

    def _resolve_optional_for_subprocess(self, path: str | None) -> str | None:
        if path is None:
            return None
        return self._resolve_for_subprocess(path)

    async def synthesize(self, request: ProviderSynthesisRequest) -> SynthesisResult:
        cfg = request.provider_config
        output_path = self._resolve_for_subprocess(self._tmp_manager.create_temp_wav_path())

        try:
            if request.engine == "voicedesign":
                logger.info(
                    "Irodori synthesize model=%s voice=%s engine=%s text=%r caption=%r",
                    request.model_id,
                    request.voice_id,
                    request.engine,
                    request.text,
                    cfg["caption"],
                )
                cmd = IrodoriCliBuilder.build_voicedesign_command(
                    checkpoint=cfg["checkpoint"],
                    text=request.text,
                    caption=cfg["caption"],
                    output_wav_path=output_path,
                    model_device=cfg.get("model_device", "cpu"),
                    codec_device=cfg.get("codec_device", "cpu"),
                    model_precision=cfg.get("model_precision", "fp32"),
                    codec_precision=cfg.get("codec_precision", "fp32"),
                    num_steps=cfg.get("num_steps", 28),
                    seed=cfg.get("seed", 0),
                    max_text_len=cfg.get("max_text_len"),
                    max_caption_len=cfg.get("max_caption_len"),
                )
            else:
                ref_latent_path = self._resolve_optional_for_subprocess(cfg.get("ref_latent_path"))
                ref_wav_path = self._resolve_optional_for_subprocess(cfg.get("ref_wav_path"))
                logger.info(
                    "Irodori synthesize model=%s voice=%s engine=%s text=%r ref_latent=%s ref_wav=%s",
                    request.model_id,
                    request.voice_id,
                    request.engine,
                    request.text,
                    ref_latent_path,
                    ref_wav_path,
                )
                cmd = IrodoriCliBuilder.build_base_command(
                    checkpoint=cfg["checkpoint"],
                    text=request.text,
                    ref_latent_path=ref_latent_path,
                    ref_wav_path=ref_wav_path,
                    output_wav_path=output_path,
                    model_device=cfg.get("model_device", "cpu"),
                    codec_device=cfg.get("codec_device", "cpu"),
                    model_precision=cfg.get("model_precision", "fp32"),
                    codec_precision=cfg.get("codec_precision", "fp32"),
                    num_steps=cfg.get("num_steps", 28),
                    seed=cfg.get("seed", 0),
                    speaker_kv_scale=cfg.get("speaker_kv_scale", 1.0),
                    max_text_len=cfg.get("max_text_len"),
                    max_caption_len=cfg.get("max_caption_len"),
                )

            logger.debug("Irodori command cwd=%s argv=%r", self._irodori_repo_dir, cmd)
            await self._runner.run(cmd, cwd=self._irodori_repo_dir)

            if not os.path.exists(output_path):
                raise ProviderExecutionError(
                    "irodori", "Output WAV file was not created"
                )

            if os.path.getsize(output_path) == 0:
                raise ProviderExecutionError(
                    "irodori", "Output WAV file is empty"
                )

            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            return SynthesisResult(audio_bytes=audio_bytes)

        finally:
            self._tmp_manager.cleanup(output_path)
