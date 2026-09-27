"""Global test fixtures."""

import os
from pathlib import Path

import yaml


_ROOT = Path(__file__).resolve().parent.parent
_TEST_ASSETS = _ROOT / "tmp" / "test-assets"
_TEST_IRODORI = _ROOT / "tmp" / "test-irodori"

(_TEST_ASSETS / "models").mkdir(parents=True, exist_ok=True)
(_TEST_ASSETS / "voices" / "your-voice-name").mkdir(parents=True, exist_ok=True)
_TEST_IRODORI.mkdir(parents=True, exist_ok=True)

(_TEST_ASSETS / "models" / "models.yaml").write_text(
    yaml.dump(
        {
            "models": [
                {
                    "id": "tts-default",
                    "object": "model",
                    "display_name": "Default TTS",
                    "provider": "fake",
                    "engine": "base",
                    "provider_config": {},
                },
                {
                    "id": "irodori-base",
                    "object": "model",
                    "display_name": "Irodori Base",
                    "provider": "irodori",
                    "engine": "base",
                    "provider_config": {
                        "checkpoint": "Aratako/Irodori-TTS-500M-v3",
                    },
                },
            ]
        },
        default_flow_style=False,
    ),
    encoding="utf-8",
)

(_TEST_ASSETS / "voices" / "your-voice-name" / "profile.yaml").write_text(
    yaml.dump(
        {
            "voice_id": "your-voice-name",
            "display_name": "your-voice-name",
            "bindings": {
                "tts-default": {"provider_config": {}},
            },
        },
        default_flow_style=False,
    ),
    encoding="utf-8",
)

os.environ.setdefault("ASSETS_DIR", str(_TEST_ASSETS))
os.environ.setdefault("IRODORI_REPO_DIR", str(_TEST_IRODORI))
