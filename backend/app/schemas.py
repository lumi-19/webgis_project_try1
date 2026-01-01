from pydantic import BaseModel
from datetime import datetime

class EventIn(BaseModel):
    source: str
    event_type: str
    title: str
    description: str | None = None
    latitude: float
    longitude: float
    magnitude: float | None = None
    severity: str | None = None
    event_time: datetime

class EventOut(BaseModel):
    id: int
    source: str
    event_type: str
    magnitude: float | None
    severity: str | None
    event_time: datetime
    geometry: dict
