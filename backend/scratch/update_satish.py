import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager, candidates_col
from bson import ObjectId

async def run():
    print("Connecting to DB...")
    connected = await db_manager.connect()
    if not connected:
        print("Failed to connect.")
        return

    candidate_id = "6a0a9edb3bf4e3de6e87ded5" # Satish P
    
    interview_data = {
        "candidate_id": candidate_id,
        "job_id": "6a0a9ed53bf4e3de6e87ded0", # placeholder job ID
        "date": "2026-05-25",
        "time": "12:48",
        "mode": "online",
        "location": "",
        "notes": "Test interview",
        "duration": 30,
        "meeting_link": "https://meet.jit.si/interview-6a0a9edb3bf4e3de6e87ded5-test",
        "secure_token": "testtoken123",
        "status": "scheduled"
    }

    res = await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {
            "status": "interview_scheduled",
            "interview": interview_data
        }}
    )
    print("Update result:", res.modified_count)

if __name__ == "__main__":
    asyncio.run(run())
