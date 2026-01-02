#api.py 

"""
FastAPI application for DisasterScope (Layer 2).

Public API:
- GET /api/health
- GET /api/events
- GET /api/events/{id}
- GET /api/air-quality
- GET /api/predictions/summary

Write API:
- POST /api/events/ingest
- POST /api/air-quality/ingest
"""

from typing import List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Query
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
# DB Dependency (THIS is where get_db lives)
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
# Events (READ)
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
        stmt = stmt.where(Event.type == type)
    if location:
        stmt = stmt.where(Event.location == location)
    if start:
        stmt = stmt.where(Event.timestamp >= start)
    if end:
        stmt = stmt.where(Event.timestamp <= end)

    stmt = stmt.order_by(Event.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/events/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event


# -------------------------------------------------------------------
# Events (INGEST)
# -------------------------------------------------------------------

@app.post("/api/events/ingest")
async def ingest_events(
    events: List[dict],
    db: AsyncSession = Depends(get_db),
):
    inserted = 0

    for e in events:
        event = Event(
            type=e.get("type"),
            location=e.get("location"),
            lat=e.get("lat"),
            lon=e.get("lon"),
            severity=e.get("severity"),
            timestamp=_parse_dt(e.get("timestamp")),
        )
        db.add(event)
        inserted += 1

    await db.commit()
    return {"status": "ok", "inserted": inserted}


# -------------------------------------------------------------------
# Air Quality (READ)
# -------------------------------------------------------------------

@app.get("/api/air-quality")
async def get_air_quality(
    db: AsyncSession = Depends(get_db),
    location: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(AirQuality)

    if location:
        stmt = stmt.where(AirQuality.location == location)
    if start:
        stmt = stmt.where(AirQuality.timestamp >= start)
    if end:
        stmt = stmt.where(AirQuality.timestamp <= end)

    stmt = stmt.order_by(AirQuality.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


# -------------------------------------------------------------------
# Air Quality (INGEST)
# -------------------------------------------------------------------

@app.post("/api/air-quality/ingest")
async def ingest_air_quality(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    inserted = 0

    for r in records:
        aq = AirQuality(
            location=r.get("location"),
            lat=r.get("lat"),
            lon=r.get("lon"),
            aqi=r.get("aqi"),
            timestamp=_parse_dt(r.get("timestamp")),
        )
        db.add(aq)
        inserted += 1

    await db.commit()
    return {"status": "ok", "inserted": inserted}


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

    events_stmt = select(Event).where(Event.timestamp >= since)
    aqi_stmt = select(AirQuality).where(AirQuality.timestamp >= since)

    events_result = await db.execute(events_stmt)
    aqi_result = await db.execute(aqi_stmt)

    events = events_result.scalars().all()
    aqis = aqi_result.scalars().all()

    summary = prediction_summary(events, aqis, days)
    cache.set(cache_key, summary)

    return summary


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


@app.post("/api/events/ingest")
async def ingest_events(
    events: List[dict],
    db: AsyncSession = Depends(get_db),
):
    inserted = 0

    for e in events:
        event = Event(
            type=e.get("type", "unknown"),
            location=e.get("location", "unknown"),
            lat=e.get("lat"),
            lon=e.get("lon"),
            severity=e.get("severity", 0.0),
            timestamp=datetime.utcnow(),
        )

        db.add(event)
        inserted += 1

    await db.commit()
    return {"status": "ok", "inserted": inserted}


#db.py

"""
Database setup and models for DisasterScope.
Async SQLAlchemy configuration.
"""

import os
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Index,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

# -------------------------------------------------
# Environment
# -------------------------------------------------

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./disasters.db"
)

# -------------------------------------------------
# Engine & Session
# -------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# -------------------------------------------------
# Models
# -------------------------------------------------

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True)
    location = Column(String, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    severity = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_events_type_location_ts", "type", "location", "timestamp"),
    )


class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    aqi = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_air_quality_location_ts", "location", "timestamp"),
    )

# -------------------------------------------------
# Init DB
# -------------------------------------------------

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


#ai.py

"""
AI agent for DisasterScope (Layer 2).

Rule-based, interpretable prediction logic operating on
historical disaster and air quality data.
"""

from typing import List, Dict


def prediction_summary(
    events: List,
    air_quality: List,
    period_days: int
) -> Dict:
    """
    Generate an interpretable risk summary over a time window.

    Rules:
    - Risk increases with average severity and AQI
    - Based on simple thresholds (no ML yet)
    """

    total_events = len(events)

    avg_severity = (
        sum(e.severity for e in events) / total_events
        if total_events > 0 else 0.0
    )

    avg_aqi = (
        sum(a.aqi for a in air_quality) / len(air_quality)
        if air_quality else 0.0
    )

    # Rule-based risk assessment
    if avg_severity >= 7.0 or avg_aqi >= 150:
        risk = "High"
    elif avg_severity >= 4.0 or avg_aqi >= 100:
        risk = "Medium"
    else:
        risk = "Low"

    return {
        "period_days": period_days,
        "total_events": total_events,
        "avg_severity": round(avg_severity, 2),
        "avg_aqi": round(avg_aqi, 2),
        "risk_level": risk,
    }


#main.py


"""
DisasterScope – Minimal FastAPI + PostGIS (Single File)
"""

# -------------------------------------------------
# Imports
# -------------------------------------------------
import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID, ST_AsGeoJSON

from dotenv import load_dotenv

# -------------------------------------------------
# Environment
# -------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# -------------------------------------------------
# Database
# -------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# -------------------------------------------------
# Models
# -------------------------------------------------
class Event(Base):
    __tablename__ = "disaster_events"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    event_type = Column(String)
    magnitude = Column(Float)
    severity = Column(String)
    event_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    geom = Column(Geometry("POINT", srid=4326))

# -------------------------------------------------
# FastAPI
# -------------------------------------------------
app = FastAPI(title="DisasterScope API")

# -------------------------------------------------
# Dependencies
# -------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/events")
def list_events(db=Depends(get_db)):
    rows = (
        db.query(
            Event.id,
            Event.source,
            Event.event_type,
            Event.magnitude,
            Event.severity,
            ST_AsGeoJSON(Event.geom).label("geometry"),
        )
        .order_by(Event.event_time.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "source": r.source,
            "event_type": r.event_type,
            "magnitude": r.magnitude,
            "severity": r.severity,
            "geometry": r.geometry,
        }
        for r in rows
    ]


@app.post("/events")
def ingest_event(
    source: str,
    event_type: str,
    magnitude: float,
    latitude: float,
    longitude: float,
    x_ingest_key: str | None = Header(default=None),
    db=Depends(get_db),
):
    if x_ingest_key != os.getenv("INGEST_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid key")

    event = Event(
        source=source,
        event_type=event_type,
        magnitude=magnitude,
        geom=ST_SetSRID(
            ST_MakePoint(longitude, latitude),
            4326,
        ),
    )

    db.add(event)
    db.commit()

    return {"status": "inserted"}




#cache.py 


"""
Simple in-memory caching with expiration for DisasterScope.
"""

import time
from typing import Any, Optional


class SimpleCache:
    def __init__(self, expiration_seconds: int = 300):
        self.store: dict[str, tuple[Any, float]] = {}
        self.expiration = expiration_seconds

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + (ttl if ttl is not None else self.expiration)
        self.store[key] = (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        item = self.store.get(key)
        if not item:
            return None

        value, expiry = item
        if time.time() < expiry:
            return value

        # expired
        del self.store[key]
        return None

    def clear(self) -> None:
        self.store.clear()


cache = SimpleCache(expiration_seconds=300)
