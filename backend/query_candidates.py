import asyncio
import os
import sys
from dotenv import load_dotenv

backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.append(backend_path)

env_path = os.path.join(backend_path, ".env")
load_dotenv(dotenv_path=env_path, override=True)

from database import candidates_col, db_manager

async def check():
    await db_manager.connect()
    async for c in candidates_col.find():
        print(f"Name: {c.get('name')} | Email: {c.get('email')} | Phone: {c.get('phone')} | Exp: {c.get('experience_years')} yrs | Score: {c.get('score')}%")

if __name__ == "__main__":
    asyncio.run(check())
