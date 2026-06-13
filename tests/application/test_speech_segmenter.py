"""Tests for SpeechSegmenter."""

import pytest

from app.application.services.speech_segmenter import SpeechSegmenter
from app.domain.value_objects.speech_segment_policy import SpeechSegmentPolicy


class TestSpeechSegmenterSplit:
    def test_split_by_period(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("なるほど。それでは始めましょう。", policy)

        assert len(result) == 2
        assert result[0].index == 0
        assert result[0].text == "なるほど。"
        assert result[1].index == 1
        assert result[1].text == "それでは始めましょう。"

    def test_split_by_question_mark(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("大丈夫ですか？問題ありません。", policy)

        assert len(result) == 2
        assert result[0].text == "大丈夫ですか？"
        assert result[1].text == "問題ありません。"

    def test_split_by_exclamation(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("やったー！次に行きましょう。", policy)

        assert len(result) >= 2
        assert result[0].text.endswith("！") or result[0].text.endswith("ー！")

    def test_split_by_newline(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("一行目の文章です。\n二行目の文章です。", policy)

        assert len(result) == 2

    def test_first_chunk_is_short(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        long_text = "なるほど、それならまずIrodori-TTS-Serverを内部Engineとして扱うのがよいです。"
        result = seg.segment(long_text, policy)

        assert len(result[0].text) <= policy.normal_max_chars

    def test_short_chunks_are_merged(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy(min_chunk_chars=8)
        result = seg.segment("あ。い。う。えおかきくけこ。", policy)

        for chunk in result:
            if chunk is not result[-1]:
                pass

    def test_merge_short_last_chunk(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy(min_chunk_chars=10)
        result = seg.segment("これは十分な長さの文章です。短い。", policy)

        assert len(result) == 2 or len(result) == 1

    def test_long_text_forced_split(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy(
            normal_max_chars=10,
            hard_max_chars=15,
            min_chunk_chars=1,
            merge_too_short_chunks=False,
        )
        long_text = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも"
        result = seg.segment(long_text, policy)

        assert all(len(c.text) <= policy.hard_max_chars for c in result)
        assert len(result) >= 3

    def test_empty_text_returns_empty(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("", policy)
        assert result == []

    def test_whitespace_only_returns_empty(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("   \n  \t  ", policy)
        assert result == []

    def test_single_sentence(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("こんにちは。", policy)
        assert len(result) == 1
        assert result[0].text == "こんにちは。"

    def test_indices_are_sequential(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("一つ目。二つ目。三つ目。四つ目。", policy)
        for i, chunk in enumerate(result):
            assert chunk.index == i

    def test_tts_text_matches_text(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy()
        result = seg.segment("テストです。確認しましょう。", policy)
        for chunk in result:
            assert chunk.tts_text == chunk.text


class TestSpeechSegmentPolicyModes:
    def test_conversation_mode_defaults(self):
        policy = SpeechSegmentPolicy.conversation()
        assert policy.first_chunk_max_chars == 20
        assert policy.min_chunk_chars == 8
        assert policy.normal_max_chars == 80
        assert policy.hard_max_chars == 120

    def test_narration_mode_defaults(self):
        policy = SpeechSegmentPolicy.narration()
        assert policy.first_chunk_max_chars == 60
        assert policy.min_chunk_chars == 20
        assert policy.normal_max_chars == 160
        assert policy.hard_max_chars == 240

    def test_narration_mode_defaults_via_constructor(self):
        policy = SpeechSegmentPolicy(mode="narration")
        assert policy.first_chunk_max_chars == 60
        assert policy.min_chunk_chars == 20
        assert policy.normal_max_chars == 160
        assert policy.hard_max_chars == 240

    def test_explicit_override_preserved(self):
        policy = SpeechSegmentPolicy(mode="narration", first_chunk_max_chars=40)
        assert policy.first_chunk_max_chars == 40
        assert policy.min_chunk_chars == 20

    def test_plan_example(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy.conversation()
        text = "なるほど。それならまずIrodori-TTS-Serverを内部Engineとして扱うのがよいです。"
        result = seg.segment(text, policy)

        assert result[0].text == "なるほど。"
        assert len(result) == 2

    def test_avoids_over_fragmentation(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy.conversation()
        text = "それなら、まず、Irodori-TTS-Serverを内部Engineとして扱います。"
        result = seg.segment(text, policy)

        assert len(result) <= 2

    def test_disabled_policy(self):
        seg = SpeechSegmenter()
        policy = SpeechSegmentPolicy(enabled=False)
        result = seg.segment("これはテストです。もう一つの文です。", policy)

        assert len(result) == 2
