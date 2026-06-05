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
    c = await candidates_col.find_one({"filename": "1777012539065.pdf"})
    if c:
        print(f"FILENAME: {c.get('filename')}")
        print(f"RAW TEXT (length {len(c.get('raw_text', ''))}):")
        print(c.get('raw_text', '')[:1000])
    else:
        print("Candidate not found!")

if __name__ == "__main__":
    asyncio.run(check())
