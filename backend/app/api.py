"""
FastAPI application for DisasterScope (Layer 2).

Public API:
- GET /api/health
- GET /api/events        (GeoJSON)
- GET /api/air-quality
- GET /api/predictions/summary

Write API (for n8n):
- POST /api/events
- POST /api/events/bulk
- POST /api/air-quality
"""

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------

from typing import List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import json
import os

from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import AsyncSessionLocal, init_db, Event, AirQuality

from .cache import cache
from .ai_agent import prediction_summary

# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------

app = FastAPI(
    title="DisasterScope Backend",
    version="1.0.0",
    description="Disaster monitoring, ingestion & prediction API"
)

# -------------------------------------------------------------------
# API Key
# -------------------------------------------------------------------

INGEST_API_KEY = os.getenv("INGEST_API_KEY", "Theking123")

async def verify_api_key(
    x_ingest_key: str = Header(..., alias="X-INGEST-KEY")
):
    if x_ingest_key != INGEST_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# -------------------------------------------------------------------
# DB Dependency
# -------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def on_startup():
    pass

# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# -------------------------------------------------------------------
# Pydantic Models
# -------------------------------------------------------------------

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


class AirQualityCreate(BaseModel):
    source: str
    location: str
    parameter: str
    value: float
    unit: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    measured_at: Optional[datetime] = None

# -------------------------------------------------------------------
# Events (READ) — GEOJSON
# -------------------------------------------------------------------

@app.get("/api/events")
async def get_events(
    db: AsyncSession = Depends(get_db),
    event_type: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(Event)

    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if start:
        stmt = stmt.where(Event.event_time >= start)
    if end:
        stmt = stmt.where(Event.event_time <= end)

    stmt = stmt.order_by(Event.event_time.desc()).limit(limit)

    result = await db.execute(stmt)
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
            },
        })

    return JSONResponse({
        "type": "FeatureCollection",
        "features": features,
    })

# -------------------------------------------------------------------
# Events (WRITE — n8n, single)
# -------------------------------------------------------------------

@app.post("/api/events")
async def create_event(
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
    authorized: None = Depends(verify_api_key),
):
    db_event = Event(
        source=event.source,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        latitude=event.latitude,
        longitude=event.longitude,
        magnitude=event.magnitude,
        severity=event.severity,
        event_time=event.event_time or datetime.utcnow(),
    )

    db.add(db_event)
    await db.commit()

    return {"status": "inserted", "event_id": db_event.id}

# -------------------------------------------------------------------
# Events (WRITE — bulk)
# -------------------------------------------------------------------

@app.post("/api/events/bulk")
async def create_events_bulk(
    events: List[EventCreate],
    db: AsyncSession = Depends(get_db),
    authorized: None = Depends(verify_api_key),
):
    for e in events:
        db.add(Event(
            source=e.source,
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            latitude=e.latitude,
            longitude=e.longitude,
            magnitude=e.magnitude,
            severity=e.severity,
            event_time=e.event_time or datetime.utcnow(),
        ))

    await db.commit()
    return {"status": "inserted", "count": len(events)}

# -------------------------------------------------------------------
# Air Quality (READ)
# -------------------------------------------------------------------

@app.get("/api/air-quality")
async def get_air_quality(
    db: AsyncSession = Depends(get_db),
    location: Optional[str] = Query(default=None),
    parameter: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(AirQuality)

    if location:
        stmt = stmt.where(AirQuality.location == location)
    if parameter:
        stmt = stmt.where(AirQuality.parameter == parameter)

    stmt = stmt.order_by(AirQuality.measured_at.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return rows

# -------------------------------------------------------------------
# Air Quality (WRITE)
# -------------------------------------------------------------------

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
            measured_at=r.measured_at or datetime.utcnow(),
        ))

    await db.commit()
    return {"status": "inserted", "count": len(records)}

# -------------------------------------------------------------------
# Prediction Summary
# -------------------------------------------------------------------

@app.get("/api/predictions/summary")
async def get_prediction_summary(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=30),
):
    cache_key = f"prediction_summary:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    since = datetime.utcnow() - timedelta(days=days)

    events = (await db.execute(
        select(Event).where(Event.event_time >= since)
    )).scalars().all()

    aq = (await db.execute(
        select(AirQuality).where(AirQuality.measured_at >= since)
    )).scalars().all()

    summary = prediction_summary(events, aq, days)
    cache.set(cache_key, summary)
    return summary

# -------------------------------------------------------------------   