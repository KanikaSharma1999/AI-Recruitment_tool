import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env")
load_dotenv(dotenv_path=env_path)
MONGO_URI = os.getenv("MONGO_URI")

async def main():
    if not MONGO_URI:
        print("MONGO_URI not found in env!")
        return
        
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["ats_platform"]
    users_col = db["users"]
    
    print("=== Registered Users ===")
    async for user in users_col.find():
        print(f"Email: {user.get('email')} | Name: {user.get('name')} | Role: {user.get('role')}")

if __name__ == "__main__":
    asyncio.run(main())
