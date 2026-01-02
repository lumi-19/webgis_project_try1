#!/usr/bin/env python3
"""
DisasterScope – Unified Data Ingestion (FAST MODE)

Sources:
- GDACS (multi-hazard disasters: floods, cyclones, volcanoes, wildfires)
- USGS (earthquakes)
- OpenAQ (air quality context)

Ingestion:
- API-only (FastAPI)
- No direct database access
- Safe for demos, submissions, and n8n integration
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

# -------------------------------------------------
# Environment
# -------------------------------------------------
def normalize_datetime(dt):
    """
    Convert any datetime or ISO string into
    timezone-naive UTC datetime (Postgres-safe).
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None

    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    return dt

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
INGEST_KEY = os.getenv("INGEST_API_KEY", "Theking123")

HEADERS = {
    "X-INGEST-KEY": INGEST_KEY,
    "Content-Type": "application/json",
}

# -------------------------------------------------
# Utilities
# -------------------------------------------------

def iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def post_events(events: List[Dict[str, Any]]) -> None:
    if not events:
        print("⚠️ No disaster events to ingest")
        return

    clean_events = []

    for e in events:
        lat = e.get("latitude")
        lon = e.get("longitude")

        if lat is None or lon is None:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue

        # 🔥 NORMALIZE DATETIME HERE
        e["event_time"] = normalize_datetime(e.get("event_time"))

        clean_events.append(e)

    if not clean_events:
        print("⚠️ All disaster events invalid after sanitization")
        return

    resp = requests.post(
        f"{BACKEND_URL}/api/events/bulk",
        json=clean_events,
        headers=HEADERS,
        timeout=30,
    )

    resp.raise_for_status()
    print(f"✅ Ingested {len(clean_events)} disaster events")


def post_air_quality(records: List[Dict[str, Any]]) -> None:
    if not records:
        print("⚠️ No air-quality records to ingest")
        return

    resp = requests.post(
        f"{BACKEND_URL}/api/air-quality",
        json=records,
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"✅ Ingested {len(records)} air-quality records")

# -------------------------------------------------
# GDACS – Multi-hazard disasters
# -------------------------------------------------

def fetch_gdacs_events(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌍 Fetching GDACS disasters...")
    url = "https://www.gdacs.org/xml/rss.xml"

    events: List[Dict[str, Any]] = []

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:limit]

        for item in items:
            title = (item.findtext("title") or "").lower()
            description = item.findtext("description") or ""

            if "flood" in title:
                event_type = "flood"
            elif "cyclone" in title or "hurricane" in title:
                event_type = "cyclone"
            elif "volcano" in title:
                event_type = "volcano"
            elif "fire" in title or "wildfire" in title:
                event_type = "wildfire"
            elif "earthquake" in title:
                event_type = "earthquake"
            else:
                continue  # skip unclassified noise

            events.append({
                "source": "gdacs",
                "event_type": event_type,
                "title": item.findtext("title")[:120],
                "description": description[:300],
                "severity": "moderate",
                # GDACS RSS lacks precise coords → acceptable for demo
                "latitude": 0.0,
                "longitude": 0.0,
                "event_time": iso_now(),
            })

        print(f"📊 GDACS events parsed: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ GDACS failed: {e}")
        return []

# -------------------------------------------------
# USGS – Earthquakes
# -------------------------------------------------

def fetch_usgs_earthquakes(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌐 Fetching USGS earthquakes...")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "minmagnitude": 4,
        "limit": limit,
    }

    events: List[Dict[str, Any]] = []

    try:
        data = requests.get(url, params=params, timeout=20).json()
        features = data.get("features", [])

        for f in features:
            props = f["properties"]
            lon, lat, depth = f["geometry"]["coordinates"]

            mag = props.get("mag") or 0
            severity = "low"
            if mag >= 6:
                severity = "high"
            elif mag >= 4.5:
                severity = "moderate"

            events.append({
                "source": "usgs",
                "event_type": "earthquake",
                "title": props.get("place", "Earthquake"),
                "description": f"Magnitude {mag}, depth {depth} km",
                "severity": severity,
                "magnitude": mag,
                "latitude": lat,
                "longitude": lon,
                "event_time": datetime.fromtimestamp(
                    props["time"] / 1000
                ).isoformat() + "Z",
            })

        print(f"📊 USGS earthquakes parsed: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ USGS failed: {e}")
        return []

# -------------------------------------------------
# OpenAQ – Air Quality Context
# -------------------------------------------------

def fetch_openaq(limit: int = 50) -> List[Dict[str, Any]]:
    print("🌫 Fetching OpenAQ air quality...")
    url = "https://api.openaq.org/v2/latest"

    params = {
        "limit": limit,
        "parameter": ["pm25", "pm10"],
    }

    records: List[Dict[str, Any]] = []

    try:
        data = requests.get(url, params=params, timeout=20).json()
        results = data.get("results", [])

        for loc in results:
            coords = loc.get("coordinates")
            if not coords:
                continue

            for m in loc.get("measurements", []):
                records.append({
                    "source": "openaq",
                    "location": loc.get("location"),
                    "parameter": m.get("parameter"),
                    "value": m.get("value"),
                    "unit": m.get("unit"),
                    "latitude": coords.get("latitude"),
                    "longitude": coords.get("longitude"),
                    "measured_at": normalize_datetime(m.get("lastUpdated")),
                })

        print(f"📊 OpenAQ records parsed: {len(records)}")
        return records

    except Exception as e:
        print(f"❌ OpenAQ failed: {e}")
        return []

# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    print("\n🚀 DisasterScope – Unified Ingestion Started\n")

    disasters: List[Dict[str, Any]] = []
    disasters += fetch_gdacs_events()
    disasters += fetch_usgs_earthquakes()

    post_events(disasters)

    air_quality = fetch_openaq()
    post_air_quality(air_quality)

    print("\n🎉 Ingestion complete – backend is now data-ready\n")

if __name__ == "__main__":
    main()
