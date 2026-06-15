from app.infrastructure.providers.aivis_speech.speaker_sync import (
    speakers_to_voice_profiles,
)


def _binding_speaker(profile) -> int:
    return profile.bindings["aivis-default"].provider_config["speaker"]


def test_default_style_normal_gets_speaker_name_as_voice_id():
    speakers = [
        {
            "name": "まお",
            "speaker_uuid": "abc",
            "styles": [
                {"name": "ノーマル", "id": 100, "type": "talk"},
                {"name": "あまあま", "id": 101, "type": "talk"},
            ],
        }
    ]

    profiles = speakers_to_voice_profiles(speakers)
    by_id = {p.voice_id: p for p in profiles}

    assert set(by_id) == {"まお", "まお/あまあま"}
    assert _binding_speaker(by_id["まお"]) == 100
    assert by_id["まお"].display_name == "まお"
    assert _binding_speaker(by_id["まお/あまあま"]) == 101
    assert by_id["まお/あまあま"].display_name == "まお (あまあま)"


def test_first_style_used_when_no_normal_style():
    speakers = [
        {
            "name": "コハク",
            "styles": [
                {"name": "せつなめ", "id": 200},
                {"name": "ねむたい", "id": 201},
            ],
        }
    ]

    by_id = {p.voice_id: p for p in speakers_to_voice_profiles(speakers)}
    assert set(by_id) == {"コハク", "コハク/ねむたい"}
    assert _binding_speaker(by_id["コハク"]) == 200


def test_english_normal_treated_as_default():
    speakers = [
        {
            "name": "Test",
            "styles": [
                {"name": "chibi", "id": 1},
                {"name": "Normal", "id": 2},
            ],
        }
    ]

    by_id = {p.voice_id: p for p in speakers_to_voice_profiles(speakers)}
    assert _binding_speaker(by_id["Test"]) == 2
    assert "Test/chibi" in by_id


def test_empty_speaker_name_skipped():
    assert speakers_to_voice_profiles([{"name": "", "styles": [{"name": "x", "id": 1}]}]) == []


def test_empty_styles_skipped():
    assert speakers_to_voice_profiles([{"name": "X", "styles": []}]) == []


def test_invalid_style_entries_skipped():
    speakers = [
        {
            "name": "X",
            "styles": [
                {"name": "valid", "id": 1},
                {"name": "missing_id"},
                {"id": 3},
                {"name": None, "id": 4},
                {"name": "str_id", "id": "not_int"},
            ],
        }
    ]

    profiles = speakers_to_voice_profiles(speakers)
    assert {p.voice_id for p in profiles} == {"X"}
    assert _binding_speaker(profiles[0]) == 1


def test_multiple_speakers_each_get_default_voice_id():
    speakers = [
        {"name": "A", "styles": [{"name": "ノーマル", "id": 1}]},
        {"name": "B", "styles": [{"name": "ノーマル", "id": 2}]},
    ]

    profiles = speakers_to_voice_profiles(speakers)
    assert {p.voice_id for p in profiles} == {"A", "B"}


def test_invalid_speaker_entries_skipped():
    speakers = [
        "not_a_dict",
        {"styles": [{"name": "x", "id": 1}]},
        {"name": "OK", "styles": [{"name": "ノーマル", "id": 9}]},
    ]

    profiles = speakers_to_voice_profiles(speakers)
    assert {p.voice_id for p in profiles} == {"OK"}
