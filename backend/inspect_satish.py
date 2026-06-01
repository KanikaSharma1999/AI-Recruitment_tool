import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
MONGO_URI = os.getenv("MONGO_URI")

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["ats_platform"]
    candidates_col = db["candidates"]
    sessions_col = db["interview_sessions"]
    
    candidate = await candidates_col.find_one({"name": "Ohli"})
    if not candidate:
        print("Candidate Ohli not found.")
        return
        
    print("=== Candidate Doc ===")
    print(f"Name: {candidate.get('name')}")
    print(f"Status: {candidate.get('status')}")
    print("Interview dict:")
    import pprint
    pprint.pprint(candidate.get("interview"))
    
    print("\n=== AI Analysis dict ===")
    pprint.pprint(candidate.get("ai_analysis"))
    
    session = await sessions_col.find_one({"candidate_id": str(candidate["_id"])})
    if session:
        print("\n=== Session Doc ===")
        pprint.pprint(session)

if __name__ == "__main__":
    asyncio.run(main())
