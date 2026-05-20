import os
import sys
from pymongo import MongoClient
import traceback
from dotenv import load_dotenv

def test_connection():
    print("==================================================")
    print("[STANDALONE TEST] MongoDB Connectivity")
    
    # Load .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=env_path)
    
    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    
    if not uri:
        print("X ERROR: MONGO_URI not found in .env")
        print(f"   Checked path: {os.path.abspath(env_path)}")
        return

    # Masking for security
    masked_uri = "MISSING"
    if "@" in uri:
        try:
            prefix, rest = uri.split("://", 1)
            creds, host = rest.split("@", 1)
            masked_uri = f"{prefix}://****:****@{host}"
        except:
            masked_uri = "INVALID_FORMAT"
    else:
        masked_uri = uri
        
    print(f"Attempting connection to: {masked_uri}")
    
    try:
        # Use a short timeout for the test
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        print("Pinging...")
        client.admin.command('ping')
        print("SUCCESS: MongoDB is reachable and authenticated!")
        
        # Test database access
        db_name = os.getenv("DB_NAME", "ats_platform")
        db = client[db_name]
        collections = db.list_collection_names()
        print(f"Connected to DB: {db_name}")
        print(f"Collections found: {collections}")
        
    except Exception as e:
        print("\n" + "!" * 50)
        print("X CONNECTION FAILED")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print("-" * 30)
        print("Full Traceback:")
        traceback.print_exc()
        print("!" * 50 + "\n")
        
        print("TROUBLESHOOTING TIPS:")
        print("1. Check if your IP is whitelisted in Atlas (Network Access).")
        print("2. Verify username and password (they must be URL-encoded if they contain special characters).")
        print("3. Ensure the cluster is active and not paused.")
        print("4. Try a Standard URI (mongodb://) instead of SRV (mongodb+srv://) if DNS issues persist.")

if __name__ == "__main__":
    test_connection()
