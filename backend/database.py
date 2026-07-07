import socket
import dns.resolver
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Force load .env and print status
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_loaded = load_dotenv(dotenv_path=env_path)

MONGO_URI = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", ""))
DB_NAME = os.getenv("DB_NAME", "ats_platform")

# print("==================================================")
# print("[DATABASE DEBUG] Environment Verification")
# print(f"   .env Path: {os.path.abspath(env_path)}")
# print(f"   .env Loaded: {env_loaded}")
# print(f"   MONGO_URI Exists: {bool(MONGO_URI)}")
# if MONGO_URI:
#     # Basic URI masking for logs
#     try:
#         prefix, rest = MONGO_URI.split("://", 1)
#         creds, host = rest.split("@", 1)
#         print(f"   URI Hostname: {host.split('/')[0]}")
#     except:
#         print(f"   URI Format: {MONGO_URI[:15]}...")
# print("==================================================")

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_connected = False
        self.last_error = None
        self.retry_count = 0
        self.max_retries_before_slowdown = 10
        self.base_delay = 5
        self._reconnect_task = None
        self._stop_reconnect = False

    def get_masked_uri(self):
        if not MONGO_URI:
            return "MISSING_URI"
        if "@" in MONGO_URI:
            try:
                prefix, rest = MONGO_URI.split("://", 1)
                creds, host = rest.split("@", 1)
                return f"{prefix}://****:****@{host}"
            except:
                return "mongodb://****:****@hidden"
        return MONGO_URI

    def verify_dns(self):
        """Perform DNS diagnostic on the MONGO_URI hostname."""
        try:
            if "://" not in MONGO_URI:
                return False, "Invalid URI format"
            
            rest = MONGO_URI.split("://", 1)[1]
            host_part = rest.split("@", 1)[1] if "@" in rest else rest
            hostname = host_part.split("/", 1)[0].split(":", 1)[0]
            
            # 1. Standard DNS Lookup
            try:
                socket.gethostbyname(hostname)
                dns_status = "OK"
            except socket.gaierror:
                dns_status = "FAILED"
            
            # 2. SRV Record Lookup (if srv uri)
            srv_status = "N/A"
            if "mongodb+srv" in MONGO_URI:
                try:
                    dns.resolver.resolve(f"_mongodb._tcp.{hostname}", 'SRV')
                    srv_status = "OK"
                except Exception:
                    srv_status = "FAILED"
            
            return True, {
                "hostname": hostname,
                "dns_lookup": dns_status,
                "srv_lookup": srv_status,
                "resolvable": dns_status == "OK" or srv_status == "OK"
            }
        except Exception as e:
            return False, str(e)

    async def connect(self) -> bool:
        """Attempt to connect and initialize collections/indexes."""
        try:
            if not MONGO_URI:
                 logger.error("[DatabaseManager] MONGO_URI IS EMPTY!")
                 self.last_error = "MONGO_URI is missing in .env"
                 return False

            if "cluster0.a2fjt.mongodb.net" in MONGO_URI:
                 logger.error("[DatabaseManager] OLD/INVALID HOSTNAME DETECTED (a2fjt)!")
                 logger.error("Please update your .env with the NEW URI (zl6ytc1).")
                 self.last_error = "Stale Atlas hostname detected"
                 return False

            if self.client is None:
                logger.info(f"[DatabaseManager] Creating AsyncIOMotorClient with URI: {self.get_masked_uri()}")
                self.client = AsyncIOMotorClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    retryWrites=True,
                    tlsAllowInvalidCertificates=True 
                )
            
            # Ping database
            logger.info("[DatabaseManager] Pinging MongoDB...")
            await self.client.admin.command('ping')
            
            self.db = self.client[DB_NAME]
            
            # Create indexes
            await self.db["users"].create_index([("email", ASCENDING)], unique=True)
            await self.db["candidates"].create_index([("job_id", ASCENDING)])
            await self.db["candidates"].create_index([("status", ASCENDING)])
            await self.db["candidates"].create_index([("pipeline_stage", ASCENDING)])
            await self.db["candidates"].create_index([("score", ASCENDING)])
            await self.db["jobs"].create_index([("created_at", ASCENDING)])
            
            self.is_connected = True
            self.last_error = None
            self.retry_count = 0
            logger.info("[DatabaseManager] Connected successfully to MongoDB Atlas!")
            
            # Run non-blocking database migrations
            asyncio.create_task(run_db_migrations())
            
            return True
            
        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            self.retry_count += 1
            
            print("\n" + "!" * 50)
            print(f"[DatabaseManager] CRITICAL CONNECTION ERROR (Attempt {self.retry_count})")
            print(f"Exception Type: {type(e).__name__}")
            print(f"Exception Message: {str(e)}")
            print("-" * 30)
            print("Full Traceback:")
            traceback.print_exc()
            print("!" * 50 + "\n")
            
            logger.error(f"[DatabaseManager] Connection failed: {self.last_error}")
            return False

    async def _reconnection_loop(self):
        """Background task to attempt reconnection with exponential backoff."""
        consecutive_failures = 0
        
        while not self._stop_reconnect:
            if not self.is_connected:
                # Calculate backoff: 5s -> 10s -> 30s -> 60s -> 300s (max)
                if consecutive_failures == 0: delay = 5
                elif consecutive_failures == 1: delay = 10
                elif consecutive_failures == 2: delay = 30
                elif consecutive_failures == 3: delay = 60
                else: delay = 300 # 5 minutes cooldown
                
                logger.info(f"[DatabaseManager] Retrying in {delay}s... (Failures: {consecutive_failures + 1})")
                await asyncio.sleep(delay)
                
                success = await self.connect()
                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            else:
                consecutive_failures = 0
                await asyncio.sleep(60)

    def start_background_reconnection(self):
        """Starts the background reconnect loop."""
        self._stop_reconnect = False
        if self._reconnect_task and not self._reconnect_task.done():
            return 
        self._reconnect_task = asyncio.create_task(self._reconnection_loop())

    def stop_background_reconnection(self):
        """Stops the background reconnect loop."""
        self._stop_reconnect = True
        if self._reconnect_task:
            self._reconnect_task.cancel()

    def get_status(self):
        return {
            "status": "connected" if self.is_connected else "offline",
            "database": DB_NAME,
            "last_error": self.last_error,
            "retry_count": self.retry_count,
            "uri_type": "srv" if "mongodb+srv" in MONGO_URI else "standard",
            "masked_uri": self.get_masked_uri()
        }

