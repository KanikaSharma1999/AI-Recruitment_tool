import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Load env
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ats_platform")

async def reset_db():
    if not MONGO_URI:
        print("MONGO_URI not found in .env!")
        return

    print(f"Connecting to MongoDB at {MONGO_URI[:30]}...")
    client = AsyncIOMotorClient(MONGO_URI, tlsAllowInvalidCertificates=True)
    db = client[DB_NAME]

    collections_to_drop = [
        "email_settings",
        "smtp_settings",
        "notification_settings",
        "recruiter_mail_config"
    ]

    print("\n--- Starting Email Config Reset ---")
    
    # 1. Drop specific collections if they exist
    existing_collections = await db.list_collection_names()
    print(f"Existing collections: {existing_collections}")

    for col in collections_to_drop:
        if col in existing_collections:
            print(f"Dropping collection: {col}")
            await db.drop_collection(col)
        else:
            print(f"Collection {col} does not exist (already clean)")

    # 2. Delete email config from 'settings' collection
    if "settings" in existing_collections:
        print("Cleaning 'settings' collection...")
        res = await db["settings"].delete_many({"type": "email_config"})
        print(f"Deleted {res.deleted_count} documents from 'settings' matching type='email_config'")
        
        # Double check if any others exist
        res_all = await db["settings"].delete_many({"type": {"$regex": ".*email.*|.*smtp.*|.*mail.*", "$options": "i"}})
        print(f"Deleted {res_all.deleted_count} other general email settings documents from 'settings'")

    # 3. Check if there are other collections
    print("\n--- Reset Completed Successfully ---")

if __name__ == "__main__":
    asyncio.run(reset_db())
