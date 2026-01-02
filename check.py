import asyncio
from backend.app.db import init_db

asyncio.run(init_db())
