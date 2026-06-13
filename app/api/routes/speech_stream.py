"""Speech stream SSE route."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_stream_speech
from app.api.schemas.speech_stream import SpeechStreamRequest
from app.application.use_cases.stream_speech import StreamSpeech

router = APIRouter()


@router.post("/v1/speech/stream")
async def speech_stream(
    req: SpeechStreamRequest,
    uc: StreamSpeech = Depends(get_stream_speech),
) -> StreamingResponse:
    async def event_generator():
        async for sse_line in uc.execute(
            model_id=req.model,
            voice_id=req.voice_id,
            text=req.speech_text,
            response_format=req.response_format,
            segment_options=req.segment.model_dump(),
            batch_options=req.batch.model_dump(),
            extra_options=req.extra_options or None,
        ):
            yield sse_line

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
