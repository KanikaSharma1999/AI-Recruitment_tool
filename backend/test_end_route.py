import asyncio
import os
import sys
from bson import ObjectId
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, candidates_col
from routes.interviews import end_interview, AnalyzeRequest

async def main():
    load_dotenv()
    await init_db()
    
    candidate = await candidates_col.find_one({"name": {"$regex": "Mrinali", "$options": "i"}})
    if not candidate:
        print("Candidate 'Mrinali' not found!")
        return
        
    candidate_id = str(candidate["_id"])
    print(f"Testing /end endpoint for candidate {candidate['name']} ({candidate_id})...")
    
    # Ensure candidate's interview is live so the route has a live session to end
    await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {
            "status": "interview_live",
            "interview.status": "live",
        }}
    )
    
    req = AnalyzeRequest(candidate_id=candidate_id)
    
    try:
        # We pass None for current_user since we bypass Depends
        response = await end_interview(req=req, current_user={})
        print("\nSUCCESS!")
        print("Endpoint Response:", response)
    except Exception as e:
        print("\nFAILED with exception:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
