from typing import Optional

from pydantic import BaseModel, Field


class AudioMetadata(BaseModel):
    format: str
    duration: float
    sample_rate: int = Field(..., alias="sampleRate")
    bit_rate: int = Field(..., alias="bitRate")
    channels: int = Field(..., ge=1, le=2)
    codec: Optional[str] = None

    model_config = {"populate_by_name": True}
