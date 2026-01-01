from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..schemas import EventIn
from ..crud import create_event, get_events
import os

router = APIRouter(prefix="/api/events", tags=["Events"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("")
def ingest_event(
    event: EventIn,
    db: Session = Depends(get_db),
    x_ingest_key: str = Header(None)
):
    if x_ingest_key != os.getenv("INGEST_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid ingest key")

    create_event(db, event)
    return {"status": "inserted"}

@router.get("")
def list_events(db: Session = Depends(get_db)):
    return get_events(db)
