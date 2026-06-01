import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
MONGO_URI = os.getenv("MONGO_URI")

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["ats_platform"]
    candidates_col = db["candidates"]
    
    candidate = await candidates_col.find_one({"name": "Ohli"})
    
    start_time_raw = candidate.get("interview", {}).get("start_time")
    end_time_raw = candidate.get("interview", {}).get("end_time") or datetime.utcnow()
    
    print(f"start_time_raw type: {type(start_time_raw)}, value: {start_time_raw}")
    print(f"end_time_raw type: {type(end_time_raw)}, value: {end_time_raw}")
    
    if start_time_raw:
        if isinstance(start_time_raw, str):
            start_time = datetime.fromisoformat(start_time_raw)
        else:
            start_time = start_time_raw
        
        if isinstance(end_time_raw, str):
            end_time = datetime.fromisoformat(end_time_raw)
        else:
            end_time = end_time_raw
            
        diff = end_time - start_time
        print(f"diff: {diff}, total_seconds: {diff.total_seconds()}")
        duration_mins = max(1, int(diff.total_seconds() / 60))
    else:
        duration_mins = -1
        
    print(f"Calculated duration_mins: {duration_mins}")

if __name__ == "__main__":
    asyncio.run(main())
