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

