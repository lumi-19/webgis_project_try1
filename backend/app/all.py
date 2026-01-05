#!/usr/bin/env python3
#get_data.py
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
INGEST_KEY = os.getenv("INGEST_API_KEY", "Theking123")

HEADERS = {
    "X-INGEST-KEY": INGEST_KEY,
    "Content-Type": "application/json",
}

# -------------------------------------------------
# Helpers
# -------------------------------------------------

COUNTRY_CENTROIDS = {
    "pakistan": (30.3753, 69.3451),
    "india": (20.5937, 78.9629),
    "china": (35.8617, 104.1954),
    "japan": (36.2048, 138.2529),
    "philippines": (12.8797, 121.7740),
    "indonesia": (-0.7893, 113.9213),
    "turkey": (38.9637, 35.2433),
    "italy": (41.8719, 12.5674),
    "mexico": (23.6345, -102.5528),
    "united states": (37.0902, -95.7129),
}

def normalize_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def infer_country_coords(text: str):
    text = text.lower()
    for country, (lat, lon) in COUNTRY_CENTROIDS.items():
        if country in text:
            return lat, lon
    return None, None

# -------------------------------------------------
# GDACS
# -------------------------------------------------

def fetch_gdacs_events(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌪️ Fetching GDACS disasters...")
    url = "https://www.gdacs.org/xml/rss.xml"
    events = []

    try:
        resp = requests.get(url, timeout=20)
        root = ET.fromstring(resp.content)

        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or ""
            description = item.findtext("description") or ""

            t = title.lower()
            if "flood" in t:
                event_type = "flood"
            elif "cyclone" in t or "hurricane" in t:
                event_type = "cyclone"
            elif "fire" in t:
                event_type = "wildfire"
            elif "volcano" in t:
                event_type = "volcano"
            elif "earthquake" in t:
                event_type = "earthquake"
            else:
                continue  # skip unknown types

            lat, lon = infer_country_coords(title + " " + description)
            if lat is None:
                continue  # no spatial fallback → skip

            events.append({
                "source": "gdacs",
                "event_type": event_type,
                "title": title[:120],
                "description": description[:300],
                "severity": "moderate",
                "latitude": lat,
                "longitude": lon,
                "event_time": normalize_datetime(datetime.utcnow()),
            })

        print(f"✅ GDACS events parsed: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ GDACS failed: {e}")
        return []

# -------------------------------------------------
# USGS Earthquakes
# -------------------------------------------------

def fetch_usgs_earthquakes(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌍 Fetching USGS earthquakes...")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "minmagnitude": 4,
        "limit": limit,
    }

    events = []

    try:
        data = requests.get(url, params=params, timeout=20).json()

        for f in data.get("features", []):
            props = f["properties"]
            lon, lat, _ = f["geometry"]["coordinates"]

            events.append({
                "source": "usgs",
                "event_type": "earthquake",
                "title": props.get("place", "Earthquake"),
                "severity": "high" if (props.get("mag") or 0) >= 6 else "moderate",
                "latitude": lat,
                "longitude": lon,
                "event_time": normalize_datetime(
                    datetime.fromtimestamp(props["time"] / 1000)
                ),
            })

        print(f"✅ USGS earthquakes: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ USGS failed: {e}")
        return []

# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    disasters = fetch_gdacs_events() + fetch_usgs_earthquakes()

    if not disasters:
        print("⚠️ No disasters to ingest")
        return

    resp = requests.post(
        f"{BACKEND_URL}/api/events/bulk",
        json=disasters,
        headers=HEADERS,
        timeout=20,
    )

    if resp.ok:
        print(f"🚀 Ingested {len(disasters)} disaster events")
    else:
        print(f"❌ Backend error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()



#api.py


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
    background_tasks: BackgroundTasks,
    authorized: None = Depends(verify_api_key),
):
    # Convert Pydantic models to dicts for background task
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
    
    # Add background task - returns immediately
    background_tasks.add_task(insert_events_background, events_data)
    
    # Return immediately without waiting for DB commit
    return {"status": "accepted", "count": len(events)}

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




"""
Database setup and models for DisasterScope
Async SQLAlchemy + PostGIS (WebGIS-ready)
"""

# -------------------------------------------------
# Standard library
# -------------------------------------------------
import os
from datetime import datetime

# -------------------------------------------------
# Third-party
# -------------------------------------------------
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
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

from geoalchemy2 import Geometry

# -------------------------------------------------
# Environment
# -------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:Gondal.io@localhost:5432/disasterscope",
)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Ensure async driver is used for async SQLAlchemy
if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    print("⚠️  Converted postgresql:// to postgresql+asyncpg:// for async support")

print("DB URL:", DATABASE_URL)

# -------------------------------------------------
# Engine & Session (ASYNC)
# -------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,              # set True only for SQL debugging
    pool_pre_ping=True,
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
    __tablename__ = "disaster_events"

    # --- Core identity ---
    id = Column(Integer, primary_key=True)

    # --- Metadata ---
    source = Column(String, index=True)
    event_type = Column(String, index=True, nullable=False)

    title = Column(String)
    description = Column(String)
    severity = Column(String)

    magnitude = Column(Float)

    # --- Time ---
    event_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- Spatial (explicit + geometry) ---
    latitude = Column(Float)
    longitude = Column(Float)
    location_accuracy = Column(String, nullable=True)  # e.g., "country_centroid", "exact"

    geom = Column(
        Geometry("POINT", srid=4326),
        nullable=True,   # IMPORTANT: allow missing geometry
    )

    


class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(String, index=True)
    location = Column(String, index=True)
    parameter = Column(String, index=True)

    value = Column(Float)
    unit = Column(String)

    measured_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    geom = Column(
        Geometry("POINT", srid=4326),
        nullable=True,

    
    )

# -------------------------------------------------
# Database init (SAFE: schema already exists)
# -------------------------------------------------

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(bind=sync_conn)
        )




#MAIN.py

"""
DisasterScope – Minimal FastAPI + PostGIS (Single File)
"""

# -------------------------------------------------
# Imports
# -------------------------------------------------
import os
import asyncio
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

from backend.app.task.ingestion import ingestion_loop


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
# Startup: Background Ingestion
# -------------------------------------------------
@app.on_event("startup")
async def start_background_ingestion():
    asyncio.create_task(ingestion_loop())

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
