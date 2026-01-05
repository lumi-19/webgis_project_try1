#!/usr/bin/env python3

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
INGEST_KEY = os.getenv("INGEST_API_KEY", "Theking123")

HEADERS = {
    "X-INGEST-KEY": INGEST_KEY,
    "Content-Type": "application/json",
}

# -------------------------------------------------
# Helpers
# -------------------------------------------------

COUNTRY_CENTROIDS = {
    "pakistan": (30.3753, 69.3451),
    "india": (20.5937, 78.9629),
    "china": (35.8617, 104.1954),
    "japan": (36.2048, 138.2529),
    "philippines": (12.8797, 121.7740),
    "indonesia": (-0.7893, 113.9213),
    "turkey": (38.9637, 35.2433),
    "italy": (41.8719, 12.5674),
    "mexico": (23.6345, -102.5528),
    "united states": (37.0902, -95.7129),
}

def normalize_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def infer_country_coords(text: str):
    text = text.lower()
    for country, (lat, lon) in COUNTRY_CENTROIDS.items():
        if country in text:
            return lat, lon
    return None, None

# -------------------------------------------------
# GDACS
# -------------------------------------------------

def fetch_gdacs_events(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌪️ Fetching GDACS disasters...")
    url = "https://www.gdacs.org/xml/rss.xml"
    events: List[Dict[str, Any]] = []

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or ""
            description = item.findtext("description") or ""

            t = title.lower()
            if "flood" in t:
                event_type = "flood"
            elif "cyclone" in t or "hurricane" in t:
                event_type = "cyclone"
            elif "fire" in t:
                event_type = "wildfire"
            elif "volcano" in t:
                event_type = "volcano"
            elif "earthquake" in t:
                event_type = "earthquake"
            else:
                continue  # unsupported GDACS item

            # ---- Spatial inference (NEVER SKIP) ----
            lat, lon = infer_country_coords(title + " " + description)
            location_accuracy = "country_centroid"

            if lat is None or lon is None:
                lat, lon = 0.0, 0.0
                location_accuracy = "unknown"

            events.append({
                "source": "gdacs",
                "event_type": event_type,
                "title": title[:120],
                "description": description[:300],
                "severity": "moderate",
                "latitude": lat,
                "longitude": lon,
                "location_accuracy": location_accuracy,
                "event_time": datetime.utcnow().isoformat(),
            })

        print(f"✅ GDACS events parsed: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ GDACS failed: {e}")
        return []


def fetch_usgs_earthquakes(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌍 Fetching USGS earthquakes...")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "minmagnitude": 4,
        "limit": limit,
    }

    events = []

    try:
        data = requests.get(url, params=params, timeout=20).json()

        for f in data.get("features", []):
            props = f["properties"]
            lon, lat, _ = f["geometry"]["coordinates"]

            events.append({
                "source": "usgs",
                "event_type": "earthquake",
                "title": props.get("place", "Earthquake"),
                "severity": "high" if (props.get("mag") or 0) >= 6 else "moderate",
                "latitude": lat,
                "longitude": lon,
                "event_time": datetime.fromtimestamp(
                    props["time"] / 1000
                    ).isoformat(),

            })

        print(f"✅ USGS earthquakes: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ USGS failed: {e}")
        return []


def main():
    disasters = fetch_gdacs_events() + fetch_usgs_earthquakes()

    if not disasters:
        print("⚠️ No disasters to ingest")
        return

    resp = requests.post(
        f"{BACKEND_URL}/api/events/bulk",
        json=disasters,
        headers=HEADERS,
        timeout=20,
    )

    if resp.ok:
        print(f"🚀 Ingested {len(disasters)} disaster events")
    else:
        print(f"❌ Backend error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()