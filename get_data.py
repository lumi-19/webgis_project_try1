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
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "b897f5ce8295801b678e7e485a3a79056216859f606bd194fb2353cee7260c10")

HEADERS = {
    "X-INGEST-KEY": INGEST_KEY,
    "Content-Type": "application/json",
}

def normalize_datetime(dt_str):
    """
    Ensures datetime is in the strict UTC ISO format: YYYY-MM-DDTHH:mm:ss.sssZ
    This matches the pattern required by the measurement schema.
    """
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None

# -------------------------------------------------
# GDACS & USGS (Disaster Events)
# -------------------------------------------------

def fetch_gdacs_events(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌍 Fetching GDACS disasters...")
    url = "https://www.gdacs.org/xml/rss.xml"
    events = []
    try:
        resp = requests.get(url, timeout=20)
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").lower()
            event_type = "other"
            if "flood" in title: event_type = "flood"
            elif "cyclone" in title: event_type = "cyclone"
            elif "volcano" in title: event_type = "volcano"
            elif "fire" in title: event_type = "wildfire"
            elif "earthquake" in title: event_type = "earthquake"

            events.append({
                "source": "gdacs",
                "event_type": event_type,
                "title": item.findtext("title")[:120],
                "description": (item.findtext("description") or "")[:300],
                "severity": "moderate",
                "latitude": 0.0,
                "longitude": 0.0,
                "event_time": normalize_datetime(datetime.utcnow().isoformat()),
            })
        return events
    except Exception as e:
        print(f"❌ GDACS failed: {e}")
        return []

def fetch_usgs_earthquakes(limit: int = 25) -> List[Dict[str, Any]]:
    print("🌐 Fetching USGS earthquakes...")
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
                "severity": "high" if props.get("mag", 0) >= 6 else "moderate",
                "latitude": lat,
                "longitude": lon,
                "event_time": normalize_datetime(datetime.fromtimestamp(props["time"]/1000).isoformat()),
            })
        return events
    except Exception as e:
        print(f"❌ USGS failed: {e}")
        return []

# -------------------------------------------------
# OpenAQ (Air Quality with Schema Corrections)
# -------------------------------------------------

def fetch_openaq(limit: int = 50) -> List[Dict[str, Any]]:
    print("🌫 Fetching OpenAQ air quality...")
    # Change endpoint to /v3/locations to get site-wide data with parameter filters
    url = "https://api.openaq.org/v3/locations"
    headers = {"X-API-Key": OPENAQ_API_KEY} if OPENAQ_API_KEY else {}
    
    # In V3, use parameters_id (2 = pm25, 1 = pm10)
    params = {
        "limit": limit,
        "parameters_id": [2, 1], # Filter for PM2.5 and PM10
    }

    records = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        
        # OpenAQ V3 locations returns a list of sites with their latest sensor values
        for loc in resp.json().get("results", []):
            coords = loc.get("coordinates")
            sensors = loc.get("sensors", []) # Sites contain multiple sensors in V3
            
            if not coords or not sensors:
                continue

            for s in sensors:
                # Normalize parameter and unit following the uploaded utils logic
                param_raw = s.get("parameter", {}).get("name", "").lower()
                param = param_raw.replace(".", "").replace("_", "") # unifyParameters logic
                
                unit = s.get("parameter", {}).get("units", "").lower()
                value = s.get("latest", {}).get("value")

                # Unit Unification: ppb to ppm
                if unit == 'ppb' and value is not None:
                    value = value / 1000
                    unit = 'ppm'
                elif 'ug/m3' in unit or 'µg/m' in unit:
                    unit = 'µg/m³'

                records.append({
                    "location": str(loc.get("id")),
                    "parameter": param,
                    "value": value,
                    "unit": unit,
                    "coordinates": {
                        "latitude": coords["latitude"], 
                        "longitude": coords["longitude"]
                    },
                    "date": {
                        "utc": normalize_datetime(s.get("latest", {}).get("datetime", {}).get("utc"))
                    },
                    "sourceName": loc.get("name") or "OpenAQ V3",
                    "sourceType": "government", # Default for schema compliance
                    "mobile": loc.get("ismobile") or False,
                    "country": loc.get("country", {}).get("code", "US")
                })
        return records
    except Exception as e:
        print(f"❌ OpenAQ failed: {e}")
        return []
# -------------------------------------------------
# Execution
# -------------------------------------------------

def main():
    # 1. Ingest Disasters (GDACS + USGS)
    disasters = fetch_gdacs_events() + fetch_usgs_earthquakes()
    if disasters:
        requests.post(f"{BACKEND_URL}/api/events/bulk", json=disasters, headers=HEADERS)
        print(f"✅ Ingested {len(disasters)} Disaster Events")

    # 2. Ingest Air Quality (OpenAQ)
    air_quality = fetch_openaq()
    if air_quality:
        requests.post(f"{BACKEND_URL}/api/air-quality", json=air_quality, headers=HEADERS)
        print(f"✅ Ingested {len(air_quality)} Air Quality Records")

if __name__ == "__main__":
    main()