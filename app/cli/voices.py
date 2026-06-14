"""Voice management CLI commands."""

import argparse
import asyncio
from pathlib import Path

from app.infrastructure.config.settings import Settings
from app.infrastructure.providers.irodori.latent_encoder import IrodoriLatentEncoder
from app.infrastructure.repositories.yaml_model_profile_repository import YamlModelProfileRepository
from app.infrastructure.repositories.yaml_voice_profile_repository import YamlVoiceProfileRepository


def _resolve_for_subprocess(path: str, base_dir: str) -> str:
    p = Path(path).expanduser()
    if p.is_absolute():
        return str(p)
    return str((Path(base_dir) / p).resolve())


def _profile_path_value(path: str, base_dir: str) -> str:
    p = Path(path).expanduser()
    if not p.is_absolute():
        return path

    try:
        return p.resolve().relative_to(Path(base_dir).resolve()).as_posix()
    except ValueError:
        return str(p)


def _require_irodori_repo_dir(settings: Settings) -> str:
    repo_dir = Path(settings.irodori_repo_dir).expanduser()
    if not repo_dir.is_dir():
        print(f"IRODORI_REPO_DIR is not a directory: {settings.irodori_repo_dir}")
        raise SystemExit(1)

    return str(repo_dir)


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    voices = subparsers.add_parser("voices", help="Voice management commands")
    voices_sub = voices.add_subparsers(dest="voices_command")

    build = voices_sub.add_parser("build-ref-latent", help="Build ref_latent.pt from ref.wav for a voice")
    build.add_argument("--voice-id", required=True)
    build.add_argument("--model-id", required=True)
    build.add_argument("--write-profile", action="store_true")
    build.set_defaults(func=_build_ref_latent)

    mat = voices_sub.add_parser("materialize-ref-latents", help="Batch convert ref.wav to ref_latent.pt for multiple voices")
    mat.add_argument("--voice-id", action="append", default=[], help="Voice IDs to process (repeatable)")
    mat.add_argument("--all", action="store_true", help="Process all voices with ref_wav_path")
    mat.add_argument("--model-id", required=True)
    mat.add_argument("--write-profile", action="store_true")
    mat.set_defaults(func=_materialize_ref_latents)


def _build_ref_latent(args: argparse.Namespace) -> None:
    settings = Settings()
    model_repo = YamlModelProfileRepository(
        str(Path(settings.assets_dir) / "models" / "models.yaml")
    )
    voice_repo = YamlVoiceProfileRepository(
        str(Path(settings.assets_dir) / "voices")
    )

    model = model_repo.get_by_id(args.model_id)
    if model is None:
        print(f"Model not found: {args.model_id}")
        raise SystemExit(1)

    voice = voice_repo.get_by_id(args.voice_id)
    if voice is None:
        print(f"Voice not found: {args.voice_id}")
        raise SystemExit(1)

    binding = voice.bindings.get(args.model_id)
    if binding is None:
        print(f"Voice '{args.voice_id}' has no binding for model '{args.model_id}'")
        raise SystemExit(1)

    ref_wav_path = binding.provider_config.get("ref_wav_path")
    if not ref_wav_path:
        print(f"Voice '{args.voice_id}' binding for '{args.model_id}' has no ref_wav_path")
        raise SystemExit(1)
    input_wav_path = _resolve_for_subprocess(ref_wav_path, settings.project_root)

    checkpoint = model.provider_config.get("checkpoint")
    if not checkpoint:
        print(f"Model '{args.model_id}' has no checkpoint in provider_config")
        raise SystemExit(1)

    codec_repo = model.provider_config.get(
        "codec_repo", "Aratako/Semantic-DACVAE-Japanese-32dim"
    )

    configured_ref_latent_path = binding.provider_config.get("ref_latent_path")
    if configured_ref_latent_path:
        output_pt_path = _resolve_for_subprocess(configured_ref_latent_path, settings.project_root)
        profile_ref_latent_path = _profile_path_value(output_pt_path, settings.project_root)
    else:
        voice_dir = Path(settings.assets_dir) / "voices" / args.voice_id
        output_pt_path = _resolve_for_subprocess(str(voice_dir / "ref_latent.pt"), settings.project_root)
        profile_ref_latent_path = _profile_path_value(output_pt_path, settings.project_root)

    encoder = IrodoriLatentEncoder(
        irodori_repo_dir=_require_irodori_repo_dir(settings),
        timeout_sec=settings.timeout_sec,
    )

    asyncio.run(encoder.encode(
        ref_wav_path=input_wav_path,
        output_pt_path=output_pt_path,
        checkpoint=checkpoint,
        codec_repo=codec_repo,
        model_device=model.provider_config.get("model_device", "cpu"),
        codec_device=model.provider_config.get("codec_device", "cpu"),
        model_precision=model.provider_config.get("model_precision", "fp32"),
        codec_precision=model.provider_config.get("codec_precision", "fp32"),
    ))

    print(f"Generated: {output_pt_path}")

    if args.write_profile:
        _write_ref_latent_to_profile(
            voice_repo, args.voice_id, args.model_id, profile_ref_latent_path
        )
        print(f"Updated profile: ref_latent_path={profile_ref_latent_path}")


def _write_ref_latent_to_profile(
    voice_repo: YamlVoiceProfileRepository,
    voice_id: str,
    model_id: str,
    ref_latent_path: str,
) -> None:
    import yaml

    profile_path = voice_repo.get_profile_path(voice_id)
    with open(profile_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    binding = data["bindings"].get(model_id, {})
    provider_config = binding.get("provider_config", {})
    provider_config["ref_latent_path"] = ref_latent_path
    binding["provider_config"] = provider_config
    data["bindings"][model_id] = binding

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _materialize_ref_latents(args: argparse.Namespace) -> None:
    settings = Settings()
    voice_repo = YamlVoiceProfileRepository(
        str(Path(settings.assets_dir) / "voices")
    )

    if args.all:
        voice_ids = [v.voice_id for v in voice_repo.list_all()]
    else:
        voice_ids = args.voice_id

    if not voice_ids:
        print("No voices to process. Use --all or --voice-id.")
        raise SystemExit(1)

    for vid in voice_ids:
        print(f"--- Processing voice: {vid}")
        try:
            inner = argparse.Namespace(
                voice_id=vid,
                model_id=args.model_id,
                write_profile=args.write_profile,
            )
            _build_ref_latent(inner)
        except SystemExit:
            print(f"  Skipped {vid} (error above)")
        print()
