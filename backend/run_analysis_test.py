import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import sys

load_dotenv(dotenv_path="../.env")
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from services.ai_analysis import generate_interview_feedback
from database import init_db

async def main():
    print("Connecting to database...")
    success = await init_db()
    if not success:
        print("Failed to connect to database.")
        return
        
    candidate_id = "6a0a9ed63bf4e3de6e87ded1"
    print(f"Running generate_interview_feedback for candidate {candidate_id}...")
    res = await generate_interview_feedback(candidate_id)
    print("Result metadata:")
    import pprint
    pprint.pprint(res.get("metadata"))

if __name__ == "__main__":
    asyncio.run(main())