# Global DB Manager
db_manager = DatabaseManager()

class SafeCollection:
    """Proxy wrapper for MongoDB collections that handles offline state gracefully."""
    def __init__(self, name: str):
        self._name = name

    def _get_collection(self):
        if not db_manager.is_connected or db_manager.db is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection unavailable. Please verify Atlas cluster and .env configuration."
            )
        return db_manager.db[self._name]

    def __getattr__(self, item):
        col = self._get_collection()
        return getattr(col, item)

# Export SafeCollections
users_col = SafeCollection("users")
jobs_col = SafeCollection("jobs")
candidates_col = SafeCollection("candidates")
settings_col = SafeCollection("settings")
interview_sessions_col = SafeCollection("interview_sessions")
workspace_notes_col = SafeCollection("workspace_notes")
workspace_files_col = SafeCollection("workspace_files")

async def init_db():
    import asyncio
    masked = db_manager.get_masked_uri()
    logger.info(f"[DatabaseManager] Startup connection to: {masked}")
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[DatabaseManager] Connection attempt {attempt}/{max_retries}...")
            success = await db_manager.connect()
            if success:
                logger.info("[DatabaseManager] Connection established successfully on startup!")
                return True
        except Exception as e:
            logger.warning(f"[DatabaseManager] Attempt {attempt} failed: {e}")
        
        if attempt < max_retries:
            logger.info(f"[DatabaseManager] Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            
    logger.error("[DatabaseManager] All startup connection attempts failed. Proceeding in degraded mode.")
    return False

def get_db_status():
    return db_manager.get_status()

async def run_db_migrations():
    """
    Normalizes candidates by populating candidate.pipeline_stage based on candidate.status.
    Ensures that every existing candidate record has pipeline_stage set.
    """
    if not db_manager.is_connected or db_manager.db is None:
        return
    
    logger.info("[Migration] Running pipeline stage normalization...")
    legacy_map = {
        "pending": "applied",
        "applied": "applied",
        "screening": "screening",
        "shortlisted": "shortlisted",
        "interview_scheduled": "interview_scheduled",
        "interview_live": "interview_scheduled",
        "interview_missed": "interview_scheduled",
        "interviewed": "interview_completed",
        "interview_completed": "interview_completed",
        "selected": "offered",
        "offered": "offered",
        "hired": "hired",
        "rejected": "rejected",
        "on_hold": "screening"
    }
    
    col = db_manager.db["candidates"]
    updated_count = 0
    
    try:
        async for candidate in col.find({}):
            cid = candidate["_id"]
            status = candidate.get("status", "applied")
            pipeline_stage = candidate.get("pipeline_stage")
            
            # Determine canonical stage
            canonical_stage = legacy_map.get(status.lower().strip() if status else "", "applied")
            
            # If pipeline_stage is not set or differs from the canonical stage, update it
            if not pipeline_stage or pipeline_stage != canonical_stage or status != canonical_stage:
                await col.update_one(
                    {"_id": cid},
                    {"$set": {"pipeline_stage": canonical_stage, "status": canonical_stage}}
                )
                updated_count += 1
                
        logger.info(f"[Migration] Pipeline stage normalization completed. Updated {updated_count} candidates.")
    except Exception as e:
        logger.error(f"[Migration] Failed to run pipeline stage normalization: {e}")

    # 2. Candidate created_by migration
    try:
        jobs_col = db_manager.db["jobs"]
        candidates_col = db_manager.db["candidates"]
        
        job_map = {}
        async for job in jobs_col.find({}):
            job_id_str = str(job["_id"])
            created_by = job.get("created_by")
            if created_by:
                job_map[job_id_str] = created_by
                
        updated_candidates_count = 0
        async for candidate in candidates_col.find({"created_by": {"$exists": False}}):
            job_id = candidate.get("job_id")
            creator_email = job_map.get(str(job_id)) if job_id else None
            if not creator_email:
                creator_email = "sandhyagowda506@gmail.com" # Default fallback for legacy orphans
            
            await candidates_col.update_one(
                {"_id": candidate["_id"]},
                {"$set": {"created_by": creator_email}}
            )
            updated_candidates_count += 1
            
        logger.info(f"[Migration] Candidate created_by migration completed. Updated {updated_candidates_count} candidates.")
    except Exception as e:
        logger.error(f"[Migration] Failed to run candidate created_by migration: {e}")

