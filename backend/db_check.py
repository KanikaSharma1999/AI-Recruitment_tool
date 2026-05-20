import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Explicitly load from ../.env if needed, but if CWD is backend, it should be fine if .env is in root
# Actually, database.py loads from .. so I will too.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ats_platform")

async def test_db():
    print(f"Connecting to: {MONGO_URI}")
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command('ping')
        print("SUCCESS: MongoDB Connection Successful!")
        db = client[DB_NAME]
        users = await db["users"].count_documents({})
        print(f"Users count: {users}")
        if users == 0:
            print("WARNING: No users found in database.")
        else:
            async for user in db["users"].find():
                print(f"User found: {user.get('email')}")
    except Exception as e:
        print(f"ERROR: Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
