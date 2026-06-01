import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager, candidates_col

async def run():
    print("Connecting to DB...")
    connected = await db_manager.connect()
    if not connected:
        print("Failed to connect. Error:", db_manager.last_error)
        return

    print("Scheduled Interviews:")
    cursor = candidates_col.find({"status": "interview_scheduled"})
    async for c in cursor:
        print(f"ID: {c['_id']}, Name: {c['name']}, Email: {c.get('email')}")
        interview = c.get("interview", {})
        print(f"  Date: {interview.get('date')}, Time: {interview.get('time')}")
        print(f"  Secure Token: {interview.get('secure_token')}")
        print(f"  Meeting Link: {interview.get('meeting_link')}")
        print("-" * 50)

    print("\nAll Candidates:")
    cursor2 = candidates_col.find().limit(10)
    async for c in cursor2:
        print(f"ID: {c['_id']}, Name: {c['name']}, Status: {c.get('status')}")

if __name__ == "__main__":
    asyncio.run(run())
