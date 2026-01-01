import asyncio
import os
from datetime import datetime
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import AsyncSessionLocal, Event

# =========================
# Configuration
# =========================

GDACS_URL = os.getenv(
    "GDACS_URL",
    "https://www.gdacs.org/xml/rss.xml",
)

SOURCE = "GDACS"


# =========================
# Helpers
# =========================

def parse_gdacs_item(item: dict) -> dict | None:
    """
    Convert one GDACS RSS item into Event schema.
    """
    try:
        # Some GDACS feeds include geo info in extensions
        lat = item.get("geo:lat")
        lon = item.get("geo:long")

        if lat is None or lon is None:
            return None

        event_time = datetime.fromisoformat(
            item["pubDate"].replace("Z", "+00:00")
        )

        return {
            "event_type": item.get("gdacs:eventtype", "DS"),
            "source": SOURCE,
            "title": item.get("title"),
            "description": item.get("description"),
            "latitude": float(lat),
            "longitude": float(lon),
            "severity": item.get("gdacs:alertlevel"),
            "event_time": event_time,
            "raw_payload": item,
        }

    except Exception:
        return None


async def fetch_gdacs_data() -> List[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(GDACS_URL)
        resp.raise_for_status()

        # Minimal XML → dict conversion (GDACS RSS is simple)
        import xmltodict
        parsed = xmltodict.parse(resp.text)
        return parsed["rss"]["channel"]["item"]


async def event_exists(
    session: AsyncSession, source: str, title: str, event_time: datetime
) -> bool:
    result = await session.execute(
        """
        SELECT 1 FROM events
        WHERE source = :source
          AND title = :title
          AND event_time = :event_time
        LIMIT 1
        """,
        {
            "source": source,
            "title": title,
            "event_time": event_time,
        },
    )
    return result.first() is not None


# =========================
# Main ingestion logic
# =========================

async def ingest_gdacs():
    items = await fetch_gdacs_data()
    parsed_events = filter(None, (parse_gdacs_item(i) for i in items))

    async with AsyncSessionLocal() as session:
        added = 0

        for data in parsed_events:
            exists = await event_exists(
                session,
                SOURCE,
                data["title"],
                data["event_time"],
            )

            if exists:
                continue

            session.add(Event(**data))
            added += 1

        await session.commit()

    print(f"[GDACS] Ingestion complete. Added {added} disaster events.")


# =========================
# Entry point
# =========================

if __name__ == "__main__":
    asyncio.run(ingest_gdacs())
