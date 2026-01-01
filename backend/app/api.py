"""
FastAPI application for DisasterScope (Layer 2).

Public API:
- GET /api/health
- GET /api/events
- GET /api/events/{id}
- GET /api/air-quality
- GET /api/predictions/summary

Write API (for n8n):
- POST /api/events (with API key auth)
- POST /api/air-quality (with API key auth)
"""

from typing import List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Query, Header
from pydantic import BaseModel, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import AsyncSessionLocal, init_db, Event, AirQuality
from .cache import cache
from .ai_agent import prediction_summary
import os

# -------------------------------------------------------------------
# Pydantic Models for Validation
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
# App
# -------------------------------------------------------------------

app = FastAPI(
    title="DisasterScope Backend",
    version="1.0.0",
    description="Disaster monitoring, ingestion & prediction API"
)

# -------------------------------------------------------------------
# API Key Validation (Simple Header Check)
# -------------------------------------------------------------------

INGEST_API_KEY = os.getenv("INGEST_API_KEY", "Theking123")





async def verify_api_key(x_ingest_key: str = Header(..., alias="X-INGEST-KEY")):
    """Simple API key validation for ingestion endpoints"""
    if x_ingest_key != INGEST_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# -------------------------------------------------------------------
# DB Dependency
# -------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def on_startup():
    await init_db()

# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# -------------------------------------------------------------------
# Events (READ) - Keep existing GET endpoints
# -------------------------------------------------------------------

@app.get("/api/events")
async def get_events(
    db: AsyncSession = Depends(get_db),
    type: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(Event)
    
    if type:
        stmt = stmt.where(Event.event_type == type)
    if location:
        stmt = stmt.where(Event.location == location)
    if start:
        stmt = stmt.where(Event.event_time >= start)
    if end:
        stmt = stmt.where(Event.event_time <= end)
    
    stmt = stmt.order_by(Event.event_time.desc()).limit(limit)
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    # Convert to dict for JSON serialization
    return [
        {
            "id": e.id,
            "source": e.source,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "latitude": e.latitude,
            "longitude": e.longitude,
            "magnitude": e.magnitude,
            "severity": e.severity,
            "event_time": e.event_time.isoformat() if e.event_time else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]

# -------------------------------------------------------------------
# Events (WRITE for n8n) - NEW ENDPOINT
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Events (WRITE for n8n) - UPDATED FOR SINGLE ITEMS
# -------------------------------------------------------------------

@app.post("/api/events")
async def create_event(
    event_data: EventCreate,  # CHANGED: Single EventCreate, not List!
    db: AsyncSession = Depends(get_db),
    authorized: bool = Depends(verify_api_key)
):
    """Create a single event - n8n will send one at a time"""
    print(f"📥 Creating event: {event_data.title}")
    
    event = Event(
        source=event_data.source,
        event_type=event_data.event_type,
        title=event_data.title,
        description=event_data.description,
        latitude=event_data.latitude,
        longitude=event_data.longitude,
        magnitude=event_data.magnitude,
        severity=event_data.severity,
        event_time=event_data.event_time or datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    
    return {
        "status": "success",
        "inserted": 1,
        "event_id": event.id,
        "message": f"Inserted event: {event_data.title}"
    }

# -------------------------------------------------------------------
# Keep this for bulk uploads (optional, for testing)
# -------------------------------------------------------------------

@app.post("/api/events/bulk")
async def create_events_bulk(
    events: List[EventCreate],
    db: AsyncSession = Depends(get_db),
    authorized: bool = Depends(verify_api_key)
):
    """Bulk create events (for manual/testing)"""
    inserted = 0
    
    for event_data in events:
        event = Event(
            source=event_data.source,
            event_type=event_data.event_type,
            title=event_data.title,
            description=event_data.description,
            latitude=event_data.latitude,
            longitude=event_data.longitude,
            magnitude=event_data.magnitude,
            severity=event_data.severity,
            event_time=event_data.event_time or datetime.utcnow(),
        )
        db.add(event)
        inserted += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "inserted": inserted,
        "message": f"Inserted {inserted} events"
    }

# -------------------------------------------------------------------
# Air Quality (WRITE for n8n) - NEW ENDPOINT
# -------------------------------------------------------------------

@app.post("/api/air-quality")
async def create_air_quality(
    records: List[AirQualityCreate],
    db: AsyncSession = Depends(get_db),
    authorized: bool = Depends(verify_api_key)
):
    """Bulk create air quality records from n8n workflows"""
    inserted = 0
    
    for record_data in records:
        aq = AirQuality(
            source=record_data.source,
            location=record_data.location,
            parameter=record_data.parameter,
            value=record_data.value,
            unit=record_data.unit,
            latitude=record_data.latitude,
            longitude=record_data.longitude,
            measured_at=record_data.measured_at or datetime.utcnow(),
        )
        db.add(aq)
        inserted += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "inserted": inserted,
        "message": f"Inserted {inserted} air quality records"
    }

# -------------------------------------------------------------------
# Air Quality (READ) - Updated to match new model
# -------------------------------------------------------------------

@app.get("/api/air-quality")
async def get_air_quality(
    db: AsyncSession = Depends(get_db),
    location: Optional[str] = Query(default=None),
    parameter: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(AirQuality)
    
    if location:
        stmt = stmt.where(AirQuality.location == location)
    if parameter:
        stmt = stmt.where(AirQuality.parameter == parameter)
    if start:
        stmt = stmt.where(AirQuality.measured_at >= start)
    if end:
        stmt = stmt.where(AirQuality.measured_at <= end)
    
    stmt = stmt.order_by(AirQuality.measured_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    aq_records = result.scalars().all()
    
    return [
        {
            "id": aq.id,
            "source": aq.source,
            "location": aq.location,
            "parameter": aq.parameter,
            "value": aq.value,
            "unit": aq.unit,
            "latitude": aq.latitude,
            "longitude": aq.longitude,
            "measured_at": aq.measured_at.isoformat() if aq.measured_at else None,
            "created_at": aq.created_at.isoformat() if aq.created_at else None,
        }
        for aq in aq_records
    ]

# -------------------------------------------------------------------
# Prediction Summary - Updated to use new model fields
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
    
    events_stmt = select(Event).where(Event.event_time >= since)
    aqi_stmt = select(AirQuality).where(AirQuality.measured_at >= since)
    
    events_result = await db.execute(events_stmt)
    aqi_result = await db.execute(aqi_stmt)
    
    events = events_result.scalars().all()
    aqis = aqi_result.scalars().all()
    
    summary = prediction_summary(events, aqis, days)
    cache.set(cache_key, summary)
    
    return summary