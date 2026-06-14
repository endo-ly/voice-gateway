"""Stream speech use case — SSE-friendly chunked TTS."""

import base64
import json
from typing import Any, AsyncIterator

from app.application.services.speech_batch_synthesizer import SpeechBatchSynthesizer
from app.application.services.speech_segmenter import SpeechSegmenter
from app.domain.errors import VoiceGatewayError
from app.domain.value_objects.speech_batch_policy import SpeechBatchPolicy
from app.domain.value_objects.speech_segment_policy import SpeechSegmentPolicy


class StreamSpeech:
    def __init__(
        self,
        segmenter: SpeechSegmenter,
        batch_synthesizer: SpeechBatchSynthesizer,
    ) -> None:
        self._segmenter = segmenter
        self._synthesizer = batch_synthesizer

    async def execute(
        self,
        model_id: str,
        voice_id: str,
        text: str,
        response_format: str = "wav",
        segment_options: dict[str, Any] | None = None,
        batch_options: dict[str, Any] | None = None,
        extra_options: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        try:
            seg_policy = SpeechSegmentPolicy(**(segment_options or {}))
            batch_policy = SpeechBatchPolicy(**(batch_options or {}))
        except Exception as e:
            yield self._format_sse("error", {"message": str(e), "code": "invalid_options"})
            return

        if not seg_policy.enabled:
            from app.domain.value_objects.speech_chunk import SpeechChunk
            chunks = [SpeechChunk(index=0, text=text, tts_text=text)]
        else:
            chunks = self._segmenter.segment(text, seg_policy)

        if not chunks:
            yield self._format_sse("error", {"message": "No chunks to synthesize", "code": "empty_input"})
            return

        sent = 0

        try:
            async for event in self._synthesizer.synthesize_stream(
                chunks=chunks,
                model_id=model_id,
                voice_id=voice_id,
                response_format=response_format,
                extra_options=extra_options,
                batch_policy=batch_policy,
            ):
                if event.is_error and event.error is not None:
                    yield self._format_sse(
                        "error",
                        {
                            "index": event.error.index,
                            "message": event.error.message,
                            "code": event.error.code,
                        },
                    )
                    if batch_policy.stop_on_error:
                        return

                if event.result is not None:
                    sent += 1
                    yield self._format_sse(
                        "audio_chunk",
                        {
                            "index": event.result.index,
                            "text": event.result.text,
                            "tts_text": event.result.tts_text,
                            "format": event.result.format,
                            "media_type": event.result.media_type,
                            "audio_base64": base64.b64encode(
                                event.result.audio_bytes
                            ).decode("ascii"),
                        },
                    )
        except VoiceGatewayError as e:
            yield self._format_sse(
                "error",
                {"message": str(e), "code": type(e).__name__},
            )
            return

        yield self._format_sse("done", {"chunks": sent})

    @staticmethod
    def _format_sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
