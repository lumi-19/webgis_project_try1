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

# Update your db.py Event model
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)  # "usgs", "gdacs", etc.
    event_type = Column(String, index=True)  # "earthquake", "flood", etc.
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    magnitude = Column(Float, nullable=True)  # For earthquakes
    severity = Column(String, nullable=True)  # Could be string like "Red", "Orange"
    event_time = Column(DateTime, nullable=True)  # When the event happened
    created_at = Column(DateTime, default=datetime.utcnow)  # When we stored it

class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)  # "openaq"
    location = Column(String, index=True)
    parameter = Column(String, index=True)  # "pm25", "pm10", etc.
    value = Column(Float)
    unit = Column(String)  # "µg/m³"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    measured_at = Column(DateTime, nullable=True)  # When measurement was taken
    created_at = Column(DateTime, default=datetime.utcnow)  # When we stored it



# -------------------------------------------------
# Init DB
# -------------------------------------------------

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
