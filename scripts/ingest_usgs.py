import asyncio
import os
from datetime import datetime
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

# IMPORTANT: reuse backend DB setup
from backend.app.db import AsyncSessionLocal, Event

# =========================
# Configuration
# =========================

USGS_FEED_URL = os.getenv(
    "USGS_FEED_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
)

EVENT_TYPE = "EQ"
SOURCE = "USGS"


# =========================
# Helpers
# =========================

def parse_usgs_feature(feature: dict) -> dict | None:
    """
    Convert one USGS GeoJSON feature into our Event schema.
    """
    try:
        props = feature["properties"]
        geom = feature["geometry"]

        if not geom or geom["type"] != "Point":
            return None

        lon, lat, depth = geom["coordinates"]

        event_time = datetime.utcfromtimestamp(props["time"] / 1000)

        return {
            "event_type": EVENT_TYPE,
            "source": SOURCE,
            "title": props.get("title"),
            "description": props.get("place"),
            "latitude": lat,
            "longitude": lon,
            "severity": props.get("mag"),
            "event_time": event_time,
            "raw_payload": feature,
        }

    except Exception:
        return None


async def fetch_usgs_data() -> List[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(USGS_FEED_URL)
        resp.raise_for_status()
        return resp.json()["features"]


async def event_exists(
    session: AsyncSession, source: str, event_time: datetime, lat: float, lon: float
) -> bool:
    """
    Simple deduplication heuristic.
    """
    result = await session.execute(
        """
        SELECT 1 FROM events
        WHERE source = :source
          AND event_time = :event_time
          AND latitude = :lat
          AND longitude = :lon
        LIMIT 1
        """,
        {
            "source": source,
            "event_time": event_time,
            "lat": lat,
            "lon": lon,
        },
    )
    return result.first() is not None


# =========================
# Main ingestion logic
# =========================

async def ingest_usgs():
    features = await fetch_usgs_data()
    parsed_events = filter(None, (parse_usgs_feature(f) for f in features))

    async with AsyncSessionLocal() as session:
        added = 0

        for data in parsed_events:
            exists = await event_exists(
                session,
                SOURCE,
                data["event_time"],
                data["latitude"],
                data["longitude"],
            )

            if exists:
                continue

            event = Event(**data)
            session.add(event)
            added += 1

        await session.commit()

    print(f"[USGS] Ingestion complete. Added {added} new earthquake events.")


# =========================
# Entry point
# =========================

if __name__ == "__main__":
    asyncio.run(ingest_usgs())
