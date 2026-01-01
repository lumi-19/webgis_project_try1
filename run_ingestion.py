#!/usr/bin/env python3
"""
Simple script to run data ingestion - put this in your PROJECT ROOT
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the FUNCTION, not the module
from scripts.simple_ingestor import run_all_ingestion

def main():
    """Run ingestion"""
    print("🚀 DisasterScope Data Ingestion")
    print("=" * 40)
    
    # Run ingestion
    result = asyncio.run(run_all_ingestion())  # 👈 This should work now
    
    print("\n✅ Done! Your data is ready.")
    print("\n📊 To view your data:")
    print("   1. Make sure backend is running: uvicorn backend.app.api:app --reload")
    print("   2. Visit: http://localhost:8080/api/events")
    print("   3. Visit: http://localhost:8080/api/air-quality")
    
    return result

if __name__ == "__main__":
    main()