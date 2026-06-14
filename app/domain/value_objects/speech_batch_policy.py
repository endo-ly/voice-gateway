"""SpeechBatchPolicy value object."""

from pydantic import BaseModel


class SpeechBatchPolicy(BaseModel):
    max_concurrency: int = 1
    ordered: bool = True
    stop_on_error: bool = True
