"""
Simple All-in-One Data Ingestor
Fetches from USGS, GDACS, OpenAQ and saves to your database
"""
import requests
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db import AsyncSessionLocal, Event, AirQuality
import os

async def fetch_and_save_usgs():
    """Fetch earthquakes from USGS and save to DB"""
    print("🌍 Fetching USGS earthquakes...")
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "minmagnitude": 4
    }
    
    # Fetch data
    response = requests.get(url, params=params)
    data = response.json()
    
    print(f"📊 Found {len(data.get('features', []))} earthquakes")
    
    # Save to database
    async with AsyncSessionLocal() as session:
        inserted = 0
        for feature in data.get("features", []):
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            
            # Check if already exists
            existing = await session.execute(
                f"SELECT id FROM events WHERE source='usgs' AND title='{props['place']}' "
                f"AND event_time='{datetime.fromtimestamp(props['time']/1000).isoformat()}'"
            )
            
            if existing.scalar() is None:
                severity = "low"
                if props["mag"] >= 6.0:
                    severity = "high"
                elif props["mag"] >= 4.5:
                    severity = "moderate"
                
                event = Event(
                    source="usgs",
                    event_type="earthquake",
                    title=props["place"],
                    description=f"Magnitude: {props['mag']}, Depth: {coords[2]}km",
                    latitude=coords[1],
                    longitude=coords[0],
                    magnitude=props["mag"],
                    severity=severity,
                    event_time=datetime.fromtimestamp(props["time"]/1000)
                )
                session.add(event)
                inserted += 1
        
        await session.commit()
        print(f"✅ Saved {inserted} new earthquakes to database")
        return inserted

async def fetch_and_save_gdacs():
    """Fetch disasters from GDACS RSS feed and save to DB"""
    print("🌪️ Fetching GDACS disasters...")
    
    url = "https://www.gdacs.org/xml/rss.xml"
    
    # Fetch RSS feed
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch GDACS: {response.status_code}")
        return 0
    
    # Parse XML
    root = ET.fromstring(response.content)
    
    # Namespaces for GDACS XML
    namespaces = {
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'gdacs': 'http://www.gdacs.org'
    }
    
    disasters = []
    
    # Parse each item in RSS feed
    for item in root.findall('.//item'):
        title_elem = item.find('title')
        description_elem = item.find('description')
        pubdate_elem = item.find('pubDate')
        link_elem = item.find('link')
        
        # Get coordinates
        lat_elem = item.find('geo:lat', namespaces)
        lon_elem = item.find('geo:long', namespaces)
        
        # Get GDACS severity
        severity_elem = item.find('gdacs:severity', namespaces)
        alert_elem = item.find('gdacs:alertlevel', namespaces)
        
        if title_elem is not None:
            title = title_elem.text
            description = description_elem.text if description_elem else ""
            link = link_elem.text if link_elem else ""
            
            # Determine disaster type from title
            disaster_type = "other"
            title_lower = title.lower()
            
            if any(word in title_lower for word in ['earthquake', 'quake']):
                disaster_type = "earthquake"
            elif any(word in title_lower for word in ['flood', 'flooding']):
                disaster_type = "flood"
            elif any(word in title_lower for word in ['cyclone', 'hurricane', 'typhoon']):
                disaster_type = "cyclone"
            elif any(word in title_lower for word in ['volcano', 'eruption']):
                disaster_type = "volcano"
            elif any(word in title_lower for word in ['wildfire', 'fire']):
                disaster_type = "wildfire"
            elif any(word in title_lower for word in ['drought']):
                disaster_type = "drought"
            
            # Parse coordinates
            latitude = float(lat_elem.text) if lat_elem is not None else None
            longitude = float(lon_elem.text) if lon_elem is not None else None
            
            # Get severity
            severity = "unknown"
            if severity_elem is not None:
                severity = severity_elem.text
            elif alert_elem is not None:
                severity = alert_elem.text
            
            disasters.append({
                "title": title,
                "description": description,
                "link": link,
                "type": disaster_type,
                "latitude": latitude,
                "longitude": longitude,
                "severity": severity,
                "pub_date": pubdate_elem.text if pubdate_elem else datetime.utcnow().isoformat()
            })
    
    print(f"📊 Found {len(disasters)} GDACS disasters")
    
    # Save to database
    async with AsyncSessionLocal() as session:
        inserted = 0
        for disaster in disasters:
            # Parse publication date
            try:
                # Try to parse the date string
                pub_date_str = disaster["pub_date"]
                # Remove timezone info for simplicity
                if "GMT" in pub_date_str or "UTC" in pub_date_str:
                    pub_date_str = pub_date_str.split(" GMT")[0].split(" UTC")[0]
                event_time = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S")
            except:
                event_time = datetime.utcnow()
            
            # Check if already exists
            existing = await session.execute(
                f"SELECT id FROM events WHERE source='gdacs' AND title='{disaster['title']}'"
            )
            
            if existing.scalar() is None:
                event = Event(
                    source="gdacs",
                    event_type=disaster["type"],
                    title=disaster["title"],
                    description=disaster["description"],
                    latitude=disaster["latitude"],
                    longitude=disaster["longitude"],
                    magnitude=None,  # GDACS doesn't have magnitude
                    severity=disaster["severity"],
                    event_time=event_time,
                    url=disaster["link"]
                )
                session.add(event)
                inserted += 1
        
        await session.commit()
        print(f"✅ Saved {inserted} new GDACS disasters to database")
        return inserted

