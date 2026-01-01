"""
Database setup and models for DisasterScope.
Async SQLAlchemy + PostGIS
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

from geoalchemy2 import Geometry

# -------------------------------------------------
# Environment
# -------------------------------------------------

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

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
    __tablename__ = "disaster_events"  # 🔥 USE POSTGIS TABLE

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    event_type = Column(String, index=True)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)

    magnitude = Column(Float, nullable=True)
    severity = Column(String, nullable=True)

    event_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔥 Spatial column (PostGIS)
    geom = Column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_disaster_events_geom", "geom", postgresql_using="gist"),
    )


class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    location = Column(String, index=True)
    parameter = Column(String, index=True)
    value = Column(Float)
    unit = Column(String)

    measured_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    geom = Column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

# -------------------------------------------------
# Init DB
# -------------------------------------------------

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


print("DATABASE_URL =", DATABASE_URL)
