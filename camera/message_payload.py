from typing import Optional
from pydantic import BaseModel, Field


class CameraRouterMessagePayload(BaseModel):
    id: int
    rtsp: Optional[str] = Field(default=None)
