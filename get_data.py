#!/usr/bin/env python3
"""
DisasterScope Data Fetcher - WORKING VERSION
Gets USGS + GDACS data (OpenAQ optional)
"""
import requests
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🚀 DisasterScope Data Fetcher")
print("=" * 50)

# Your backend URL and API key
BACKEND_URL = "http://localhost:8080"
API_KEY = os.getenv("INGEST_API_KEY", "Theking123")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

HEADERS = {
    "X-INGEST-KEY": API_KEY,
    "Content-Type": "application/json"
}

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not running! {e}")
        print("\n💡 Start backend with:")
        print("   uvicorn backend.app.api:app --reload --host 0.0.0.0 --port 8080")
        return False

def fetch_usgs():
    """Fetch earthquakes from USGS and send to backend"""
    print("\n🌍 Fetching USGS earthquakes...")
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "minmagnitude": 4,
        "limit": 50  # Limit for testing
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        features = data.get("features", [])
        print(f"📊 Found {len(features)} earthquakes")
        
        if not features:
            print("⚠️ No earthquakes found in last 24 hours")
            return 0
        
        # Process and send earthquakes
        inserted = 0
        for feature in features[:10]:  # Send only first 10 for testing
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            
            severity = "low"
            mag = props.get("mag", 0)
            if mag >= 6.0:
                severity = "high"
            elif mag >= 4.5:
                severity = "moderate"
            
            earthquake = {
                "source": "usgs",
                "event_type": "earthquake",
                "title": props.get("place", "Unknown Location"),
                "description": f"Magnitude: {mag}, Depth: {coords[2]}km",
                "latitude": coords[1],
                "longitude": coords[0],
                "magnitude": mag,
                "severity": severity,
                "event_time": datetime.fromtimestamp(props["time"]/1000).isoformat() + "Z"
            }
            
            # Send to backend
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/events",
                    headers=HEADERS,
                    json=earthquake,
                    timeout=5
                )
                if response.status_code == 200:
                    inserted += 1
                    print(f"   ✅ {earthquake['title']}")
                else:
                    print(f"   ❌ Failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print(f"✅ Sent {inserted} earthquakes to backend")
        return inserted
        
    except Exception as e:
        print(f"❌ Error fetching USGS: {e}")
        return 0

def fetch_gdacs():
    """Fetch disasters from GDACS"""
    print("\n🌪️ Fetching GDACS disasters...")
    
    # Try to fetch GDACS - it might be blocked or slow
    try:
        response = requests.get("https://www.gdacs.org/xml/rss.xml", timeout=10)
        response.raise_for_status()
        
        # Simple parsing - just count items
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        items = root.findall('.//item')
        print(f"📊 Found {len(items)} GDACS disaster alerts")
        
        # Send a few sample disasters
        inserted = 0
        for i, item in enumerate(items[:5]):  # Send only 5 for testing
            title_elem = item.find('title')
            if title_elem is None:
                continue
                
            title = title_elem.text
            description_elem = item.find('description')
            description = description_elem.text if description_elem else ""
            
            # Determine disaster type
            disaster_type = "other"
            title_lower = title.lower()
            
            if 'earthquake' in title_lower:
                disaster_type = "earthquake"
            elif 'flood' in title_lower:
                disaster_type = "flood"
            elif 'cyclone' in title_lower or 'hurricane' in title_lower:
                disaster_type = "cyclone"
            elif 'volcano' in title_lower:
                disaster_type = "volcano"
            elif 'wildfire' in title_lower:
                disaster_type = "wildfire"
            
            disaster = {
                "source": "gdacs",
                "event_type": disaster_type,
                "title": title[:100],  # Limit title length
                "description": description[:200] if description else "No description",
                "latitude": 0.0,  # Placeholder
                "longitude": 0.0,
                "severity": "medium",
                "event_time": datetime.utcnow().isoformat() + "Z"
            }
            
            # Send to backend
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/events",
                    headers=HEADERS,
                    json=disaster,
                    timeout=5
                )
                if response.status_code == 200:
                    inserted += 1
                    print(f"   ✅ {disaster_type.title()}: {title[:50]}...")
                else:
                    print(f"   ❌ Failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print(f"✅ Sent {inserted} GDACS disasters to backend")
        return inserted
        
    except Exception as e:
        print(f"❌ Error fetching GDACS: {e}")
        print("⚠️ GDACS might be blocked or slow. Using sample data instead.")
        
        # Use sample disasters if GDACS fails
        sample_disasters = [
            {
                "source": "gdacs",
                "event_type": "earthquake",
                "title": "Sample Earthquake - Magnitude 5.6",
                "description": "Test earthquake data",
                "latitude": 34.0,
                "longitude": 72.0,
                "severity": "high",
                "event_time": datetime.utcnow().isoformat() + "Z"
            },
            {
                "source": "gdacs",
                "event_type": "flood",
                "title": "Sample Flood Alert",
                "description": "Test flood data",
                "latitude": 31.5,
                "longitude": 74.3,
                "severity": "medium",
                "event_time": datetime.utcnow().isoformat() + "Z"
            }
        ]
        
        inserted = 0
        for disaster in sample_disasters:
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/events",
                    headers=HEADERS,
                    json=disaster,
                    timeout=5
                )
                if response.status_code == 200:
                    inserted += 1
            except:
                pass
        
        print(f"✅ Sent {inserted} sample disasters to backend")
        return inserted

