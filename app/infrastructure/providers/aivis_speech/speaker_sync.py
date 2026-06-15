"""Convert AivisSpeech /speakers payload into VoiceProfile entries."""

from typing import Any, Iterable

from app.domain.entities.voice_profile import VoiceBinding, VoiceDefaults, VoiceProfile

AIVIS_MODEL_ID = "aivis-default"
DEFAULT_STYLE_NAMES = {"ノーマル", "normal"}


def _is_default_style(style_name: str) -> bool:
    return style_name in DEFAULT_STYLE_NAMES or style_name.lower() == "normal"


def speakers_to_voice_profiles(speakers: Iterable[dict[str, Any]]) -> list[VoiceProfile]:
    profiles: list[VoiceProfile] = []
    for speaker in speakers:
        if not isinstance(speaker, dict):
            continue
        name = speaker.get("name")
        styles = speaker.get("styles") or []
        if not isinstance(name, str) or not name:
            continue
        if not styles:
            continue

        default_style = next(
            (s for s in styles if _is_default_style(str(s.get("name", "")))),
            styles[0],
        )

        for style in styles:
            style_name = style.get("name")
            style_id = style.get("id")
            if not isinstance(style_name, str) or not isinstance(style_id, int):
                continue

            is_default = style is default_style
            voice_id = name if is_default else f"{name}/{style_name}"
            display_name = name if is_default else f"{name} ({style_name})"
            profiles.append(
                VoiceProfile(
                    voice_id=voice_id,
                    display_name=display_name,
                    description=f"AivisSpeech: {name} / {style_name}",
                    defaults=VoiceDefaults(preferred_model=AIVIS_MODEL_ID),
                    bindings={
                        AIVIS_MODEL_ID: VoiceBinding(
                            provider_config={"speaker": style_id}
                        )
                    },
                )
            )

    return profiles
