import asyncio
import os
from datetime import datetime
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import AsyncSessionLocal, AirQuality

# =========================
# Configuration
# =========================

OPENAQ_URL = os.getenv(
    "OPENAQ_URL",
    "https://api.openaq.org/v2/latest",
)

SOURCE = "OpenAQ"
LIMIT = 100


# =========================
# Helpers
# =========================

def parse_openaq_result(result: dict) -> List[dict]:
    """
    Convert OpenAQ location result into AirQuality rows.
    """
    records = []

    coords = result.get("coordinates")
    if not coords:
        return records

    lat = coords["latitude"]
    lon = coords["longitude"]

    for m in result.get("measurements", []):
        try:
            records.append(
                {
                    "source": SOURCE,
                    "parameter": m["parameter"],
                    "value": m["value"],
                    "unit": m["unit"],
                    "latitude": lat,
                    "longitude": lon,
                    "measured_at": datetime.fromisoformat(
                        m["lastUpdated"].replace("Z", "+00:00")
                    ),
                    "raw_payload": m,
                }
            )
        except Exception:
            continue

    return records


async def fetch_openaq_data() -> List[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            OPENAQ_URL,
            params={"limit": LIMIT},
        )
        resp.raise_for_status()
        return resp.json()["results"]


async def record_exists(
    session: AsyncSession,
    parameter: str,
    measured_at: datetime,
    lat: float,
    lon: float,
) -> bool:
    result = await session.execute(
        """
        SELECT 1 FROM air_quality
        WHERE parameter = :parameter
          AND measured_at = :measured_at
          AND latitude = :lat
          AND longitude = :lon
        LIMIT 1
        """,
        {
            "parameter": parameter,
            "measured_at": measured_at,
            "lat": lat,
            "lon": lon,
        },
    )
    return result.first() is not None


# =========================
# Main ingestion logic
# =========================

async def ingest_openaq():
    results = await fetch_openaq_data()

    async with AsyncSessionLocal() as session:
        added = 0

        for r in results:
            records = parse_openaq_result(r)

            for data in records:
                exists = await record_exists(
                    session,
                    data["parameter"],
                    data["measured_at"],
                    data["latitude"],
                    data["longitude"],
                )

                if exists:
                    continue

                session.add(AirQuality(**data))
                added += 1

        await session.commit()

    print(f"[OpenAQ] Ingestion complete. Added {added} AQ records.")


# =========================
# Entry point
# =========================

if __name__ == "__main__":
    asyncio.run(ingest_openaq())
