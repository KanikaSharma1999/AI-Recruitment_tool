import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

async def check_feedback():
    client = AsyncIOMotorClient("mongodb+srv://sandhya:sandhya@cluster0.a2fjt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["job_resume_ranker"]
    candidates_col = db["candidates"]
    
    print("Checking last 5 candidates feedback...")
    async for c in candidates_col.find().sort("uploaded_at", -1).limit(5):
        print(f"Candidate: {c.get('name')}")
        feedback = c.get('feedback', '')
        print(f"Feedback Length: {len(feedback)}")
        print(f"Feedback Preview: {feedback[:200]}...")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_feedback())
