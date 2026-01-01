"""
AI agent for DisasterScope (Layer 2).

Rule-based, interpretable prediction logic operating on
historical disaster and air quality data.
"""

from typing import List, Dict
from datetime import datetime, timedelta

def prediction_summary(
    events: List,
    air_quality: List,
    period_days: int
) -> Dict:
    """
    Generate an interpretable risk summary over a time window.
    """
    
    if not events and not air_quality:
        return {
            "period_days": period_days,
            "risk_level": "Unknown",
            "message": "No data available for the selected period",
            "events_summary": {},
            "air_quality_summary": {}
        }
    
    # Event Analysis
    total_events = len(events)
    earthquake_count = sum(1 for e in events if e.event_type == "earthquake")
    flood_count = sum(1 for e in events if "flood" in str(e.event_type).lower())
    
    avg_magnitude = None
    if any(e.magnitude for e in events if e.magnitude):
        magnitudes = [e.magnitude for e in events if e.magnitude]
        avg_magnitude = sum(magnitudes) / len(magnitudes)
    
    # Air Quality Analysis
    total_aq_readings = len(air_quality)
    
    # Group by parameter
    pm25_readings = [aq for aq in air_quality if aq.parameter == "pm25"]
    pm10_readings = [aq for aq in air_quality if aq.parameter == "pm10"]
    
    avg_pm25 = None
    if pm25_readings:
        avg_pm25 = sum(aq.value for aq in pm25_readings) / len(pm25_readings)
    
    avg_pm10 = None
    if pm10_readings:
        avg_pm10 = sum(aq.value for aq in pm10_readings) / len(pm10_readings)
    
    # Rule-based Risk Assessment
    risk_level = "Low"
    reasons = []
    
    # Earthquake risk rules
    if earthquake_count >= 5:
        risk_level = "High"
        reasons.append(f"High seismic activity ({earthquake_count} earthquakes)")
    elif earthquake_count >= 2:
        risk_level = "Medium" if risk_level == "Low" else risk_level
        reasons.append(f"Moderate seismic activity ({earthquake_count} earthquakes)")
    
    # Magnitude-based risk
    if avg_magnitude and avg_magnitude >= 6.0:
        risk_level = "High"
        reasons.append(f"High average magnitude ({avg_magnitude:.1f})")
    elif avg_magnitude and avg_magnitude >= 4.5:
        risk_level = "Medium" if risk_level == "Low" else risk_level
        reasons.append(f"Moderate average magnitude ({avg_magnitude:.1f})")
    
    # Air quality risk rules (WHO guidelines)
    if avg_pm25 and avg_pm25 >= 75:  # WHO 24-hour mean: 15 µg/m³
        risk_level = "High"
        reasons.append(f"Very high PM2.5 levels ({avg_pm25:.1f} µg/m³)")
    elif avg_pm25 and avg_pm25 >= 35:
        risk_level = "Medium" if risk_level == "Low" else risk_level
        reasons.append(f"Elevated PM2.5 levels ({avg_pm25:.1f} µg/m³)")
    
    if avg_pm10 and avg_pm10 >= 150:  # WHO 24-hour mean: 45 µg/m³
        risk_level = "High"
        reasons.append(f"Very high PM10 levels ({avg_pm10:.1f} µg/m³)")
    elif avg_pm10 and avg_pm10 >= 100:
        risk_level = "Medium" if risk_level == "Low" else risk_level
        reasons.append(f"Elevated PM10 levels ({avg_pm10:.1f} µg/m³)")
    
    return {
        "period_days": period_days,
        "risk_level": risk_level,
        "reasons": reasons,
        "events_summary": {
            "total_events": total_events,
            "earthquake_count": earthquake_count,
            "flood_count": flood_count,
            "avg_magnitude": round(avg_magnitude, 2) if avg_magnitude else None
        },
        "air_quality_summary": {
            "total_readings": total_aq_readings,
            "avg_pm25": round(avg_pm25, 2) if avg_pm25 else None,
            "avg_pm10": round(avg_pm10, 2) if avg_pm10 else None,
            "pm25_readings": len(pm25_readings),
            "pm10_readings": len(pm10_readings)
        },
        "timestamp": datetime.utcnow().isoformat()
    }