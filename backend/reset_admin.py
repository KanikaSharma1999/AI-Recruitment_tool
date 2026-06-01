import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ats_platform")

async def reset_admin():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_col = db["users"]
    
    email = "sandhyagowda506@gmail.com"
    password = "admin123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    res = await users_col.update_one(
        {"email": email},
        {"$set": {
            "password": hashed,
            "name": "Admin",
            "role": "admin"
        }},
        upsert=True
    )
    if res.upserted_id:
        print(f"SUCCESS: Created new admin user: {email} / {password}")
    else:
        print(f"SUCCESS: Reset password for existing admin: {email} / {password}")

if __name__ == "__main__":
    asyncio.run(reset_admin())
