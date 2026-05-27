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
        transcription, ts = result
        data = LatestTranscriptionData(
            text=transcription.text,
            language=transcription.language,
            duration_sec=transcription.duration_sec,
            processing_ms=transcription.processing_ms,
            provider=transcription.provider,
            model=transcription.model,
            source=transcription.source,
            audio=transcription.audio_info,
            timestamp=ts,
        )
        response = LatestTranscriptionResponse(data=data)
    return JSONResponse(content=response.model_dump(by_alias=True))
