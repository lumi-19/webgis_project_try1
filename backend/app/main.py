from fastapi import FastAPI
from .routers import events
from .db import init_db

app = FastAPI(
    title="DisasterScope API",
    version="1.0"
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

app.include_router(events.router)
