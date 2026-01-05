"""
DisasterScope Backend – FINAL STABLE VERSION
FastAPI + Async SQLAlchemy + PostGIS
"""

# -------------------------------------------------
# Imports
# -------------------------------------------------
import os
from datetime import datetime
from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

from .db import AsyncSessionLocal, init_db, Event, AirQuality
print("🚀 RUNNING ASYNC API BACKEND (api.py)")

# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(
    title="DisasterScope Backend",
    version="1.0.0",
    description="Disaster & Air-Quality Ingestion API"
)

# -------------------------------------------------
# API KEY
# -------------------------------------------------
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "Theking123")

async def verify_api_key(
    x_ingest_key: str = Header(..., alias="X-INGEST-KEY")
):
    if x_ingest_key != INGEST_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# -------------------------------------------------
# DB Dependency
# -------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    await init_db()

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def to_utc_naive(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.utcnow()
    if dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt

def make_geom(lat: Optional[float], lon: Optional[float]):
    if lat is None or lon is None:
        return None
    return ST_SetSRID(ST_MakePoint(lon, lat), 4326)

# -------------------------------------------------
# Schemas
# -------------------------------------------------
class EventCreate(BaseModel):
    source: str
    event_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    magnitude: Optional[float] = None
    severity: Optional[str] = None
    event_time: Optional[datetime] = None
    location_accuracy: Optional[str] = None

class AirQualityCreate(BaseModel):
    source: str
    location: str
    parameter: str
    value: float
    unit: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    measured_at: Optional[datetime] = None

# -------------------------------------------------
# Health
# -------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# -------------------------------------------------
# READ – Events (GeoJSON)
# -------------------------------------------------
@app.get("/api/events")
async def get_events(
    db: AsyncSession = Depends(get_db),
    limit: int = 200
):
    result = await db.execute(
        select(Event).order_by(Event.event_time.desc()).limit(limit)
    )
    rows = result.scalars().all()

    features = []
    for e in rows:
        if e.latitude is None or e.longitude is None:
            continue

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [e.longitude, e.latitude],
            },
            "properties": {
                "id": e.id,
                "source": e.source,
                "event_type": e.event_type,
                "title": e.title,
                "magnitude": e.magnitude,
                "severity": e.severity,
                "event_time": e.event_time.isoformat() if e.event_time else None,
            }
        })

    return JSONResponse({
        "type": "FeatureCollection",
        "features": features
    })

# -------------------------------------------------
# Background Task: Async DB Insert
# -------------------------------------------------
async def insert_events_background(events_data: List[dict]):
    """Background task to insert events into database asynchronously"""
    async with AsyncSessionLocal() as session:
        try:
            for e_data in events_data:
                session.add(Event(
                    source=e_data["source"],
                    event_type=e_data["event_type"],
                    title=e_data.get("title"),
                    description=e_data.get("description"),
                    latitude=e_data.get("latitude"),
                    longitude=e_data.get("longitude"),
                    magnitude=e_data.get("magnitude"),
                    severity=e_data.get("severity"),
                    event_time=to_utc_naive(e_data.get("event_time")),
                    location_accuracy=e_data.get("location_accuracy"),
                    geom=make_geom(e_data.get("latitude"), e_data.get("longitude")),
                ))
            
            await session.flush()
            await session.commit()
            print(f"✅ Background insert complete: {len(events_data)} events")
        except Exception as e:
            print(f"❌ Background insert failed: {e}")
            await session.rollback()
            raise

# -------------------------------------------------
# WRITE – Events (Bulk)
# -------------------------------------------------
@app.post("/api/events/bulk")
async def create_events_bulk(
    events: List[EventCreate],
    authorized: None = Depends(verify_api_key),
):
    events_data = [
        {
            "source": e.source,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "latitude": e.latitude,
            "longitude": e.longitude,
            "magnitude": e.magnitude,
            "severity": e.severity,
            "event_time": e.event_time,
            "location_accuracy": e.location_accuracy,
        }
        for e in events
    ]

    # 🔥 NO BACKGROUND TASK
    await insert_events_background(events_data)

    return {"status": "inserted", "count": len(events)}

# -------------------------------------------------
# WRITE – Air Quality
# -------------------------------------------------
@app.post("/api/air-quality")
async def create_air_quality(
    records: List[AirQualityCreate],
    db: AsyncSession = Depends(get_db),
    authorized: None = Depends(verify_api_key),
):
    for r in records:
        db.add(AirQuality(
            source=r.source,
            location=r.location,
            parameter=r.parameter,
            value=r.value,
            unit=r.unit,
            latitude=r.latitude,
            longitude=r.longitude,
            measured_at=to_utc_naive(r.measured_at),
            geom=make_geom(r.latitude, r.longitude),
        ))

    await db.commit()
    return {"status": "inserted", "count": len(records)}
