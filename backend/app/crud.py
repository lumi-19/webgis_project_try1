from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint, ST_AsGeoJSON
from .models import DisasterEvent

def create_event(db: Session, data):
    event = DisasterEvent(
        event_type=data.event_type,
        event_name=data.title,
        magnitude=data.magnitude,
        severity=data.severity,
        source=data.source,
        start_time=data.event_time,
        geom=ST_SetSRID(
            ST_MakePoint(data.longitude, data.latitude),
            4326
        )
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(db: Session):
    rows = (
        db.query(
            DisasterEvent.id,
            DisasterEvent.source,
            DisasterEvent.event_type,
            DisasterEvent.magnitude,
            DisasterEvent.severity,
            DisasterEvent.start_time,
            ST_AsGeoJSON(DisasterEvent.geom).label("geometry")
        )
        .order_by(DisasterEvent.start_time.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "source": r.source,
            "event_type": r.event_type,
            "magnitude": r.magnitude,
            "severity": r.severity,
            "event_time": r.start_time,
            "geometry": r.geometry
        }
        for r in rows
    ]