def fetch_openaq():
    """Fetch air quality from OpenAQ (optional)"""
    print("\n🌫️ OpenAQ requires API key")
    
    if not OPENAQ_API_KEY:
        print("⚠️  Skipping OpenAQ - No API key found")
        print("💡 Get free key from: https://docs.openaq.org/docs")
        print("💡 Then add to .env: OPENAQ_API_KEY=your_key_here")
        return 0
    
    print("📡 Fetching OpenAQ data with API key...")
    
    url = "https://api.openaq.org/v3/measurements"
    params = {
        "limit": 20,
        "page": 1,
        "sort": "desc",
        "order_by": "datetime"
    }
    headers = {"X-API-Key": OPENAQ_API_KEY}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        print(f"📊 Found {len(results)} air quality readings")
        
        inserted = 0
        for result in results[:5]:  # Send only 5 for testing
            reading = {
                "source": "openaq",
                "location": result.get("location", "Unknown"),
                "parameter": result.get("parameter", "pm25"),
                "value": result.get("value", 0),
                "unit": result.get("unit", "µg/m³"),
                "latitude": result.get("coordinates", {}).get("latitude"),
                "longitude": result.get("coordinates", {}).get("longitude"),
                "measured_at": datetime.utcnow().isoformat() + "Z"
            }
            
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/air-quality",
                    headers=HEADERS,
                    json=reading,
                    timeout=5
                )
                if response.status_code == 200:
                    inserted += 1
            except:
                pass
        
        print(f"✅ Sent {inserted} air quality readings to backend")
        return inserted
        
    except Exception as e:
        print(f"❌ Error fetching OpenAQ: {e}")
        return 0

def check_database():
    """Check what's in the database"""
    print("\n📊 Checking database contents...")
    
    try:
        # Get events
        events_response = requests.get(f"{BACKEND_URL}/api/events", timeout=5)
        if events_response.status_code == 200:
            events = events_response.json()
            print(f"🌍 Events in database: {len(events)}")
            
            # Group by source
            sources = {}
            for event in events:
                source = event.get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1
            
            for source, count in sources.items():
                print(f"   - {source}: {count}")
        
        # Get air quality
        aq_response = requests.get(f"{BACKEND_URL}/api/air-quality", timeout=5)
        if aq_response.status_code == 200:
            aq_data = aq_response.json()
            print(f"🌫️  Air quality readings: {len(aq_data)}")
            
        # Get predictions
        pred_response = requests.get(f"{BACKEND_URL}/api/predictions/summary?days=7", timeout=5)
        if pred_response.status_code == 200:
            pred_data = pred_response.json()
            print(f"📈 Risk level: {pred_data.get('risk_level', 'unknown')}")
            
    except Exception as e:
        print(f"⚠️ Could not check database: {e}")

def main():
    """Main function"""
    start_time = time.time()
    
    print("🔧 Configuration:")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   API Key: {'✓ Set' if API_KEY else '✗ Missing'}")
    print(f"   OpenAQ Key: {'✓ Set' if OPENAQ_API_KEY else '✗ Missing (optional)'}")
    
    # Check backend
    if not check_backend():
        return
    
    print("\n" + "="*50)
    print("🚀 STARTING DATA FETCH")
    print("="*50)
    
    # Check current database state
    check_database()
    
    # Fetch data
    usgs_count = fetch_usgs()
    time.sleep(1)
    
    gdacs_count = fetch_gdacs()
    time.sleep(1)
    
    openaq_count = fetch_openaq()
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*50)
    print("🎉 FETCH COMPLETE")
    print(f"⏱️  Time: {elapsed:.2f} seconds")
    print(f"🌍 USGS Earthquakes: {usgs_count}")
    print(f"🌪️  GDACS Disasters: {gdacs_count}")
    print(f"🌫️  OpenAQ Readings: {openaq_count}")
    print("="*50)
    
    # Check database again
    check_database()
    
    print("\n✅ All done!")
    print("\n🔗 Useful links:")
    print(f"   📊 View data: {BACKEND_URL}/api/events")
    print(f"   📝 API docs: {BACKEND_URL}/docs")
    print(f"   📈 Predictions: {BACKEND_URL}/api/predictions/summary")

if __name__ == "__main__":
    main()