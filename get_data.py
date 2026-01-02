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

        # 🔥 NORMALIZE DATETIME HERE → ensure ISO strings for JSON
        dt = normalize_datetime(e.get("event_time"))
        if dt is None:
            e["event_time"] = None
        else:
            # make timezone-naive UTC explicit ISO string
            e["event_time"] = dt.isoformat()

        clean_events.append(e)

    if not clean_events:
        print("⚠️ All disaster events invalid after sanitization")
        return

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/events/bulk",
            json=clean_events,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        print(f"✅ Ingested {len(clean_events)} disaster events")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to ingest events: {e}")
        return


def post_air_quality(records: List[Dict[str, Any]]) -> None:
    if not records:
        print("⚠️ No air-quality records to ingest")
        return

    # Normalize any datetime objects to ISO strings
    clean = []
    for r in records:
        dt = normalize_datetime(r.get("measured_at"))
        if dt is None:
            r["measured_at"] = None
        else:
            r["measured_at"] = dt.isoformat()
        clean.append(r)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/air-quality",
            json=clean,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        print(f"✅ Ingested {len(clean)} air-quality records")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to ingest air-quality records: {e}")
        return

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
api_key_present = bool(os.getenv("OPENAQ_API_KEY", ""))
print("🔑 OPENAQ_API_KEY present:", api_key_present)

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
    print("🌫 Fetching OpenAQ air quality (v3)...")

    url = "https://api.openaq.org/v3/measurements"
    api_key = os.getenv("OPENAQ_API_KEY", "")
    headers = {"X-API-Key": api_key} if api_key else {}

    params = {
        "limit": limit,
        "parameter": ["pm25", "pm10"],
        "sort": "desc"
    }

    records: List[Dict[str, Any]] = []

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"❌ OpenAQ HTTP {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()

        for r in data.get("results", []):
            coords = r.get("coordinates")
            if not coords:
                continue

            records.append({
                "source": "openaq",
                "location": r.get("location"),
                "parameter": r.get("parameter"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
                "measured_at": r.get("date", {}).get("utc"),
            })

        print(f"📊 OpenAQ records parsed: {len(records)}")
        return records

    except Exception as e:
        print(f"❌ OpenAQ failed: {e}")
        return []


# -------------------------------------------------
# OpenAQ key validation & diagnostics
# -------------------------------------------------

def diagnose_openaq_key() -> None:
    """Try several v3 endpoints with and without the API key and print results.
    Does NOT print the key value (only presence).
    """
    api_key = os.getenv("OPENAQ_API_KEY", "")
    base = "https://api.openaq.org"
    endpoints = ["/v3/measurements", "/v3/locations", "/v3/parameters"]

    print("🔬 Running OpenAQ diagnostic (requests with and without X-API-Key)")
    for ep in endpoints:
        url = base + ep
        params = {"limit": 1}
        for use_key in (False, True):
            label = f"with key" if use_key else "without key"
            print(f"  • Requesting {ep} {label} → {url}?limit=1")
            headers = {"X-API-Key": api_key} if (use_key and api_key) else {}
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                snippet = resp.text.replace("\n", " ")[:300]
                print(f"    → HTTP {resp.status_code} | using_key={use_key} | snippet={snippet}")
            except requests.RequestException as e:
                print(f"    → Request failed: {e}")


def validate_openaq_key() -> bool:
    api_key = os.getenv("OPENAQ_API_KEY", "")
    if not api_key:
        print("❌ OPENAQ_API_KEY not set. Please add it to your .env or environment.")
        return False

    # Quick authenticated check against a simple documented endpoint
    url = "https://api.openaq.org/v3/locations"
    try:
        print("🔎 Performing quick authenticated request to /v3/locations?limit=1")
        resp = requests.get(url, headers={"X-API-Key": api_key}, params={"limit": 1}, timeout=10)
        print(f"🔎 Quick check HTTP {resp.status_code}")

        if resp.status_code == 401:
            print("❌ Unauthorized. The API key appears invalid or needs to be enabled.")
            print("Response snippet:", resp.text[:500])
            print("Running extended diagnostic...")
            diagnose_openaq_key()
            return False

        if resp.status_code == 404:
            print("❌ Not Found (404) for /v3/locations — unexpected. Running full diagnosis.")
            diagnose_openaq_key()
            return False

        resp.raise_for_status()
        print("✅ OpenAQ key accepted (quick check)")
        return True

    except requests.RequestException as e:
        print(f"❌ OpenAQ key check failed: {e}")
        print("Running extended diagnostic...")
        diagnose_openaq_key()
        return False


# -------------------------------------------------
# Main (OpenAQ-only)
# -------------------------------------------------

def main():
    print("\n🚀 DisasterScope – Unified Ingestion Started (OpenAQ-only mode)\n")

    if not validate_openaq_key():
        print("Aborting: OpenAQ validation failed. Fix API key and re-run.")
        return

    air_quality = fetch_openaq()
    post_air_quality(air_quality)

    print("\n🎉 Ingestion complete – backend is now data-ready (OpenAQ-only)\n")


if __name__ == "__main__":
    main()
