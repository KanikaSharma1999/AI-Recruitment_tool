import asyncio
import os
import sys
from bson import ObjectId
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, candidates_col
from services.ai_analysis import generate_interview_feedback

async def main():
    load_dotenv()
    await init_db()
    
    candidate = await candidates_col.find_one({"name": {"$regex": "Mrinali", "$options": "i"}})
    if not candidate:
        print("Candidate 'Mrinali' not found in database!")
        return
        
    print(f"Found candidate: {candidate['name']} with ID: {candidate['_id']}")
    print(f"Current status: {candidate.get('status')}")
    print(f"Interview details: {candidate.get('interview')}")
    
    print("\nRunning generate_interview_feedback...")
    try:
        feedback = await generate_interview_feedback(str(candidate["_id"]))
        print("\nSUCCESS!")
        print("Feedback keys:", list(feedback.keys()))
        print("Verdict:", feedback.get("verdict"))
    except Exception as e:
        print("\nFAILED with exception:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
