import asyncio
import subprocess
from datetime import datetime
import sys
import os

# Get project root (so get_data.py is found correctly)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../")
)

GET_DATA_SCRIPT = os.path.join(PROJECT_ROOT, "get_data.py")


import asyncio
import subprocess
import sys
from datetime import datetime

async def ingestion_loop():
    """
    Background loop that runs get_data.py repeatedly
    """

    # 🔴 CRITICAL: wait for FastAPI/Uvicorn to be fully ready
    print("⏳ Waiting for API to be ready before first ingestion...")
    await asyncio.sleep(10)

    while True:
        try:
            print("🔄 Background ingestion started:", datetime.utcnow())

            subprocess.run(
                [sys.executable, GET_DATA_SCRIPT],
                check=True
            )

            print("🟢 Background ingestion finished")

        except subprocess.CalledProcessError as e:
            print("❌ Ingestion subprocess failed:", e)

        except Exception as e:
            print("❌ Unexpected ingestion error:", e)

        # ⏱️ Run every 30 minutes
        await asyncio.sleep(1800)