async def fetch_and_save_openaq():
    """Fetch air quality from OpenAQ and save to DB"""
    print("🌫️ Fetching OpenAQ air quality...")
    
    url = "https://api.openaq.org/v3/measurements"
    params = {
        "limit": 100,  # Reduced for faster testing
        "page": 1,
        "sort": "desc",
        "order_by": "datetime"
    }
    headers = {}
    
    # Optional: Add your OpenAQ API key if you have one
    api_key = os.getenv("OPENAQ_API_KEY", "b897f5ce8295801b678e7e485a3a79056216859f606bd194fb2353cee7260c10")
    if api_key:
        headers["X-API-Key"] = 'Theking123'
    
    # Fetch data
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch OpenAQ: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return 0
    
    data = response.json()
    
    print(f"📊 Found {len(data.get('results', []))} air quality readings")
    
    # Save to database
    async with AsyncSessionLocal() as session:
        inserted = 0
        for result in data.get("results", []):
            # Parse datetime
            try:
                measured_at = datetime.fromisoformat(
                    result.get("date", {}).get("utc", datetime.utcnow().isoformat())
                )
            except:
                measured_at = datetime.utcnow()
            
            # Check if already exists (simplified check)
            location = result.get("location", "Unknown").replace("'", "''")
            parameter = result.get("parameter", "unknown")
            value = result.get("value", 0)
            
            existing = await session.execute(
                f"SELECT id FROM air_quality WHERE location='{location}' "
                f"AND parameter='{parameter}' AND value={value}"
            )
            
            if existing.scalar() is None:
                coordinates = result.get("coordinates", {})
                aq = AirQuality(
                    source="openaq",
                    location=location,
                    parameter=parameter,
                    value=value,
                    unit=result.get("unit", "µg/m³"),
                    latitude=coordinates.get("latitude"),
                    longitude=coordinates.get("longitude"),
                    measured_at=measured_at,
                    city=result.get("city", ""),
                    country=result.get("country", "")
                )
                session.add(aq)
                inserted += 1
        
        await session.commit()
        print(f"✅ Saved {inserted} new air quality readings to database")
        return inserted

async def run_all_ingestion():
    """Run all data ingestion"""
    print("\n" + "="*50)
    print("🚀 STARTING DATA INGESTION")
    print("="*50)
    
    start_time = time.time()
    
    # Run all three ingestions
    usgs_count = await fetch_and_save_usgs()
    await asyncio.sleep(1)  # Small delay between requests
    
    gdacs_count = await fetch_and_save_gdacs()
    await asyncio.sleep(1)
    
    aq_count = await fetch_and_save_openaq()
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*50)
    print("📊 INGESTION COMPLETE")
    print(f"⏱️  Time taken: {elapsed:.2f} seconds")
    print(f"🌍 USGS Earthquakes: {usgs_count}")
    print(f"🌪️  GDACS Disasters: {gdacs_count}")
    print(f"🌫️  OpenAQ Readings: {aq_count}")
    print("="*50)
    
    # Show total counts
    async with AsyncSessionLocal() as session:
        # Count by source
        events_by_source = await session.execute(
            "SELECT source, COUNT(*) FROM events GROUP BY source"
        )
        total_events = await session.execute("SELECT COUNT(*) FROM events")
        total_aq = await session.execute("SELECT COUNT(*) FROM air_quality")
        
        print(f"\n📈 DATABASE TOTALS:")
        print(f"   Total events: {total_events.scalar()}")
        for source, count in events_by_source.fetchall():
            print(f"   - {source}: {count}")
        print(f"   Total air quality: {total_aq.scalar()}")
    
    return {
        "usgs_count": usgs_count,
        "gdacs_count": gdacs_count,
        "aq_count": aq_count,
        "total_time": elapsed
    }

if __name__ == "__main__":
    # Run when executed directly
    result = asyncio.run(run_all_ingestion())
    print(f"\n🎉 Result: {result}")