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
