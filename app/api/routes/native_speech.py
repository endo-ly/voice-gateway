"""Native speech synthesis route."""

import json

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.dependencies import get_synthesize_speech
from app.api.schemas.native_speech import NativeSpeechRequest
from app.application.services.error_mapper import ErrorMapper
from app.application.use_cases.synthesize_speech import SynthesizeSpeech
from app.domain.errors import VoiceGatewayError

router = APIRouter()


@router.post("/v1/speech")
async def native_speech(
    req: NativeSpeechRequest,
    uc: SynthesizeSpeech = Depends(get_synthesize_speech),
) -> Response:
    try:
        result = await uc.execute(
            model_id=req.model,
            voice_id=req.voice_id,
            text=req.speech_text,
            response_format=req.response_format,
            extra_options=req.style_hints,
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
