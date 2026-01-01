from sqlalchemy import Column, Integer, String, Float, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from .database import Base

class DisasterEvent(Base):
    __tablename__ = "disaster_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    event_name = Column(String)
    magnitude = Column(Float)
    severity = Column(String)
    source = Column(String)
    start_time = Column(DateTime)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
