"""Native STT transcription route."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.dependencies import get_transcribe_audio
from app.api.schemas.transcription import NativeTranscriptionData, NativeTranscriptionResponse
from app.application.services.error_mapper import ErrorMapper
from app.application.use_cases.transcribe_audio import TranscribeAudio
from app.domain.errors import AudioTooLargeError, VoiceGatewayError

router = APIRouter()


@router.post("/v1/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form("stt-default"),
    source: str = Form("unknown"),
    language: str | None = Form(None),
    uc: TranscribeAudio = Depends(get_transcribe_audio),
) -> Response:
    try:
        data = await file.read()
        max_bytes = 25 * 1024 * 1024
        if len(data) > max_bytes:
            raise AudioTooLargeError(max_size_mb=25)

        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with NamedTemporaryFile(suffix=suffix, delete=True) as temp:
            temp.write(data)
            temp.flush()
            result = await uc.execute(
                model_id=model,
                audio_path=temp.name,
                source=source,
                language=language,
            )

        response_data = NativeTranscriptionData(
            text=result.text,
            language=result.language,
            duration_sec=result.duration_sec,
            processing_ms=result.processing_ms,
            provider=result.provider,
            model=result.model,
            source=result.source,
            audio=result.audio_info,
        )
        return JSONResponse(
            content=NativeTranscriptionResponse(data=response_data).model_dump()
        )
    except VoiceGatewayError as e:
        status, body = ErrorMapper.map(e)
        return Response(
            content=json.dumps(body),
            status_code=status,
            media_type="application/json",
        )
