"""OpenAI-compatible speech synthesis route."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import get_stream_speech, get_synthesize_speech
from app.api.schemas.openai_speech import OpenAISpeechRequest
from app.application.services.error_mapper import ErrorMapper
from app.application.use_cases.stream_speech import StreamSpeech
from app.application.use_cases.synthesize_speech import SynthesizeSpeech
from app.domain.errors import VoiceGatewayError

router = APIRouter()


@router.post("/v1/audio/speech", response_model=None)
async def openai_speech(
    req: OpenAISpeechRequest,
    synthesize_uc: SynthesizeSpeech = Depends(get_synthesize_speech),
    stream_uc: StreamSpeech = Depends(get_stream_speech),
) -> Response | StreamingResponse:
    if req.stream_format is not None:
        normalized = req.stream_format.strip().lower()
        if normalized != "sse":
            return Response(
                content=json.dumps({
                    "error": {
                        "message": "stream_format must be 'sse' when specified.",
                        "type": "invalid_request_error",
                        "param": "stream_format",
                        "code": None,
                    }
                }),
                status_code=400,
                media_type="application/json",
            )

        async def event_generator():
            async for sse_line in stream_uc.execute(
                model_id=req.model,
                voice_id=req.voice,
                text=req.input,
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

    try:
        result = await synthesize_uc.execute(
            model_id=req.model,
            voice_id=req.voice,
            text=req.input,
            response_format=req.response_format,
            speed=req.speed,
        )
        return Response(
            content=result.audio_bytes,
            media_type=result.media_type,
        )
    except VoiceGatewayError as e:
        status, body = ErrorMapper.map(e)
        return Response(
            content=json.dumps(body),
            status_code=status,
            media_type="application/json",
        )
