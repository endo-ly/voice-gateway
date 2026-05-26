"""Latest transcription route."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_latest_transcription
from app.api.schemas.transcription import LatestTranscriptionData, LatestTranscriptionResponse
from app.application.use_cases.get_latest_transcription import GetLatestTranscription

router = APIRouter()


@router.get("/v1/transcriptions/latest")
async def latest_transcription(
    uc: GetLatestTranscription = Depends(get_latest_transcription),
) -> JSONResponse:
    result = uc.execute()
    if result is None:
        response = LatestTranscriptionResponse(data=None)
    else:
        data = LatestTranscriptionData(
            text=result.text,
            language=result.language,
            duration_sec=result.duration_sec,
            processing_ms=result.processing_ms,
            provider=result.provider,
            model=result.model,
            source=result.source,
            audio=result.audio_info,
            timestamp="",
        )
        response = LatestTranscriptionResponse(data=data)
    return JSONResponse(content=response.model_dump())
